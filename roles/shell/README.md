# shell

Sets up the Fish shell, Ghostty terminal, Starship prompt, and Fish plugins.

## What it does

- Installs fish, fisher, starship, gnupg, and the ghostty cask via `BREW_PACKAGES`.
- Adds fish to `/etc/shells` and switches the user's login shell to fish.
- Backs up any existing fish/ghostty/starship configs to `<repo>/backups/` before symlinking.
- Symlinks fish config, conf.d snippets, functions, ghostty config, and starship config from `files/`.
- Renders `~/.config/fish/conf.d/secrets.fish` from `templates/secrets.fish.j2` using vault vars.
- Installs Fisher plugins listed in `FISH_PLUGINS`.

## Vars

- `FISH_PATH` (defaults/main.yml) — Apple Silicon Homebrew fish path. Override per-profile if your layout differs.
- `FISH_PLUGINS` (defaults/main.yml) — list of Fisher plugin specs.
- `BREW_PACKAGES` (defaults/main.yml) — fish, fisher, starship, gnupg formulas + ghostty cask.

## Templates

- `templates/secrets.fish.j2` — exports `NPM_TOKEN`, `GH_TOKEN`, `GLAB_TOKEN` from vault. Mode 0600.

## Side effects

- Modifies `/etc/shells` (requires sudo).
- Changes the user's default shell (requires sudo).
- Existing configs are copied to `backups/` (one-shot, on first run).
