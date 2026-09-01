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
import { Container, Text, visibleWidth, type EditorTheme, type TUI } from "@earendil-works/pi-tui";

const HINT_STATUS_KEY = "dotfiles-activity-hint";
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

function conciseCall(activity: Activity, theme: { fg: (color: string, text: string) => string }): Text {
  const colour = activity.action === "Updating" || activity.action === "Writing" ? "toolDiffAdded" : "muted";
  const marker = `${theme.fg("accent", "●")} `;
  const target = activity.target ? ` ${theme.fg("muted", activity.target)}` : "";
  return new Text(`${marker}${theme.fg(colour, activity.action)}${target}`, 0, 0);
}

function conciseResult(isError: boolean, activity: Activity, theme: { fg: (color: string, text: string) => string }): Container | Text {
  if (!isError) return new Container();
  const content = ["Failed", activity.action.toLowerCase(), activity.target].filter((part) => part !== undefined).join(" ");
  return new Text(theme.fg("error", content), 0, 0);
}

function conciseDefinition(
  definition: ToolDefinition<any, any, any>,
  cwd: string,
  showErrors: () => boolean,
  errorInvalidators: Set<() => void>,
): ToolDefinition<any, any, any> {
  return {
    ...definition,
    renderShell: "self",
    renderCall(args, theme, context) {
      if (context.expanded && definition.renderCall) return definition.renderCall(args, theme, context);
      return conciseCall(describeActivity(definition.name, args as Record<string, unknown>, cwd), theme);
    },
    renderResult(result, options, theme, context) {
      if (context.expanded && definition.renderResult) return definition.renderResult(result, options, theme, context);
      if (context.isError) errorInvalidators.add(context.invalidate);
      return conciseResult(
        context.isError && showErrors(),
        describeActivity(definition.name, context.args as Record<string, unknown>, cwd),
        theme,
      );
    },
  };
}

function registerConciseTools(
  pi: ExtensionAPI,
  cwd: string,
  showErrors: () => boolean,
  errorInvalidators: Set<() => void>,
): void {
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
    pi.registerTool(conciseDefinition(definition, cwd, showErrors, errorInvalidators));
  }
}

export default function activity(pi: ExtensionAPI): void {
  let running: RunningActivity[] = [];
  let started = new Map<string, number>();
  let showErrors = false;
  const errorInvalidators = new Set<() => void>();
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
    registerConciseTools(pi, ctx.cwd, () => showErrors, errorInvalidators);
    ctx.ui.setEditorComponent((tui, theme, keybindings) => new ClaudeEditor(tui, theme, keybindings));
    ctx.ui.setWorkingIndicator({
      frames: CLAUDE_WORKING_FRAMES.map((frame) => ctx.ui.theme.fg("accent", frame)),
    });
    ctx.ui.setWorkingVisible(true);
  });

  pi.on("before_agent_start", (_event, ctx) => {
    running = [];
    started = new Map();
    showErrors = false;
    errorInvalidators.clear();
    clearTimer();
    ctx.ui.setWorkingMessage();
    ctx.ui.setStatus(HINT_STATUS_KEY, undefined);
  });

  pi.on("tool_execution_start", (event, ctx) => {
    begin(event, ctx);
  });

  pi.on("tool_execution_end", (event, ctx) => {
    finish(event.toolCallId, ctx);
  });

  pi.on("tool_result", (event, ctx) => {
    if (event.isError) showErrors = true;
    ctx.ui.setStatus(HINT_STATUS_KEY, ctx.ui.theme.fg("dim", keyHint("app.tools.expand", "for details")));
  });

  pi.on("message_end", (event) => {
    const message = event.message as { content?: unknown; role: string };
    const hasToolCall = Array.isArray(message.content) && message.content.some(
      (content) => typeof content === "object" && content !== null && "type" in content && content.type === "toolCall",
    );
    if (message.role !== "assistant" || hasToolCall) return;
    showErrors = false;
    for (const invalidate of errorInvalidators) invalidate();
  });

  pi.on("session_shutdown", (_event, ctx) => {
    clearTimer();
    ctx.ui.setEditorComponent(undefined);
    ctx.ui.setWorkingIndicator();
    ctx.ui.setWorkingMessage();
  });
}
