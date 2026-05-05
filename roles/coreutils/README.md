# coreutils

Installs modern replacements for traditional Unix utilities, plus the configs they need.

> **Note**: this role is *not* the GNU `coreutils` package. The name reflects intent — these are the always-on, day-to-day tools that replace classic Unix commands (cat → bat, ls → eza, find → fd, grep → ripgrep, top → btop, etc.). Domain-specific CLIs (awscli, gh, docker, lazygit, …) live in the `apps` role alongside their configs.

## What it does

- Installs utilities listed in `BREW_PACKAGES.formulas` via `community.general.homebrew`.
- Symlinks per-tool configs (bat, ripgrep, eza, btop, ctop) from `files/` into `~/.config/`.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — formulas only: bat, btop, duf, eza, fastfetch, fd, fzf, httpie, hyperfine, nnn, ripgrep, scc, wget, zoxide, unar.

## Files

- `files/bat/config`, `files/ripgrep/config`, `files/eza/theme.yml`, `files/btop/btop.conf`, `files/fastfetch/config.jsonc` — checked-in configs symlinked into `~/.config/`.

## Notes

Configs are symlinked with `force: true` — edits in the repo are immediately reflected in `~/.config/`.
