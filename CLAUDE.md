# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

Ansible-based macOS dotfiles for Darwin/arm64 (Apple Silicon).
The playbook in [dotfiles.yml](dotfiles.yml) provisions a development machine end-to-end: brew, system prefs, shell, SSH, apps, AI tooling, and per-profile work extras.
Re-running it is the supported maintenance path, so every task must be idempotent.

## Common commands

All workflows go through the [Makefile](Makefile).
Most plays prompt for the vault password (decrypts `vars/secrets.yml` / `vars/work.yml`) and the become password (your macOS password; Touch ID can't work here because Ansible's local connection spawns sudo in a new session).

| Command | Purpose |
|---|---|
| `make lint` | `ansible-lint` (config in [.ansible-lint](.ansible-lint)). Needs the vault password, so it can't run unattended |
| `make test` | pytest over every python suite. Roots live in [pytest.ini](pytest.ini), not the Makefile. No vault, no become password, no network, so this is the only unattended target |
| `make syntax` | Playbook syntax check. Vault password only |
| `make check` | Full dry-run with `--check --diff` |
| `make check-role ROLE=shell` | Dry-run a single role by tag |
| `make run` | Apply the full playbook (personal profile) |
| `make run PROFILE=work` | Apply with the work profile |
| `make run-role ROLE=ai` | Apply a single role by tag |
| `make verify` | Smoke test: core binaries + config symlinks exist |
| `make deps` | Install pinned collections from [requirements.yml](requirements.yml) |

VM-based fresh-install testing uses [Tart](https://github.com/cirruslabs/tart): `make vm-create`, `make vm-start`, `make vm-ssh`, `make vm-destroy`.

## Architecture

Roles live in `roles/<name>/` with the usual `tasks/main.yml`, `files/`, `defaults/main.yml`, `templates/` layout.
What is not obvious from the tree:

- **Profiles gate roles.** `personal` (default) and `work`. Each role in [dotfiles.yml](dotfiles.yml) is gated `when: '<role>' in profile_roles[profile]`, mapped in [group_vars/all.yml](group_vars/all.yml). Per-profile overrides go in `host_vars/<profile>.yml`, loaded by `pre_tasks`. The `reboot` role is intentionally ungated, because it prompts and that prompt is the opt-in.
- **Homebrew is per-role.** Each installing role defines `BREW_PACKAGES` in its `defaults/main.yml` with optional `taps`, `formulas`, `casks`, `trusted` keys. There is no central package list, so adding a tool means editing the role it belongs to.
- **Role execution order is load-bearing.** `brew` runs first so every later role can assume Homebrew is on PATH. Control sequencing through the order in [dotfiles.yml](dotfiles.yml) and **never add `meta/main.yml` deps**.
- **Configs are symlinks, not copies.** Linked with `ansible.builtin.file state=link force=true`, so editing a file under `roles/<x>/files/` takes effect in `$HOME` immediately without re-running the playbook. Pre-existing targets are backed up to [backups/](backups/).
- **Secrets** are vault-encrypted in `vars/secrets.yml` (personal) and `vars/work.yml` (work), both loaded unconditionally. Config files reference `${NAME}` and resolve at runtime. [vars/work.yml.example](vars/work.yml.example) lists the keys a fork must provide.

Roles whose name does not tell you what is inside:

| Role | Holds |
|---|---|
| [coreutils](roles/coreutils/) | Modern Unix replacements (bat, eza, fd, ripgrep, television, btop). **Not** the GNU `coreutils` package. Domain CLIs (awscli, gh, docker, lazygit) live in `apps` beside their configs |
| [ai](roles/ai/) | Claude Code / Gemini / Pi tooling. Pi runs over Claude's payload rather than a copy of it, described in [the pi harness](docs/internals/pi-harness.md). `rtk` ships here and is opt-in per shell via `RTK_ENABLE` |
| [shell](roles/shell/) | fish, Ghostty, Starship, Television, plus the custom fish functions and the vendored television cables |
| [ssh](roles/ssh/) | Drives off `SSH_KEYS + SSH_KEYS_EXTRA`; per-profile keys go in `host_vars/<profile>.yml` |
| [macos](roles/macos/) | `osx_defaults` plus nvram/pmset firmware tweaks |

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
| [The pi harness](docs/internals/pi-harness.md) | Working on Pi: what it shares with Claude Code by symlink, the translated guardrail hooks, the derived `pi-sandbox` permission config, the two trust stores, the footer segment, or `tokencost --pi` |
| [Context hygiene](docs/internals/context-hygiene.md) | Investigating token or usage spend, or deciding where a piece of documentation should live |

Two rules that apply without opening anything: a **name must mean one artifact** across `skill-registry.json`, `agent-registry.json` and `plugins/`, and `~/.claude/skills/` and `~/.claude/agents/` are **role-owned and pruned** by `claude-kit sync`, so a link there that is not derived from the `global` tag is deleted on the next run.

## Conventions

- **Idempotency is mandatory.** Every task must be safe to re-run. If a task isn't naturally idempotent, gate it with a `stat` / `register` check.
- **Commits and branch names follow the global conventions**, defined in the global CLAUDE.md and the commit skill, not per-repo.
- **Lint exclusions** ([.ansible-lint](.ansible-lint)) skip `yaml[truthy]` and `var-naming` (uppercase Ansible vars are intentional). Don't fight the linter on those, they're conscious choices.
- **A new script prints through the shared vocabulary**: `_ui` in fish, `dotkit.ui` in python. No hand-rolled colours, no invented glyphs, emoji only on a heading or the closing summary. See [Script output style](docs/internals/script-output-style.md).
