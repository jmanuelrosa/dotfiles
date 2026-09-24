import { existsSync, readFileSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";

interface ProbeOptions {
  piExecutable: string;
  cwd: string;
  agentDir: string;
  extensionPaths: string[];
  model: { provider: string; id: string };
  calls: Array<{ name: string; input: Record<string, unknown> }>;
}

interface ProviderPath {
  provider: string;
  api: string;
  registeredConfig: boolean;
  registeredNative: boolean;
}

interface ProviderPathClassification {
  outcome: "pi-core-provider" | "known-host-tools" | "extension-config-unverified" | "extension-native-unverified";
  providerPathGate: "eligible" | "blocked";
  containmentGate: "blocked";
}

interface ProviderPathInspector {
  getRegisteredProviderConfig(provider: string): unknown;
  getRegisteredNativeProvider(provider: string): unknown;
}

export function classifyProviderPath(path: ProviderPath): ProviderPathClassification {
  if (path.api === "cursor-sdk") {
    return { outcome: "known-host-tools", providerPathGate: "blocked", containmentGate: "blocked" };
  }
  if (path.registeredNative) {
    return { outcome: "extension-native-unverified", providerPathGate: "blocked", containmentGate: "blocked" };
  }
  if (path.registeredConfig) {
    return { outcome: "extension-config-unverified", providerPathGate: "blocked", containmentGate: "blocked" };
  }
  return { outcome: "pi-core-provider", providerPathGate: "eligible", containmentGate: "blocked" };
}

function observeProviderPath(modelRuntime: ProviderPathInspector, model: { provider: string; api: string }) {
  const path = {
    provider: model.provider,
    api: String(model.api),
    registeredConfig: modelRuntime.getRegisteredProviderConfig(model.provider) !== undefined,
    registeredNative: modelRuntime.getRegisteredNativeProvider(model.provider) !== undefined,
  };
  return { ...path, classification: classifyProviderPath(path) };
}

function providerPathRejection(path: ReturnType<typeof observeProviderPath>): string | undefined {
  if (path.classification.outcome === "known-host-tools") {
    return `Selected provider path ${path.provider}/${path.api} exposes provider-owned host tools outside Pi tool_call`;
  }
  if (path.classification.outcome === "extension-native-unverified") {
    return `Selected provider path ${path.provider}/${path.api} is an extension-native provider; Pi tool mediation is unverified`;
  }
  if (path.classification.outcome === "extension-config-unverified") {
    return `Selected provider path ${path.provider}/${path.api} is an extension-registered provider; Pi tool mediation is unverified`;
  }
  return undefined;
}

function rejectsStartup(notification: { message: string; type: string }): boolean {
  return notification.type === "error" || notification.message.startsWith("Sandbox disabled");
}

export function resolveSdk(piExecutable: string): string {
  const binary = realpathSync(piExecutable);
  const packageName = "@earendil-works/pi-coding-agent";
  for (let directory = dirname(binary); directory !== dirname(directory); directory = dirname(directory)) {
    for (const root of [directory, join(directory, "lib", "node_modules", packageName), join(directory, "libexec", "lib", "node_modules", packageName)]) {
      const manifestPath = join(root, "package.json");
      if (!existsSync(manifestPath)) continue;
      const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
      if (manifest.name === packageName) return realpathSync(join(root, manifest.exports["."].import));
    }
  }
  throw new Error(`Cannot resolve the installed Pi SDK from ${binary}`);
}

export async function probeRuntime(options: ProbeOptions, exercise?: (session: unknown) => Promise<unknown>) {
  const sdkPath = resolveSdk(options.piExecutable);
  const sdk = await import(pathToFileURL(sdkPath).href);
  const settingsManager = sdk.SettingsManager.inMemory({ compaction: { enabled: false } });
  sdk.initTheme(settingsManager.getTheme(), false);
  const modelRuntime = await sdk.ModelRuntime.create({
    authPath: join(options.agentDir, "auth.json"),
    modelsPath: null,
    modelsStorePath: join(options.agentDir, "models-store.json"),
    allowModelNetwork: false,
    refreshOnCreate: false,
  });
  const report = {
    sdkPath,
    model: null as ProbeOptions["model"] | null,
    modelError: null as string | null,
    modelFallbackMessage: null as string | null,
    providerPath: null as ReturnType<typeof observeProviderPath> | null,
    extensions: [] as string[],
    tools: [] as string[],
    loadErrors: [] as Array<{ path: string; error: string }>,
    startupErrors: [] as Array<{ error: string }>,
    notifications: [] as Array<{ message: string; type: string }>,
    calls: [] as Array<{ name: string; blocked: boolean; reason?: string }>,
    rejections: [] as string[],
    exercise: null as unknown,
  };
  if (exercise && !options.extensionPaths.length) {
    report.rejections.push("Tool exercises require explicit guard extensions");
    return report;
  }
  const resourceLoader = new sdk.DefaultResourceLoader({
    cwd: options.cwd,
    agentDir: options.agentDir,
    settingsManager,
    noExtensions: true,
    noSkills: true,
    noPromptTemplates: true,
    noThemes: true,
    additionalExtensionPaths: options.extensionPaths,
    agentsFilesOverride: () => ({ agentsFiles: [] }),
  });
  await resourceLoader.reload();
  const extensions = resourceLoader.getExtensions();
  report.extensions = extensions.extensions.map((extension: { path: string }) => extension.path);
  report.loadErrors = extensions.errors;
  if (report.loadErrors.length) {
    report.rejections.push(...report.loadErrors.map(({ path, error }) => `${path}: ${error}`));
    return report;
  }
  for (const { name, config, extensionPath } of extensions.runtime.pendingProviderRegistrations) {
    try {
      modelRuntime.registerProvider(name, config);
    } catch (error) {
      report.loadErrors.push({ path: extensionPath, error: String(error) });
    }
  }
  extensions.runtime.pendingProviderRegistrations.length = 0;
  for (const { provider, extensionPath } of extensions.runtime.pendingNativeProviderRegistrations) {
    try {
      modelRuntime.registerNativeProvider(provider);
    } catch (error) {
      report.loadErrors.push({ path: extensionPath, error: String(error) });
    }
  }
  extensions.runtime.pendingNativeProviderRegistrations.length = 0;
  if (report.loadErrors.length) {
    report.rejections.push(...report.loadErrors.map(({ path, error }) => `${path}: ${error}`));
    return report;
  }
  const model = modelRuntime.getModel(options.model.provider, options.model.id);
  if (!model) {
    report.modelError = `Selected model not found: ${options.model.provider}/${options.model.id}`;
    report.rejections.push(report.modelError);
    return report;
  }
  report.providerPath = observeProviderPath(modelRuntime, model);
  const preflightProviderRejection = providerPathRejection(report.providerPath);
  if (preflightProviderRejection) {
    report.rejections.push(preflightProviderRejection);
    return report;
  }
  const { session, modelFallbackMessage } = await sdk.createAgentSession({
    cwd: options.cwd,
    agentDir: options.agentDir,
    model,
    modelRuntime,
    settingsManager,
    resourceLoader,
    sessionManager: sdk.SessionManager.inMemory(options.cwd),
    tools: ["read", "bash", "write", "edit"],
  });
  const ui = session.extensionRunner.createContext().ui;
  const originalNotify = ui.notify;
  // Replacing the no-UI object would make the SDK report hasUI as true.
  ui.notify = (message: string, type = "info") => report.notifications.push({ message, type });
  try {
    report.modelFallbackMessage = modelFallbackMessage ?? null;
    await session.bindExtensions({
      mode: "print",
      onError: (error: { error: string }) => report.startupErrors.push(error),
    });
    report.model = session.model ? { provider: session.model.provider, id: session.model.id } : null;
    report.tools = session.getActiveToolNames();
    report.rejections.push(
      ...report.startupErrors.map(({ error }) => error),
      ...report.notifications.filter(rejectsStartup).map(({ message }) => message),
    );
    if (report.model?.provider !== options.model.provider || report.model?.id !== options.model.id) {
      report.rejections.push("Selected model changed during startup");
    }
    if (session.model) {
      report.providerPath = observeProviderPath(modelRuntime, session.model);
      const startupProviderRejection = providerPathRejection(report.providerPath);
      if (startupProviderRejection) report.rejections.push(startupProviderRejection);
    }
    if (report.modelFallbackMessage) report.rejections.push(report.modelFallbackMessage);
    if (report.rejections.length) return report;
    for (const [index, call] of options.calls.entries()) {
      try {
        const result = await session.agent.beforeToolCall({
          toolCall: { type: "toolCall", id: String(index), name: call.name, arguments: call.input },
          args: call.input,
        });
        report.calls.push({ name: call.name, blocked: result?.block === true, reason: result?.reason });
      } catch (error) {
        report.calls.push({ name: call.name, blocked: true, reason: String(error) });
      }
    }
    if (exercise) report.exercise = await exercise(session);
    return report;
  } finally {
    try {
      await session.extensionRunner.emit({ type: "session_shutdown", reason: "quit" });
    } finally {
      ui.notify = originalNotify;
      session.dispose();
    }
  }
}
