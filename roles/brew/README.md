# brew

Keeps Homebrew current and owns the shared task file every installing role uses for its packages.
Homebrew itself is installed by `bootstrap.sh`, because Ansible is installed through it.

## What it does

- Runs `brew update`.
- Installs `BREW_PACKAGES.formulas`: `mas` (used by the `security` role), `ansible` and `ansible-lint` (used by `make lint` and CI).

## Shared package install

`tasks/packages.yml` adds `taps`, runs `brew trust` on `trusted`, and installs `formulas` and `casks`, each only when that key is set.
Every installing role includes it by path:

```yaml
- name: Install <role> Homebrew packages
  ansible.builtin.include_tasks: "{{ CURRENT_DIR }}/roles/brew/tasks/packages.yml"
```

An included task file runs in the including role's context, so `BREW_PACKAGES` resolves against that role's defaults.

## Vars

- `BREW_PACKAGES` (defaults/main.yml): formulas `mas`, `ansible`, `ansible-lint`.

## Why this is first

Every other role installs packages through `tasks/packages.yml`, so `brew update` has run before any of them.
Don't rely on `meta/main.yml` deps: keep this role at the top of `dotfiles.yml`.
