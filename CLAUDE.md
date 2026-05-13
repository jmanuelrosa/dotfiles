# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

Ansible-based macOS dotfiles for Darwin/arm64 (Apple Silicon). The playbook in [dotfiles.yml](dotfiles.yml) provisions a development machine end-to-end: brew, system prefs, shell, SSH, apps, AI tooling, and per-profile work extras. Re-running it is the supported maintenance path — every task must be idempotent.

## Common commands

All workflows go through the [Makefile](Makefile). Every play prompts for two passwords: the vault password (`--ask-vault-password`, decrypts `vars/secrets.yml` / `vars/work.yml`) and the become password (`--ask-become-pass`, your macOS password, streamed to each `become: true` task via `sudo -S`). Touch ID isn't used for the become flow because Ansible's local connection plugin spawns sudo in a new session, which can't see tty-bound timestamps on macOS — the password prompt is the reliable path.

| Command | Purpose |
|---|---|
| `make lint` | `ansible-lint` (config in [.ansible-lint](.ansible-lint)) |
| `make syntax` | Playbook syntax check, no vault needed |
| `make check` | Full dry-run with `--check --diff` |
| `make check-role ROLE=shell` | Dry-run a single role by tag |
| `make run` | Apply the full playbook (personal profile) |
| `make run PROFILE=work` | Apply with the work profile |
| `make run-role ROLE=ai` | Apply a single role by tag |
| `make verify` | Smoke test — checks core binaries + config symlinks exist |
| `make deps` | Install pinned collections from [requirements.yml](requirements.yml) |

VM-based fresh-install testing uses [Tart](https://github.com/cirruslabs/tart): `make vm-create`, `make vm-start`, `make vm-ssh`, `make vm-destroy`.

## Architecture

### Profiles gate roles

Two profiles ship: `personal` (default) and `work`. Each role in [dotfiles.yml](dotfiles.yml) is gated with `when: '<role>' in profile_roles[profile]`. The mapping lives in [group_vars/all.yml](group_vars/all.yml) under `profile_roles`. Per-profile overrides go in [host_vars/personal.yml](host_vars/personal.yml) and [host_vars/work.yml](host_vars/work.yml), loaded by `pre_tasks` from `host_vars/{{ profile }}.yml`.

The `reboot` role is intentionally not profile-gated — it prompts the user, which is the opt-in.

### Role layout

```
roles/<name>/
├── tasks/main.yml      # entry point
├── files/              # static assets symlinked or copied to $HOME
├── defaults/main.yml   # overridable vars, including BREW_PACKAGES dict
└── templates/          # jinja2 (when needed)
```

`roles/apps/` further splits installs across `tasks/{browsers,development,editors,infrastructure,system}.yml`, all included from `tasks/main.yml`.

### Homebrew is per-role

Each role that installs packages defines a `BREW_PACKAGES` dict in `defaults/main.yml` with optional `taps`, `formulas`, `casks` keys. The role's tasks loop those over `community.general.homebrew_tap` / `homebrew` / `homebrew_cask`. There is no central package list — adding a tool means editing the role it belongs to.

### Role execution order matters

Playbook order is load-bearing — `brew` runs first so every later role can assume Homebrew is on PATH. **Don't add `meta/main.yml` deps**; control sequencing via the order in [dotfiles.yml](dotfiles.yml).

### Config files are symlinks, not copies

Configs are linked from the repo with `ansible.builtin.file state=link force=true`. Editing a file under `roles/<x>/files/` takes effect immediately in `$HOME` without re-running the playbook. Backups of any pre-existing target go to [backups/](backups/).

### Roles of note

- [roles/coreutils/](roles/coreutils/) — modern Unix replacements (bat, eza, fd, ripgrep, television, btop, …). **Not** the GNU `coreutils` package. Domain-specific CLIs (awscli, gh, docker, lazygit, …) live in `apps`, next to their configs.
- [roles/ai/](roles/ai/) — Claude Code / Gemini / Pi tooling. Skills under `files/claude/skills/` are shared with Pi via symlink.
- [roles/shell/](roles/shell/) — fish, Ghostty, Starship, Television. Custom fish functions live here (e.g. `claude-skill`, `claude-agent`, `tv_change_dir`). Manages the television config + vendored cables under `files/television/`, plus the `TV_CABLE_ALLOWLIST` that prunes upstream cables after `tv update-channels`.
- [roles/ssh/](roles/ssh/) — drives off `SSH_KEYS + SSH_KEYS_EXTRA`. Per-profile keys go in `host_vars/<profile>.yml` as `SSH_KEYS_EXTRA`.
- [roles/macos/](roles/macos/) — `osx_defaults` plus nvram/pmset firmware tweaks.

### Secrets

Vault-encrypted vars live in `vars/secrets.yml` (personal) and `vars/work.yml` (work). Both are loaded unconditionally by the playbook. Config files reference env vars as `${NAME}` and resolve at runtime. [vars/work.yml.example](vars/work.yml.example) lists the keys a fork needs to provide.

## Conventions

- **Idempotency is mandatory.** Every task must be safe to re-run. If a task isn't naturally idempotent, gate it with a `stat` / `register` check.
- **Commits use short conventional-commit prefixes**, lowercase, informal: `feat:`, `fix:`, `chore:`. Subject under ~70 chars. Body optional.
- **Lint exclusions** ([.ansible-lint](.ansible-lint)) skip `yaml[truthy]` and `var-naming` (uppercase Ansible vars are intentional). Don't fight the linter on those — they're conscious choices.
