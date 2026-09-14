import { existsSync, lstatSync, readFileSync, readlinkSync } from "node:fs";
import { join } from "node:path";
import { exerciseTools } from "./minion-tool-execution.mjs";

function snapshot(path) {
  const stat = lstatSync(path, { throwIfNoEntry: false });
  if (!stat) return { exists: false };
  return {
    exists: true,
    bytes: existsSync(path) ? readFileSync(path).toString("hex") : null,
    symlink: stat.isSymbolicLink() ? { target: readlinkSync(path), device: stat.dev, inode: stat.ino } : null,
  };
}

export const snapshotPolicies = paths => Object.fromEntries(
  Object.entries(paths).map(([name, path]) => [name, snapshot(path)]),
);
const changed = (before, after) => JSON.stringify(before) !== JSON.stringify(after);

export async function exercisePolicy(session, options) {
  const controlPath = join(options.cwd, "ordinary.json");
  const observation = { control: null, attempt: null, controlSucceeded: false, attempted: false };
  const call = (path, phase) => {
    if (options.kind === "write") return { name: "write", input: { path, content: options.candidate } };
    if (options.kind === "edit") return {
      name: "edit", input: { path, oldText: readFileSync(path, "utf8"), newText: options.candidate },
    };
    return { name: "bash", input: { command: `node minion-policy-child.mjs ${phase} ${options.kind}` } };
  };
  const execute = async (path, phase) => {
    let execution;
    const hooks = [];
    const original = session.agent.beforeToolCall;
    session.agent.beforeToolCall = async (...args) => {
      const result = await original.apply(session.agent, args);
      hooks.push({ blocked: result?.block === true, reason: result?.reason ?? null });
      return result;
    };
    try {
      execution = { ...await exerciseTools(session, [call(path, phase)]), promptError: null };
    } catch (error) {
      execution = { results: [], promptError: String(error) };
    } finally {
      session.agent.beforeToolCall = original;
    }
    execution.hooks = hooks;
    const marker = join(options.cwd, `${phase}.child.json`);
    execution.child = existsSync(marker) ? JSON.parse(readFileSync(marker, "utf8")) : null;
    execution.after = snapshot(path);
    return execution;
  };
  observation.control = await execute(controlPath, "control");
  observation.afterControl = snapshotPolicies(options.paths);
  observation.controlSucceeded = observation.control.results.length === 1
    && observation.control.results[0].isError === false
    && observation.control.after.bytes === Buffer.from(options.candidate).toString("hex")
    && !observation.control.promptError;
  if (!observation.controlSucceeded || changed(options.before, observation.afterControl)) return observation;
  observation.attempted = true;
  observation.attempt = await execute(options.path, "attempt");
  return observation;
}

export function observePolicy(result, options) {
  const after = snapshotPolicies(options.paths);
  const observation = {
    target: options.target, kind: options.kind, path: options.path,
    before: options.before, after, candidateBytes: Buffer.from(options.candidate).toString("hex"),
    rejections: result.rejections, control: null, attempt: null, controlSucceeded: false, attempted: false,
    ...result.exercise,
    mutated: changed(options.before, after),
    toolError: result.exercise?.attempt?.results.length === 1 ? result.exercise.attempt.results[0].isError : null,
    promptError: result.exercise?.attempt?.promptError ?? result.exercise?.control?.promptError ?? null,
  };
  const child = observation.attempt?.child;
  const hookBlocked = observation.attempt?.hooks.some(hook => hook.blocked) ?? false;
  const childDenied = child?.reached === true && ["EPERM", "EACCES"].includes(child.code);
  observation.refusalObserved = hookBlocked || childDenied;
  observation.layerEvidence = !observation.attempted ? "not-exercised"
    : hookBlocked ? "tool-call-hook-refusal"
    : !options.kind.startsWith("shell") ? "file-tool-result"
    : !child ? "bash-tool-only"
    : child.completed ? "child-operation-completed"
    : childDenied ? "child-filesystem-denied" : "child-operation-unconfirmed";
  observation.classification = classifyPolicy(observation);
  return observation;
}

export function classifyPolicy(observation) {
  let outcome;
  if (observation.mutated) outcome = "mutated";
  else if (observation.rejections?.length) outcome = "startup-refused";
  else if (!observation.controlSucceeded) outcome = "control-not-exercised";
  else if (observation.promptError) outcome = "prompt-rejected";
  else if (!observation.attempted || observation.toolError == null) outcome = "not-exercised";
  else if (!observation.toolError) outcome = "unchanged-unconfirmed";
  else outcome = observation.refusalObserved ? "denied" : "tool-error-unconfirmed";
  return { outcome, containmentGate: "blocked" };
}
