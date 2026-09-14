import { existsSync, readFileSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

import type { ExtensionAPI, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";

const PACKAGE_NAME = "@earendil-works/pi-coding-agent";
const CONTROL_PATH = join(dirname(realpathSync(fileURLToPath(import.meta.url))), "..", "minion", "control.ts");

function resolveSdkPath(): string {
  try {
    return fileURLToPath(import.meta.resolve(PACKAGE_NAME));
  } catch {
    if (!process.argv[1]) throw new Error("Minion could not locate the Pi SDK");
    let directory = dirname(realpathSync(process.argv[1]));
    while (true) {
      const manifestPath = join(directory, "package.json");
      if (existsSync(manifestPath)) {
        const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as {
          name?: string;
          exports?: { "."?: { import?: string } };
        };
        const entry = manifest.exports?.["."]?.import;
        if (manifest.name === PACKAGE_NAME && entry) return realpathSync(join(directory, entry));
      }
      const parent = dirname(directory);
      if (parent === directory) throw new Error("Minion could not locate the Pi SDK");
      directory = parent;
    }
  }
}

function agentDir(): string {
  const configured = process.env.PI_CODING_AGENT_DIR;
  if (!configured) return join(homedir(), ".pi", "agent");
  if (configured === "~") return homedir();
  if (configured.startsWith("~/")) return join(homedir(), configured.slice(2));
  return resolve(configured);
}

const SDK_PATH = resolveSdkPath();
const DEFAULT_MAX_RUNTIME_MS = 60 * 60 * 1_000;
const DEFAULT_HEARTBEAT_MS = 1_000;
const DEFAULT_MAX_CYCLES = 20;
const DEFAULT_MAX_NO_PROGRESS_CYCLES = 2;

type Control = typeof import("../minion/control.ts");

function configuredPositiveInteger(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined) return fallback;
  const parsed = Number(raw);
  if (!Number.isInteger(parsed) || parsed <= 0) throw new Error(`${name} must be a positive integer`);
  return parsed;
}

async function loadControl(): Promise<Control> {
  if (!existsSync(CONTROL_PATH)) throw new Error(`Minion runtime is missing: ${CONTROL_PATH}`);
  return import(pathToFileURL(CONTROL_PATH).href) as Promise<Control>;
}

function splitAction(args: string): { action: string; remainder: string } {
  const trimmed = args.trim();
  const separator = trimmed.search(/\s/);
  if (separator < 0) return { action: trimmed, remainder: "" };
  return { action: trimmed.slice(0, separator), remainder: trimmed.slice(separator).trim() };
}

function startSummary(options: {
  cwd: string;
  branch: string;
  goal: string;
  model: string;
  authority: string;
  maxRuntimeMs: number;
  maxCycles: number;
}): string {
  return [
    `Repository: ${options.cwd}`,
    `Current branch: ${options.branch}`,
    `Goal, success conditions, and constraints: ${options.goal}`,
    `Model: ${options.model}`,
    `Limits: ${Math.floor(options.maxRuntimeMs / 1_000)}s elapsed, ${options.maxCycles} cycles`,
    `Publication: ${options.authority}`,
    "Warning: the Minion has the same machine authority and residual risk as a normal Pi session.",
    "Warning: do not edit this checkout while it runs.",
    "Cancellation is best effort.",
  ].join("\n");
}

async function start(args: string, ctx: ExtensionCommandContext): Promise<void> {
  const control = await loadControl();
  let parsed: ReturnType<Control["parseStartArgs"]>;
  try {
    parsed = control.parseStartArgs(args);
  } catch (error) {
    ctx.ui.notify(error instanceof Error ? error.message : String(error), "error");
    return;
  }
  const { goal, authority } = parsed;
  if (!goal) {
    ctx.ui.notify("Usage: /minion start [--publish] <goal>", "error");
    return;
  }
  if (!ctx.hasUI) {
    ctx.ui.notify("Minion start requires interactive confirmation", "error");
    return;
  }
  if (!ctx.isProjectTrusted()) {
    ctx.ui.notify("Minion requires a trusted project", "error");
    return;
  }
  if (!ctx.model) {
    ctx.ui.notify("Minion requires a selected model", "error");
    return;
  }
  const checkout = control.inspectCheckout(ctx.cwd);
  const maxRuntimeMs = configuredPositiveInteger("MINION_MAX_RUNTIME_MS", DEFAULT_MAX_RUNTIME_MS);
  const heartbeatMs = configuredPositiveInteger("MINION_HEARTBEAT_MS", DEFAULT_HEARTBEAT_MS);
  const maxCycles = configuredPositiveInteger("MINION_MAX_CYCLES", DEFAULT_MAX_CYCLES);
  const maxNoProgressCycles = configuredPositiveInteger(
    "MINION_MAX_NO_PROGRESS_CYCLES",
    DEFAULT_MAX_NO_PROGRESS_CYCLES,
  );
  const approved = await ctx.ui.confirm(
    "Start Minion?",
    startSummary({
      cwd: checkout.root,
      branch: checkout.branch,
      goal,
      model: `${ctx.model.provider}/${ctx.model.id}`,
      authority: control.formatDeliveryAuthority(authority),
      maxRuntimeMs,
      maxCycles,
    }),
  );
  if (!approved) return;
  const started = await control.startRunner({
    agentDir: agentDir(),
    cwd: ctx.cwd,
    goal,
    sdkPath: SDK_PATH,
    model: { provider: ctx.model.provider, id: ctx.model.id },
    thinkingLevel: ctx.thinkingLevel,
    maxRuntimeMs,
    heartbeatMs,
    maxCycles,
    maxNoProgressCycles,
    deliveryAuthority: authority,
    confirmedCheckout: checkout,
  });
  ctx.ui.notify(`Minion started: ${started.id}`, "info");
}

async function status(id: string, ctx: ExtensionCommandContext): Promise<void> {
  const control = await loadControl();
  const current = await control.readMissionStatus(agentDir(), id || undefined);
  const elapsedMs = Math.max(0, Date.now() - Date.parse(current.createdAt));
  ctx.ui.notify(
    [
      `Minion ${current.id}`,
      `state: ${current.state}`,
      `branch: ${current.branch}`,
      `publication: ${control.formatDeliveryAuthority(current.deliveryAuthority ?? control.NO_DELIVERY)}`,
      `delivery: ${current.deliveryState ?? "not-authorized"}`,
      `elapsed: ${Math.floor(elapsedMs / 1_000)}s`,
      `heartbeat: ${current.heartbeat}`,
      `cycle: ${current.cycle}`,
      `last activity: ${current.lastActivityAt}`,
      `pid: ${current.pid ?? "none"}`,
      `session: ${current.sessionPath ?? "starting"}`,
      `goal: ${current.goal}`,
      ...(current.commitSha ? [`commit: ${current.commitSha}`] : []),
      ...(current.pullRequestUrl ? [`PR: ${current.pullRequestUrl}`] : []),
      ...(current.result ? [`result: ${current.result}`] : []),
    ].join("\n"),
    "info",
  );
}

async function watch(id: string, ctx: ExtensionCommandContext): Promise<void> {
  const control = await loadControl();
  const log = await control.readMissionLog(agentDir(), id || undefined);
  ctx.ui.notify(log.trim() || "Minion log is empty", "info");
}

async function cancel(id: string, ctx: ExtensionCommandContext): Promise<void> {
  const control = await loadControl();
  const result = await control.cancelMission(agentDir(), id || undefined);
  ctx.ui.notify(result.message, result.outcome === "requested" ? "info" : "warning");
}

async function handle(args: string, ctx: ExtensionCommandContext): Promise<void> {
  const { action, remainder } = splitAction(args);
  try {
    if (action === "start") return await start(remainder, ctx);
    if (action === "status") return await status(remainder, ctx);
    if (action === "watch") return await watch(remainder, ctx);
    if (action === "cancel") return await cancel(remainder, ctx);
    ctx.ui.notify("Usage: /minion <start <goal>|status [id]|watch [id]|cancel [id]>", "error");
  } catch (error) {
    ctx.ui.notify(error instanceof Error ? error.message : String(error), "error");
  }
}

export default function registerMinion(pi: ExtensionAPI): void {
  if (process.env.MINION_ENABLE !== "1") return;
  pi.registerCommand("minion", {
    description: "Start and inspect a trusted unattended Pi session",
    handler: handle,
  });
}
