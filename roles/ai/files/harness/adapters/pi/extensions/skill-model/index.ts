/**
 * skill-model - a skill that names a model runs on that model.
 *
 * Pi's skill loader reads `name`, `description` and `disable-model-invocation` from a
 * SKILL.md and drops everything else, so `model:` is inert under pi while Claude Code
 * honours it. This closes that gap without a second declaration: the key stays one plain
 * string in the shared SKILL.md, and bare values resolve against this session's scoped
 * catalogue, so reordering `enabledModels` reorders which model a bare `opus` wins.
 *
 * model-routing.json `redirects` translate a declared spec to the model pi should run
 * instead, before lookup, because the shared catalog names models pi has no auth for.
 * Unpinned agent runs apply the same redirects to the session's selected model.
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
const { redirects } = JSON.parse(readFileSync(routingPath, "utf8")) as {
  redirects: Readonly<Record<string, string>>;
};

interface SkillModelPinV1 {
  version: 1;
  state: "pinned" | "released";
  skill: string;
  model: string;
  previousModel: string | null;
  previousThinking: ThinkingLevel;
}

interface RunRedirect {
  previousModel: string;
  previousThinking: ThinkingLevel;
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

function redirected(spec: string): string {
  return redirects[spec.toLowerCase()] ?? spec;
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
  let active: SkillModelPinV1 | null = null;
  let runRedirect: RunRedirect | null = null;

  const pin = async (skill: string, path: string, ctx: ExtensionContext) => {
    if (active) return;
    const spec = declaredModel(path);
    if (!spec || spec.toLowerCase() === INHERIT) return;

    const target = resolveSpec(ctx, redirected(spec));
    if (!target) {
      ctx.ui.notify(`${skill} wants "${spec}", which no enabled model matches`, "warning");
      return;
    }
    const targetReference = reference(target);
    const previousModel = ctx.model ? reference(ctx.model) : null;
    if (previousModel === targetReference) return;

    const previousThinking = pi.getThinkingLevel();
    if (!(await pi.setModel(target))) {
      ctx.ui.notify(`${skill} wants ${targetReference}, which has no configured auth`, "warning");
      return;
    }

    active = {
      version: 1,
      state: "pinned",
      skill,
      model: targetReference,
      previousModel,
      previousThinking,
    };
    pi.appendEntry(CUSTOM_TYPE, active);
    ctx.ui.setStatus(STATUS_KEY, ctx.ui.theme.fg("accent", `${skill} on ${target.id}`));
  };

  const redirectRun = async (ctx: ExtensionContext) => {
    if (active || runRedirect || !ctx.model) return;

    const previousModel = reference(ctx.model);
    const spec = redirected(previousModel);
    if (spec === previousModel) return;
    const target = resolveSpec(ctx, spec);
    if (!target || reference(target) === previousModel) return;

    const previousThinking = pi.getThinkingLevel();
    if (!(await pi.setModel(target))) return;
    runRedirect = { previousModel, previousThinking };
  };

  const release = async (ctx: ExtensionContext) => {
    const pinned = active;
    if (!pinned) return;
    active = null;

    const previous = pinned.previousModel ? fromReference(ctx, pinned.previousModel) : undefined;
    if (previous) await pi.setModel(previous);
    pi.setThinkingLevel(pinned.previousThinking);
    pi.appendEntry(CUSTOM_TYPE, { ...pinned, state: "released" });
    ctx.ui.setStatus(STATUS_KEY, undefined);
  };

  const releaseRun = async (ctx: ExtensionContext) => {
    const run = runRedirect;
    runRedirect = null;
    if (!run) return;

    const previous = fromReference(ctx, run.previousModel);
    if (previous) await pi.setModel(previous);
    pi.setThinkingLevel(run.previousThinking);
  };

  pi.on("session_start", async (_event, ctx) => {
    active = null;
    runRedirect = null;
    let stranded: SkillModelPinV1 | null = null;
    try {
      stranded = latestPin(ctx.sessionManager.getBranch());
    } catch {
      return;
    }
    if (stranded?.state !== "pinned") return;
    active = stranded;
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
    await redirectRun(ctx);
  });

  pi.on("agent_settled", async (_event, ctx) => {
    await release(ctx);
    await releaseRun(ctx);
  });
}
