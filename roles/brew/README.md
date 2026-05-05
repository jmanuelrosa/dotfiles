# brew

Bootstraps Homebrew itself, plus the `mas` CLI for Mac App Store automation.

## What it does

- Installs Homebrew if missing (via the official `install.sh`).
- Runs `brew update`.
- Installs the `mas` formula (used by the `security` role).

## Vars

None.

## Side effects

- Writes to `/opt/homebrew/...` (Apple Silicon).
- Requires `become: true` for the initial Homebrew install.

## Why this is first

Every other role that installs packages does so via `community.general.homebrew*` modules driven by each role's `BREW_PACKAGES` dict, so Homebrew must exist before any of them run. Don't rely on `meta/main.yml` deps — keep this role at the top of `dotfiles.yml`.
