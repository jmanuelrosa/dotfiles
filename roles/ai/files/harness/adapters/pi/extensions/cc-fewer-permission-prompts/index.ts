import type { ExtensionAPI, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";

const COMMAND = "cc-fewer-permission-prompts";
const DESCRIPTION = "Mine transcripts for read-only commands and add them to the shared permission policy";

function skillPrompt(args: string): string {
  const guidance = args.trim();
  return guidance ? `/skill:${COMMAND} ${guidance}` : `/skill:${COMMAND}`;
}

function invokeSkill(pi: ExtensionAPI, args: string, ctx: ExtensionCommandContext): void {
  const prompt = skillPrompt(args);
  if (ctx.isIdle()) {
    pi.sendUserMessage(prompt, { expandPromptTemplates: true });
    return;
  }
  pi.sendUserMessage(prompt, { expandPromptTemplates: true, deliverAs: "followUp" });
}

export default function registerFewerPermissionPrompts(pi: ExtensionAPI): void {
  pi.registerCommand(COMMAND, {
    description: DESCRIPTION,
    handler: async (args, ctx) => invokeSkill(pi, args, ctx),
  });
}
