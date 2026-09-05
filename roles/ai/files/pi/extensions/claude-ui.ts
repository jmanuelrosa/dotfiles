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
  keyHint,
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
const CLAUDE_BULLET = "⏺ ";
const CLAUDE_WORKING_FRAMES = ["✻", "✽", "✶", "✳", "✢", "✳", "✶", "✽"];
const THINKING_LABEL = "✻ Thinking…";
const SOURCE_PREVIEW_LINES = 10;
const RESULTS_PREVIEW_LINES = 10;
const SHELL_PREVIEW_LINES = 20;
const DIFF_PREVIEW_LINES = 30;

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
  if (context.messageType === "user") return `${CLAUDE_PROMPT}${markdown}`;
  if (context.messageType === "assistant") return `${CLAUDE_BULLET}${markdown}`;
  return markdown;
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

type ToolResult = {
  content: Array<{ type: string; text?: string }>;
  details?: unknown;
};

function resultText(result: ToolResult): string {
  return result.content.find((part) => part.type === "text")?.text ?? "";
}

function textLines(text: string): string[] {
  const lines = text.split("\n");
  if (lines.at(-1) === "") lines.pop();
  return lines;
}

function lineCount(text: string): number {
  return textLines(text).length;
}

function resultLineCount(result: ToolResult): number {
  const details = result.details as { truncation?: { totalLines?: number } } | undefined;
  return details?.truncation?.totalLines ?? lineCount(resultText(result));
}

function firstResultLine(result: ToolResult): string | undefined {
  return textLines(resultText(result)).find((line) => line.trim() !== "")?.trim();
}

function successfulResult(toolName: string, args: Record<string, unknown>, result: ToolResult, cwd: string): string {
  const firstLine = firstResultLine(result);
  const count = resultLineCount(result);
  const target = relativePath(args.path, cwd);
  switch (toolName) {
    case "read":
      if (firstLine?.startsWith("Read image file")) return firstLine;
      return `Read ${count} line${count === 1 ? "" : "s"}`;
    case "grep":
      if (firstLine === "No matches found") return firstLine;
      return `Found ${count} match${count === 1 ? "" : "es"}`;
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
      return "Completed";
    default:
      return firstLine ?? "Completed";
  }
}

function toolCallLabel(toolName: string, args: Record<string, unknown>, cwd: string): string {
  const path = relativePath(args.path, cwd);
  switch (toolName) {
    case "read":
      return `Read(${path ?? ""})`;
    case "write":
      return `Write(${path ?? ""})`;
    case "edit":
      return `Update(${path ?? ""})`;
    case "bash":
      return `Bash(${String(args.command ?? "")})`;
    case "powershell":
      return `PowerShell(${String(args.command ?? "")})`;
    case "grep":
      return `Grep(${[quoted(args.pattern), path].filter(Boolean).join(", ")})`;
    case "find":
      return `Find(${[args.pattern, path].filter(Boolean).join(", ")})`;
    case "ls":
      return `List(${path ?? ""})`;
    default:
      return title(toolName);
  }
}

function resultOutput(toolName: string, args: Record<string, unknown>, result: ToolResult): string {
  if (toolName === "write") return typeof args.content === "string" ? args.content : "";
  if (toolName === "edit") {
    const diff = (result.details as { diff?: unknown } | undefined)?.diff;
    return typeof diff === "string" ? diff : resultText(result);
  }
  return resultText(result);
}

function previewLimit(toolName: string): number {
  if (toolName === "edit") return DIFF_PREVIEW_LINES;
  if (toolName === "bash" || toolName === "powershell") return SHELL_PREVIEW_LINES;
  if (toolName === "read" || toolName === "write") return SOURCE_PREVIEW_LINES;
  return RESULTS_PREVIEW_LINES;
}

function previewLines(lines: string[], limit: number, fromEnd: boolean, expanded: boolean): { lines: string[]; omitted: number } {
  if (expanded || lines.length <= limit) return { lines, omitted: 0 };
  return { lines: fromEnd ? lines.slice(-limit) : lines.slice(0, limit), omitted: lines.length - limit };
}

function resultComponent(
  toolName: string,
  args: Record<string, unknown>,
  result: ToolResult,
  expanded: boolean,
  isError: boolean,
  theme: { fg: (color: string, text: string) => string },
  cwd: string,
): Component {
  const activity = describeActivity(toolName, args, cwd);
  const summary = isError
    ? ["Failed", activity.action.toLowerCase(), activity.target].filter(Boolean).join(" ")
    : successfulResult(toolName, args, result, cwd);
  const output = resultOutput(toolName, args, result);
  const preview = previewLines(textLines(output), previewLimit(toolName), toolName === "bash" || toolName === "powershell", expanded || isError);
  const lines = [theme.fg(isError ? "error" : "muted", summary)];
  lines.push(...preview.lines.map((line) => theme.fg(isError ? "error" : "toolOutput", line)));
  if (preview.omitted > 0) {
    lines.push(theme.fg("muted", `+${preview.omitted} lines (${keyHint("app.tools.expand", "to expand")})`));
  }
  return new Text(lines.join("\n"), 0, 0);
}

function hierarchicalDefinition(definition: ToolDefinition<any, any, any>, cwd: string): ToolDefinition<any, any, any> {
  return {
    ...definition,
    renderShell: "self",
    renderCall(args, theme, context) {
      const previous = context.lastComponent instanceof HierarchyComponent ? context.lastComponent : undefined;
      const child = new Text(theme.fg("toolTitle", toolCallLabel(definition.name, args as Record<string, unknown>, cwd)), 0, 0);
      const component = previous ?? new HierarchyComponent(child, "", "");
      component.update(child, `${theme.fg("accent", "⏺")} `, "  ");
      return component;
    },
    renderResult(result, options, theme, context) {
      const previous = context.lastComponent instanceof HierarchyComponent ? context.lastComponent : undefined;
      const child = resultComponent(
        definition.name,
        context.args as Record<string, unknown>,
        result as ToolResult,
        options.expanded,
        context.isError,
        theme,
        cwd,
      );
      const component = previous ?? new HierarchyComponent(child, "", "");
      component.update(child, theme.fg("dim", "  ⎿  "), "     ");
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
  for (const definition of definitions) pi.registerTool(hierarchicalDefinition(definition, cwd));
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
    ctx.ui.setHiddenThinkingLabel(THINKING_LABEL);
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
    ctx.ui.setHiddenThinkingLabel();
  });
}
