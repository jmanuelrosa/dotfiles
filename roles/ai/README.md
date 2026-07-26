# ai

Installs and configures AI tooling: Claude Code, Gemini CLI, Pi (mariozechner), ChatGPT desktop, CodexBar.

## What it does

- Installs gemini-cli, pi-coding-agent, and casks for ChatGPT/Claude/Claude Code/Cursor/CodexBar via `BREW_PACKAGES`.
- Symlinks per-tool configs into `~/.claude/`, `~/.gemini/`, `~/.pi/agent/`.
- Symlinks `files/claude/skills/` into `~/.pi/agent/skills/` so Claude skills are reusable from the Pi agent.
- Symlinks the global skills and agents into `~/.claude/skills/` and `~/.claude/agents/` so they are available to Claude Code in every project without a per-project `add`, and **prunes** any link there that is no longer in the derived set. Those two directories are role-owned: what belongs in them is decided by the `global` group tag, not by where you ran a command from.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — taps (`steipete/tap`), formulas (gemini-cli, pi-coding-agent), casks (chatgpt, claude, claude-code, cursor, codexbar).
- `GLOBAL_CLAUDE_SKILLS` / `GLOBAL_CLAUDE_AGENTS` are **not** vars you set: `tasks/main.yml` derives them from the `global` group tag in `skill-registry.json` and `agent-registry.json`. `GLOBAL_CLAUDE_SKILLS_EFFECTIVE` then expands the skills by one level of declared dependencies, which is why `~/.claude/skills/` holds more than the tagged set (`grilling` and `jira` arrive that way). Tag an entry `global` to add it; there is no list to maintain.

## Notes

Claude Code fetches up-to-date library docs with the Context7 CLI, run on demand via `bunx ctx7` (bun is installed by the apps role) on the free anonymous tier — nothing is installed by this role and no API key is configured. The usage rule lives in `files/claude/CLAUDE.md`; the `CTX7_TELEMETRY_DISABLED` opt-out is exported by the shell role.
