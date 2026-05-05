# ai

Installs and configures AI tooling: Claude Code, Gemini CLI, Pi (mariozechner), Ollama, ChatGPT desktop, CodexBar.

## What it does

- Installs gemini-cli, ollama, pi-coding-agent, and casks for ChatGPT/Claude/Claude Code/Cursor/CodexBar via `BREW_PACKAGES`.
- Symlinks per-tool configs into `~/.claude/`, `~/.gemini/`, `~/.pi/agent/`.
- Symlinks `files/claude/skills/` into `~/.pi/agent/skills/` so Claude skills are reusable from the Pi agent.
- Kills any running `ollama serve` so it stays on-demand.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — taps (`steipete/tap`), formulas (gemini-cli, ollama, pi-coding-agent), casks (chatgpt, claude, claude-code, cursor, codexbar).
- `OLLAMA_MODELS` (defaults/main.yml) — list of models to pull manually with `ollama pull`. Not pulled by the playbook.

## Notes

`pkill -x ollama` returns rc=1 if Ollama wasn't running; `failed_when` accepts rc 0 or 1.
