/**
 * skill-model.ts - a skill that names a model runs on that model.
 *
 * Pi's skill loader reads `name`, `description` and `disable-model-invocation` from a
 * SKILL.md and drops everything else, so `model:` is inert under pi while Claude Code
 * honours it. This closes that gap without a second declaration: the key stays one plain
 * string in the shared SKILL.md, and bare values resolve against this session's scoped
 * catalogue, so reordering `enabledModels` reorders which model a bare `opus` wins.
 *
 * Model pins with an exact route keep their declared model first and switch to the mapped
 * Codex model when the source has no auth or returns an account or capacity error. The error
 * is rewritten to pi's retryable provider form after the model switch, so pi repeats the
 * failed assistant turn on the fallback; network, server and generic SDK failures retain
 * pi's normal provider retry behavior.
 *
 * The pin lasts one agent run, which is the boundary Claude Code uses as well: the
 * override "applies for the rest of the current turn" and the session model resumes on the
 * next prompt.
 *
 * Prior model and thinking level are recorded as a session entry rather than held in a
 * closure, because a resume or a reload mid-pin would otherwise strand the session on the
 * pinned model with nothing left that knows what to restore.
 */

import { readFileSync } from "node:fs";
import { basename, dirname } from "node:path";
import type {
  ExtensionAPI,
  ExtensionContext,
  ScopedModel,
  SessionEntry,
} from "@earendil-works/pi-coding-agent";

type Model = ScopedModel["model"];
type ThinkingLevel = ReturnType<ExtensionAPI["getThinkingLevel"]>;

const CUSTOM_TYPE = "skill-model";
const STATUS_KEY = "dotfiles-skill-model";
const SKILL_COMMAND = /^\/skill:([A-Za-z0-9_.-]+)/;
const FRONTMATTER = /^---\r?\n([\s\S]*?)\r?\n---/;
const MODEL_FIELD = /^model:[ \t]*(.+?)[ \t]*$/m;
const SKILL_FILE = "SKILL.md";
const INHERIT = "inherit";
const MODEL_ROUTES: Readonly<Record<string, readonly string[]>> = {
  "cursor/claude-opus-5@1m": ["openai-codex/gpt-5.6-sol"],
  "cursor/claude-sonnet-5@1m": ["openai-codex/gpt-5.6-terra"],
  "anthropic/claude-opus-5": ["openai-codex/gpt-5.6-sol"],
  "anthropic/claude-sonnet-5": ["openai-codex/gpt-5.6-terra"],
  "cursor/composer-2-5": ["openai-codex/gpt-5.6-luna"],
  "cursor/gpt-5.6-terra@1m": ["openai-codex/gpt-5.6-terra"],
  "cursor/gpt-5.6-sol@1m": ["openai-codex/gpt-5.6-sol"],
  "anthropic/claude-haiku-4-5": ["openai-codex/gpt-5.6-terra"],
};
const ACCOUNT_OR_LIMIT_ERROR = new RegExp(
  [
    "unauthenticated",
    "unauthorized",
    "unauthorised",
    "forbidden",
    "invalid (?:api )?key",
    "authentication",
    "(?:^|\\D)40[123](?:\\D|$)",
    "(?:^|\\D)429(?:\\D|$)",
    "rate.?limit",
    "too many requests",
    "usage limit",
    "quota (?:exceeded|exhausted)",
    "insufficient_quota",
    "out of budget",
    "spend.?limit",
    "billing",
    "subscription",
  ].join("|"),
  "i",
);

interface SkillModelPinV1 {
  version: 1;
  state: "pinned" | "released";
  skill: string;
  model: string;
  previousModel: string | null;
  previousThinking: ThinkingLevel;
}

interface ActivePin {
  pin: SkillModelPinV1;
  route: readonly string[];
  routeIndex: number;
  currentModel: string;
}

function reference(model: Model): string {
  return `${model.provider}/${model.id}`;
}

function fromReference(ctx: ExtensionContext, ref: string): Model | undefined {
  const separator = ref.indexOf("/");
  if (separator < 0) return undefined;
  return ctx.modelRegistry.find(ref.slice(0, separator), ref.slice(separator + 1));
}

/** Declared order is the tiebreak: `opus` resolves to whichever provider `enabledModels` lists first. */
function resolveSpec(ctx: ExtensionContext, spec: string): Model | undefined {
  const catalogue =
    ctx.scopedModels.length > 0
      ? ctx.scopedModels.map((scoped) => scoped.model)
      : ctx.modelRegistry.getAvailable();
  const wanted = spec.toLowerCase();
  if (wanted.includes("/")) {
    return catalogue.find((model) => reference(model).toLowerCase() === wanted);
  }
  return (
    catalogue.find((model) => model.id.toLowerCase() === wanted) ??
    catalogue.find((model) => model.id.toLowerCase().includes(wanted))
  );
}

function routeFor(ctx: ExtensionContext, spec: string): readonly string[] {
  const primary = resolveSpec(ctx, spec);
  if (!primary) return [spec];
  const primaryReference = reference(primary);
  const fallbacks = MODEL_ROUTES[primaryReference.toLowerCase()];
  return fallbacks ? [primaryReference, ...fallbacks] : [spec];
}

function declaredModel(skillPath: string): string | null {
  let text: string;
  try {
    text = readFileSync(skillPath, "utf8");
  } catch {
    return null;
  }
  const frontmatter = FRONTMATTER.exec(text);
  if (!frontmatter) return null;
  const field = MODEL_FIELD.exec(frontmatter[1]);
  if (!field) return null;
  return field[1].replace(/^["']|["']$/g, "").trim() || null;
}

function skillPath(pi: ExtensionAPI, name: string): string | null {
  for (const command of pi.getCommands()) {
    if (command.source !== "skill") continue;
    if (command.name !== name && command.name !== `skill:${name}`) continue;
    return command.sourceInfo.path;
  }
  return null;
}

function latestPin(branch: readonly SessionEntry[]): SkillModelPinV1 | null {
  for (let index = branch.length - 1; index >= 0; index -= 1) {
    const entry = branch[index];
    if (entry.type !== "custom" || entry.customType !== CUSTOM_TYPE) continue;
    const data = entry.data as SkillModelPinV1 | undefined;
    return data?.version === 1 ? data : null;
  }
  return null;
}

export default function registerSkillModel(pi: ExtensionAPI): void {
  let active: ActivePin | null = null;

  const pin = async (skill: string, path: string, ctx: ExtensionContext) => {
    if (active) return;
    const spec = declaredModel(path);
    if (!spec || spec.toLowerCase() === INHERIT) return;

    const route = routeFor(ctx, spec);
    const previousModel = ctx.model ? reference(ctx.model) : null;
    const previousThinking = pi.getThinkingLevel();
    let matchedReference: string | undefined;
    let selected: { target: Model; index: number } | undefined;

    for (let index = 0; index < route.length; index += 1) {
      const target = resolveSpec(ctx, route[index]);
      if (!target) continue;
      matchedReference ??= reference(target);
      const alreadySelected = ctx.model && reference(ctx.model) === reference(target);
      if (!alreadySelected && !(await pi.setModel(target))) continue;
      selected = { target, index };
      break;
    }

    if (!selected) {
      const wanted = route.length === 1 ? matchedReference : route.join(" then ");
      const message = matchedReference
        ? `${skill} wants ${wanted}, which has no configured auth`
        : `${skill} wants "${spec}", which no enabled model matches`;
      ctx.ui.notify(message, "warning");
      return;
    }

    const { target, index } = selected;
    const targetReference = reference(target);
    if (previousModel === targetReference && route.length === 1) return;

    const candidate: SkillModelPinV1 = {
      version: 1,
      state: "pinned",
      skill,
      model: targetReference,
      previousModel,
      previousThinking,
    };
    active = {
      pin: candidate,
      route,
      routeIndex: index,
      currentModel: targetReference,
    };
    pi.appendEntry(CUSTOM_TYPE, candidate);
    ctx.ui.setStatus(STATUS_KEY, ctx.ui.theme.fg("accent", `${skill} on ${target.id}`));
    if (index > 0) {
      ctx.ui.notify(
        `${skill}: ${route[0]} is unavailable; using ${targetReference}`,
        "warning",
      );
    }
  };

  const fallback = async (ctx: ExtensionContext): Promise<Model | undefined> => {
    if (!active) return undefined;
    for (let index = active.routeIndex + 1; index < active.route.length; index += 1) {
      const target = resolveSpec(ctx, active.route[index]);
      if (!target) continue;
      const targetReference = reference(target);
      if (ctx.model && reference(ctx.model) !== targetReference && !(await pi.setModel(target))) {
        continue;
      }
      active.routeIndex = index;
      active.currentModel = targetReference;
      ctx.ui.setStatus(
        STATUS_KEY,
        ctx.ui.theme.fg("accent", `${active.pin.skill} on ${target.id}`),
      );
      return target;
    }
    return undefined;
  };

  const release = async (ctx: ExtensionContext) => {
    const activePin = active;
    if (!activePin) return;
    active = null;
    const pinned = activePin.pin;

    const previous = pinned.previousModel ? fromReference(ctx, pinned.previousModel) : undefined;
    if (previous) await pi.setModel(previous);
    pi.setThinkingLevel(pinned.previousThinking);
    pi.appendEntry(CUSTOM_TYPE, { ...pinned, state: "released" });
    ctx.ui.setStatus(STATUS_KEY, undefined);
  };

  pi.on("session_start", async (_event, ctx) => {
    active = null;
    let stranded: SkillModelPinV1 | null = null;
    try {
      stranded = latestPin(ctx.sessionManager.getBranch());
    } catch {
      return;
    }
    if (stranded?.state !== "pinned") return;
    active = {
      pin: stranded,
      route: [stranded.model],
      routeIndex: 0,
      currentModel: stranded.model,
    };
    await release(ctx);
  });

  pi.on("input", async (event, ctx) => {
    const invoked = SKILL_COMMAND.exec(event.text.trim());
    if (invoked) {
      const path = skillPath(pi, invoked[1]);
      if (path) await pin(invoked[1], path, ctx);
    }
    return { action: "continue" };
  });

  pi.on("tool_result", async (event, ctx) => {
    if (event.toolName !== "read" || event.isError) return;
    const path = event.input.path;
    if (typeof path !== "string" || basename(path) !== SKILL_FILE) return;
    await pin(basename(dirname(path)), path, ctx);
  });

  pi.on("message_end", async (event, ctx) => {
    if (!active || event.message.role !== "assistant") return;
    const message = event.message;
    if (message.stopReason !== "error") return;
    if (!message.errorMessage || !ACCOUNT_OR_LIMIT_ERROR.test(message.errorMessage)) return;
    if (`${message.provider}/${message.model}` !== active.currentModel) return;

    const target = await fallback(ctx);
    if (!target) return;
    ctx.ui.notify(
      `${active.pin.skill}: ${message.provider} account or capacity failure; retrying with ${reference(target)}`,
      "warning",
    );
    return {
      message: {
        ...message,
        errorMessage: `Provider returned error: retrying ${active.pin.skill} with ${reference(target)}`,
      },
    };
  });

  pi.on("agent_settled", async (_event, ctx) => {
    await release(ctx);
  });
}
