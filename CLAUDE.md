# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

Ansible-based macOS dotfiles for Darwin/arm64 (Apple Silicon). The playbook in [dotfiles.yml](dotfiles.yml) provisions a development machine end-to-end: brew, system prefs, shell, SSH, apps, AI tooling, and per-profile work extras. Re-running it is the supported maintenance path — every task must be idempotent.

## Common commands

All workflows go through the [Makefile](Makefile). Every play prompts for two passwords: the vault password (`--ask-vault-password`, decrypts `vars/secrets.yml` / `vars/work.yml`) and the become password (`--ask-become-pass`, your macOS password, streamed to each `become: true` task via `sudo -S`). Touch ID isn't used for the become flow because Ansible's local connection plugin spawns sudo in a new session, which can't see tty-bound timestamps on macOS — the password prompt is the reliable path.

| Command | Purpose |
|---|---|
| `make lint` | `ansible-lint` (config in [.ansible-lint](.ansible-lint)) |
| `make test` | pytest over `claude-kit` and the registries. No vault, no become password, no network |
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
- [roles/ai/](roles/ai/) — Claude Code / Gemini / Pi tooling. Skills under `files/claude/skills/` are shared with Pi via symlink. [rtk](https://www.rtk-ai.app/) (token-optimizing CLI proxy) ships here too: it is opt-in per shell, so the Claude `PreToolUse` hook only rewrites commands when `RTK_ENABLE` is exported in the terminal (`RTK_HOOK_AUDIT` in [settings.json](roles/ai/files/claude/settings.json) records rewrite metrics). Its config is symlinked from `files/rtk/config.toml` to `~/Library/Application Support/rtk/config.toml`, which is the only path rtk reads (it ignores `XDG_CONFIG_HOME`).
- [roles/shell/](roles/shell/) — fish, Ghostty, Starship, Television. Custom fish functions live here (e.g. `claude-skill`, `claude-agent`, `tv_change_dir`). Manages the television config + vendored cables under `files/television/`, plus the `TV_CABLE_ALLOWLIST` that prunes upstream cables after `tv update-channels`.
- [roles/ssh/](roles/ssh/) — drives off `SSH_KEYS + SSH_KEYS_EXTRA`. Per-profile keys go in `host_vars/<profile>.yml` as `SSH_KEYS_EXTRA`.
- [roles/macos/](roles/macos/) — `osx_defaults` plus nvram/pmset firmware tweaks.

### claude-kit

[roles/ai/files/scripts/claude_kit/](roles/ai/files/scripts/claude_kit/) is a stdlib-only Python package managing skills, agents and plugins. [roles/ai/files/scripts/claude-kit](roles/ai/files/scripts/claude-kit) is a three-line shim that the `ai` role symlinks into `~/.local/bin/`; the logic lives in the package **so pytest can import it**, which is the whole reason this is not a fish function. An extensionless executable cannot be imported, so tests could only ever drive it as a subprocess.

Everything claude-kit owns lives in that one directory: the shim, the package, its tests and the README. The shim finds the package by putting **its own directory** on `sys.path`, so the two must stay siblings. That the package can sit in a directory the `ai` role globs onto `PATH` is not luck: Ansible's `fileglob` lookup filters matches through `os.path.isfile`, so directories are invisible to it, and only the README needs the task's `when` guard.

Commands: `list`, `add`, `remove`, `update`, `outdated`, `doctor`, `adopt`. **`--type skill|agent|plugin` is required on all of them except `doctor` and `adopt`**, where it narrows an otherwise cross-type result: `doctor`'s checks cross types by nature, and one `claude-kit.json` holds all three. Nothing is inferred from a name, so the three namespaces may legally overlap and a collision is a `doctor` note rather than an error.

They fall into two families, and `claude-kit -h` groups them that way: **scope-aware** (`add`, `remove`, `list`, `doctor`, `adopt`) act on a project's `.claude/` or on `~/.claude`, where `--global` is meaningful, while **registry-wide** (`update`, `outdated`) rewrite this repo's skill sources and accept no scope at all. argparse allows one subparsers action, so the grouped listing is a generated `epilog` in [cli.py](roles/ai/files/scripts/claude_kit/cli.py) and the subparsers pass no `help=`, which is what suppresses the flat listing that would otherwise duplicate it. Adding a command means adding it to `COMMANDS`, `FAMILIES` and `SCOPE`; `test_help.py` fails if it reaches the CLI without reaching the listing.

Full command reference, worked examples and a corner-case FAQ live in [roles/ai/files/scripts/README.md](roles/ai/files/scripts/README.md). Tests assert every command, flag and exit code appears there, so it cannot silently fall behind the CLI.

**A project is any directory.** `scope.project_root` returns cwd, with no git call and no detection, so `add` works wherever you run it and a subdirectory is its own project rather than a window onto the repo above it. The single exception is `$HOME`, whose `.claude` *is* `~/.claude`: a project-scoped install there would be a silent global one, would load in every repo, and would then be pruned by this role. `NO_PROJECT` therefore has exactly one cause, which is why its messages name `$HOME` directly.

This **diverges from the fish tooling**, which still anchors at the git top level ([_claude_scope_target](roles/shell/files/fish/functions/_claude_scope_target.fish):19-22). In a directory with no repo above it, `claude-skill add x` refuses where `claude-kit add x --type skill` succeeds, and from a subdirectory the two choose different targets. The fish functions are reference-only, so the divergence is recorded rather than fixed; aligning them is a separate decision.

Two rules carry most of the design:

- **`--global` is mandatory whenever an artifact lands in `~/.claude` by direct request.** For a `global`-tagged artifact the flag is confirmation and its absence exits `WRONG_SCOPE`; for an untagged one it is an override. Dependencies are exempt: they resolve their own scope and never need the flag, or `add grill-me` would be impossible since `grilling` is both `dependency_only` and effectively global.
- **`remove` cascades, but never leaves the project it starts in.** A global dependency is always kept and removing a global artifact cascades nothing, because claude-kit standing in one project cannot see the others and would break them. Getting cross-scope removal right would need a machine-wide index of every project, which goes stale the moment a checkout moves.

The cascade needs `<project>/.claude/claude-kit.json`, which records **why** each project-scoped artifact is present (`direct` or `dep-of:<parent>`). Reading the directory cannot substitute: `add tdd` then `add sdd` leaves byte-identical links to `add sdd` alone, yet `remove sdd` must keep `test-driven-development` in the first case and delete it in the second. The distinguishing fact is history. Eight of the ten dependency edges in the registry point at ordinary addable skills, so that ambiguity is the common case. There is deliberately **no pin file**: an untagged artifact in `~/.claude` can only have arrived via `--global`, so the symlink is the record.

`claude-kit adopt` rebuilds that file from disk, for a cloned repo that ships `.claude/` without the manifest and for every project the `claude-skill` fish functions set up before claude-kit existed. Without it those projects lose the cascade silently: `state.read` returns `{}`, `remove` takes its "no record, so keep it" branch, and the project collects dependencies nothing needs. What *is* recoverable is whether something installed **declares** an artifact, which is a fact about the registry read against the current directory rather than about history; what is lost is whether a declared skill was also named directly. So a declared skill is recorded `dep-of:<parent>` (what a clean `add <parent>` would have written, and what usually did happen), and `add`-ing it again promotes it back to `direct`. Adoption is idempotent and additive: an artifact already recorded is skipped, so a re-run tops up a partial file and can never demote a `direct` record. When several installed artifacts declare the same skill the alphabetically first is stored, which is safe rather than arbitrary because `remove.cascade` recomputes dependants from the registry and reads the record only through `state.is_direct` — **the recorded parent name reaches display and nothing else**.

**Skills and plugins share `.claude/skills/`**, so a link's *name* never identifies its type. `scope.installed_names` classifies by which store the link points into ([catalog.py](roles/ai/files/scripts/claude_kit/catalog.py) keeps `LEAF` for where a type installs and `STORE` for where it is kept, and the two differ only for plugins). Comparing names alone counted every link as both a skill and a plugin.

Tests live in [roles/ai/files/scripts/claude_kit/tests/](roles/ai/files/scripts/claude_kit/tests/) at three altitudes, which is what the package layout buys: pure functions over literal dicts (most of them), `tmp_path` for real symlinks, and a handful of subprocess runs through the shim. `HOME` and `DOTFILES_DIR` are the only environmental seams. The directory deliberately has **no `__init__.py`**: pytest walks up from a test module while it keeps finding one, so adding it would import the suite as `claude_kit.tests.*` and break every `from conftest import ...`. `update`/`outdated` stub one function, `upstream.fetch`, and build real tarballs in `tmp_path`, so extraction, the exclude set, the byte comparison and the atomic swap all run for real without a network.

Two constraints worth not breaking: the package is **stdlib-only at runtime**, with no exemption, and `sync.targets` iterates skills regardless of `--type`, so the `--type skill` guard in `update`/`outdated` is the only thing preventing a `--type agent` run from downloading every tracked repo.

PyYAML held the last exemption, in `doctor`'s frontmatter check, and it is what made the check useless where it counted: PyYAML is a test dependency, so on a machine with only `python3` the check reported that it had not run. [frontmatter.py](roles/ai/files/scripts/claude_kit/frontmatter.py) replaces it by **scanning the dialect these artifacts write** rather than parsing YAML in general. That dialect is a flat mapping of scalars with folded values, multi-line plain values and the occasional nested `metadata`, and the failure the check exists for is lexical: an unquoted `": "` in a plain value, which YAML reads as a mapping where none is allowed, so the block fails whole and the artifact silently does not load.

The scanner is therefore **deliberately incomplete, and biased toward silence**: it reports only what is certainly malformed, so a construction it does not model reads as valid rather than broken. A false problem costs more than a missed one, because it teaches the reader to skip the report, which is exactly what happened when this check once emitted 69 findings on a clean repo. The contract is one-directional and [test_frontmatter.py](roles/ai/files/scripts/claude_kit/tests/test_frontmatter.py) is where it is held: **whatever the scanner calls malformed, PyYAML must also reject.** Its `CASES` table records the gaps it knowingly lets through (unterminated quotes, undefined aliases, errors nested under another key) and it runs every real block in `files/claude/` past PyYAML too, plugin-bundled artifacts included, since those are in no registry and nothing else would scan them. PyYAML stays a test dependency, and it is the oracle rather than the implementation.

`claude-kit sync` does not exist yet. Commit `0624d1c` removed the `ai` role's global symlink and prune block on the promise that `sync` would replace it, so **nothing currently provisions `~/.claude/skills` or `~/.claude/agents`**. The `claude-skill` / `claude-agent` fish functions are unchanged and kept as reference.

### Skill registry & dependencies

Skills are tracked in [roles/ai/files/claude/skill-registry.json](roles/ai/files/claude/skill-registry.json): `repos` (synced from upstream GitHub repos) and `local_skills` (authored here). A skill entry may declare `dependencies: [<name>, ...]` — other skills it invokes at runtime (e.g. the dispatcher `grill-me` runs `/grilling`, so it depends on `grilling`). Each named dependency must itself be a registered or on-disk skill.

Two consumers honor the field. The `claude-skill` fish function (`add`) resolves a skill's transitive dependency closure, downloading and symlinking each into the project; `claude-skill list` shows `(needs: …)` annotations. The `ai` role symlinks `GLOBAL_CLAUDE_SKILLS` plus one level of their declared dependencies into `~/.claude/skills/`, so a global dispatcher skill never ships without the skills it calls. Declare dependencies in the registry, not in `SKILL.md` prose — the latter is overwritten on every `claude-skill update`.

A skill that exists *only* to satisfy another skill's `dependencies` (e.g. `grilling`, `domain-modeling`) carries `dependency_only: true`. It stays a normal tracked entry — synced by `update`/`outdated` and pulled automatically when the skill that needs it is added — but the `claude-skill` browsing surfaces (`list`, `list --group`, `add --group`, the Television picker) hide it and `claude-skill add <name>` refuses it directly, pointing the user at the parent skill. The flag works by a `visibleskills` view in the jq prelude (kept in sync between `claude-skill.fish` and `_tv_claude_list.fish`) that drops these entries; resolution paths keep using the unfiltered `allskills`.

Agent entries in [roles/ai/files/claude/agent-registry.json](roles/ai/files/claude/agent-registry.json) may also declare `dependencies` — naming **skills** (not agents) the agent invokes at runtime (e.g. `architect` depends on `planning-and-task-breakdown`). Both consumers honor it: the `ai` role slurps both registries and folds each `GLOBAL_CLAUDE_AGENTS` agent's skills (plus one level of those skills' own deps) into `GLOBAL_CLAUDE_SKILLS_EFFECTIVE`, and `claude-agent add` installs each declared skill's transitive closure into the project via `claude-skill`'s internal helpers — deliberately bypassing the `dependency_only` direct-add refusal, so an agent may depend on a skill like `domain-modeling`. `claude-agent list` shows the same `(needs: …)` annotations as `claude-skill list`.

**A name must mean one artifact.** `skill-registry.json`, `agent-registry.json` and `plugins/` share a single namespace, because `claude-kit add <name>` infers the type from the name alone. A collision is not a naming annoyance, it is a silent mis-install: skills and plugins share the `.claude/skills/` leaf, so the wrong one lands at the right-looking path and the command still reports success. `duplicate_names` over the real catalog is asserted empty in [test_catalog.py](roles/ai/files/scripts/claude_kit/tests/test_catalog.py), so a colliding entry fails CI before it ships. The CLI still refuses rather than guessing at runtime, since a `claude-skill update` can pull an upstream skill whose name we do not control: it exits 8 listing the qualified commands, and `claude-kit add <name> --type skill|agent|plugin` picks one. `--type` applies to every name in the call. Dependencies never need it: every dependency edge (a skill's `dependencies`, an agent's `dependencies`, a plugin's `skillDependencies`) names a **skill**, and the resolver looks one up by type.

Each entry also carries `groups` — a **flat** array of tags drawn from a controlled, multi-facet vocabulary. The tooling treats it as an opaque tag set (`claude-skill list --group <tag>`, `add --group`, `remove --group`, and the Television picker all filter by membership), so adding a tag needs no code change. Tag in this order, deduped: **discipline** (exactly one — `engineering` · `quality` · `product` · `marketing` · `productivity`), then **profile/persona** (`frontend` · `backend` · `mobile` · `ios` · `devops` · `qa` · `security` · `designer` · `marketer` · `pm` · `writer`), then **technology** (`react` · `react-native` · `expo` · `swift` · `swiftui` · `node` · `nestjs` · `fastify` · `hono` · `graphql` · `apollo` · `prisma` · `tailwind` · `astro` · `tanstack` · `playwright` · `sentry` · `typescript`), then **topic/activity** (`design` · `ui` · `testing` · `review` · `refactoring` · `performance` · `architecture` · `seo` · `conversion` · `copywriting` · `writing` · `ci` · `deployment` · `observability` · `workflow` · `documentation` · `planning` · `git` · `language` · `ai` · `web` · `data` · `database` · `learning`). Reuse an existing tag before coining a new one. `agent-registry.json` uses the same `groups` shape but a simpler vocabulary.

One tag sits outside those capability facets: `global` is a **scope** marker, appended last. It flags the entries the `ai` role symlinks into `~/.claude/skills/` and `~/.claude/agents/` so they are available in every project without a per-project `add`. This tag is the single source of truth for that set: `roles/ai/tasks/main.yml` derives `GLOBAL_CLAUDE_SKILLS` / `GLOBAL_CLAUDE_AGENTS` from `groups` membership (there is no hand-maintained list in `defaults/main.yml`), then expands the skills by their declared dependencies as described above. Tag an entry `global` to add it to the set. The Television skill and agent pickers expose a **No global** source (in `claude-skills.toml` / `claude-agents.toml`, backed by the `noglobal` filter in `_tv_claude_list.fish`) that hides entries already installed everywhere, so browsing to install into a specific project shows only what is not.

**The tag decides *location*, not just membership, and the fish tooling enforces it.** There is no `--global` flag and no dependence on your cwd: a global artifact installs **only** into `~/.claude/`, everything else **only** into a project, and `claude-skill`/`claude-agent` refuse a project-scoped install when there is no project (running from `$HOME` used to silently write into `~/.claude/`, which is how a non-global `idea-refine` ended up auto-firing in every repo). [_claude_scope_target](roles/shell/files/fish/functions/_claude_scope_target.fish) is the authority; `list`, `add`, `remove`, both dependency installers, and the Television picker all route through it, and dependencies resolve **per dependency** rather than inheriting the parent's scope. The matching predicate is [_claude_scope_global_skills](roles/shell/files/fish/functions/_claude_scope_global_skills.fish), which mirrors `GLOBAL_CLAUDE_SKILLS_EFFECTIVE`: membership is tag **plus one level of declared dependencies**, so `grilling` and `jira` count as global even though neither carries the tag. Keep it in sync with the role, which is the authority.

Because that invariant holds, `~/.claude/skills/` and `~/.claude/agents/` are role-owned and the `ai` role now **prunes** them: any symlink resolving into `files/claude/{skills,agents}/` that is not in the derived set is deleted on every run. Seat plugins are untouched because they resolve into `files/claude/plugins/`, and `file_type: link` means a real directory is never a candidate. Removing a global link by hand is a transient override, since the next `make run-role ROLE=ai` restores it; to drop one for good, remove its `global` tag.

### Seat plugins & the staff-engineer fleet

Staff-engineer seats are one of two plugin classes here (the other is [product-team](#the-product-team-plugin)), and plugins are the artifact class that lives outside the registries. A seat is a self-contained plugin at `roles/ai/files/claude/plugins/<discipline>/` bundling the agent with its paired failure-modes skill: `.claude-plugin/plugin.json`, `agents/<discipline>-staff-engineer.md`, and `skills/<discipline>-failure-modes/SKILL.md` alongside a `references/` directory of 8-10 checklists. Fourteen ship today: analytics, backend, cloud, data, database, design, dx, frontend, gtm, mobile, platform, qa, security, sre. **These carry no `agent-registry.json` or `skill-registry.json` rows** (`claude-agent.fish` says so at the point of use): `plugin.json` is their metadata, holding `name`, `description`, `version`, `author`, and a `groups` array drawn from the same controlled vocabulary as the registries, and `claude-agent` discovers seats by scanning `plugins/` for a manifest rather than reading a list. `claude-agent add <discipline>` symlinks `plugins/<discipline>` into `$project_root/.claude/skills/<discipline>`, where it loads as `<discipline>@skills-dir`.

Two seat variants exist and the difference is deliberate, not drift. The **implementer seat** carries a fixed 13-section skeleton: an operating loop, three numbered steps (detect the stack, route to installed skills, open the failure-mode checklists), then ways of thinking, red flags, boundaries, a verification gate, a pre-handoff self-check, common rationalizations, and a structured completion report. The **advisor seat** (`security` today) is read-only, declares a `tools:` allowlist, and swaps three sections: hard rules up front, escalation triggers in place of the verification gate, and an output contract in place of the completion report. [references/advisor-adaptation.md](roles/ai/files/claude/skills/agent-writer/references/advisor-adaptation.md) defines that divergence.

The failure-modes `SKILL.md` is a router, not content. Its body is an intro asserting that an unresolved item blocks `done` and escalates as `needs-decision`, a two-column trigger table mapping "the brief or diff touches …" to a `references/*.md` file, and a coda declaring the shape every reference follows: **Failure modes to rule out** (each bullet carrying a `Check:`), **Escalation triggers**, and **What good looks like**. References are stack-agnostic by design, so a seat is useful before the project's framework is known. Two reference names are shared vocabulary and should not be re-coined per seat: `failure-visibility.md` covers whether a failure surfaces with correlating identity (10 seats), and `errors-and-resilience.md` covers UI error boundaries, fallback states, and retry semantics (`design`, `frontend`). `sre` is exempt from both because it is the observability seat itself, splitting the concern across nine specialized references.

Authoring or upgrading a seat goes through the [agent-writer](roles/ai/files/claude/skills/agent-writer/SKILL.md) skill, which owns the whole pipeline: mode selection, the two-researcher protocol, seat anatomy, the failure-modes template, coherence rules, packaging, the fresh-eyes audit, and the verification sweep. `backend` and `platform` are the canon exemplars, and the skill is explicit that they get read in full rather than the pattern being re-derived from memory.

### The product-team plugin

The gated product pipeline ships as a plugin at `roles/ai/files/claude/plugins/product-team/`, not as global skills.
It bundles ten skills (the eight numbered stages, `setup-strategy`, and `product-lead`) with the seven agents the stages dispatch (`competitive-researcher`, `user-evidence-researcher`, `market-sizer`, `strategy-checker`, `pm-red-team`, `ac-writer`, `adr-scribe`).
The pipeline is per-repo by nature: every stage writes `docs/initiatives/<slug>/`, reads `docs/strategy/`, and treats `STATUS.md` as its state machine, so only a repo actually running initiatives needs it loaded.

`product-lead` lives *inside* the bundle because it owns the pipeline's shared library, `references/conventions.md` (gate protocol, branching, local mode) plus ten templates, which every stage reads via `../product-lead/references/`.
A thin signpost skill of the same name stays at `skills/product-lead/` and carries the bundle's only registry row: it holds no mechanics, it just names the install command and the namespaced entry point so the pipeline stays discoverable in a repo that has not installed it.

Two loading facts matter, and both are easy to miss:

- **Artifacts are namespaced by plugin name.** A bundled skill loads as `product-team:<skill>` and a bundled agent as `product-team:<agent>`, so the commands are `/product-team:2-write-prd`, not `/2-write-prd`. Stage bodies, the README table, and the templates all use the namespaced form. The `name:` field in each file's frontmatter stays **bare**: Claude Code applies the prefix, it is never written into the artifact.
- **A project plugin only loads in a trusted workspace, after a relaunch.** Accept the trust dialog (or set `hasTrustDialogAccepted` for the project in `~/.claude.json`), then restart Claude from the repo root. `claude-agent` prints this as a hint on every plugin install.

**A plugin bundles only what it owns.** A skill vendored from an upstream repo stays under `skills/`, because `claude-skill update` syncs it by `upstream_path` and a copy inside a plugin would silently fork from upstream.
Those are declared in `plugin.json` under **`skillDependencies`** instead, and `claude-agent add <plugin>` installs each one's transitive closure into `$project_root/.claude/skills/` next to the plugin symlink (`_claude_agent_install_plugin_deps`, mirroring what `claude-agent add <agent>` already does for agent dependencies).
The key name is load-bearing: `dependencies` is reserved by Claude Code, and an array of skill names there makes the plugin ship **nothing**, silently. Every agent and skill stops registering while `claude plugin details` still lists them all, so the manifest looks healthy (verified on 2.1.220). Unknown keys like `groups` and `skillDependencies` are ignored safely; `dependencies` is not.
`product-team` uses this for `idea-refine`, which is vendored from `addyosmani/agent-skills` and seeds the `setup-strategy` and `0-refine-idea` interviews.
Because the dependency is a normal skill rather than a plugin artifact, it keeps its bare name: the command is `/idea-refine`, not `/product-team:idea-refine`.

### Secrets

Vault-encrypted vars live in `vars/secrets.yml` (personal) and `vars/work.yml` (work). Both are loaded unconditionally by the playbook. Config files reference env vars as `${NAME}` and resolve at runtime. [vars/work.yml.example](vars/work.yml.example) lists the keys a fork needs to provide.

## Conventions

- **Idempotency is mandatory.** Every task must be safe to re-run. If a task isn't naturally idempotent, gate it with a `stat` / `register` check.
- **Commits and branch names follow the global conventions** (conventional commits via `/commit`, Conventional Branch naming); they are defined in the global CLAUDE.md and the commit skill, not per-repo.
- **Lint exclusions** ([.ansible-lint](.ansible-lint)) skip `yaml[truthy]` and `var-naming` (uppercase Ansible vars are intentional). Don't fight the linter on those — they're conscious choices.
