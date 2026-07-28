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

- `files/fish/` — `config.fish`, `conf.d/{aliases,exports}.fish`, plus functions: `clean_claude` (+ `_clean_claude_{usage,excludes,find,confirm,tracked,purge_state,state_roots,worktree_main,pretty}`), `clean_docker`, `clean_node`, `create_gitconfig`, `claude-skill`, `claude-mcp`, `claude-agent`, `_tv_claude_list`, `_tv_claude_toggle`, `tv_change_dir`. (Work-only helpers like `_tv_jira` live in the `work` role.)
- `files/ghostty/config` — Ghostty terminal config.
- `files/starship.toml` — Starship prompt config.
- `files/television/config.toml` — top-level television config (keybindings, theme, shell-integration channel triggers).
- `files/television/cable/*.toml` — vendored custom channels. Each one becomes a symlink in `~/.config/television/cable/`. Currently ships: `aerospace`, `claude-agents`, `claude-skills`, `sentry`. (The `jira` cable lives in the `work` role since it depends on `acli`.)

## Templates

- `templates/secrets.fish.j2` — exports `NPM_TOKEN` from vault. Mode 0600.

## Custom fish commands worth knowing

- `claude-skill {list|add|remove|outdated|update}` and `claude-agent …` — project-scoped management of Claude Code skills and agents.
- `claude-mcp` — wrapper for the Claude MCP CLI.
- `clean_claude [MODE] [ROOT] [--dry-run] [--exclude PATTERN] [--include PATTERN]` — one recursive cleaner with four modes, always walking `ROOT` (default: cwd) and everything below it with `fd`.
  - `project` (the default, alias `clean:claude`) removes every `.claude` in the tree, then purges Claude Code's stored state for the tree.
    State is scoped from the two real stores, not from `.claude` presence, because a project keeps transcripts and a `~/.claude.json` entry long after its `.claude` is gone: one `claude project purge --yes ROOT` call sweeps transcripts, tasks, file history and `history.jsonl` for the whole tree (the CLI prefix-matches those at path-segment boundaries), then one exact call per `~/.claude.json` project at or below `ROOT` removes its config entry (those are matched exactly, never by prefix, so subprojects would otherwise keep their trust and MCP servers).
    A **linked git worktree is skipped** with an explanation: purging one deletes its *main* repo's config entry, since the CLI resolves a worktree path to the main checkout and offers no way to drop transcripts without it. `--worktree-config` opts in.
    Note `--exclude`/`--include` govern which directories get deleted, not state scoping, which is keyed by path in the state stores.
  - `skills` / `agents` (aliases `clean:claude:skills`, `clean:claude:agents`) remove just `.claude/skills` or `.claude/agents` at every level and leave the rest of each `.claude` alone.
  - `purge` (alias `clean:claude:purge`) is the machine-wide nuke: every `.claude` under `$HOME` **plus** `~/.claude` itself, plus `claude project purge --all --yes`.
  Every mode takes `--dry-run`, which lists the exact directories and pipes `--dry-run` through to the `claude` CLI so you see the real state plan before committing.
- `clean_claude` never touches a `.claude` inside a dependency, cache, build or app-owned tree: `node_modules`, `packages`, `apps`, `deps`, `vendor`, `Pods`, `dist`, `build`, `target`, `.next`, `.venv`, `~/Library`, the bun/npm/yarn/cargo/gradle caches, `.git`, and friends (see `_clean_claude_excludes`).
  Add names for one run with `--exclude`, permanently via `CLEAN_CLAUDE_EXCLUDES`, or opt a default-excluded name back in with `--include` (e.g. `--include packages` when the monorepo workspace really is yours).
  Candidates are always listed before anything is touched and git-tracked ones are flagged.
  Only `purge` may touch `~/.claude`: it holds credentials, history, plugins and the `ai` role's symlinks, so other modes skip it with a note even when run from `$HOME`, and `purge` gates it behind typing `purge` (restoring is `make run-role ROLE=ai` plus a re-login).
- `tv_change_dir` — bound to `alt-c` in `config.fish`. Pipes the `dirs` television channel into `tv` and `cd`s to the pick.

## Side effects

- Modifies `/etc/shells` (requires sudo).
- Changes the user's default shell (requires sudo).
- Pre-existing target files are copied to `backups/` on first run.
- `tv update-channels` performs a network fetch; allowlist pruning then removes non-symlink cables outside `TV_CABLE_ALLOWLIST` on every run.
