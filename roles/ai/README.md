# ai

Installs and configures AI tooling: Claude Code, Gemini CLI, Pi (mariozechner), ChatGPT desktop, CodexBar.

## What it does

- Installs gemini-cli, pi-coding-agent, and casks for ChatGPT/Claude/Claude Code/Cursor/CodexBar via `BREW_PACKAGES`.
- Symlinks per-tool configs into `~/.claude/`, `~/.gemini/`, `~/.pi/agent/`.
- Symlinks `files/claude/skills/` into `~/.pi/agent/skills/` so Claude skills are reusable from the Pi agent.
- Symlinks the skills in `GLOBAL_CLAUDE_SKILLS` into `~/.claude/skills/` so they are available to Claude Code in every project without `claude-skill add`.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — taps (`steipete/tap`), formulas (gemini-cli, pi-coding-agent), casks (chatgpt, claude, claude-code, cursor, codexbar).
- `GLOBAL_CLAUDE_SKILLS` (defaults/main.yml) — skills under `files/claude/skills/` to symlink into `~/.claude/skills/` for project-wide Claude Code availability.

## Notes

Claude Code fetches up-to-date library docs with the Context7 CLI, run on demand via `bunx ctx7` (bun is installed by the apps role) on the free anonymous tier — nothing is installed by this role and no API key is configured. The usage rule lives in `files/claude/CLAUDE.md`; the `CTX7_TELEMETRY_DISABLED` opt-out is exported by the shell role.
