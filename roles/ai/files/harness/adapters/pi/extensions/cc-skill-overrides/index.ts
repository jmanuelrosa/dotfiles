import { readFileSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

type OverrideState = "on" | "name-only" | "user-invocable-only" | "off";

interface ListedSkill {
  name: string;
  description: string;
  disableModelInvocation: boolean;
}

// Rendered by harness-build from the same registry and override table as Claude's skillOverrides.
// Reached through the realpath because this file is loaded through the link in ~/.pi/agent/extensions.
const OVERRIDES_PATH = join(
  dirname(realpathSync(fileURLToPath(import.meta.url))),
  "..",
  "..",
  "generated",
  "skill-overrides.json",
);

function loadOverrides(path: string = OVERRIDES_PATH): Record<string, OverrideState> {
  return JSON.parse(readFileSync(path, "utf8"));
}

/**
 * Claude's four states, on the copies pi builds the system prompt from.
 *
 * pi's prompt lists only skills without `disableModelInvocation`, which is the model-facing half of
 * both `off` and `user-invocable-only`; `name-only` keeps the entry and drops what it says.
 */
function applyOverrides(skills: ListedSkill[], overrides: Record<string, OverrideState>): void {
  for (const [index, skill] of skills.entries()) {
    const state = overrides[skill.name];
    if (state === "name-only") skills[index] = { ...skill, description: "" };
    if (state === "user-invocable-only" || state === "off") skills[index] = { ...skill, disableModelInvocation: true };
  }
}

// The user-facing half of `off`, which pi has no setting for: `/skill:name` still expands otherwise.
function refusedInvocation(text: string, overrides: Record<string, OverrideState>): string | undefined {
  const name = /^\/skill:(\S+)/.exec(text.trim())?.[1];
  return name !== undefined && overrides[name] === "off" ? name : undefined;
}

export default function (pi: ExtensionAPI) {
  const overrides = loadOverrides();

  pi.on("before_agent_start", async (event) => {
    applyOverrides(event.systemPromptOptions.skills ?? [], overrides);
  });

  pi.on("input", async (event, ctx) => {
    const name = refusedInvocation(event.text, overrides);
    if (name === undefined) return undefined;
    ctx.ui.notify(`Skill "${name}" is off in skillOverrides.`, "warning");
    return { action: "handled" };
  });
}
