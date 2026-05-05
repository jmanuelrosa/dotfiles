# apps

Catch-all role for desktop apps and their configs. Browsers, chat apps, dev tools, editors, infra CLIs, multimedia, system utilities — anything that isn't already covered by a more focused role.

## What it does

1. Installs all taps, formulas, and casks declared in `BREW_PACKAGES` (defaults/main.yml).
2. Subtask files under `tasks/` handle config symlinks per category:
   - `browsers.yml` — Harper config.
   - `development.yml` — git, lazygit, npmrc, gh, pgcli configs.
   - `editors.yml` — VSCode settings, keybindings, extensions.
   - `infrastructure.yml` — `brew link docker`, docker config, ctop config.
   - `system.yml` — aerospace.
   - `npm-packages.yml` — global bun installs from `NPM_PACKAGES`.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — taps, formulas, casks for browsers, dev tools, databases, infra, multimedia, system, and other apps.
- `VSCODE_EXTENSIONS` (defaults/main.yml) — extension IDs.
- `NPM_PACKAGES` (defaults/main.yml) — global npm/bun packages, including `@github/copilot` and `@mariozechner/pi-coding-agent` (consumed by the `ai` role).

## Notes

VSCode extensions are checked against `code --list-extensions` first; missing ones are installed.
