# brew

Bootstraps Homebrew itself, plus the tooling that other roles assume is already on PATH (`mas`, `ansible`, `ansible-lint`).

## What it does

- Installs Homebrew if missing (via the official `install.sh`).
- Runs `brew update`.
- Installs `BREW_PACKAGES.formulas`: `mas` (used by `security` role), `ansible` and `ansible-lint` (used by `make lint` and CI).

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — formulas: `mas`, `ansible`, `ansible-lint`.

## Side effects

- Writes to `/opt/homebrew/...` (Apple Silicon).
- Requires `become: true` for the initial Homebrew install.

## Why this is first

Every other role that installs packages does so via `community.general.homebrew*` modules driven by each role's `BREW_PACKAGES` dict, so Homebrew must exist before any of them run. Don't rely on `meta/main.yml` deps — keep this role at the top of `dotfiles.yml`.
