/**
 * skill-model - a skill that names a model runs on that model.
 *
 * Pi's skill loader reads `name`, `description` and `disable-model-invocation` from a
 * SKILL.md and drops everything else, so `model:` is inert under pi while Claude Code
 * honours it. This closes that gap without a second declaration: the key stays one plain
 * string in the shared SKILL.md, and bare values resolve against this session's scoped
 * catalogue, so reordering `enabledModels` reorders which model a bare `opus` wins.
 *
 * model-routing.json redirects legacy Cursor pins before lookup, then switches to a mapped
 * Codex model when the primary has no auth or returns an account or capacity error. Unpinned
 * agent runs arm the same routes from their selected model, which also covers child sessions
 * created by pi-subagents. The error is rewritten to pi's retryable provider form after the
 * model switch, so pi repeats the failed assistant turn on the fallback; network, server and
 * generic SDK failures retain pi's normal provider retry behavior.
 *
 * The pin lasts one agent run, which is the boundary Claude Code uses as well: the
 * override "applies for the rest of the current turn" and the session model resumes on the
 * next prompt.
 *
 * Prior model and thinking level are recorded as a session entry rather than held in a
 * closure, because a resume or a reload mid-pin would otherwise strand the session on the
 * pinned model with nothing left that knows what to restore.
 */

import { readFileSync, realpathSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
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
const routingPath = resolve(dirname(realpathSync(fileURLToPath(import.meta.url))), "../../model-routing.json");
const MODEL_ROUTING = JSON.parse(readFileSync(routingPath, "utf8")) as {
  redirects: Readonly<Record<string, string>>;
  fallbacks: Readonly<Record<string, readonly string[]>>;
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

interface ActiveRoute {
  route: readonly string[];
  routeIndex: number;
  currentModel: string;
}

interface ActivePin extends ActiveRoute {
  pin: SkillModelPinV1;
}

interface ActiveRunRoute extends ActiveRoute {
  previousModel: string;
  previousThinking: ThinkingLevel;
  switched: boolean;
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
  const redirected = MODEL_ROUTING.redirects[spec.toLowerCase()] ?? spec;
  const primary = resolveSpec(ctx, redirected);
  const primaryReference = primary ? reference(primary) : redirected;
  const fallbacks = MODEL_ROUTING.fallbacks[primaryReference.toLowerCase()] ?? [];
  return [primaryReference, ...fallbacks];
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
  let runRoute: ActiveRunRoute | null = null;

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

  const armRunRoute = async (ctx: ExtensionContext) => {
    if (active || runRoute || !ctx.model) return;

    const previousModel = reference(ctx.model);
    const route = routeFor(ctx, previousModel);
    if (route.length === 1 && route[0].toLowerCase() === previousModel.toLowerCase()) return;

    const previousThinking = pi.getThinkingLevel();
    let selected: { target: Model; index: number } | undefined;
    for (let index = 0; index < route.length; index += 1) {
      const target = resolveSpec(ctx, route[index]);
      if (!target) continue;
      const alreadySelected = ctx.model && reference(ctx.model) === reference(target);
      if (!alreadySelected && !(await pi.setModel(target))) continue;
      selected = { target, index };
      break;
    }
    if (!selected) return;

    const currentModel = reference(selected.target);
    runRoute = {
      route,
      routeIndex: selected.index,
      currentModel,
      previousModel,
      previousThinking,
      switched: currentModel !== previousModel,
    };
    if (selected.index > 0) {
      ctx.ui.notify(
        `agent run: ${route[0]} is unavailable; using ${currentModel}`,
        "warning",
      );
    }
  };

  const advance = async (
    route: ActiveRoute,
    ctx: ExtensionContext,
  ): Promise<Model | undefined> => {
    for (let index = route.routeIndex + 1; index < route.route.length; index += 1) {
      const target = resolveSpec(ctx, route.route[index]);
      if (!target) continue;
      const targetReference = reference(target);
      if (ctx.model && reference(ctx.model) !== targetReference && !(await pi.setModel(target))) {
        continue;
      }
      route.routeIndex = index;
      route.currentModel = targetReference;
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

  const releaseRunRoute = async (ctx: ExtensionContext) => {
    const route = runRoute;
    runRoute = null;
    if (!route?.switched) return;

    const previous = fromReference(ctx, route.previousModel);
    if (previous) await pi.setModel(previous);
    pi.setThinkingLevel(route.previousThinking);
  };

  pi.on("session_start", async (_event, ctx) => {
    active = null;
    runRoute = null;
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

  pi.on("before_agent_start", async (_event, ctx) => {
    await armRunRoute(ctx);
  });

  pi.on("message_end", async (event, ctx) => {
    const skillPin = active;
    const route = skillPin ?? runRoute;
    if (!route || event.message.role !== "assistant") return;
    const message = event.message;
    if (message.stopReason !== "error") return;
    if (!message.errorMessage || !ACCOUNT_OR_LIMIT_ERROR.test(message.errorMessage)) return;
    if (`${message.provider}/${message.model}` !== route.currentModel) return;

    const target = await advance(route, ctx);
    if (!target) return;
    const label = skillPin?.pin.skill ?? "agent run";
    if (skillPin) {
      ctx.ui.setStatus(
        STATUS_KEY,
        ctx.ui.theme.fg("accent", `${skillPin.pin.skill} on ${target.id}`),
      );
    } else if (runRoute) {
      runRoute.switched = true;
    }
    ctx.ui.notify(
      `${label}: ${message.provider} account or capacity failure; retrying with ${reference(target)}`,
      "warning",
    );
    return {
      message: {
        ...message,
        errorMessage: `Provider returned error: retrying ${label} with ${reference(target)}`,
      },
    };
  });

  pi.on("agent_settled", async (_event, ctx) => {
    await release(ctx);
    await releaseRunRoute(ctx);
  });
}
