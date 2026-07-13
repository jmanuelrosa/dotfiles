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

An optional `trusted` key records Homebrew tap-trust entries — a list of whole-tap (`user/repo`) or fully-qualified (`user/repo/name`) targets the role passes to `brew trust` (the Ansible module has no trust parameter, so it's a `command` task after the tap loop). This pre-trusts non-official taps so installs keep working once Homebrew enforces tap trust by default (5.2/6.0). Trust is recorded into a shared `~/.homebrew/trust.json` but only *enforced* when `HOMEBREW_REQUIRE_TAP_TRUST` is set, which the playbook does not set.

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

### Skill registry & dependencies

Skills are tracked in [roles/ai/files/claude/skill-registry.json](roles/ai/files/claude/skill-registry.json): `repos` (synced from upstream GitHub repos) and `local_skills` (authored here). A skill entry may declare `dependencies: [<name>, ...]` — other skills it invokes at runtime (e.g. the dispatcher `grill-me` runs `/grilling`, so it depends on `grilling`). Each named dependency must itself be a registered or on-disk skill.

Two consumers honor the field. The `claude-skill` fish function (`add`) resolves a skill's transitive dependency closure, downloading and symlinking each into the project; `claude-skill list` shows `(needs: …)` annotations. The `ai` role symlinks `GLOBAL_CLAUDE_SKILLS` plus one level of their declared dependencies into `~/.claude/skills/`, so a global dispatcher skill never ships without the skills it calls. Declare dependencies in the registry, not in `SKILL.md` prose — the latter is overwritten on every `claude-skill update`.

A skill that exists *only* to satisfy another skill's `dependencies` (e.g. `grilling`, `domain-modeling`) carries `dependency_only: true`. It stays a normal tracked entry — synced by `update`/`outdated` and pulled automatically when the skill that needs it is added — but the `claude-skill` browsing surfaces (`list`, `list --group`, `add --group`, the Television picker) hide it and `claude-skill add <name>` refuses it directly, pointing the user at the parent skill. The flag works by a `visibleskills` view in the jq prelude (kept in sync between `claude-skill.fish` and `_tv_claude_list.fish`) that drops these entries; resolution paths keep using the unfiltered `allskills`.

Agent entries in [roles/ai/files/claude/agent-registry.json](roles/ai/files/claude/agent-registry.json) may also declare `dependencies` — naming **skills** (not agents) the agent invokes at runtime (e.g. `architect` depends on `planning-and-task-breakdown`). Both consumers honor it: the `ai` role slurps both registries and folds each `GLOBAL_CLAUDE_AGENTS` agent's skills (plus one level of those skills' own deps) into `GLOBAL_CLAUDE_SKILLS_EFFECTIVE`, and `claude-agent add` installs each declared skill's transitive closure into the project via `claude-skill`'s internal helpers — deliberately bypassing the `dependency_only` direct-add refusal, so an agent may depend on a skill like `domain-modeling`. `claude-agent list` shows the same `(needs: …)` annotations as `claude-skill list`.

Each entry also carries `groups` — a **flat** array of tags drawn from a controlled, multi-facet vocabulary. The tooling treats it as an opaque tag set (`claude-skill list --group <tag>`, `add --group`, `remove --group`, and the Television picker all filter by membership), so adding a tag needs no code change. Tag in this order, deduped: **discipline** (exactly one — `engineering` · `quality` · `product` · `marketing` · `productivity`), then **profile/persona** (`frontend` · `backend` · `mobile` · `ios` · `devops` · `qa` · `security` · `designer` · `marketer` · `pm` · `writer`), then **technology** (`react` · `react-native` · `expo` · `swift` · `swiftui` · `node` · `nestjs` · `fastify` · `hono` · `graphql` · `apollo` · `prisma` · `tailwind` · `astro` · `tanstack` · `playwright` · `sentry` · `typescript`), then **topic/activity** (`design` · `ui` · `testing` · `review` · `refactoring` · `performance` · `architecture` · `seo` · `conversion` · `copywriting` · `writing` · `ci` · `deployment` · `observability` · `workflow` · `documentation` · `planning` · `git` · `language` · `ai` · `web` · `data` · `database` · `learning`). Reuse an existing tag before coining a new one. `agent-registry.json` uses the same `groups` shape but a simpler vocabulary.

### Secrets

Vault-encrypted vars live in `vars/secrets.yml` (personal) and `vars/work.yml` (work). Both are loaded unconditionally by the playbook. Config files reference env vars as `${NAME}` and resolve at runtime. [vars/work.yml.example](vars/work.yml.example) lists the keys a fork needs to provide.

## Conventions

- **Idempotency is mandatory.** Every task must be safe to re-run. If a task isn't naturally idempotent, gate it with a `stat` / `register` check.
- **Commits and branch names follow the global conventions** (conventional commits via `/commit`, Conventional Branch naming); they are defined in the global CLAUDE.md and the commit skill, not per-repo.
- **Lint exclusions** ([.ansible-lint](.ansible-lint)) skip `yaml[truthy]` and `var-naming` (uppercase Ansible vars are intentional). Don't fight the linter on those — they're conscious choices.
