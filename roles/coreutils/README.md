# coreutils

Installs modern replacements for traditional Unix utilities, plus the configs they need.

> **Note**: this role is *not* the GNU `coreutils` package. The name reflects intent — these are the always-on, day-to-day tools that replace classic Unix commands (cat → bat, ls → eza, find → fd, grep → ripgrep, top → btop, etc.). Domain-specific CLIs (awscli, gh, docker, lazygit, …) live in the `apps` role alongside their configs.

## What it does

- Installs utilities listed in `BREW_PACKAGES.formulas` via `community.general.homebrew`.
- Symlinks per-tool configs (bat, ripgrep, eza, btop) from `files/` into `~/.config/`.
- Downloads the pinned `hostof` release asset directly to `~/.local/bin/hostof`. This role creates `~/.local/bin` itself because it runs before the `ai` role that otherwise would.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — formulas only: bat, btop, duf, eza, fastfetch, fd, httpie, hyperfine, nnn, ripgrep, scc, television, vnstat, wget, zoxide, unar.
- `HOSTOF` (defaults/main.yml): upstream repository, release, and SHA-256 checksum for the installed `hostof` asset.

## Tools

- [`hostof`](https://github.com/jmanuelrosa/hostof): reports which service and region host a site while keeping edge, origin, and network as separate facts. The standalone stdlib-only release is checksum-verified before installation. `--deep` adds conventional undocumented paths and refuses any host without an entry in `~/.config/hostof/authorized.json`.

## hostof lifecycle

- Upgrade or rollback by changing `HOSTOF.release` and `HOSTOF.checksum` together, then applying the coreutils role.
- Develop from a separate checkout and invoke its `./hostof` executable directly; do not replace the managed command on `PATH`.
- Uninstall through an explicit role change that removes only `~/.local/bin/hostof`. Cache and authorization state remain user-owned.

## Files

- `files/bat/config`, `files/ripgrep/config`, `files/eza/theme.yml`, `files/btop/btop.conf`, `files/fastfetch/config.jsonc` — checked-in configs symlinked into `~/.config/`.

## Notes

Configs are symlinked with `force: true` — edits in the repo are immediately reflected in `~/.config/`.
