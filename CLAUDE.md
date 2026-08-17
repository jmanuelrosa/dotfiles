# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

Ansible-based macOS dotfiles for Darwin/arm64 (Apple Silicon). The playbook in [dotfiles.yml](dotfiles.yml) provisions a development machine end-to-end: brew, system prefs, shell, SSH, apps, AI tooling, and per-profile work extras. Re-running it is the supported maintenance path — every task must be idempotent.

## Common commands

All workflows go through the [Makefile](Makefile). Every play prompts for two passwords: the vault password (`--ask-vault-password`, decrypts `vars/secrets.yml` / `vars/work.yml`) and the become password (`--ask-become-pass`, your macOS password, streamed to each `become: true` task via `sudo -S`). Touch ID isn't used for the become flow because Ansible's local connection plugin spawns sudo in a new session, which can't see tty-bound timestamps on macOS — the password prompt is the reliable path.

| Command | Purpose |
|---|---|
| `make lint` | `ansible-lint` (config in [.ansible-lint](.ansible-lint)). Needs the vault password to load `vars_files`, so it can't run unattended |
| `make test` | pytest over every python suite: `claude-kit`, the registries, the skill scripts, the git hook, and the suite layout itself. Roots live in [pytest.ini](pytest.ini), not the Makefile. No vault, no become password, no network — the only unattended target |
| `make syntax` | Playbook syntax check. Prompts for the vault password (but not the become password) |
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

`roles/apps/` further splits installs across `tasks/{development,editors,infrastructure,system}.yml`, all included from `tasks/main.yml`.

### Homebrew is per-role

Each role that installs packages defines a `BREW_PACKAGES` dict in `defaults/main.yml` with optional `taps`, `formulas`, `casks` keys. The role's tasks loop those over `community.general.homebrew_tap` / `homebrew` / `homebrew_cask`. There is no central package list — adding a tool means editing the role it belongs to.

An optional `trusted` key records Homebrew tap-trust entries — a list of whole-tap (`user/repo`) or fully-qualified (`user/repo/name`) targets the role passes to `brew trust` (the Ansible module has no trust parameter, so it's a `command` task after the tap loop). This pre-trusts non-official taps so installs keep working once Homebrew enforces tap trust by default (5.2/6.0). Trust is recorded into a shared `~/.homebrew/trust.json` but only *enforced* when `HOMEBREW_REQUIRE_TAP_TRUST` is set, which the playbook does not set.

### Role execution order matters

Playbook order is load-bearing — `brew` runs first so every later role can assume Homebrew is on PATH. **Don't add `meta/main.yml` deps**; control sequencing via the order in [dotfiles.yml](dotfiles.yml).

### Config files are symlinks, not copies

Configs are linked from the repo with `ansible.builtin.file state=link force=true`. Editing a file under `roles/<x>/files/` takes effect immediately in `$HOME` without re-running the playbook. Backups of any pre-existing target go to [backups/](backups/).

### Roles of note

- [roles/coreutils/](roles/coreutils/) — modern Unix replacements (bat, eza, fd, ripgrep, television, btop, …). **Not** the GNU `coreutils` package. Domain-specific CLIs (awscli, gh, docker, lazygit, …) live in `apps`, next to their configs.
- [roles/ai/](roles/ai/) — Claude Code / Gemini / Pi tooling. Skills under `files/claude/skills/` are shared with Pi via symlink. [rtk](https://www.rtk-ai.app/) (token-optimizing CLI proxy) ships here too: it is opt-in per shell, so the Claude `PreToolUse` hook only rewrites commands when `RTK_ENABLE` is exported in the terminal (`RTK_HOOK_AUDIT` in [settings.json](roles/ai/files/claude/settings.json) records rewrite metrics). Its config is symlinked from `files/rtk/config.toml` to `~/Library/Application Support/rtk/config.toml`, which is the only path rtk reads (it ignores `XDG_CONFIG_HOME`).
- [roles/shell/](roles/shell/) — fish, Ghostty, Starship, Television. Custom fish functions live here (e.g. `clean_claude`, `lns`, `tv_change_dir`, and the `_tv_claude_*` picker helpers). Manages the television config + vendored cables under `files/television/`, plus the `TV_CABLE_ALLOWLIST` that prunes upstream cables after `tv update-channels`.
- [roles/ssh/](roles/ssh/) — drives off `SSH_KEYS + SSH_KEYS_EXTRA`. Per-profile keys go in `host_vars/<profile>.yml` as `SSH_KEYS_EXTRA`.
- [roles/macos/](roles/macos/) — `osx_defaults` plus nvram/pmset firmware tweaks.

### Deep reference

The subsystems below are documented outside this file so they cost nothing on a turn that does not touch them.
Open the one you are working in, and only that one.

| Open this | When you are |
|---|---|
| [claude-kit](roles/ai/files/scripts/claude-kit/ARCHITECTURE.md) | Changing the `claude-kit` CLI, its commands, scopes, provenance manifest, dependency resolution, `sync` pruning, or workspace trust |
| [Skill registry & dependencies](docs/internals/skill-registry.md) | Adding or retagging a skill or agent, touching `skill-registry.json` / `agent-registry.json`, the `groups` vocabulary, or the `global` scope tag |
| [Seat plugins](docs/internals/seat-plugins.md) | Authoring or upgrading a staff-engineer seat, its failure-mode references, or the design-versus-frontend boundary |
| [The product-team plugin](docs/internals/product-team.md) | Working on the two-gate product pipeline, its stages, `pt.py`, or `docs/initiatives/` artifacts |
| [Code review policy](docs/internals/code-review-policy.md) | Changing the review bar, its severities or axes, or anything under `roles/ai/files/claude/rules/` |
| [Skill precedence](docs/internals/skill-precedence.md) | Resolving a conflict between an installed skill and an agent's own checklist |
| [Script output style](docs/internals/script-output-style.md) | Writing or changing any script that prints, in fish or python |
| [Where a test lives](docs/internals/testing-layout.md) | Adding a test suite, or changing `pytest.ini` roots |
| [Plan files](docs/internals/plan-files.md) | Touching `plansDirectory`, the plan date-stamp hook, or `docs/plans/` |
| [Acceptance criteria](docs/internals/acceptance-criteria.md) | Working on the `ac` skill or its Jira publishing path |
| [Context hygiene](docs/internals/context-hygiene.md) | Investigating token or usage spend, or deciding where a piece of documentation should live |

Two rules that apply without opening anything: a **name must mean one artifact** across `skill-registry.json`, `agent-registry.json` and `plugins/`, and `~/.claude/skills/` and `~/.claude/agents/` are **role-owned and pruned** by `claude-kit sync`, so a link there that is not derived from the `global` tag is deleted on the next run.

### Secrets

Vault-encrypted vars live in `vars/secrets.yml` (personal) and `vars/work.yml` (work). Both are loaded unconditionally by the playbook. Config files reference env vars as `${NAME}` and resolve at runtime. [vars/work.yml.example](vars/work.yml.example) lists the keys a fork needs to provide.

## Conventions

- **Idempotency is mandatory.** Every task must be safe to re-run. If a task isn't naturally idempotent, gate it with a `stat` / `register` check.
- **Commits and branch names follow the global conventions** (conventional commits via `/commit`, Conventional Branch naming); they are defined in the global CLAUDE.md and the commit skill, not per-repo.
- **Lint exclusions** ([.ansible-lint](.ansible-lint)) skip `yaml[truthy]` and `var-naming` (uppercase Ansible vars are intentional). Don't fight the linter on those — they're conscious choices.
- **A new script prints through the shared vocabulary.** See [Script output style](#script-output-style): `_ui` in fish, `dotkit.ui` in python. No hand-rolled colours, no invented glyphs, emoji only on a heading or the closing summary.
