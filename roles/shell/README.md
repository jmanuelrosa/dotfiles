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

- `files/fish/` — `config.fish`, `conf.d/{aliases,exports}.fish`, plus functions: `clean_claude` (+ `_clean_claude_{usage,excludes,find,confirm,tracked,purge_state,state_roots,worktree_main}`), `clean_all`, `clean_docker`, `clean_node`, `create_gitconfig`, `lns` (+ `_lns_{usage,target}`), `wt`, `_tv_claude_list`, `_tv_claude_toggle` (both thin: every fact they show or act on comes from `claude-kit list --json`), `tv_change_dir`, `tv_history`, `_ui`. Dropping a new `.fish` in there is self-installing: the role globs the directory, and prunes links whose source is gone. (Work-only helpers like `_tv_jira` live in the `work` role.)
- `files/ghostty/config` — Ghostty terminal config.
- `files/starship.toml` — Starship prompt config.
- `files/television/config.toml` — top-level television config (keybindings, theme, shell-integration channel triggers).
- `files/television/cable/*.toml` — vendored custom channels. Each one becomes a symlink in `~/.config/television/cable/`. Currently ships: `aerospace`, `claude-agents`, `claude-skills`, `sentry`. (The `jira` cable lives in the `work` role since it depends on `acli`.)

## Templates

- `templates/secrets.fish.j2` — exports `NPM_TOKEN` from vault. Mode 0600. Cloudflare credentials are deliberately not here: `cf` and `wrangler` each authenticate themselves, because an exported `CLOUDFLARE_API_TOKEN` outranks `cf`'s named profiles and pins every command to one account.

## Output style

Every fish function here prints through `_ui`, the shared line vocabulary in [`files/fish/functions/_ui.fish`](files/fish/functions/_ui.fish). It is one style expressed twice: `dotkit/ui.py` is the python half, and a differential test renders every kind through both and compares the bytes, so the two cannot drift.

```fish
_ui title "🧹 Removing Claude artifacts"   # bold; the only line kind that takes a topic emoji
_ui step  "Fetching upstream"              # cyan →
_ui ok    "Linked 'commit'"                # green ✓
_ui warn  "3 were git-tracked"             # yellow ⚠
_ui err   "Not a directory"                # magenta ✗, to stderr
_ui item  "~/dev/api/.claude"              # dim ·, indented 2
_ui note  "restore with make run-role"     # dim aside, indented 2
_ui done  "Removed 3 of 3"                 # ✨ closing summary
```

`-i N` overrides the indent (before the kind: `_ui -i 4 ok "…"`). Three helpers compose instead of printing: `_ui color cyan` yields the escape alone, `_ui paint cyan "text"` wraps and resets it, and `_ui path ~/dev/api` collapses `$HOME` back to `~`. Status is always a narrow coloured glyph and an emoji only ever appears on a `title` or a `done`, because a double-width marker knocks every following column out of alignment; the full rationale is in the repo `CLAUDE.md`.

Unlike a bare `set_color`, `_ui` decides colour per stream: `NO_COLOR` beats `FORCE_COLOR` beats the tty check, so piping any of these commands into a file gives plain text.

That decision is made where a line is **printed**, never where a fragment is composed. `_ui color` and `_ui paint` only run inside a command substitution, and fish gives one a pipe for stdout, so a tty check there is false however the command was run: they emit their escapes regardless (only `NO_COLOR` silences them) and the printing kind strips what its stream refuses. A script building a row with `echo` instead has nothing to strip it, so it asks **`_ui color-enabled`** first, as a bare command, and fills its palette inside that `if`.

**Television cable rows** (`_tv_claude_fmt`) stay outside the vocabulary on purpose: they are fixed-width columns a picker lays out and filters, not lines a human reads.

## Custom fish commands worth knowing

- `clean_claude [MODE] [ROOT] [--dry-run] [--exclude PATTERN] [--include PATTERN]` — one recursive cleaner with four modes, always walking `ROOT` (default: cwd) and everything below it with `fd`.
  - `project` (the default, alias `clean:claude`) removes every `.claude` in the tree, then purges Claude Code's stored state for the tree.
    State is scoped from the two real stores, not from `.claude` presence, because a project keeps transcripts and a `~/.claude.json` entry long after its `.claude` is gone: one `claude project purge --yes ROOT` call sweeps transcripts, tasks, file history and `history.jsonl` for the whole tree (the CLI prefix-matches those at path-segment boundaries), then one exact call per `~/.claude.json` project at or below `ROOT` removes its config entry (those are matched exactly, never by prefix, so subprojects would otherwise keep their trust and MCP servers).
    A **linked git worktree is skipped** with an explanation: purging one deletes its *main* repo's config entry, since the CLI resolves a worktree path to the main checkout and offers no way to drop transcripts without it. `--worktree-config` opts in.
    Note `--exclude`/`--include` govern which directories get deleted, not state scoping, which is keyed by path in the state stores.
  - `skills` / `agents` (aliases `clean:claude:skills`, `clean:claude:agents`) remove just `.claude/skills` or `.claude/agents` at every level and leave the rest of each `.claude` alone.
  - `purge` (alias `clean:claude:purge`) is the machine-wide nuke: every `.claude` under `$HOME` **plus** `~/.claude` itself, plus `claude project purge --all --yes`.
  Every mode takes `--dry-run`, which lists the exact directories and pipes `--dry-run` through to the `claude` CLI so you see the real state plan before committing.
- `clean_claude` never touches a `.claude` inside a dependency, cache, build or app-owned tree: `node_modules`, `deps`, `dependencies`, `submodules`, `vendor`, `Pods`, `dist`, `build`, `target`, `.next`, `.venv`, `~/Library`, the bun/npm/yarn/cargo/gradle caches, `.git`, and friends (see `_clean_claude_excludes`).
  Every name on that list has to mean "someone else's code" unambiguously, since a false hit is an unrecoverable `rm -rf` of your own settings and history.
  **Monorepo workspace directories are deliberately not on it.** `packages` and `apps` used to be, and the effect was that a `.claude` in `apps/api/` was reported as "No `.claude` … outside dependency trees" — the walk had never entered the directory. In modern monorepo layout those hold first-party source far more often than vendored sub-projects, so they are candidates like any other directory; `deps`, `dependencies` and `submodules` stay excluded because those names still mean imported code.
  Add names for one run with `--exclude`, permanently via `CLEAN_CLAUDE_EXCLUDES`, or opt a default-excluded name back in with `--include`.
  Candidates are always listed before anything is touched and git-tracked ones are flagged.
  Only `purge` may touch `~/.claude`: it holds credentials, history, plugins and the `ai` role's symlinks, so other modes skip it with a note even when run from `$HOME`, and `purge` gates it behind typing `purge` (restoring is `make run-role ROLE=ai` plus a re-login).
- `lns [ROOT] [--contains STRING] [--broken] [--remove] [--dry-run] [--yes] [--all]` - lists every symlink under `ROOT` (default: cwd) with the absolute path it points at, and optionally removes them. Read-only unless `--remove`.
  `--contains` matches the **target**, not the link's own name, which is what makes it useful: `lns --contains old-repo --remove` drops every link still pointing into a repo you moved or deleted. Broken links are flagged `⚠ broken` and are removable like any other; a link whose target cannot be read at all is flagged `⚠ unreadable` and never matches a `--contains`, since a filter is a claim about the target.
  `--broken` keeps only the links that resolve to nothing, so `lns --broken` is the report and `lns --broken --remove` is the sweep. The two filters compose (`lns -b -c old-repo` is the dead links from one target), and both are independent of `--remove`, which is why either reads the same whether you are looking or deleting. Unlike `--contains` it is a claim about the **link**, answered by `test -e` and nothing else, so an `⚠ unreadable` link counts as broken: it resolves to nothing either way, and the case for excluding it from `--contains` was that its target is unknown, which `--broken` never asks about.
  The target is resolved **one hop** and normalized, not chased to the end of the chain. `path resolve` would be shorter but rewrites the path out from under you: on macOS a link to `/var/folders/x` reads back as `/private/var/folders/x`, which no longer contains the string you asked about.
  A link is reported and never followed (no `fd -L`), so the walk cannot descend into a target and loop.
  Like `clean_claude`, it skips dependency, cache and build trees unless `--all`, because recursing them means hundreds of `node_modules/.bin` links drowning your own. It reuses `_clean_claude_excludes` rather than restating forty names, so `CLEAN_CLAUDE_EXCLUDES` extends `lns` too, and the skip is always stated in a note so a count never reads as "that is all of them".
  `--remove` lists candidates first, then confirms once (`--yes` skips the prompt, `--dry-run` stops before it). Only the links go; their targets are untouched.
- `tv_change_dir` — bound to `alt-c` in `config.fish`. Pipes the `dirs` television channel into `tv` and `cd`s to the pick.

## Side effects

- Modifies `/etc/shells` (requires sudo).
- Changes the user's default shell (requires sudo).
- Pre-existing target files are copied to `backups/` on first run.
- `tv update-channels` performs a network fetch; allowlist pruning then removes non-symlink cables outside `TV_CABLE_ALLOWLIST` on every run.
