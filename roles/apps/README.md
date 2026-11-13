# apps

Catch-all role for desktop apps and their configs. Browsers, chat apps, dev tools, editors, infra CLIs, multimedia, system utilities: anything that isn't already covered by a more focused role.

## What it does

1. Installs the taps, formulas and casks declared in `BREW_PACKAGES` through the shared `roles/brew/tasks/packages.yml`.
2. Creates `APPS_DIRS` and links every config in `APPS_LINKS` (git, lazygit, superfile, npm, gh, gh-dash, diffnav, pgcli, herdr, Caddy, Neovim, VSCode, Docker, Colima, lazydocker, dive, Triage, AeroSpace).
3. Links each tool in `APPS_SCRIPTS` into `~/.local/bin/`, and creates one private Sentry config dir per account plus the map the `sentry` wrapper reads.
4. Fails with login instructions when `gh` is not authenticated, then installs the `GH_EXTENSIONS`.
5. Installs the npm-only `cf` Cloudflare CLI with bun, and the missing `VSCODE_EXTENSIONS`.

Caddy is never started or registered at boot: `lokl start` and `lokl stop` run it on demand.

## Vars

- `BREW_PACKAGES`: taps, formulas, casks for browsers, dev tools, databases, infra, multimedia, system, and other apps.
- `APPS_DIRS`, `APPS_LINKS`: the directories to create and the configs to link, `src` relative to `files/`.
- `APPS_SCRIPTS`, `GH_EXTENSIONS`, `VSCODE_EXTENSIONS`: linked tools, gh extensions as `repository` plus pinned `release` tag, VSCode extension IDs.
- `CF_CLI`: the npm package and exact version of Cloudflare's `cf`, reinstalled whenever the installed version differs.
- `SENTRY_ACCOUNTS`: account `name` and the directory `roots` it claims. `SENTRY_ACCOUNTS_DIR` is where their config dirs live.
- `CADDYFILE_PATH`: where Homebrew's caddy reads its config; the site directory is linked beside it.

> **Convention**: prefer brew when a formula exists. There's no `NPM_PACKAGES` mechanism here today: if a future tool only ships via npm with no brew alternative, re-add a thin `tasks/npm-packages.yml` driven by an `NPM_PACKAGES` list.

## Neovim

Run `make run-role ROLE=apps` to install Neovim and link `roles/apps/files/nvim/init.lua` at `~/.config/nvim/init.lua`.
The plugin-free config enables line numbers, case-insensitive search unless the pattern contains uppercase, and the system clipboard.
Indentation, keybindings and the default shell editor stay unchanged.
No login or activation is needed.

Start with `nvim`, then type `:Tutor` and press Enter for the built-in tutorial.
Open a file with `nvim path/to/file`.

| Keys | Action |
|---|---|
| `i` | Enter insert mode to type |
| `Esc` | Return to normal mode |
| `h`, `j`, `k`, `l` | Move left, down, up, right (arrow keys also work) |
| `:w` then Enter | Save |
| `:q` then Enter | Quit |
| `:q!` then Enter | Quit and discard unsaved changes |
| `u`, `Ctrl+r` | Undo, redo |
| `/text` then Enter | Search; `n` goes to the next match |
| `:help` then Enter | Open the built-in help |

## AeroSpace

Edit `roles/apps/files/.aerospace.toml`, linked at `~/.aerospace.toml`.
Run `aerospace reload-config --dry-run` to validate it, then `aerospace reload-config` once to enable automatic reloads after saving.
On a new machine, grant AeroSpace Accessibility access when prompted.

Named display assignments prefer the ASUS `MB16AHV`, falling back to the main display when it is disconnected.
Editors keeps its Dell/main assignment.
Workspaces 6-9 and Vault are unpinned, so `Alt+Shift+Tab` can move them onto an occasional extra display.
That shortcut cannot move workspaces with forced monitor assignments.

| Shortcut | Action |
|---|---|
| `Alt+1` through `Alt+9` | Visit a numbered workspace |
| `Alt+Shift+1` through `Alt+Shift+9` | Send a window there without following it |
| `Alt+Ctrl+Tab` | Focus the next monitor without moving windows |
| `Alt+Tab` | Return to the previous workspace |
| `Alt+Backtick` | Return to the previous focused window |
| `Alt+Shift+;`, then `b` | Balance window sizes without flattening groups |

`Alt+Shift+F` keeps AeroSpace fullscreen rather than creating a native fullscreen Space.
The pointer follows keyboard focus; moving the pointer does not change focus.
App routing still explicitly tiles windows, except Bitwarden.
If a dialog tiles awkwardly, add a specific floating exception before its app rule rather than changing every app's behavior.

The macos role manages Mission Control's **Group windows by application** setting so AeroSpace's offscreen windows do not produce tiny previews.
Apply it through `make run-role ROLE=macos`; Dock preferences may need a logout to take effect.
Keep one native Space, or one per display when **Displays have separate Spaces** is enabled, and use AeroSpace workspaces for daily navigation.
Remove unused native Spaces manually in Mission Control; provisioning does not close Spaces or move their windows.
The separate-Spaces setting is left unchanged because disabling it makes native fullscreen black out the other displays.

## Herdr

Press `Ctrl+d`, then `m` to open Glow's Markdown browser in a temporary popup from the active pane's working directory.
Quit Glow to return to the unchanged pane layout; no reader stays running after it closes.
Glow is installed by the `coreutils` role.
The popup passes the managed Glow config and style paths explicitly, so it does not depend on the server's shell environment.
After editing Herdr's config, run `herdr server reload-config` or use `Ctrl+d`, then `r`.

The sidebar's `$branch`, `$ctx`, `$handoff`, `$ticket` and `$pr` tokens and the tab bar's usage entry come from the ai role's `hooks/herdr-sidebar.sh`, which Claude's status line and hooks and pi's footer drive.
Its token names, refresh intervals and PR glyphs live in the harness `statusline.json`; the colours stay here, so a renamed token or glyph has to change in both.
s-task records each issue title as the branch description, which is where `$ticket` reads it from.

## Sentry

`~/.local/bin/sentry` shadows the Homebrew binary and sets `SENTRY_CONFIG_DIR` to `~/.config/sentry/<account>`, where the account is the one whose root is the longest prefix of the working directory.
`SENTRY_ACCOUNT=<name>` picks one explicitly, an already-set `SENTRY_CONFIG_DIR` passes straight through, and a directory no account claims is refused, so nothing ever falls back to `~/.sentry`.
Agents call bare `sentry` from a non-interactive shell, which is why this is a script on `PATH` and not a fish alias.

Every stored credential is read-only, because any agent that can run `sentry` can also run `sentry api --method DELETE`, and only the token's scopes stop it:

- An org you administer: an internal integration with Read on Project, Issue & Event and Organization. Its token is bound to that one org. Log in with `sentry auth login --token <token>` from inside a mapped directory.
- An org you are only a member of: `sentry auth login --read-only`. This login, like a personal token, reaches every org your Sentry user belongs to.
- A write (resolve, assign): the web UI, or `SENTRY_CONFIG_DIR=(mktemp -d) sentry auth login` followed by `sentry auth logout`.

Never put a token in `.sentryclirc`: a stored login outranks it silently. Keep `.sentryclirc` for `[defaults] org`/`project`.
The harness policy denies agents reading either config location and running `sentry auth login`, `logout` or `token`.

## Triage

The managed `~/.config/triage/config.yaml` preserves the current browser profiles and routing rules, and `fallback-browser.json` preserves Helium as the fallback.
Only these files are linked, so `triage.log` stays local.
The fallback timestamp is required by Triage's state format, not used to choose the browser.
Edit the managed fallback file directly: Triage's **Set Fallback Browser** menu atomically replaces the symlink rather than updating its target.
If you use that menu, import the resulting file into `files/triage/fallback-browser.json` before rerunning the role.

On a new machine, launch Triage, select **Set as Default Web Browser** and confirm the macOS prompt, then enable **Launch at Login** from its menu.
Chrome profiles named `Jose Manuel`, `Jose Manuel [Dev]` and `3bitslost` must exist; their account sessions are not dotfiles.
Allow Triage to read Chrome's profile index when macOS requests Application Data access so those friendly profile names resolve.

## Colima

[The managed profile](files/colima/colima.yaml) preserves Colima 0.10.3's template comments and examples.
It uses 6 CPUs and 8 GiB RAM on the 14-core, 24 GB M4 Pro, leaving room for host apps, with a 30 GiB container disk.
The profile uses `aarch64` on Apple's `vz` backend, with `sshfs` mounts and `mountInotify` disabled.
Colima warns that `sshfs` is its least reliable mount option under concurrent I/O.
Kubernetes and Rosetta remain disabled, without adding an installation dependency.

It does not start, stop or recreate the VM.
CPU and memory changes take effect after a stop/start; Colima marks architecture, VM type and mount type as immutable after creation, so changing those on an existing VM requires a deliberate migration with container data backed up first.
Colima saves startup configuration through the symlink into the repository, preserving changes made with CLI flags.
Its YAML writer adds trailing spaces to blank lines, so `.gitattributes` and `.yamllint` exempt only this file from trailing-space checks; other validation remains enabled.
Use `colima start --save-config=false` only when startup changes should not persist.

## Notes

VSCode extensions are checked against `code --list-extensions` first; missing ones are installed.
