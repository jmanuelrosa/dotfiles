# Dotfiles repo

Personal Ansible dotfiles for macOS. Primary target is a Darwin/arm64 workstation managed by Homebrew + Ansible.

## Layout

```
roles/<name>/
├── tasks/main.yml        # entry point, included by the top-level playbook
├── files/                # static assets symlinked or copied to $HOME
├── defaults/main.yml     # overridable role vars (host_vars/<profile>.yml can override)
│                         # — includes BREW_PACKAGES dict when the role installs packages
└── templates/            # jinja2 templates (when needed)
```

Roles of note:

- `roles/ai/` — AI tooling (Claude Code, Gemini, Pi). Skills under `files/claude/skills/` are shared with Pi via symlink.
- `roles/apps/` — general developer apps; sub-tasks under `tasks/*.yml` handle config symlinks. Brew installs are driven by `BREW_PACKAGES` in `defaults/main.yml`. NPM globals in `tasks/npm-packages.yml`.
- `roles/coreutils/` — modern Unix-replacement utilities (bat, eza, fd, fzf, ripgrep, btop, etc.). Configs symlinked from `files/`. Note: this is *not* the GNU `coreutils` package — these are individual modern alternatives. Domain-specific CLIs (awscli, gh, docker, lazygit, etc.) live in the `apps` role next to their configs.
- `roles/macos/` — `osx_defaults` plus nvram/pmset firmware tweaks.
- `roles/shell/` — fish config, functions, and helpers (e.g. `claude-skill`, `claude-agent`).
- `roles/ssh/` — SSH key install. Drives off `SSH_KEYS + SSH_KEYS_EXTRA`. Per-profile keys come from `host_vars/<profile>.yml`.
- `roles/work/` — work-specific scripts under `files/scripts/`. Brew installs in `defaults/main.yml`.

## Conventions

- **Idempotent tasks only.** Config files are symlinked from the repo with `ansible.builtin.file state=link force=true` so edits in the repo immediately take effect.
- **Homebrew via per-role `BREW_PACKAGES`.** Each role that installs packages defines a `BREW_PACKAGES` dict (`taps`, `formulas`, `casks` — all optional) in `defaults/main.yml`. The role's tasks loop over those keys with `community.general.homebrew_tap`, `homebrew`, and `homebrew_cask`. host_vars overrides work like any other Ansible var.
- **Profiles select roles.** Two profiles ship: `personal` (default) and `work`. The mapping lives in `group_vars/all.yml` under `profile_roles`. Each role in `dotfiles.yml` is gated with `when: '<role>' in profile_roles[profile]`.
- **Role execution order matters.** `brew` is first; every other role that installs packages assumes Homebrew is already on PATH. Don't rely on `meta/main.yml` deps — use playbook order.
- **Secrets stay out of the repo.** Env vars are referenced with `${NAME}` in config files and resolved at runtime. Vault-encrypted vars live in `vars/secrets.yml` and `vars/work.yml`.

## Commit style

Short conventional-commit prefixes, lowercase, informal: `feat:`, `fix:`, `chore:`. Keep the subject under ~70 chars. Body is optional.

## Running

```
ansible-playbook -i inventory.yml dotfiles.yml                                          # full run, personal profile
ansible-playbook -i inventory.yml dotfiles.yml --extra-vars 'profile=work'              # work profile
ansible-playbook -i inventory.yml dotfiles.yml --tags ai                                # single role
ansible-playbook -i inventory.yml dotfiles.yml --check --diff                           # dry run
```

Or use the Makefile: `make run`, `make run PROFILE=work`, `make run-role ROLE=ai`, `make check`, `make verify`.
