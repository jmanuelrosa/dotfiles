# apps

Catch-all role for desktop apps and their configs. Browsers, chat apps, dev tools, editors, infra CLIs, multimedia, system utilities — anything that isn't already covered by a more focused role.

## What it does

1. Installs all taps, formulas, and casks declared in `BREW_PACKAGES` (defaults/main.yml).
2. Subtask files under `tasks/` handle config symlinks per category:
   - `development.yml` — git, lazygit, npmrc, gh, pgcli configs.
   - `editors.yml` — VSCode settings, keybindings, extensions.
   - `infrastructure.yml` - `brew link docker`, Docker, Colima, lazydocker and dive configs.
   - `system.yml` — aerospace.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — taps, formulas, casks for browsers, dev tools, databases, infra, multimedia, system, and other apps.
- `VSCODE_EXTENSIONS` (defaults/main.yml) — extension IDs.
- `COLIMA_CONFIG_PATH` (defaults/main.yml) - active default-profile config, normally `~/.colima/default/colima.yaml`.
- `COLIMA_CONFIG_BACKUP_PATH` (defaults/main.yml) - original config backup under the repo's `backups/` directory.

> **Convention**: prefer brew when a formula exists. There's no `NPM_PACKAGES` mechanism here today — if a future tool only ships via npm with no brew alternative, re-add a thin `tasks/npm-packages.yml` driven by an `NPM_PACKAGES` list.

## Colima

[The managed profile](files/colima/colima.yaml) preserves Colima 0.10.3's template comments and examples.
It uses 6 CPUs and 8 GiB RAM on the 14-core, 24 GB M4 Pro, leaving room for host apps, and keeps the default 100 GiB container disk.
The native `host` architecture, Apple's `vz` backend and `virtiofs` suit Apple Silicon; `mountInotify` keeps the existing file-event propagation enabled for development, although Colima marks it experimental.
Other settings retain the template defaults, including disabled Kubernetes and Rosetta, without adding an installation dependency.

`make run-role ROLE=apps` backs up an unmanaged config once before linking the profile; subsequent runs leave the backup intact.
It keeps the existing `~/.colima` location rather than migrating VM state to `~/.config/colima`, and does not start, stop or recreate the VM.
CPU and memory changes take effect after a stop/start; Colima marks architecture, VM type and mount type as immutable after creation, so changing those on an existing VM requires a deliberate migration with container data backed up first.
Use `colima start --save-config=false` to avoid writing startup changes back through the symlink into the repository.

## Notes

VSCode extensions are checked against `code --list-extensions` first; missing ones are installed.
