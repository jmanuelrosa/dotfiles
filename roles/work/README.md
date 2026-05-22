# work

Work-only role. Runs only when `profile=work`.

## What it does

- Installs `acli` (Atlassian) and the `fossa` cask via `BREW_PACKAGES` (with the `atlassian/homebrew-acli` tap). Relies on `shell` / `coreutils` (which run before `work` in `profile_roles[work]`) for `fish` and `television`.
- Renders `~/.config/fish/conf.d/work-secrets.fish` from `templates/exports.fish.j2` (work tokens, mode 0600).
- Symlinks every script under `files/scripts/` into `~/.local/bin/`.
- Copies `files/glab/config.yml` to `~/Library/Application Support/glab-cli/config.yml`.
- Symlinks the Jira Television cable (`files/television/cable/jira.toml`) and its helper fish function (`files/fish/functions/_tv_jira.fish`) into `~/.config/`. Both depend on `acli` so they live here rather than in `shell`.

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — taps/formulas/casks for the work tooling.
- Vault-encrypted secrets live in `vars/work.yml`. See `vars/work.yml.example` for the full key list.

## SSH keys

Work SSH keys are deployed by the `ssh` role from `SSH_KEYS_EXTRA`, defined in `host_vars/work.yml`. This role does not touch `~/.ssh/`.

## Profile gating

Listed in `profile_roles[work]` only; the personal profile skips this role.
