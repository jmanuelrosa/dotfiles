import type { ExtensionAPI, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";

const SKILLS = {
  commit: "Stage changes and create approved conventional commits",
  pr: "Push the branch and open a pull request or merge request",
} as const;

type SkillName = keyof typeof SKILLS;

function skillPrompt(name: SkillName, args: string): string {
  const guidance = args.trim();
  return guidance ? `/skill:${name} ${guidance}` : `/skill:${name}`;
}

function invokeSkill(pi: ExtensionAPI, name: SkillName, args: string, ctx: ExtensionCommandContext): void {
  const prompt = skillPrompt(name, args);
  if (ctx.isIdle()) {
    pi.sendUserMessage(prompt, { expandPromptTemplates: true });
    return;
  }
  pi.sendUserMessage(prompt, { expandPromptTemplates: true, deliverAs: "followUp" });
}

export default function registerSkillAliases(pi: ExtensionAPI): void {
  for (const [name, description] of Object.entries(SKILLS) as [SkillName, string][]) {
    pi.registerCommand(name, {
      description,
      handler: async (args, ctx) => invokeSkill(pi, name, args, ctx),
    });
  }
}
