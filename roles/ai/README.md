# ai

Installs and configures AI tooling: Claude Code, Gemini CLI, Pi (mariozechner), ChatGPT desktop, CodexBar.

## What it does

- Installs gemini-cli, pi-coding-agent, and casks for ChatGPT/Claude/Claude Code/Cursor/CodexBar via `BREW_PACKAGES`.
- Symlinks per-tool configs into `~/.claude/`, `~/.gemini/`, `~/.pi/agent/`.
- Symlinks `files/claude/skills/` into `~/.pi/agent/skills/` so Claude skills are reusable from the Pi agent.
- Symlinks each tool named in `AI_SCRIPTS` into `~/.local/bin/`, from `files/scripts/<name>/<name>`. `claude-kit` is the only one: `weekly-recap` belongs to the `work` role, whose Jira, GitHub and GitLab accounts it actually queries.
- Runs `claude-kit sync`, which links every artifact tagged `global` into `~/.claude/skills/` and `~/.claude/agents/` so it is available to Claude Code in every project without a per-project `add`, and **unlinks** any link there that is no longer in the derived set. Those directories are role-owned: what belongs in them is decided by the `global` group tag, not by where you ran a command from. Under `make check` the task passes `--dry-run`, so a check reports what it would change without changing it.

- Runs `herdr integration install claude` so Claude Code reports agent state to [herdr](https://herdr.dev). `herdr integration status` gates it: the task only runs when the line for `claude` is not `current (v<n>)`, so a herdr upgrade that ships a newer hook reinstalls on the next run.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — taps (`steipete/tap`), formulas (gemini-cli, pi-coding-agent), casks (chatgpt, claude, claude-code, cursor, codexbar).
- **There is no var for the global set, and nothing to maintain by hand.** `claude-kit sync` derives it from the `global` group tag in `skill-registry.json`, `agent-registry.json` and the plugin manifests, then expands the skills by one level of declared dependencies, which is why `~/.claude/skills/` holds more than the tagged set (`grilling` and `jira` arrive that way). Tag an entry `global` to add it. This role once derived the same set itself, in about 130 lines of Jinja; it is now one `command` task, because the tool already had to compute the set to answer "does this need `--global`?" and two copies of that rule drifted.

## Notes

The herdr integration is the one thing in `~/.claude/hooks/` this role does not symlink from the repo: herdr writes `herdr-agent-state.sh` there as a real file and appends its own `SessionStart` entry to `settings.json`, keyed on the absolute hook path. The `herdr` formula comes from the apps role, which runs before this one.

Claude Code fetches up-to-date docs for libraries, frameworks, SDKs, APIs, CLI tools and cloud services with the Context7 CLI, run on demand via `bunx ctx7` (bun is installed by the apps role) on the free anonymous tier — nothing is installed by this role and no API key is configured. The usage rule lives in `files/claude/CLAUDE.md`; the `CTX7_TELEMETRY_DISABLED` opt-out is exported by the shell role.
