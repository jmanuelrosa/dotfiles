import { readFileSync, realpathSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const routingPath = resolve(dirname(realpathSync(fileURLToPath(import.meta.url))), "../../model-routing.json");
const { cursorModels } = JSON.parse(readFileSync(routingPath, "utf8")) as { cursorModels: string[] };
const allowed = new Set(cursorModels);
const POLICY_MARKER = Symbol.for("dotfiles.cursor-model-policy");

function assertAllowed(model: { id: string }): void {
  if (!allowed.has(model.id)) {
    throw new Error(`Cursor model "${model.id}" is disabled by model-routing.json; use ${cursorModels.join(" or ")}`);
  }
}

export default function registerCursorModelPolicy(pi: ExtensionAPI): void {
  const install = (_event: unknown, ctx: ExtensionContext) => {
    const provider = ctx.modelRegistry.getProvider("cursor");
    if (!provider || Reflect.get(provider, POLICY_MARKER) === true) return;

    pi.registerProvider({
      ...provider,
      [POLICY_MARKER]: true,
      getModels: () => provider.getModels().filter((model) => allowed.has(model.id)),
      filterModels: (models, credential) =>
        (provider.filterModels?.(models, credential) ?? models).filter((model) => allowed.has(model.id)),
      stream: (model, context, options) => {
        assertAllowed(model);
        return provider.stream(model, context, options);
      },
      streamSimple: (model, context, options) => {
        assertAllowed(model);
        return provider.streamSimple(model, context, options);
      },
    });
  };

  pi.on("session_start", install);
  pi.on("before_agent_start", install);
  pi.on("turn_start", install);
  pi.on("model_select", install);
  pi.on("session_before_compact", install);
  pi.on("session_before_tree", install);
}
