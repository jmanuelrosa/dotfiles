# shell

Sets up the interactive shell stack: Fish, Ghostty, Starship, and Television. Manages every config that lives under `~/.config/{fish,ghostty,starship,television}/`.

## What it does

- Installs `fish`, `fisher`, `starship`, `gnupg` formulas and the `ghostty` cask via `BREW_PACKAGES`.
- Adds fish to `/etc/shells` and switches the user's login shell to fish.
- Installs Fisher plugins listed in `FISH_PLUGINS`.
- Backs up any pre-existing fish / ghostty / starship / television configs to `<repo>/backups/` before symlinking.
- Symlinks Ghostty config, fish `config.fish` + conf.d snippets + functions, and the Starship prompt config from `files/`.
- Renders `~/.config/fish/conf.d/secrets.fish` from `templates/secrets.fish.j2` using vault vars (mode 0600).
- Television management:
  - Runs `tv update-channels` to fetch the upstream cable catalog.
  - Prunes any non-symlink `.toml` in `~/.config/television/cable/` whose basename isn't in `TV_CABLE_ALLOWLIST` — keeps the cable set tight despite upstream syncing everything.
  - Symlinks every `.toml` under `files/television/cable/` into `~/.config/television/cable/` (via `with_fileglob`, so dropping a new cable in the repo is self-installing).
  - Symlinks `files/television/config.toml` into `~/.config/television/config.toml`.
  - Generates `~/.config/television/shell/integration.fish` from `tv init fish` so the integration always matches the installed `tv` version (the file is no longer vendored).

## Vars

- `FISH_PATH` (defaults/main.yml) — Apple Silicon Homebrew fish path. Override per-profile if your layout differs.
- `FISH_PLUGINS` (defaults/main.yml) — list of Fisher plugin specs.
- `BREW_PACKAGES` (defaults/main.yml) — fish, fisher, starship, gnupg formulas + ghostty cask.
- `TV_CABLE_ALLOWLIST` (defaults/main.yml) — bare cable names (no `.toml`) of upstream television cables to keep after `tv update-channels`. Anything else that isn't a symlink gets pruned each run. Symlinks (i.e. the cables vendored in `files/television/cable/`) are always preserved regardless of this list.

## Files

- `files/fish/` — `config.fish`, `conf.d/{aliases,exports}.fish`, plus functions: `clean_claude` (+ `_clean_claude_sweep`, `_clean_claude_pretty`), `clean_docker`, `clean_node`, `create_gitconfig`, `claude-skill`, `claude-mcp`, `claude-agent`, `_tv_claude_list`, `_tv_claude_toggle`, `tv_change_dir`. (Work-only helpers like `_tv_jira` live in the `work` role.)
- `files/ghostty/config` — Ghostty terminal config.
- `files/starship.toml` — Starship prompt config.
- `files/television/config.toml` — top-level television config (keybindings, theme, shell-integration channel triggers).
- `files/television/cable/*.toml` — vendored custom channels. Each one becomes a symlink in `~/.config/television/cable/`. Currently ships: `aerospace`, `claude-agents`, `claude-skills`, `sentry`. (The `jira` cable lives in the `work` role since it depends on `acli`.)

## Templates

- `templates/secrets.fish.j2` — exports `NPM_TOKEN` from vault. Mode 0600.

## Custom fish commands worth knowing

- `claude-skill {list|add|remove|outdated|update}` and `claude-agent …` — project-scoped management of Claude Code skills and agents.
- `claude-mcp` — wrapper for the Claude MCP CLI.
- `clean_claude {skills|agents|all}` — cleans the **current project**: `skills`/`agents` drop everything that isn't a dotfiles-managed symlink, `all` wipes `.claude` outright.
- `clean_claude sweep [root] [--dry-run] [--exclude PATTERN]` (alias `clean:claude:sweep`) — walks `$HOME` (or `root`) with `fd` and removes **every** `.claude` it finds, skipping vendored and app-owned trees: `node_modules`, `~/Library`, the bun/npm/yarn/cargo/gradle caches, `.venv`, `Pods`, `.git`, … Add more with `--exclude`, or permanently via `CLEAN_CLAUDE_EXCLUDES`. Workspace dirs (`apps/*`, `packages/*`) are *not* exempt — a `.claude` you authored there is a hit. Candidates are listed before anything is touched, git-tracked ones are flagged, and `~/.claude` is gated separately (it holds credentials, history and the `ai` role's symlinks; restoring it is `make run-role ROLE=ai` plus a re-login).
- `tv_change_dir` — bound to `alt-c` in `config.fish`. Pipes the `dirs` television channel into `tv` and `cd`s to the pick.

## Side effects

- Modifies `/etc/shells` (requires sudo).
- Changes the user's default shell (requires sudo).
- Pre-existing target files are copied to `backups/` on first run.
- `tv update-channels` performs a network fetch; allowlist pruning then removes non-symlink cables outside `TV_CABLE_ALLOWLIST` on every run.
