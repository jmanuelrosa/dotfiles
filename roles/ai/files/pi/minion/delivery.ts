import { execFileSync } from "node:child_process";

export type DeliveryState = "not-authorized" | "pending" | "committing" | "push-and-pr" | "published" | "failed";

export interface DeliveryAuthority {
  commit: boolean;
  push: boolean;
  openPr: boolean;
}

export const NO_DELIVERY: DeliveryAuthority = { commit: false, push: false, openPr: false };

export function normalizeDeliveryAuthority(authority: DeliveryAuthority): DeliveryAuthority {
  const approved = authority.commit && authority.push && authority.openPr;
  const denied = !authority.commit && !authority.push && !authority.openPr;
  if (!approved && !denied) {
    throw new Error("Minion publication authority must include commit, push, and PR creation together");
  }
  return { commit: approved, push: approved, openPr: approved };
}

export function deliveryApproved(authority: DeliveryAuthority): boolean {
  return normalizeDeliveryAuthority(authority).commit;
}

export function formatDeliveryAuthority(authority: DeliveryAuthority): string {
  const normalized = normalizeDeliveryAuthority(authority);
  return [
    `commit: ${normalized.commit ? "yes" : "no"}`,
    `push: ${normalized.push ? "yes" : "no"}`,
    `PR: ${normalized.openPr ? "yes" : "no"}`,
  ].join(", ");
}

export function parseStartArgs(remainder: string): { goal: string; authority: DeliveryAuthority } {
  const tokens = remainder.split(/\s+/).filter(Boolean);
  const authority: DeliveryAuthority = { commit: false, push: false, openPr: false };
  const goalParts: string[] = [];
  for (const token of tokens) {
    if (token === "--publish") {
      authority.commit = true;
      authority.push = true;
      authority.openPr = true;
    } else if (token.startsWith("--")) {
      throw new Error(`Unknown Minion start flag: ${token}`);
    } else {
      goalParts.push(token);
    }
  }
  return { goal: goalParts.join(" "), authority: normalizeDeliveryAuthority(authority) };
}

export function deliverySkillPrompts(authority: DeliveryAuthority): string[] {
  const normalized = normalizeDeliveryAuthority(authority);
  const prompts: string[] = [];
  if (normalized.commit) prompts.push("/skill:commit --minion-approved-at-launch");
  if (normalized.openPr) prompts.push("/skill:pr --minion-approved-at-launch");
  return prompts;
}

interface DeliverySession {
  prompt(text: string): Promise<void>;
  state: { messages: unknown[] };
}

export type DeliveryResult =
  | { ok: true; commitSha: string; pullRequestUrl: string }
  | { ok: false; blocker: string };

interface CheckoutState {
  branch: string;
  head: string;
  status: string;
}

function checkoutState(cwd: string): CheckoutState {
  const run = (args: string[]) =>
    execFileSync("git", ["-C", cwd, ...args], {
      encoding: "utf8",
      env: { ...process.env, GIT_OPTIONAL_LOCKS: "0" },
      stdio: ["ignore", "pipe", "pipe"],
    }).trim();
  return {
    branch: run(["branch", "--show-current"]),
    head: run(["rev-parse", "HEAD"]),
    status: run(["status", "--porcelain=v1", "--untracked-files=all"]),
  };
}

function messageText(message: unknown): string {
  const candidate = message as { role?: unknown; content?: unknown } | null;
  if (!candidate || candidate.role !== "assistant") return "";
  if (typeof candidate.content === "string") return candidate.content;
  if (!Array.isArray(candidate.content)) return "";
  return candidate.content
    .filter((block): block is { type: "text"; text: string } => {
      const value = block as { type?: unknown; text?: unknown } | null;
      return value?.type === "text" && typeof value.text === "string";
    })
    .map((block) => block.text)
    .join("\n");
}

function createdPullRequest(messages: unknown[]): string | undefined {
  const match = messages.map(messageText).join("\n").match(/(?:^|\n)Created:\s+(https:\/\/\S+)/);
  return match?.[1];
}

export async function runDelivery(
  session: DeliverySession,
  authority: DeliveryAuthority,
  cwd?: string,
  expectedBranch?: string,
  onState?: (state: DeliveryState) => Promise<void> | void,
): Promise<DeliveryResult> {
  const failed = async (blocker: string): Promise<DeliveryResult> => {
    await onState?.("failed");
    return { ok: false, blocker };
  };
  const prompts = deliverySkillPrompts(authority);
  let beforeCommit: CheckoutState | undefined;
  if (cwd) {
    try {
      beforeCommit = checkoutState(cwd);
    } catch (error) {
      return failed(`Delivery could not inspect the checkout: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  if (expectedBranch && beforeCommit?.branch !== expectedBranch) {
    return failed(`Delivery left the Minion mission branch ${expectedBranch}`);
  }
  let commitSha = beforeCommit?.head ?? "unverified";
  for (const prompt of prompts) {
    await onState?.(prompt.startsWith("/skill:commit ") ? "committing" : "push-and-pr");
    const messageOffset = session.state.messages.length;
    try {
      await session.prompt(prompt);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return failed(`Delivery prompt failed: ${message}`);
    }
    if (prompt.startsWith("/skill:commit ") && beforeCommit) {
      let afterCommit: CheckoutState;
      try {
        afterCommit = checkoutState(cwd!);
      } catch (error) {
        return failed(`Delivery could not verify the commit: ${error instanceof Error ? error.message : String(error)}`);
      }
      if (expectedBranch && afterCommit.branch !== expectedBranch) {
        return failed(`Delivery left the Minion mission branch ${expectedBranch}`);
      }
      if (afterCommit.status) return failed("The commit skill did not commit all eligible mission changes");
      if (beforeCommit.status && afterCommit.head === beforeCommit.head) {
        return failed("The commit skill did not create a commit for the mission changes");
      }
      commitSha = afterCommit.head;
    }
    if (prompt.startsWith("/skill:pr ")) {
      if (cwd && expectedBranch) {
        let afterPublication: CheckoutState;
        try {
          afterPublication = checkoutState(cwd);
        } catch (error) {
          return failed(`Delivery could not verify the PR: ${error instanceof Error ? error.message : String(error)}`);
        }
        if (afterPublication.branch !== expectedBranch) {
          return failed(`Delivery left the Minion mission branch ${expectedBranch}`);
        }
        if (afterPublication.status) return failed("The checkout changed during PR publication");
      }
      const pullRequestUrl = createdPullRequest(session.state.messages.slice(messageOffset));
      if (!pullRequestUrl) return failed("The PR skill did not report a created PR URL");
      await onState?.("published");
      return { ok: true, commitSha, pullRequestUrl };
    }
  }
  return failed("Approved Minion delivery did not include the PR skill");
}
