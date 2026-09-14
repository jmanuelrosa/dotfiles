import { spawn, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { closeSync, openSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  acquireCheckoutLease,
  admitCheckout,
  checkoutFingerprint,
  type CheckoutAdmission,
  type MissionBranch,
  prepareMissionBranch,
  releaseCheckoutLease,
  restoreMissionBranch,
} from "./checkout.ts";
import {
  type DeliveryAuthority,
  formatDeliveryAuthority,
  NO_DELIVERY,
  normalizeDeliveryAuthority,
  parseStartArgs,
} from "./delivery.ts";
import {
  createMission,
  missionPaths,
  readMissionLog,
  readMissionStatus,
  type RunnerStatus,
  writeMissionStatus,
} from "./state.ts";

export { formatDeliveryAuthority, NO_DELIVERY, parseStartArgs };

interface StartRunnerOptions {
  agentDir: string;
  cwd: string;
  goal: string;
  sdkPath: string;
  model: { provider: string; id: string };
  thinkingLevel?: string;
  maxRuntimeMs: number;
  heartbeatMs: number;
  maxCycles: number;
  maxNoProgressCycles: number;
  deliveryAuthority?: DeliveryAuthority;
  confirmedCheckout?: CheckoutAdmission;
}

interface CancelOperations {
  inspectCommand(pid: number): string | undefined;
  signalProcessGroup(pid: number): void;
}

const PROCESS_INSPECTION_TIMEOUT_MS = 2_000;

export interface StartedRunner {
  id: string;
  pid: number;
  missionDir: string;
  statusPath: string;
  logPath: string;
}

function positiveInteger(value: number, name: string): void {
  if (!Number.isInteger(value) || value <= 0) throw new Error(`${name} must be a positive integer`);
}

function inspectCommand(pid: number): string | undefined {
  const inspected = spawnSync("ps", ["-o", "command=", "-p", String(pid)], {
    encoding: "utf8",
    timeout: PROCESS_INSPECTION_TIMEOUT_MS,
  });
  if (inspected.error || inspected.status !== 0) return undefined;
  return inspected.stdout.trim() || undefined;
}

const DEFAULT_CANCEL_OPERATIONS: CancelOperations = {
  inspectCommand,
  signalProcessGroup: (pid) => process.kill(-pid, "SIGTERM"),
};

export function inspectCheckout(cwd: string) {
  return admitCheckout(cwd);
}

function runnerIdentityMatches(status: RunnerStatus, command: string): boolean {
  return command.includes(status.runnerPath) && command.includes(status.missionDir) && command.includes(status.token);
}

export async function startRunner(options: StartRunnerOptions): Promise<StartedRunner> {
  const goal = options.goal.trim();
  if (!goal) throw new Error("Minion goal must not be empty");
  positiveInteger(options.maxRuntimeMs, "maxRuntimeMs");
  positiveInteger(options.heartbeatMs, "heartbeatMs");
  positiveInteger(options.maxCycles, "maxCycles");
  positiveInteger(options.maxNoProgressCycles, "maxNoProgressCycles");

  const confirmed = options.confirmedCheckout;
  let checkout: CheckoutAdmission;
  try {
    checkout = admitCheckout(options.cwd);
  } catch (error) {
    if (confirmed) throw new Error("The checkout changed after Minion confirmation");
    throw error;
  }
  if (
    confirmed &&
    (checkout.root !== confirmed.root || checkout.branch !== confirmed.branch || checkout.fingerprint !== confirmed.fingerprint)
  ) {
    throw new Error("The checkout changed after Minion confirmation");
  }
  const deliveryAuthority = normalizeDeliveryAuthority(options.deliveryAuthority ?? NO_DELIVERY);
  const id = randomUUID();
  const token = randomUUID();
  const lease = await acquireCheckoutLease(options.agentDir, checkout.root, id, token);
  let missionBranch: MissionBranch | undefined;
  try {
    missionBranch = prepareMissionBranch(checkout.root, goal);
    const fingerprint = checkoutFingerprint(checkout.root);
    const runnerPath = realpathSync(join(dirname(fileURLToPath(import.meta.url)), "runner.ts"));
    const createdAt = new Date().toISOString();
    const paths = await createMission(options.agentDir, {
      id,
      cwd: checkout.root,
      branch: missionBranch.branch,
      checkoutFingerprint: fingerprint,
      leasePath: lease.path,
      goal,
      deliveryAuthority,
      missionBranchCreated: missionBranch.created,
      createdAt,
      token,
      runnerPath,
      sdkPath: options.sdkPath,
      model: options.model,
      thinkingLevel: options.thinkingLevel,
      maxRuntimeMs: options.maxRuntimeMs,
      heartbeatMs: options.heartbeatMs,
      maxCycles: options.maxCycles,
      maxNoProgressCycles: options.maxNoProgressCycles,
    });
    await writeMissionStatus(paths.statusPath, {
      id,
      state: "starting",
      cwd: checkout.root,
      branch: missionBranch.branch,
      goal,
      deliveryAuthority,
      deliveryState: deliveryAuthority.commit ? "pending" : "not-authorized",
      createdAt,
      lastActivityAt: createdAt,
      heartbeat: 0,
      cycle: 0,
      noProgressCycles: 0,
      pid: null,
      token,
      runnerPath,
      missionDir: paths.missionDir,
    });

    const log = openSync(paths.logPath, "a", 0o600);
    const child = spawn(
      process.execPath,
      [runnerPath, "--mission-dir", paths.missionDir, "--token", token],
      {
        cwd: checkout.root,
        detached: true,
        stdio: ["ignore", log, log],
      },
    );
    try {
      await new Promise<void>((resolve, reject) => {
        child.once("spawn", resolve);
        child.once("error", reject);
      });
    } catch (error) {
      await writeMissionStatus(paths.statusPath, {
        id,
        state: "crashed",
        cwd: checkout.root,
        branch: missionBranch.branch,
        goal,
        deliveryAuthority,
        deliveryState: deliveryAuthority.commit ? "pending" : "not-authorized",
        createdAt,
        lastActivityAt: new Date().toISOString(),
        heartbeat: 0,
        cycle: 0,
        noProgressCycles: 0,
        pid: child.pid ?? null,
        token,
        runnerPath,
        missionDir: paths.missionDir,
        result: error instanceof Error ? error.message : String(error),
      });
      throw error;
    } finally {
      closeSync(log);
    }
    if (child.pid === undefined) throw new Error("Minion runner started without a process id");
    child.unref();
    return { id, pid: child.pid, missionDir: paths.missionDir, statusPath: paths.statusPath, logPath: paths.logPath };
  } catch (error) {
    let failure = error;
    if (missionBranch) {
      try {
        restoreMissionBranch(checkout.root, missionBranch);
      } catch (restoreError) {
        const cause = error instanceof Error ? error.message : String(error);
        const restore = restoreError instanceof Error ? restoreError.message : String(restoreError);
        failure = new Error(`${cause}\nMinion could not restore the pre-launch branch: ${restore}`);
      }
    }
    await releaseCheckoutLease(lease).catch(() => {});
    throw failure;
  }
}

export async function cancelMission(
  agentDir: string,
  id?: string,
  operations: CancelOperations = DEFAULT_CANCEL_OPERATIONS,
): Promise<{ outcome: "requested" | "not-running" | "inspection-unavailable" | "identity-mismatch" | "signal-failed"; message: string }> {
  const status = await readMissionStatus(agentDir, id);
  if (status.pid === null || status.state !== "running") {
    return { outcome: "not-running", message: `Minion is ${status.state}` };
  }
  const command = operations.inspectCommand(status.pid);
  if (command === undefined) {
    return { outcome: "inspection-unavailable", message: "Could not verify the Minion runner process identity" };
  }
  if (!runnerIdentityMatches(status, command)) {
    return { outcome: "identity-mismatch", message: "The recorded PID no longer belongs to this Minion runner" };
  }
  try {
    operations.signalProcessGroup(status.pid);
  } catch (error) {
    return { outcome: "signal-failed", message: error instanceof Error ? error.message : String(error) };
  }
  return { outcome: "requested", message: "Cancellation requested for the Minion runner process group" };
}

export { readMissionLog, readMissionStatus };
