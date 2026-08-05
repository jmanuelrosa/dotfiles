# coreutils

Installs modern replacements for traditional Unix utilities, plus the configs they need.

> **Note**: this role is *not* the GNU `coreutils` package. The name reflects intent — these are the always-on, day-to-day tools that replace classic Unix commands (cat → bat, ls → eza, find → fd, grep → ripgrep, top → btop, etc.). Domain-specific CLIs (awscli, gh, docker, lazygit, …) live in the `apps` role alongside their configs.

## What it does

- Installs utilities listed in `BREW_PACKAGES.formulas` via `community.general.homebrew`.
- Symlinks per-tool configs (bat, ripgrep, eza, btop, ctop) from `files/` into `~/.config/`.
- Symlinks each tool named in `CORE_SCRIPTS` into `~/.local/bin/`, from `files/scripts/<name>/<name>`. `hostof` is the only one. This role also creates `~/.local/bin` itself, because it runs 15 roles before the `ai` role that otherwise would.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — formulas only: bat, btop, duf, eza, fastfetch, fd, httpie, hyperfine, nnn, ripgrep, scc, television, vnstat, wget, zoxide, unar.
- `CORE_SCRIPTS` (defaults/main.yml): tool directories under `files/scripts/` to put on PATH. Named rather than globbed, because Ansible's `fileglob` filters through `os.path.isfile` and every entry is a directory.

## Tools

- `files/scripts/hostof/` : reports which service and region host a site, keeping edge, origin and network as separate facts rather than collapsing them into one verdict. Reads only what a browser reads (DNS, the TLS certificate, one HTTP response, the assets it links). Stdlib-only, and it needs no brew package: `dig` and `curl` ship with macOS. `--deep` adds conventional undocumented paths and refuses any host without an entry in `~/.config/hostof/authorized.json`.

## Files

- `files/bat/config`, `files/ripgrep/config`, `files/eza/theme.yml`, `files/btop/btop.conf`, `files/fastfetch/config.jsonc` — checked-in configs symlinked into `~/.config/`.

## Notes

Configs are symlinked with `force: true` — edits in the repo are immediately reflected in `~/.config/`.
