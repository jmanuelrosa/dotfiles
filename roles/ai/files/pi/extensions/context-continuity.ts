/**
 * context-continuity.ts - a model switch is a new projection of the same conversation.
 *
 * Pi keeps one JSONL branch across `/model`. The next request is not the same effective
 * context: images may become placeholders, opaque reasoning may disappear, and usage from the
 * previous model is not a measurement of the new one. This extension does not rewrite that
 * branch. It records the projection, warns once when something the active context still holds
 * cannot survive the switch, and leaves compaction to pi.
 *
 * Custom entries are metadata. A prompt, an image, a tool argument or a thinking block stored
 * here would be the feature logging the conversation it exists only to describe.
 */

import { createHash } from "node:crypto";
import type {
  ExtensionAPI,
  ExtensionContext,
  SessionEntry,
} from "@earendil-works/pi-coding-agent";

const CUSTOM_TYPE = "context-continuity";
const CONTEXT_ENTRY_TYPES = new Set(["message", "compaction", "branch_summary"]);

type Degradation =
  | "images-unsupported"
  | "opaque-reasoning-unavailable"
  | "orphaned-tool-result-synthesized"
  | "smaller-context-window";

interface ModelIdentity {
  provider: string;
  api: string;
  id: string;
  contextWindow: number;
}

interface LogicalContextIdentity {
  sessionId: string;
  contextEntryId: string | null;
  compactionEntryId: string | null;
  systemPromptHash: string;
  activeToolsHash: string;
}

interface ContextProjectionEntryV1 {
  version: 1;
  event: "model-switch";
  source: "set" | "cycle";
  logicalContext: LogicalContextIdentity;
  previousModel: ModelIdentity | null;
  activeModel: ModelIdentity;
  usageQuality: "unknown";
  degradations: Degradation[];
}

interface ModelLike {
  provider?: string;
  api?: string;
  id?: string;
  contextWindow?: number;
  input?: string[];
}

interface ContentBlock {
  type?: string;
  id?: string;
  redacted?: boolean;
  thinkingSignature?: string;
  thoughtSignature?: string;
}

interface ConversationMessage {
  role?: string;
  content?: unknown;
  provider?: string;
  api?: string;
  model?: string;
  toolCallId?: string;
}

function digest(value: string): string {
  return createHash("sha256").update(value).digest("hex").slice(0, 16);
}

function modelIdentity(model: ModelLike | undefined): ModelIdentity | null {
  if (!model?.provider || !model.api || !model.id) return null;
  return {
    provider: model.provider,
    api: model.api,
    id: model.id,
    contextWindow: model.contextWindow ?? 0,
  };
}

function sameModel(message: ConversationMessage, model: ModelLike): boolean {
  return (
    message.provider === model.provider &&
    message.api === model.api &&
    message.model === model.id
  );
}

function contentBlocks(content: unknown): ContentBlock[] {
  if (!content) return [];
  if (Array.isArray(content)) return content as ContentBlock[];
  return [{ type: "text" }];
}

function activeEntries(branch: SessionEntry[]): SessionEntry[] {
  let start = 0;
  for (let index = 0; index < branch.length; index += 1) {
    if (branch[index].type === "compaction") start = index + 1;
  }
  return branch.slice(start);
}

function messagesFromBranch(branch: SessionEntry[]): ConversationMessage[] {
  return activeEntries(branch)
    .filter((entry) => entry.type === "message")
    .map((entry) => entry.message as ConversationMessage);
}

function detectDegradations(
  messages: ConversationMessage[],
  model: ModelLike,
  previous: ModelLike | undefined,
): Degradation[] {
  const supportsImage = Array.isArray(model.input) && model.input.includes("image");
  const calls = new Set<string>();
  const results = new Set<string>();
  let images = false;
  let opaque = false;

  for (const message of messages) {
    const blocks = contentBlocks(message.content);
    if ((message.role === "user" || message.role === "toolResult") && !supportsImage) {
      if (blocks.some((block) => block.type === "image")) images = true;
    }
    if (message.role === "assistant") {
      const replayable = sameModel(message, model);
      for (const block of blocks) {
        if (
          block.type === "thinking" &&
          !replayable &&
          (block.redacted || block.thinkingSignature)
        ) {
          opaque = true;
        }
        if (block.type === "toolCall") {
          if (block.id) calls.add(block.id);
          if (!replayable && block.thoughtSignature) opaque = true;
        }
      }
    }
    if (message.role === "toolResult" && message.toolCallId) {
      results.add(message.toolCallId);
    }
  }

  const degradations: Degradation[] = [];
  if (images) degradations.push("images-unsupported");
  if (opaque) degradations.push("opaque-reasoning-unavailable");
  if ([...calls].some((id) => !results.has(id))) {
    degradations.push("orphaned-tool-result-synthesized");
  }
  if (
    previous &&
    typeof previous.contextWindow === "number" &&
    typeof model.contextWindow === "number" &&
    model.contextWindow < previous.contextWindow
  ) {
    degradations.push("smaller-context-window");
  }
  return degradations;
}

function logicalContext(ctx: ExtensionContext, tools: string[]): LogicalContextIdentity {
  const branch = ctx.sessionManager.getBranch();
  let contextEntryId: string | null = null;
  let compactionEntryId: string | null = null;
  for (const entry of branch) {
    if (entry.type === "compaction") compactionEntryId = entry.id;
    if (CONTEXT_ENTRY_TYPES.has(entry.type)) contextEntryId = entry.id;
  }
  return {
    sessionId: ctx.sessionManager.getSessionId(),
    contextEntryId,
    compactionEntryId,
    systemPromptHash: digest(ctx.getSystemPrompt?.() ?? ""),
    activeToolsHash: digest([...tools].sort().join("\0")),
  };
}

function notifyText(degradations: Degradation[], model: ModelIdentity): string | undefined {
  if (degradations.length === 0) return undefined;
  const name = `${model.provider}/${model.id}`;
  const parts: string[] = [];
  if (degradations.includes("images-unsupported")) parts.push("images are unavailable");
  if (degradations.includes("opaque-reasoning-unavailable")) {
    parts.push("opaque reasoning cannot be replayed");
  }
  if (degradations.includes("orphaned-tool-result-synthesized")) {
    parts.push("an unresolved tool call will be synthesized");
  }
  if (degradations.includes("smaller-context-window")) {
    parts.push("the context window is smaller");
  }
  return `Context projection changed: ${parts.join("; ")} for ${name}.`;
}

function epochKey(projection: ContextProjectionEntryV1): string | null {
  const identity = projection.logicalContext;
  const model = projection.activeModel;
  if (!identity || !model) return null;
  return [
    identity.sessionId,
    model.provider,
    model.api,
    model.id,
    identity.contextEntryId ?? "",
  ].join("\0");
}

function buildProjection(
  event: { source: string; model: ModelLike; previousModel?: ModelLike },
  ctx: ExtensionContext,
  tools: string[],
): ContextProjectionEntryV1 | undefined {
  const active = modelIdentity(event.model) ?? modelIdentity(ctx.model);
  if (!active) return undefined;
  const source = event.source === "cycle" ? "cycle" : "set";
  return {
    version: 1,
    event: "model-switch",
    source,
    logicalContext: logicalContext(ctx, tools),
    previousModel: modelIdentity(event.previousModel),
    activeModel: active,
    usageQuality: "unknown",
    degradations: detectDegradations(
      messagesFromBranch(ctx.sessionManager.getBranch()),
      event.model ?? ctx.model ?? {},
      event.previousModel,
    ),
  };
}

export default function contextContinuity(pi: ExtensionAPI): void {
  let notified: string | null = null;

  const notifyOnce = (projection: ContextProjectionEntryV1, ctx: ExtensionContext) => {
    const key = epochKey(projection);
    if (!key || notified === key) return;
    const text = notifyText(projection.degradations, projection.activeModel);
    if (!text) return;
    notified = key;
    ctx.ui.notify(text, "warning");
  };

  pi.on("session_start", (_event, ctx) => {
    try {
      notified = null;
      const branch = ctx.sessionManager.getBranch();
      for (let index = branch.length - 1; index >= 0; index -= 1) {
        const entry = branch[index];
        if (entry.type === "custom" && entry.customType === CUSTOM_TYPE) {
          const data = entry.data as ContextProjectionEntryV1 | undefined;
          if (data?.version === 1) notified = epochKey(data);
          break;
        }
      }
    } catch {
      // A missing branch is a session that has not been written yet.
    }
  });

  pi.on("model_select", (event, ctx) => {
    try {
      const projection = buildProjection(event, ctx, pi.getActiveTools());
      if (!projection) return;
      if (event.source !== "restore") {
        pi.appendEntry(CUSTOM_TYPE, projection);
      }
      notifyOnce(projection, ctx);
    } catch {
      // A footer-adjacent warning is never worth interrupting a switch for.
    }
  });

  pi.on("context", () => {
    // Version 1 observes the selected messages only. Returning a replacement would duplicate
    // pi's provider adapters, which is the one thing this extension exists not to do.
  });
}
