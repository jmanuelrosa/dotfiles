import { basename, relative, resolve } from "node:path";
import {
  createBashToolDefinition,
  createEditToolDefinition,
  createFindToolDefinition,
  createGrepToolDefinition,
  createLsToolDefinition,
  createPowerShellToolDefinition,
  createReadToolDefinition,
  createWriteToolDefinition,
  CustomEditor,
  type ExtensionAPI,
  type ExtensionContext,
  type KeybindingsManager,
  type MarkdownTransformContext,
  type ToolDefinition,
} from "@earendil-works/pi-coding-agent";
import { stripTerminalSequences, Text, visibleWidth, type Component, type EditorTheme, type TUI } from "@earendil-works/pi-tui";
const ELAPSED_AFTER_MS = 5_000;
const CLAUDE_PROMPT = "❯ ";
const CLAUDE_PROMPT_PADDING = visibleWidth(CLAUDE_PROMPT);
const CLAUDE_WORKING_FRAMES = ["✻", "✽", "✶", "✳", "✢", "✳", "✶", "✽"];

type Activity = {
  action: string;
  target?: string;
};

type RunningActivity = Activity & {
  id: string;
  toolName: string;
  startedAt: number;
};

function claudeMessage(markdown: string, context: MarkdownTransformContext): string {
  return context.messageType === "user" ? `${CLAUDE_PROMPT}${markdown}` : markdown;
}

function decorateEditorLines(lines: string[], prompt: string): string[] {
  if (lines.length < 2) return lines;
  const decorated = [...lines];
  decorated[1] = `${prompt}${decorated[1]!.slice(CLAUDE_PROMPT_PADDING)}`;
  return decorated;
}

class ClaudeEditor extends CustomEditor {
  constructor(tui: TUI, theme: EditorTheme, keybindings: KeybindingsManager) {
    super(tui, theme, keybindings, { paddingX: CLAUDE_PROMPT_PADDING });
  }

  render(width: number): string[] {
    return decorateEditorLines(super.render(width), `${this.borderColor("❯")} `);
  }
}

function relativePath(path: unknown, cwd: string): string | undefined {
  if (typeof path !== "string" || path === "") return undefined;
  const display = relative(cwd, resolve(cwd, path));
  return display === "" ? basename(path) : display;
}

function quoted(value: unknown): string | undefined {
  if (typeof value !== "string" || value === "") return undefined;
  return `"${value}"`;
}

function title(value: string): string {
  return value
    .split(/[-_\s]+/)
    .filter((word) => word !== "")
    .map((word) => `${word.slice(0, 1).toUpperCase()}${word.slice(1)}`)
    .join(" ");
}

export function describeActivity(toolName: string, args: Record<string, unknown>, cwd: string): Activity {
  switch (toolName) {
    case "read":
      return { action: "Reading", target: relativePath(args.path, cwd) };
    case "grep":
      return { action: "Searching for", target: quoted(args.pattern) };
    case "find":
      return { action: "Searching files", target: relativePath(args.path, cwd) };
    case "ls":
      return { action: "Listing", target: relativePath(args.path, cwd) };
    case "edit":
      return { action: "Updating", target: relativePath(args.path, cwd) };
    case "write":
      return { action: "Writing", target: relativePath(args.path, cwd) };
    case "bash":
    case "powershell":
      return { action: "Running command" };
    case "Agent":
      return { action: "Delegating task" };
    default:
      return { action: title(toolName) };
  }
}

function activityMessage(running: RunningActivity[], started: Map<string, number>): string | undefined {
  const current = running.at(-1);
  if (!current) return undefined;
  const count = started.get(current.action) ?? 1;
  let message = current.action;
  if (current.action === "Reading") message += ` ${count} file${count === 1 ? "" : "s"}`;
  else if (current.action === "Listing") message += ` ${count} director${count === 1 ? "y" : "ies"}`;
  if (current.target) message += ` · ${current.target}`;
  const remaining = running.length - 1;
  if (remaining > 0) message += ` · ${remaining} more`;
  const elapsed = Date.now() - current.startedAt;
  if (elapsed >= ELAPSED_AFTER_MS) message += ` · ${Math.floor(elapsed / 1000)}s`;
  return message;
}

class HierarchyComponent implements Component {
  child: Component;
  private firstPrefix: string;
  private continuationPrefix: string;
  private fallback?: Component;

  constructor(child: Component, firstPrefix: string, continuationPrefix: string, fallback?: Component) {
    this.child = child;
    this.firstPrefix = firstPrefix;
    this.continuationPrefix = continuationPrefix;
    this.fallback = fallback;
  }

  update(child: Component, firstPrefix: string, continuationPrefix: string, fallback?: Component): void {
    this.child = child;
    this.firstPrefix = firstPrefix;
    this.continuationPrefix = continuationPrefix;
    this.fallback = fallback;
  }

  invalidate(): void {
    this.child.invalidate();
    this.fallback?.invalidate();
  }

  render(width: number): string[] {
    const prefixWidth = Math.max(visibleWidth(this.firstPrefix), visibleWidth(this.continuationPrefix));
    const contentWidth = Math.max(1, width - prefixWidth);
    let lines = this.child.render(contentWidth);
    while (lines.length > 0 && stripTerminalSequences(lines[0] ?? "").trim() === "") lines.shift();
    if (lines.length === 0 && this.fallback) lines = this.fallback.render(contentWidth);
    return lines.map((line, index) => `${index === 0 ? this.firstPrefix : this.continuationPrefix}${line}`);
  }
}

type ConciseToolResult = {
  content: Array<{ type: string; text?: string }>;
  details?: unknown;
};

function resultText(result: ConciseToolResult): string | undefined {
  return result.content.find((part) => part.type === "text")?.text;
}

function lineCount(text: string): number {
  if (text === "") return 0;
  const lines = text.split("\n");
  if (lines.at(-1) === "") lines.pop();
  while (lines.length >= 2 && lines.at(-2) === "" && /^\[.*(?:continue|more lines).+\]$/.test(lines.at(-1) ?? "")) {
    lines.splice(-2);
  }
  return lines.length;
}

function resultLineCount(result: ConciseToolResult): number {
  const details = result.details as { truncation?: { totalLines?: number } } | undefined;
  return details?.truncation?.totalLines ?? lineCount(resultText(result) ?? "");
}

function firstResultLine(result: ConciseToolResult): string | undefined {
  return resultText(result)
    ?.split("\n")
    .find((line) => line.trim() !== "")
    ?.trim();
}

function successfulResult(
  toolName: string,
  args: Record<string, unknown>,
  result: ConciseToolResult,
  cwd: string,
): string {
  const firstLine = firstResultLine(result);
  const count = resultLineCount(result);
  const target = relativePath(args.path, cwd);
  switch (toolName) {
    case "read":
      if (firstLine?.startsWith("Read image file")) return firstLine;
      return `Read ${count} line${count === 1 ? "" : "s"}`;
    case "grep":
      if (firstLine === "No matches found") return firstLine;
      return `Returned ${count} line${count === 1 ? "" : "s"}`;
    case "find":
      if (firstLine === "No files found matching pattern") return firstLine;
      return `Found ${count} file${count === 1 ? "" : "s"}`;
    case "ls":
      if (firstLine === "(empty directory)") return firstLine;
      return `Listed ${count} entr${count === 1 ? "y" : "ies"}`;
    case "edit": {
      const edits = Array.isArray(args.edits) ? args.edits.length : 1;
      return [`Updated ${edits} block${edits === 1 ? "" : "s"} in`, target].filter(Boolean).join(" ");
    }
    case "write": {
      const content = typeof args.content === "string" ? args.content : "";
      const lines = lineCount(content);
      return [`Wrote ${lines} line${lines === 1 ? "" : "s"} to`, target].filter(Boolean).join(" ");
    }
    case "bash":
    case "powershell":
      return firstLine ?? "Completed";
    default:
      return firstLine ?? "Completed";
  }
}

function hierarchicalDefinition(
  definition: ToolDefinition<any, any, any>,
  cwd: string,
): ToolDefinition<any, any, any> {
  return {
    ...definition,
    renderShell: "self",
    renderCall(args, theme, context) {
      if (!definition.renderCall) return new Text("", 0, 0);
      const previous = context.lastComponent instanceof HierarchyComponent ? context.lastComponent : undefined;
      const child = definition.renderCall(args, theme, {
        ...context,
        expanded: true,
        lastComponent: previous?.child,
      });
      const component = previous ?? new HierarchyComponent(child, "", "");
      component.update(child, `${theme.fg("accent", "●")} `, "  ");
      return component;
    },
    renderResult(result, options, theme, context) {
      if (!definition.renderResult) return new Text("", 0, 0);
      const previous = context.lastComponent instanceof HierarchyComponent ? context.lastComponent : undefined;
      const child = definition.renderResult(result, { ...options, expanded: true }, theme, {
        ...context,
        expanded: true,
        lastComponent: previous?.child,
      });
      const args = context.args as Record<string, unknown>;
      const activity = describeActivity(definition.name, args, cwd);
      const fallbackText = context.isError
        ? ["Failed", activity.action.toLowerCase(), activity.target].filter(Boolean).join(" ")
        : successfulResult(definition.name, args, result as ConciseToolResult, cwd);
      const fallback = new Text(theme.fg(context.isError ? "error" : "muted", fallbackText), 0, 0);
      const component = previous ?? new HierarchyComponent(child, "", "");
      component.update(child, theme.fg("dim", "  └ "), "    ", fallback);
      return component;
    },
  };
}

function registerHierarchicalTools(pi: ExtensionAPI, cwd: string): void {
  const definitions = [
    createReadToolDefinition(cwd),
    createGrepToolDefinition(cwd),
    createFindToolDefinition(cwd),
    createLsToolDefinition(cwd),
    createEditToolDefinition(cwd),
    createWriteToolDefinition(cwd),
    createBashToolDefinition(cwd),
    createPowerShellToolDefinition(cwd),
  ];
  for (const definition of definitions) {
    pi.registerTool(hierarchicalDefinition(definition, cwd));
  }
}

export default function activity(pi: ExtensionAPI): void {
  let running: RunningActivity[] = [];
  let started = new Map<string, number>();
  let timer: NodeJS.Timeout | undefined;

  const clearTimer = () => {
    if (!timer) return;
    clearInterval(timer);
    timer = undefined;
  };

  const refreshWorking = (ctx: ExtensionContext) => {
    const message = activityMessage(running, started);
    if (message) ctx.ui.setWorkingMessage(ctx.ui.theme.fg("accent", message));
    else ctx.ui.setWorkingMessage();
  };

  const begin = (event: { toolCallId: string; toolName: string; args: Record<string, unknown> }, ctx: ExtensionContext) => {
    const next = describeActivity(event.toolName, event.args, ctx.cwd);
    started.set(next.action, (started.get(next.action) ?? 0) + 1);
    running.push({ ...next, id: event.toolCallId, toolName: event.toolName, startedAt: Date.now() });
    refreshWorking(ctx);
    timer ??= setInterval(() => refreshWorking(ctx), 1_000);
  };

  const finish = (id: string, ctx: ExtensionContext) => {
    running = running.filter((entry) => entry.id !== id);
    if (running.length === 0) clearTimer();
    refreshWorking(ctx);
  };

  pi.registerMarkdownTransformer(claudeMessage);

  pi.on("session_start", (_event, ctx) => {
    if (ctx.mode !== "tui") return;
    registerHierarchicalTools(pi, ctx.cwd);
    ctx.ui.setEditorComponent((tui, theme, keybindings) => new ClaudeEditor(tui, theme, keybindings));
    ctx.ui.setWorkingIndicator({
      frames: CLAUDE_WORKING_FRAMES.map((frame) => ctx.ui.theme.fg("accent", frame)),
    });
    ctx.ui.setWorkingVisible(true);
  });

  pi.on("before_agent_start", (_event, ctx) => {
    running = [];
    started = new Map();
    clearTimer();
    ctx.ui.setWorkingMessage();
  });

  pi.on("tool_execution_start", (event, ctx) => {
    begin(event, ctx);
  });

  pi.on("tool_execution_end", (event, ctx) => {
    finish(event.toolCallId, ctx);
  });

  pi.on("session_shutdown", (_event, ctx) => {
    clearTimer();
    ctx.ui.setEditorComponent(undefined);
    ctx.ui.setWorkingIndicator();
    ctx.ui.setWorkingMessage();
  });
}
