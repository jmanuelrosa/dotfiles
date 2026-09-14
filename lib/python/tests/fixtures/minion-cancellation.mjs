import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { exerciseTools } from "./minion-tool-execution.mjs";

const bounds = { lifetimeMs: 6000, readyMs: 2000, settleMs: 1000, observeMs: 300, pollMs: 25, cleanupMs: 1000 };

const readRecord = path => existsSync(path) ? JSON.parse(readFileSync(path, "utf8")) : null;
const countWrites = path => existsSync(path) ? readFileSync(path, "utf8").trim().split("\n").filter(Boolean).length : 0;

async function waitUntil(predicate, timeoutMs) {
  const end = performance.now() + timeoutMs;
  while (!predicate() && performance.now() < end) await delay(bounds.pollMs);
  return predicate();
}

function processState(pid) {
  if (!pid) return { alive: false, group: null };
  const result = spawnSync("ps", ["-o", "pgid=,stat=", "-p", String(pid)], { encoding: "utf8", timeout: bounds.settleMs });
  if (result.error || result.stderr.trim()) return { alive: null, group: null, error: String(result.error ?? result.stderr) };
  if (!result.stdout.trim()) return { alive: false, group: null };
  const [group, state] = result.stdout.trim().split(/\s+/);
  return { alive: !state.startsWith("Z"), group: Number(group) };
}

export async function exerciseCancellation(session, cwd, mode) {
  const directory = join(cwd, mode);
  mkdirSync(directory);
  const childName = "minion-cancellation-child.mjs";
  copyFileSync(new URL(`./${childName}`, import.meta.url), join(cwd, childName));
  const deadline = Date.now() + bounds.lifetimeMs;
  const observation = {
    mode, bounds, deadline, ready: false, readyAt: null, groupVerified: false,
    abortRequestedAt: null, abortReturnedAt: null, abortReturned: false, abortError: null,
    promptSettledAt: null, promptSettled: false, promptError: null, results: [],
    writesAfterAbortReturn: null, aliveBeforeCleanup: null,
    deadlineReachedBeforeCleanup: false, cleanupRequestedAt: null, processInspectionError: null,
  };
  const state = pid => {
    if (pid && observation.processInspectionError) return { alive: null, group: null };
    const result = processState(pid);
    if (result.error) observation.processInspectionError = result.error;
    return result;
  };
  exerciseTools(session, [{
    name: "bash", input: { command: `node ${childName} launcher ${mode} ${deadline} ${bounds.pollMs}` },
  }]).then(result => {
    observation.results = result.results;
    observation.promptSettledAt = Date.now();
  }, error => {
    observation.promptError = String(error);
    observation.promptSettledAt = Date.now();
  });
  let writer;
  let launcher;
  const refreshChildren = () => {
    writer = readRecord(join(directory, "writer.ready.json"));
    launcher = readRecord(join(directory, "launcher.ready.json"));
    return writer && launcher;
  };
  try {
    await waitUntil(() => refreshChildren() || observation.promptSettledAt !== null, bounds.readyMs);
    observation.ready = Boolean(refreshChildren());
    if (observation.ready) {
      observation.readyAt = Math.max(writer.at, launcher.at);
      observation.writesAtReady = countWrites(join(directory, "writes.txt"));
      observation.writer = { ...writer, ...state(writer.pid) };
      observation.launcher = { ...launcher, ...state(launcher.pid) };
      const writerGroup = observation.writer.group;
      const launcherGroup = observation.launcher.group;
      observation.groupVerified = Boolean(writerGroup && launcherGroup && (mode === "same-group"
        ? writerGroup === launcherGroup : writerGroup !== launcherGroup && writerGroup === writer.pid));
      observation.abortRequestedAt = Date.now();
      let writesAtAbortReturn;
      session.abort().then(() => {
        observation.abortReturnedAt = Date.now();
        writesAtAbortReturn = countWrites(join(directory, "writes.txt"));
      }, error => { observation.abortError = String(error); });
      await waitUntil(() => observation.abortReturnedAt !== null || observation.abortError !== null, bounds.settleMs);
      await delay(bounds.observeMs);
      observation.abortReturned = observation.abortReturnedAt !== null;
      observation.writesAfterAbortReturn = observation.abortReturned
        ? countWrites(join(directory, "writes.txt")) - writesAtAbortReturn : null;
    }
    observation.promptSettled = observation.promptSettledAt !== null;
    observation.aliveBeforeCleanup = state(writer?.pid).alive;
    observation.launcherAliveBeforeCleanup = state(launcher?.pid).alive;
    observation.observationEndedAt = Date.now();
    observation.deadlineReachedBeforeCleanup = observation.observationEndedAt >= deadline;
  } finally {
    observation.cleanupRequestedAt = Date.now();
    // Only these two scratch processes watch this private stop-file; no PID or group killing.
    writeFileSync(join(directory, "cleanup"), "stop");
    const cleanupWait = Math.max(bounds.cleanupMs, deadline - Date.now() + bounds.cleanupMs);
    if (observation.processInspectionError) {
      await delay(cleanupWait);
    } else {
      await waitUntil(() => {
        refreshChildren();
        return state(writer?.pid).alive === false && state(launcher?.pid).alive === false;
      }, cleanupWait);
    }
    await waitUntil(() => observation.promptSettledAt !== null, bounds.cleanupMs);
    observation.aliveAfterCleanup = state(writer?.pid).alive;
    observation.launcherAliveAfterCleanup = state(launcher?.pid).alive;
    observation.writerExit = readRecord(join(directory, "writer.exit.json"));
    observation.launcherExit = readRecord(join(directory, "launcher.exit.json"));
    observation.cleanupFinishedAt = Date.now();
  }
  observation.classification = classifyCancellation(observation);
  return observation;
}

export function classifyCancellation(observation) {
  let outcome;
  if (!observation.ready) outcome = "not-exercised";
  else if (!observation.groupVerified) outcome = "group-unverified";
  else if (!observation.abortReturned) outcome = "abort-unsettled";
  else if (!observation.promptSettled) outcome = "prompt-unsettled";
  else if (observation.promptError) outcome = "prompt-rejected";
  else if (observation.writesAfterAbortReturn > 0) outcome = "writes-after-abort";
  else if (observation.aliveBeforeCleanup) outcome = "survived-abort";
  else if (observation.aliveBeforeCleanup !== false) outcome = "termination-unverified";
  else if (observation.deadlineReachedBeforeCleanup) outcome = "deadline-confounded";
  else outcome = "stopped-before-cleanup";
  return { outcome, containmentGate: "blocked" };
}
