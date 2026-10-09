# apps

Catch-all role for desktop apps and their configs. Browsers, chat apps, dev tools, editors, infra CLIs, multimedia, system utilities: anything that isn't already covered by a more focused role.

## What it does

1. Installs the taps, formulas and casks declared in `BREW_PACKAGES` through the shared `roles/brew/tasks/packages.yml`.
2. Creates `APPS_DIRS` and links every config in `APPS_LINKS` (git, lazygit, npm, gh, gh-dash, diffnav, pgcli, herdr, Caddy, VSCode, Docker, Colima, lazydocker, dive, AeroSpace).
3. Links each tool in `APPS_SCRIPTS` into `~/.local/bin/`.
4. Fails with login instructions when `gh` is not authenticated, then installs the `GH_EXTENSIONS`.
5. Installs the npm-only `cf` Cloudflare CLI with bun, and the missing `VSCODE_EXTENSIONS`.

Caddy is never started or registered at boot: `lokl start` and `lokl stop` run it on demand.

## Vars

- `BREW_PACKAGES`: taps, formulas, casks for browsers, dev tools, databases, infra, multimedia, system, and other apps.
- `APPS_DIRS`, `APPS_LINKS`: the directories to create and the configs to link, `src` relative to `files/`.
- `APPS_SCRIPTS`, `GH_EXTENSIONS`, `VSCODE_EXTENSIONS`: linked tools, gh extensions, VSCode extension IDs.
- `CADDYFILE_PATH`: where Homebrew's caddy reads its config; the site directory is linked beside it.

> **Convention**: prefer brew when a formula exists. There's no `NPM_PACKAGES` mechanism here today: if a future tool only ships via npm with no brew alternative, re-add a thin `tasks/npm-packages.yml` driven by an `NPM_PACKAGES` list.

## Colima

[The managed profile](files/colima/colima.yaml) preserves Colima 0.10.3's template comments and examples.
It uses 6 CPUs and 8 GiB RAM on the 14-core, 24 GB M4 Pro, leaving room for host apps, with a 30 GiB container disk.
The profile uses `aarch64` on Apple's `vz` backend, with `sshfs` mounts and `mountInotify` disabled.
Colima warns that `sshfs` is its least reliable mount option under concurrent I/O.
Kubernetes and Rosetta remain disabled, without adding an installation dependency.

It does not start, stop or recreate the VM.
CPU and memory changes take effect after a stop/start; Colima marks architecture, VM type and mount type as immutable after creation, so changing those on an existing VM requires a deliberate migration with container data backed up first.
Use `colima start --save-config=false` to avoid writing startup changes back through the symlink into the repository.

## Notes

VSCode extensions are checked against `code --list-extensions` first; missing ones are installed.
