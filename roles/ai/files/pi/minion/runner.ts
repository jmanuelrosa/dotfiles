import { existsSync } from "node:fs";
import { join } from "node:path";

import { releaseCheckoutLease, releaseCheckoutLeaseSync } from "./checkout.ts";
import type { DeliveryState } from "./delivery.ts";
import { MissionBlockedError, runSdkMission, type SdkMissionResult } from "./runtime.ts";
import { readLaunch, type RunnerState, type RunnerStatus, writeMissionStatus, writeMissionStatusSync } from "./state.ts";

const SDK_ABORT_GRACE_MS = 250;

interface RunnerArguments {
  missionDir: string;
  token: string;
}

function parseArguments(argv: string[]): RunnerArguments {
  const missionIndex = argv.indexOf("--mission-dir");
  const tokenIndex = argv.indexOf("--token");
  const missionDir = missionIndex >= 0 ? argv[missionIndex + 1] : undefined;
  const token = tokenIndex >= 0 ? argv[tokenIndex + 1] : undefined;
  if (!missionDir || !token) throw new Error("Usage: runner.ts --mission-dir <path> --token <token>");
  return { missionDir, token };
}

function positiveInteger(value: string | undefined, name: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) throw new Error(`${name} must be a positive integer`);
  return parsed;
}

function resultMessage(result: SdkMissionResult): string {
  if (result.state === "done") {
    return [
      result.report.summary,
      `Changed areas: ${result.report.changedAreas.join(", ") || "none"}`,
      `Checks: ${result.report.checks.join(", ") || "none"}`,
      ...(result.commitSha ? [`Commit: ${result.commitSha}`] : []),
      ...(result.pullRequestUrl ? [`PR: ${result.pullRequestUrl}`] : []),
    ].join("\n");
  }
  if (result.state === "blocked") return `${result.report.summary}\nBlocker: ${result.report.blocker}`;
  return result.result;
}

async function run(): Promise<void> {
  const { missionDir, token } = parseArguments(process.argv.slice(2));
  const launchPath = join(missionDir, "launch.json");
  const statusPath = join(missionDir, "status.json");
  if (!existsSync(launchPath)) throw new Error(`Missing Minion launch record: ${launchPath}`);
  const launch = await readLaunch(launchPath);
  if (launch.token !== token) throw new Error("Minion runner token does not match its launch record");
  const maxRuntimeMs = positiveInteger(String(launch.maxRuntimeMs), "maxRuntimeMs");
  const heartbeatMs = positiveInteger(String(launch.heartbeatMs), "heartbeatMs");
  const maxCycles = positiveInteger(String(launch.maxCycles), "maxCycles");
  const maxNoProgressCycles = positiveInteger(String(launch.maxNoProgressCycles), "maxNoProgressCycles");
  const started = Date.now();
  const deadlineAt = started + maxRuntimeMs;
  const abortController = new AbortController();
  let heartbeat = 0;
  let cycle = 0;
  let noProgressCycles = 0;
  let sessionPath: string | undefined;
  let deliveryState: DeliveryState = launch.deliveryAuthority?.commit ? "pending" : "not-authorized";
  let commitSha: string | undefined;
  let pullRequestUrl: string | undefined;
  let finished = false;
  let requestedStop: { state: "cancelled" | "limit-reached"; result: string } | undefined;
  let pendingWrite = Promise.resolve();

  const status = (state: RunnerState, result?: string): RunnerStatus => ({
    id: launch.id,
    state,
    cwd: launch.cwd,
    branch: launch.branch,
    goal: launch.goal,
    deliveryAuthority: launch.deliveryAuthority ?? { commit: false, push: false, openPr: false },
    deliveryState,
    createdAt: launch.createdAt,
    lastActivityAt: new Date().toISOString(),
    heartbeat,
    cycle,
    noProgressCycles,
    pid: process.pid,
    token: launch.token,
    runnerPath: launch.runnerPath,
    missionDir,
    ...(sessionPath ? { sessionPath } : {}),
    ...(commitSha ? { commitSha } : {}),
    ...(pullRequestUrl ? { pullRequestUrl } : {}),
    ...(result ? { result } : {}),
  });

  const writeStatus = (value: RunnerStatus) => {
    pendingWrite = pendingWrite.then(() => writeMissionStatus(statusPath, value));
    return pendingWrite;
  };

  let heartbeatTimer: ReturnType<typeof setInterval>;
  let deadlineTimer: ReturnType<typeof setTimeout>;

  const requestStop = (state: "cancelled" | "limit-reached", result: string) => {
    if (finished || requestedStop) return;
    requestedStop = { state, result };
    abortController.abort();
  };

  const finish = async (state: RunnerState, result: string) => {
    if (finished) return;
    finished = true;
    let finalState = state;
    let finalResult = result;
    await pendingWrite;
    try {
      await releaseCheckoutLease({ path: launch.leasePath, token: launch.token });
    } catch (error) {
      finalState = "blocked";
      finalResult = `Checkout lease could not be released: ${error instanceof Error ? error.message : String(error)}`;
    }
    await writeMissionStatus(statusPath, status(finalState, finalResult));
    clearInterval(heartbeatTimer);
    clearTimeout(deadlineTimer);
    console.log(`runner stopped: ${finalState}`);
  };

  const terminate = (state: "cancelled" | "limit-reached", result: string) => {
    requestStop(state, result);
    finished = true;
    let finalState: RunnerState = requestedStop?.state ?? state;
    let finalResult = requestedStop?.result ?? result;
    try {
      releaseCheckoutLeaseSync({ path: launch.leasePath, token: launch.token });
    } catch (error) {
      finalState = "blocked";
      finalResult = `Checkout lease could not be released: ${error instanceof Error ? error.message : String(error)}`;
    }
    writeMissionStatusSync(statusPath, status(finalState, finalResult));
    process.exit(0);
  };
  const cancel = () => terminate("cancelled", "Cancellation requested");
  const expire = () => {
    const result = `Runtime limit reached after ${Date.now() - started} ms`;
    requestStop("limit-reached", result);
    try {
      process.kill(-process.pid, "SIGTERM");
    } catch {
      terminate("limit-reached", result);
    }
  };
  process.once("SIGTERM", cancel);
  process.once("SIGINT", cancel);

  heartbeatTimer = setInterval(() => {
    if (finished) return;
    heartbeat += 1;
    void writeStatus(status("running"));
  }, heartbeatMs);
  deadlineTimer = setTimeout(expire, maxRuntimeMs + SDK_ABORT_GRACE_MS);

  await writeStatus(status("running"));
  console.log("runner started");

  try {
    const result = await runSdkMission({
      sdkPath: launch.sdkPath,
      agentDir: join(missionDir, "..", "..", ".."),
      missionDir,
      cwd: launch.cwd,
      branch: launch.branch,
      goal: launch.goal,
      model: launch.model,
      thinkingLevel: launch.thinkingLevel,
      maxCycles,
      maxNoProgressCycles,
      deadlineAt,
      checkoutFingerprint: launch.checkoutFingerprint,
      deliveryAuthority: launch.deliveryAuthority,
      signal: abortController.signal,
      log: (message) => console.log(message),
      onCycle: (currentCycle, currentNoProgressCycles, currentSessionPath) => {
        cycle = currentCycle;
        noProgressCycles = currentNoProgressCycles;
        sessionPath = currentSessionPath;
        return writeStatus(status("running"));
      },
      onDeliveryState: (currentDeliveryState) => {
        deliveryState = currentDeliveryState;
        return writeStatus(status("running"));
      },
    });
    sessionPath = result.sessionFile;
    commitSha = result.commitSha;
    pullRequestUrl = result.pullRequestUrl;
    if (requestedStop) {
      await finish(requestedStop.state, requestedStop.result);
    } else {
      await finish(result.state === "aborted" ? "cancelled" : result.state, resultMessage(result));
    }
  } catch (error) {
    if (requestedStop) {
      await finish(requestedStop.state, requestedStop.result);
      return;
    }
    if (error instanceof MissionBlockedError) {
      await finish("blocked", error.message);
      return;
    }
    const message = error instanceof Error ? error.stack ?? error.message : String(error);
    console.error(message);
    await finish("crashed", message);
  }
}

run().catch((error) => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exitCode = 1;
});
