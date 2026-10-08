import { readFileSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";

const COMMAND = "cc-batch";
const PLACEHOLDER = "{{instruction}}";
const PROMPT_PATH = join(dirname(realpathSync(fileURLToPath(import.meta.url))), "prompt.md");
const TEMPLATE = readFileSync(PROMPT_PATH, "utf8");

const USAGE = [
  "Provide an instruction describing the batch change you want to make.",
  "Examples:",
  `  /${COMMAND} migrate from react to vue`,
  `  /${COMMAND} replace all uses of lodash with native equivalents`,
  `  /${COMMAND} add type annotations to all untyped function parameters`,
].join("\n");

const NOT_A_REPOSITORY = `/${COMMAND} runs each worker in its own git worktree, and none can be created here because this directory is not inside a git repository. Run /${COMMAND} from inside one.`;

function orchestrationPrompt(instruction: string): string {
  return TEMPLATE.split(PLACEHOLDER).join(instruction);
}

async function insideRepository(pi: ExtensionAPI, cwd: string): Promise<boolean> {
  try {
    const result = await pi.exec("git", ["rev-parse", "--is-inside-work-tree"], { cwd });
    return result.code === 0 && result.stdout.trim() === "true";
  } catch {
    return false;
  }
}

async function handle(pi: ExtensionAPI, args: string, ctx: ExtensionCommandContext): Promise<void> {
  const instruction = args.trim();
  if (!instruction) {
    ctx.ui.notify(USAGE, "warning");
    return;
  }
  if (!(await insideRepository(pi, ctx.cwd))) {
    ctx.ui.notify(NOT_A_REPOSITORY, "error");
    return;
  }

  const prompt = orchestrationPrompt(instruction);
  if (ctx.isIdle()) {
    pi.sendUserMessage(prompt);
    return;
  }
  pi.sendUserMessage(prompt, { deliverAs: "followUp" });
}

export default function registerCcBatch(pi: ExtensionAPI): void {
  pi.registerCommand(COMMAND, {
    description: "Plan a large change, then run worktree-isolated pi-subagents workers that each open a PR",
    handler: async (args, ctx) => handle(pi, args, ctx),
  });
}
