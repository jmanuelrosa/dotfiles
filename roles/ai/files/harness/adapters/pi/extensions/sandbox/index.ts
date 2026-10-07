import { readFileSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  createBashToolDefinition,
  type ExtensionAPI,
  getAgentDir,
  isToolCallEventType,
  SettingsManager,
  type ToolDefinition,
} from "@earendil-works/pi-coding-agent";

const CONFIG_PATH = join(dirname(realpathSync(fileURLToPath(import.meta.url))), "..", "..", "sandbox.json");
const excludedCommands: string[] = JSON.parse(readFileSync(CONFIG_PATH, "utf8")).excludedCommands;

function isExcludedCommand(command: string): boolean {
  const executable = /^[ \t]*([a-z][a-z0-9-]*)(?:[ \t]|$)/.exec(command)?.[1];
  return executable !== undefined && excludedCommands.includes(executable) && !/[;&|<>`$\\\r\n()]/.test(command);
}

export default async function (pi: ExtensionAPI) {
  const localCwd = process.cwd();
  const shellPath = SettingsManager.create(localCwd).getShellPath();
  const localBash = createBashToolDefinition(localCwd, { shellPath });
  const { default: sandbox } = await import(join(getAgentDir(), "npm", "node_modules", "pi-sandbox", "index.ts"));

  const adapter = new Proxy(pi, {
    get(target, property) {
      if (property === "registerTool") {
        return (tool: ToolDefinition) => target.registerTool(tool.name !== "bash" ? tool : {
          ...tool,
          async execute(id, params, signal, onUpdate, ctx) {
            if (isExcludedCommand(params.command as string)) {
              return localBash.execute(id, params, signal, onUpdate, ctx);
            }
            return tool.execute(id, params, signal, onUpdate, ctx);
          },
        });
      }
      if (property === "on") {
        return ((event, handler) => {
          if (event === "tool_call") {
            return target.on("tool_call", (call, ctx) => {
              if (isToolCallEventType("bash", call) && isExcludedCommand(call.input.command)) return;
              return handler(call, ctx);
            });
          }
          if (event === "user_bash") {
            return target.on("user_bash", (call, ctx) => {
              if (isExcludedCommand(call.command)) return;
              return handler(call, ctx);
            });
          }
          return target.on(event, handler);
        }) as ExtensionAPI["on"];
      }
      return Reflect.get(target, property);
    },
  });
  await sandbox(adapter);
}
