# apps

Catch-all role for desktop apps and their configs. Browsers, chat apps, dev tools, editors, infra CLIs, multimedia, system utilities: anything that isn't already covered by a more focused role.

## What it does

1. Installs the taps, formulas and casks declared in `BREW_PACKAGES` through the shared `roles/brew/tasks/packages.yml`.
2. Creates `APPS_DIRS` and links every config in `APPS_LINKS` (git, lazygit, superfile, npm, gh, gh-dash, diffnav, pgcli, herdr, Caddy, Neovim, VSCode, OpenTofu, Docker, Colima, act, lazydocker, dive, Triage, AeroSpace), then writes the plist preferences in `APPS_OSX_DEFAULTS` (Maccy).
3. Links each tool in `APPS_SCRIPTS` into `~/.local/bin/`, and creates one private Sentry config dir per account plus the map the `sentry` wrapper reads.
4. Creates the empty `GCLOUD_NEUTRAL_CONFIG` gcloud configuration, leaving an existing one untouched, and makes it the global active configuration.
5. Fails with login instructions when `gh` is not authenticated, then installs the `GH_EXTENSIONS`.
6. Installs the npm-only `cf` Cloudflare CLI with bun, and the missing `VSCODE_EXTENSIONS`.
7. Where `OVIS_ENABLED` is true, installs Ovis on herdr and the Cloudflare Tunnel that publishes it, both off until `herdr-remote on` ([Ovis](#ovis)).

Caddy is never started or registered at boot: `lokl start` and `lokl stop` run it on demand.

## Vars

- `BREW_PACKAGES`: taps, formulas, casks for browsers, dev tools, databases, infra, multimedia, system, and other apps.
- `APPS_DIRS`, `APPS_LINKS`: the directories to create and the configs to link, `src` relative to `files/`.
- `APPS_OSX_DEFAULTS`: `domain`, `key`, `type` and `value` of each app preference written with `defaults`, the same shape as the macos role's `OSX_DEFAULTS`.
- `APPS_SCRIPTS`, `GH_EXTENSIONS`, `VSCODE_EXTENSIONS`: linked tools, gh extensions as `repository` plus pinned `release` tag, VSCode extension IDs.
- `CF_CLI`: the npm package and exact version of Cloudflare's `cf`, reinstalled whenever the installed version differs.
- `SENTRY_ACCOUNTS`: account `name` and the directory `roots` it claims. `SENTRY_ACCOUNTS_DIR` is where their config dirs live.
- `GCLOUD_CONFIG_DIR`, `GCLOUD_NEUTRAL_CONFIG`: gcloud's config directory and the empty configuration made globally active, so a command outside a gcloud-profiles mapping fails instead of writing into a work configuration.
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

The prefix is `Ctrl+Space`, which nothing inside a pane uses; the `macos` role disables the system input-source shortcut that would otherwise take it.
Every binding belongs to one of four families, so a forgotten key can be rebuilt from its family instead of looked up:

| Family | Keys | Plain | Shift | Ctrl |
|---|---|---|---|---|
| Make | `t` tab, `w` workspace, `g` worktree, `p` pane (name only) | create | name it (`T`, `W`, `P`); `G` opens an existing worktree | |
| Move | `i` `j` `k` `l`, as in Ghostty | focus | swap the pane | |
| Erase | `x` | close pane | close tab | close workspace (`Ctrl+g` removes a worktree) |
| Jump | `Space` anywhere, `s` workspaces, `` ` `` next workspace, `Tab` tabs, `a` agents, `o` notification, `Backspace` back | forward | backward | |

Numbers follow the sidebar: `1..9` jumps to a workspace by its row, `Shift+1..9` to an agent, and `Option+1..9` to a tab.

Ctrl after the prefix always destroys something big.
The rest: `\` and `-` split along the line the key draws, `z` zoom, `b` sidebar (bar, as VS Code's `Cmd+b`), `r` resize mode, `[` copy mode, `e` scrollback in `$EDITOR`, `,` settings, `?` help, `Shift+r` reload, `q` detach.

Press `Ctrl+Space`, then `m` to open Glow's Markdown browser in a temporary popup from the active pane's working directory.
Quit Glow to return to the unchanged pane layout; no reader stays running after it closes.
Glow is installed by the `coreutils` role.
The popup passes the managed Glow config and style paths explicitly, so it does not depend on the server's shell environment.
After editing Herdr's config, run `herdr server reload-config` or use `Ctrl+Space`, then `Shift+r`.

The sidebar's `$branch`, `$ctx`, `$handoff`, `$ticket` and `$pr` tokens and the tab bar's usage entry come from the ai role's `hooks/herdr-sidebar.sh`, which Claude's status line and hooks and pi's footer drive.
Its token names, refresh intervals and PR glyphs live in the harness `statusline.json`; the colours stay here, so a renamed token or glyph has to change in both.
s-task records each issue title as the branch description, which is where `$ticket` reads it from.

## Ovis

Runs [Ovis](https://github.com/devswha/ovis) as a herdr plugin and publishes it at `herdr.jmanuelrosa.dev` through a Cloudflare Tunnel behind Cloudflare Access, so the herdr sessions on this Mac can be driven from a phone.
On only where `OVIS_ENABLED` is true, which `host_vars/personal.yml` sets: a tunnel serves one Mac.

```text
phone ──HTTPS──▶ Cloudflare Access ◀──tunnel── cloudflared (launch agent) ──▶ Ovis 127.0.0.1:7317 ──▶ herdr
```

Three gates stand in front of the terminals:

1. **Cloudflare Access** lets in only the emails its policy allows.
2. **cloudflared** verifies the Access token on every request before forwarding it, so a deleted or misconfigured Access application leaves the tunnel closed rather than open.
3. **`OVIS_TOKEN`**, Ovis's own gate, entered once per device. Access cannot hand it to the app, so it stays on.

Ovis listens on loopback only: nothing on the LAN reaches it, and the Mac opens no inbound port.

### Turning it on and off

Nothing starts at login or with herdr: Ovis and the tunnel stay off until you ask for them.

```sh
herdr-remote on       # start Ovis in the herdr session it serves, then open the tunnel
herdr-remote off      # close the tunnel, stop Ovis
herdr-remote status
```

`on` needs the `OVIS_HERDR_SESSION` herdr session running, since Ovis runs inside it, and leaves the tunnel closed when Ovis does not start.
`off` also disables the plugin, because an enabled Ovis starts again with the next herdr session.

### What the Ovis tasks do

- Installs the Ovis plugin with `herdr plugin install` when `herdr plugin list` does not show it, then disables it so it does not start with herdr.
- Writes the plugin's `env` file (in `herdr plugin config-dir devswha.ovis`, mode `0600`): host, port, token and `OVIS_SETTINGS`. A change stops a running Ovis, and the next `herdr-remote on` starts it with the new settings.
- Writes the tunnel credentials, `~/.cloudflared/ovis.yml` and the `dotfiles.ovis-tunnel` launch agent that runs `cloudflared tunnel run`. The agent lives in `~/.cloudflared`, not `~/Library/LaunchAgents`, so launchd never loads it at login; an open tunnel is reloaded on a config change, a closed one stays closed. Logs go to `~/Library/Logs/ovis-tunnel.log`.
- Writes `~/.config/herdr-remote/config` and links `herdr-remote` into `~/.local/bin`.

### Vars

- `OVIS_ENABLED` (`defaults/main.yml`, `false`; `true` in `host_vars/personal.yml`): whether this machine runs Ovis and the tunnel.
- `OVIS_TUNNEL` (`defaults/main.yml`): hostname, the Zero Trust team name and the Access application's audience tag.
- `OVIS_HERDR_SESSION` (`defaults/main.yml`, empty; `work` in `host_vars/personal.yml`): the named herdr session Ovis shows. One Ovis serves one session, so the others are not reachable from the phone, and Ovis has nothing to show while that session is not running.
- `OVIS_SETTINGS` (`defaults/main.yml`): extra Ovis variables, from its [configuration table](https://github.com/devswha/ovis/blob/main/docs/guide.md#configuration).
- `OVIS_TOKEN` (vault, `vars/secrets.yml`): Ovis's token.
- `OVIS_TUNNEL_CREDENTIALS` (vault, `vars/secrets.yml`): the tunnel credentials JSON as a mapping. The tunnel ID is read from it.

The play stops with a message naming what is missing until all four are set.

### One-time Cloudflare setup

The tunnel, its DNS record and the Access application live in the Cloudflare account, not on this Mac.

1. Create the tunnel and its DNS record with `cloudflared`, which this role installs on every profile:

   ```sh
   cloudflared tunnel login
   cloudflared tunnel create herdr
   cloudflared tunnel route dns herdr herdr.jmanuelrosa.dev
   ```

   `create` prints the path of the credentials file, `~/.cloudflared/<tunnel ID>.json`.
2. In Zero Trust, **Access → Applications → Add an application → Self-hosted**, for `herdr.jmanuelrosa.dev`:
   - a policy with action **Allow** that includes only your email;
   - **One-time PIN** or GitHub as the login method;
   - a session duration of 7 to 30 days, so the phone is not asked every day.
3. Copy the application's **Application Audience (AUD) Tag** into `OVIS_TUNNEL.access_aud`, and the team name (`<team>` in the `<team>.cloudflareaccess.com` team domain shown under **Settings**) into `OVIS_TUNNEL.access_team`.
4. Add the secrets with `ansible-vault edit vars/secrets.yml`:

   ```yaml
   OVIS_TOKEN: <output of `openssl rand -hex 32`>
   OVIS_TUNNEL_CREDENTIALS:
     AccountTag: <from the credentials file>
     TunnelSecret: <from the credentials file>
     TunnelID: <from the credentials file>
   ```

   Then delete `~/.cloudflared/<tunnel ID>.json`; the role writes it back from the vault. `cert.pem` from `tunnel login` is only needed to create or route tunnels, and can go too.
5. `make run-role ROLE=ovis`, then `herdr-remote on`.

### Checks

With `herdr-remote on`:

- `curl -sI https://herdr.jmanuelrosa.dev` answers with a redirect to `<team>.cloudflareaccess.com`.
- `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:7317/api/session` answers `401` without the token.
- `herdr plugin action invoke devswha.ovis.status` reports the server and the env files it read.

### On the phone

Open `https://herdr.jmanuelrosa.dev` in Safari, sign in to Access, enter the token, then **Share → Add to Home Screen** and turn on **Alerts** from the **⋯** menu (iOS 16.4 or later).
The App Store and Play Store apps cannot get past the Access sign-in yet ([devswha/ovis#2008](https://github.com/devswha/ovis/issues/2008)).

## Helium

`Cmd+b` toggles the vertical-tab sidebar; `Cmd+s` saves the page again.
Only the configured `Default` profile (`HELIUM_PROFILE_DIR`) is managed; browser profiles stay local, not linked into this repo.
Launch Helium once to create its profile, then quit it fully and run `make run-role ROLE=helium` without reinstalling apps.
Missing profiles are skipped; a running browser or an unreadable process list blocks changes.
The tasks preserve unrelated settings and shortcuts, and create a local `Preferences.*` backup beside the profile before each change.
Resolve conflicting custom `Cmd+b` or `Cmd+s` bindings in Helium's Settings before retrying.
Reopen Helium afterward to activate the shortcuts.

## Bruno and DBeaver

`Ctrl+Tab` and `Ctrl+Shift+Tab` move forward and backward through tabs.
Bruno cycles within the active collection.
DBeaver uses window tab navigation rather than the recent-editor switcher; dialogs keep their own navigation.

Launch each app once to create its settings, quit both fully, then run `make run-role ROLE=bruno,dbeaver` and reopen them.
Missing settings are skipped; a running app or unreadable process list blocks its changes.
Both tasks keep local backups and leave unrelated preferences untouched.
Bruno merges only the two macOS shortcuts, preserving its Windows bindings and other custom shortcuts.
DBeaver currently has no custom keybindings; its custom-keybinding property is owned by `roles/apps/files/dbeaver/keybindings.prefs`, so make subsequent DBeaver shortcut changes there rather than in its UI.
`BRUNO_PREFERENCES_PATH` and `DBEAVER_PREFERENCES_PATH` select the settings files; DBeaver defaults to `workspace6`.

## Tab navigation

Use visible tab order rather than recently used order.
VS Code switches within the current editor group; its Quick Open picker keeps its own navigation.

| Apps | Next tab | Previous tab |
|---|---|---|
| VS Code, Helium, Chrome, Bruno, DBeaver | `Ctrl+Tab` | `Ctrl+Shift+Tab` |
| Herdr | `Ctrl+Space`, then `Tab` | `Ctrl+Space`, then `Shift+Tab` |

Herdr keeps its prefix so direct shortcuts remain available to nested programs when the terminal passes them through.
Ghostty's own tab shortcuts are unchanged.

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

## OpenTofu

The role installs the `opentofu` Homebrew formula and links `roles/apps/files/.tofurc` at `~/.tofurc`.
The config is empty, keeping OpenTofu defaults without a shared provider cache.
Make future non-secret CLI settings changes in the managed file; credentials, project state and downloaded providers stay outside this repository.
The `.tofurc` file takes precedence over legacy `.terraformrc` settings, so import any non-secret settings you want to preserve before provisioning.
OpenTofu itself needs no activation; authenticate with each provider separately.

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

## Maccy

`APPS_OSX_DEFAULTS` restores the history size, menu bar icon, clipboard types, keyboard shortcuts and popup layout.
Maccy is sandboxed, so `defaults` writes into its container, which macOS creates on the first launch.
On a new machine, launch Maccy once and quit it before `make run-role ROLE=apps`, then grant Accessibility access when it asks so paste works.
After changing a setting in Maccy, read it with `defaults read org.p0deje.Maccy` and update `APPS_OSX_DEFAULTS`.

## Unmanaged settings

These apps are installed but their settings are not restored, for the reason given.

| App | Why | Manual step |
|---|---|---|
| mpv, VLC, SF Symbols, mole | Nothing customized: no `mpv.conf`, VLC's `vlcrc` holds only the volume and audio device, SF Symbols and mole store only window frames and a log | Import the file into `files/` and link it the first time a setting changes |
| ImageMagick | CLI with no user configuration | None |
| Brave | The profile's `Preferences` mixes settings with account, history and machine state | Turn on Brave Sync for settings and extensions |
| Slack, Discord, WhatsApp, Notion, Figma, TradingView, Spotify | Settings live in the account or in Electron storage beside sessions and caches; Spotify's `prefs` and Figma's `settings.json` also hold login and client ids | Sign in; settings follow the account |
| Bitwarden | `data.json` keeps app settings in the same file as access tokens, key material and the account email | Sign in, then re-enable unlock with Touch ID and the browser integration |
| Logi Options+ | Proprietary store | Sign in to Logi and restore from its cloud backup |
| Bruno | `preferences.json` holds proxy and cloud credential fields beside window state, and collections carry environments and secrets | Re-open the collections from their repositories |
| DBeaver | `data-sources.json` holds connections and credentials, and the workspace `.prefs` mix settings with machine paths and update timestamps | Use **File > Export > Preferences** and **File > Import** for settings; add connections by hand |
| Wrangler | Its global config holds the OAuth login | Run `wrangler login` |
| Ovis tunnel, DNS record, Access application | They live in the Cloudflare account | [One-time Cloudflare setup](#one-time-cloudflare-setup) |
| Ovis paired devices, push subscriptions | Machine-local state in `~/.config/ovis` | Sign in again from each device after a reinstall |
| Ovis while the Mac sleeps | The tunnel goes down whenever the Mac sleeps | None: reach it only while the Mac is awake and online |

## Notes

VSCode extensions are checked against `code --list-extensions` first; missing ones are installed.
