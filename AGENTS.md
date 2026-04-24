# Dotfiles repo

Personal Ansible dotfiles for macOS. Primary target is a Darwin/arm64 workstation managed by Homebrew + Ansible.

## Layout

```
roles/<name>/
├── tasks/main.yml        # entry point, included by the top-level playbook
├── files/                # static assets symlinked or copied to $HOME
├── vars/main.yml         # role-scoped vars (formulas, casks, lists)
├── defaults/             # overridable defaults
└── templates/            # jinja2 templates (when needed)
```

Roles of note:

- `roles/ai/` — AI tooling (Claude Code, Gemini, Pi). Skills under `files/claude/skills/` are shared with Pi via symlink.
- `roles/apps/` — general developer apps, including `tasks/npm-packages.yml` for global npm installs via `bun install -g`.
- `roles/shell/` — fish config, functions, and helpers (e.g. `claude:skill`, `claude:agent`).
- `roles/work/` — work-specific scripts under `files/scripts/`.

## Conventions

- Idempotent tasks only. Config files are symlinked from the repo with `ansible.builtin.file state=link force=true` so edits in the repo immediately take effect.
- Homebrew is the package manager of choice; taps go in `vars/main.yml`.
- Secrets stay out of the repo. Env vars are referenced with `${NAME}` in config files and resolved at runtime.

## Commit style

Short conventional-commit prefixes, lowercase, informal: `feat:`, `fix:`, `chore:`. Keep the subject under ~70 chars. Body is optional.

## Running

```
ansible-playbook -i hosts main.yml            # full run
ansible-playbook -i hosts main.yml --tags ai  # single role
ansible-playbook -i hosts main.yml --check --diff  # dry run
```
