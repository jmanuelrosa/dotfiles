import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { checkoutFingerprint } from "./checkout.ts";
import {
  type DeliveryAuthority,
  type DeliveryState,
  NO_DELIVERY,
  deliveryApproved,
  formatDeliveryAuthority,
  runDelivery,
} from "./delivery.ts";
import { createMinionReporter, runGoalLoop, type GoalLoopResult } from "./goal-loop.ts";

interface SdkMissionOptions {
  sdkPath: string;
  agentDir: string;
  missionDir: string;
  cwd: string;
  branch: string;
  goal: string;
  model: { provider: string; id: string };
  thinkingLevel?: string;
  maxCycles: number;
  maxNoProgressCycles: number;
  deadlineAt: number;
  checkoutFingerprint?: string;
  deliveryAuthority?: DeliveryAuthority;
  signal?: AbortSignal;
  log?: (message: string) => void;
  onCycle?: (cycle: number, noProgressCycles: number, sessionFile: string | undefined) => Promise<void> | void;
  onDeliveryState?: (state: DeliveryState) => Promise<void> | void;
}

export type SdkMissionResult = GoalLoopResult & {
  sessionFile: string | undefined;
  commitSha?: string;
  pullRequestUrl?: string;
};

export class MissionBlockedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MissionBlockedError";
  }
}

function startupFailures(services: any): string[] {
  const failures = services.diagnostics
    .filter((diagnostic: { type: string }) => diagnostic.type === "error")
    .map((diagnostic: { message: string }) => diagnostic.message);
  failures.push(
    ...services.resourceLoader
      .getExtensions()
      .errors.map(({ path, error }: { path: string; error: string }) => `${path}: ${error}`),
  );
  return failures;
}

export async function runSdkMission(options: SdkMissionOptions): Promise<SdkMissionResult> {
  const sdk = await import(pathToFileURL(options.sdkPath).href);
  const settingsManager = sdk.SettingsManager.create(options.cwd, options.agentDir, { projectTrusted: true });
  sdk.initTheme(settingsManager.getTheme(), false);
  const services = await sdk.createAgentSessionServices({
    cwd: options.cwd,
    agentDir: options.agentDir,
    settingsManager,
    modelRuntimeSignal: options.signal,
  });
  const failures = startupFailures(services);
  if (failures.length) throw new MissionBlockedError(failures.join("\n"));

  const model = services.modelRuntime.getModel(options.model.provider, options.model.id);
  if (!model) throw new MissionBlockedError(`Selected model not found: ${options.model.provider}/${options.model.id}`);

  const reporter = createMinionReporter();
  const sessionManager = sdk.SessionManager.create(options.cwd, join(options.missionDir, "session"));
  const { session, modelFallbackMessage } = await sdk.createAgentSessionFromServices({
    services,
    sessionManager,
    model,
    thinkingLevel: options.thinkingLevel,
    customTools: [reporter.tool],
  });
  if (modelFallbackMessage) {
    session.dispose();
    throw new MissionBlockedError(modelFallbackMessage);
  }
  if (!session.getActiveToolNames().includes("minion_report")) {
    session.dispose();
    throw new MissionBlockedError("The minion_report tool is not active");
  }

  const log = options.log ?? (() => {});
  const startupErrors: string[] = [];
  const ui = session.extensionRunner.createContext().ui;
  const originalNotify = ui.notify;
  ui.notify = (message: string, type = "info") => {
    log(`[${type}] ${message}`);
    if (type === "error" || message.startsWith("Sandbox disabled")) startupErrors.push(message);
  };
  let expectedCheckoutFingerprint = options.checkoutFingerprint;
  let checkoutObservationError: string | undefined;
  const observeWorkerCheckout = () => {
    if (!expectedCheckoutFingerprint) return;
    try {
      expectedCheckoutFingerprint = checkoutFingerprint(options.cwd);
      checkoutObservationError = undefined;
    } catch (error) {
      checkoutObservationError = error instanceof Error ? error.message : String(error);
    }
  };
  const checkCheckout = () => {
    if (!expectedCheckoutFingerprint) return undefined;
    if (checkoutObservationError) return `Checkout state could not be observed: ${checkoutObservationError}`;
    try {
      return checkoutFingerprint(options.cwd) === expectedCheckoutFingerprint
        ? undefined
        : "Checkout changed outside Minion tool execution";
    } catch (error) {
      return `Checkout state could not be observed: ${error instanceof Error ? error.message : String(error)}`;
    }
  };
  const unsubscribe = session.subscribe((event: any) => {
    if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
      log(event.assistantMessageEvent.delta);
    } else if (event.type === "tool_execution_start") {
      log(`tool started: ${event.toolName}`);
    } else if (event.type === "tool_execution_end") {
      log(`tool ${event.isError ? "failed" : "finished"}: ${event.toolName}`);
      if (event.toolName !== "minion_report") observeWorkerCheckout();
    }
  });

  let extensionsBound = false;
  try {
    await session.bindExtensions({
      mode: "print",
      onError: ({ error }: { error: string }) => startupErrors.push(error),
    });
    extensionsBound = true;
    if (startupErrors.length) throw new MissionBlockedError(startupErrors.join("\n"));
    if (session.model?.provider !== options.model.provider || session.model?.id !== options.model.id) {
      throw new MissionBlockedError("Selected model changed during startup");
    }

    const authority = options.deliveryAuthority ?? NO_DELIVERY;
    const result = await runGoalLoop({
      goal: options.goal,
      deliverySummary: formatDeliveryAuthority(authority),
      maxCycles: options.maxCycles,
      maxNoProgressCycles: options.maxNoProgressCycles,
      deadlineAt: options.deadlineAt,
      reporter,
      session,
      signal: options.signal,
      checkCheckout,
      onCycle: (cycle, noProgressCycles) => options.onCycle?.(cycle, noProgressCycles, session.sessionFile),
    });
    let commitSha: string | undefined;
    let pullRequestUrl: string | undefined;
    if (result.state === "done" && deliveryApproved(authority)) {
      const deliveryErrors: string[] = [];
      const notifyDuringDelivery = (message: string, type = "info") => {
        log(`[${type}] ${message}`);
        if (type === "error") deliveryErrors.push(message);
      };
      ui.notify = notifyDuringDelivery;
      const delivery = await runDelivery(
        session,
        authority,
        options.cwd,
        options.branch,
        options.onDeliveryState,
      );
      ui.notify = originalNotify;
      if (!delivery.ok || deliveryErrors.length) {
        if (delivery.ok) await options.onDeliveryState?.("failed");
        const blocker = delivery.ok ? deliveryErrors.join("\n") : delivery.blocker;
        return {
          state: "blocked",
          cycles: result.cycles,
          noProgressCycles: result.noProgressCycles,
          report: {
            outcome: "blocked",
            summary: "Implementation finished but publication failed",
            blocker,
          },
          sessionFile: session.sessionFile,
        };
      }
      commitSha = delivery.commitSha;
      pullRequestUrl = delivery.pullRequestUrl;
    }
    return {
      ...result,
      sessionFile: session.sessionFile,
      ...(commitSha ? { commitSha } : {}),
      ...(pullRequestUrl ? { pullRequestUrl } : {}),
    };
  } finally {
    unsubscribe();
    ui.notify = originalNotify;
    try {
      if (extensionsBound) await session.extensionRunner.emit({ type: "session_shutdown", reason: "quit" });
    } finally {
      session.dispose();
    }
  }
}
