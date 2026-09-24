import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync, lstatSync, readFileSync, readlinkSync, realpathSync, rmdirSync, unlinkSync } from "node:fs";
import { mkdir, readFile, rmdir, unlink, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";

const GIT_OPERATIONS = ["MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG", "rebase-apply", "rebase-merge", "sequencer"];
const CONVENTIONAL_BRANCH =
  /^(feature|fix|chore|docs|refactor|test|perf|ci|build|style|revert)\/([A-Z]+-[0-9]+-|gh-[0-9]+-)?[a-z0-9][a-z0-9-]*$/;

export interface MissionBranch {
  branch: string;
  previousBranch: string;
  created: boolean;
}

export interface CheckoutAdmission {
  root: string;
  branch: string;
  fingerprint: string;
}

export interface CheckoutLease {
  path: string;
  token: string;
}

function git(cwd: string, args: string[]): string {
  try {
    return execFileSync("git", ["-C", cwd, ...args], {
      encoding: "utf8",
      env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Minion could not inspect the Git checkout: ${message}`);
  }
}

function operationPath(root: string, operation: string): string {
  return resolve(root, git(root, ["rev-parse", "--git-path", operation]).trim());
}

function untrackedContent(root: string, status: string): string[] {
  const values: string[] = [];
  for (const entry of status.split("\0")) {
    if (!entry.startsWith("?? ")) continue;
    const path = resolve(root, entry.slice(3));
    const stat = lstatSync(path);
    values.push(stat.isSymbolicLink() ? `link:${readlinkSync(path)}` : `file:${readFileSync(path).toString("base64")}`);
  }
  return values;
}

export function checkoutFingerprint(root: string): string {
  const status = git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]);
  const parts = [
    git(root, ["branch", "--show-current"]),
    git(root, ["rev-parse", "HEAD"]),
    status,
    git(root, ["diff", "--no-ext-diff", "--binary", "HEAD", "--"]),
    git(root, ["diff", "--cached", "--no-ext-diff", "--binary", "HEAD", "--"]),
    ...untrackedContent(root, status),
  ];
  return createHash("sha256").update(parts.join("\0")).digest("hex");
}

export async function acquireCheckoutLease(agentDir: string, root: string, missionId: string, token: string): Promise<CheckoutLease> {
  const leases = join(agentDir, "minion", "leases");
  const path = join(leases, createHash("sha256").update(root).digest("hex"));
  await mkdir(leases, { recursive: true, mode: 0o700 });
  try {
    await mkdir(path, { mode: 0o700 });
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "EEXIST") {
      throw new Error(`A Minion is already active for ${root}`);
    }
    throw error;
  }
  try {
    await writeFile(join(path, "owner.json"), `${JSON.stringify({ missionId, root, token }, null, 2)}\n`, { flag: "wx", mode: 0o600 });
  } catch (error) {
    await rmdir(path).catch(() => {});
    throw error;
  }
  return { path, token };
}

export async function releaseCheckoutLease(lease: CheckoutLease): Promise<void> {
  const ownerPath = join(lease.path, "owner.json");
  let ownerText: string;
  try {
    ownerText = await readFile(ownerPath, "utf8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT" && !existsSync(lease.path)) return;
    throw error;
  }
  const owner = JSON.parse(ownerText) as { token: string };
  if (owner.token !== lease.token) return;
  try {
    await unlink(ownerPath);
    await rmdir(lease.path);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT" && !existsSync(lease.path)) return;
    throw error;
  }
}

export function releaseCheckoutLeaseSync(lease: CheckoutLease): void {
  const ownerPath = join(lease.path, "owner.json");
  if (!existsSync(ownerPath) && !existsSync(lease.path)) return;
  const owner = JSON.parse(readFileSync(ownerPath, "utf8")) as { token: string };
  if (owner.token !== lease.token) return;
  unlinkSync(ownerPath);
  rmdirSync(lease.path);
}

function defaultBranch(root: string): string {
  for (const candidate of ["main", "master"]) {
    try {
      git(root, ["rev-parse", "--verify", candidate]);
      return candidate;
    } catch {}
  }
  return git(root, ["branch", "--show-current"]).trim() || "main";
}

function branchExists(root: string, branch: string): boolean {
  try {
    git(root, ["rev-parse", "--verify", branch]);
    return true;
  } catch {
    return false;
  }
}

export function missionBranchSlug(goal: string): string {
  const slug = goal
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
  return slug || "mission";
}

export function prepareMissionBranch(root: string, goal: string): MissionBranch {
  const current = git(root, ["branch", "--show-current"]).trim();
  const base = defaultBranch(root);
  if (current && current !== base && CONVENTIONAL_BRANCH.test(current)) {
    return { branch: current, previousBranch: current, created: false };
  }
  if (current && current !== base && !CONVENTIONAL_BRANCH.test(current)) {
    throw new Error(`Minion refuses a nonstandard branch: ${current}`);
  }
  const branch = `feature/minion-${missionBranchSlug(goal)}`;
  if (branchExists(root, branch)) {
    const branchHead = git(root, ["rev-parse", branch]).trim();
    const currentHead = git(root, ["rev-parse", "HEAD"]).trim();
    if (branchHead !== currentHead) {
      throw new Error(`Mission branch ${branch} already exists with different history`);
    }
    git(root, ["switch", branch]);
    return { branch, previousBranch: current, created: false };
  }
  git(root, ["switch", "-c", branch]);
  return { branch, previousBranch: current, created: true };
}

export function restoreMissionBranch(root: string, mission: MissionBranch): void {
  if (mission.branch === mission.previousBranch) return;
  git(root, ["switch", mission.previousBranch]);
  if (mission.created) git(root, ["branch", "-d", mission.branch]);
}

export function admitCheckout(cwd: string): CheckoutAdmission {
  const root = realpathSync(git(cwd, ["rev-parse", "--show-toplevel"]).trim());
  const status = git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]);
  if (status) throw new Error("Minion requires a clean checkout");
  for (const operation of GIT_OPERATIONS) {
    if (existsSync(operationPath(root, operation))) {
      throw new Error(`Minion refuses an unresolved Git operation: ${operation}`);
    }
  }
  return {
    root,
    branch: git(root, ["branch", "--show-current"]).trim(),
    fingerprint: checkoutFingerprint(root),
  };
}
