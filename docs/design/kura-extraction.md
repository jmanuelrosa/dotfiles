# claude-kit extraction, and its rename to kura

**Status:** Implemented; pending a role apply on the machine and confirmation of the published asset's checksum
**Author:** Jose Manuel Rosa Moncayo
**Date:** 2026-09-09
**Backlog:** [standalone-script-apps-backlog.md](./standalone-script-apps-backlog.md)
**Pilot pattern:** [standalone-script-apps.md](./standalone-script-apps.md)
**Scope:** `roles/ai/files/scripts/claude-kit/`, `roles/ai/defaults/main.yml`, `roles/ai/tasks/main.yml`, `pytest.ini`, `lib/python/dotkit/testing.py`, `roles/ai/README.md`, the shell and Television consumers that name the command, and a new public `jmanuelrosa/kura` repository.

## Summary

Move the `claude-kit` application out of dotfiles into its own repository, released as one self-contained executable asset installed by the `ai` role at a pinned release and SHA-256 checksum, exactly as `hostof` is installed today. The artifact catalog (registries, skills, agents, plugins, hooks, settings) stays in dotfiles and the application stops knowing anything about the dotfiles layout: it reads a catalog root instead of discovering a checkout.

The command is renamed to **`kura`** in the same move. It manages artifacts for Claude Code and for Pi (`pi.py` and `pi_trust.py` are the second-largest part of the package, and `converge` exists only for Pi's `.agents/`), so a name that says `claude` describes one of its two consumers. `kura` (蔵, a storehouse for what is valuable) is type-neutral, which matters because the catalog holds skills, agents and plugins alike. Subcommands, flags, JSON rows, output markers, exit codes and the `~/.claude` and `.agents/` layouts are unchanged; only the command's own name and the two names derived from it move.

## Motivation

`claude-kit` is the largest executable application in dotfiles at roughly 6,356 source lines across a package, twelve command modules, and a 23-file test suite, and it already carries its own architecture document and user reference. It is developed like an application while being installed like a dotfile: a symlink from `~/.local/bin/claude-kit` into the checkout (`roles/ai/tasks/main.yml:167-182`), with no release, no version identity, and no test cadence of its own. Every change to it lands in the same commit stream as machine configuration.

The coupling that keeps it here is narrower than it looks. Only `paths.repo_root()` and `paths.claude_dir()` know the dotfiles layout (`roles/ai/files/scripts/claude-kit/claude_kit/paths.py:19-49`): they find `dotfiles.yml` by walking up from the executable, or accept a `DOTFILES_DIR` override, then append `roles/ai/files/claude`. Every command consumes the result and nothing else, always through `paths.claude_dir()` (`claude_kit/commands/provision.py:238`, `add.py:298`, `remove.py:230`, `listing.py:184`, `scout.py:345`, `doctor.py:102`, `pull.py:202`, `adopt.py:124`, `restore.py:145`, `pi.py:273`, `pi.py:331`). `repo_root()` has no caller outside its own module. That is a single seam, not a dependency spread through the codebase.

The consumers are also less exposed than the backlog's blocker note suggests. The `ai` role runs `claude-kit sync` and `claude-kit converge --all` from the checkout with `HOME` and `DOTFILES_DIR` pinned (`roles/ai/tasks/main.yml:190-239`), which is a call-site change rather than a redesign. The Claude Code `SessionStart` hook already calls the installed path (`roles/ai/files/claude/settings.json:289`). Fish, Television and `wt` depend on the command name and on `list --json` rows (`roles/shell/files/fish/functions/_tv_claude_list.fish:11-12,54-56`, `_tv_claude_toggle.fish:108-140`, `wt.fish:163-164`, `roles/shell/files/television/cable/claude-skills.toml:42,48`), none of which this design changes.

What genuinely needs deciding is where the catalog comes from once the application no longer walks up to a `dotfiles.yml` marker. That is the substance of this document.

## Non-goals

- Moving the artifact catalog. Registries, `skills/`, `agents/`, `plugins/`, `hooks/`, rules and `settings.json` stay in dotfiles and stay authored there.
- Publishing a shared `dotkit` package. Runtime helpers are bundled privately per application, as in the pilot.
- Adding a `--version` flag. Identity is the release tag plus the pinned checksum.
- Changing any CLI surface beyond the command's own name: subcommands, families, flags, JSON rows, the `, 0 changes` summary marker, exit codes, and the `~/.claude` and `.agents/` layouts all stay as they are.
- Any behaviour change at all. The extraction and the rename ship no feature and fix no bug, so a diff that alters what a command does is out of scope.
- Extracting `tokencost`, `lokl` or `weekly-recap`. They remain separate, separately approved work.
- Moving or reworking the Television cables. They stay in dotfiles, and beyond the command name in their `command` lines they are untouched, including their own `$DOTFILES_DIR` preview commands, which are dotfiles' business rather than a tool input. Shipping them alongside the tool is a later decision.
- Changing what `sync` derives, how the cascade works, or any behaviour documented in the application's own architecture document.
- Migrating Git history. The standalone repository starts from a clean snapshot with attribution.

## Background

### How the catalog is found today

```python
REPO_MARKER = "dotfiles.yml"
CLAUDE_SUBDIR = "roles/ai/files/claude"

def repo_root():
    override = os.environ.get("DOTFILES_DIR")
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    for directory in here.parents:
        if (directory / REPO_MARKER).is_file():
            return directory
    raise SystemExit(...)

def claude_dir(root=None):
    return (root or repo_root()) / CLAUDE_SUBDIR
```

`roles/ai/files/scripts/claude-kit/claude_kit/paths.py:19-49`. The walk works because `resolve()` follows the `~/.local/bin` symlink back into the checkout. A release asset has no such link to follow, so the walk stops being a mechanism the moment the application is installed as a file.

### How the application is installed and invoked today

- Symlinked from a per-tool directory named after its executable, driven by the `AI_SCRIPTS` manifest (`roles/ai/defaults/main.yml:43`, `roles/ai/tasks/main.yml:167-182`).
- `claude-kit sync` runs with `HOME`, `DOTFILES_DIR` and `NO_COLOR` pinned, `--dry-run` under check mode, and `changed_when` matching the `, 0 changes` marker (`roles/ai/tasks/main.yml:190-215`).
- `claude-kit converge --all` runs the same way (`roles/ai/tasks/main.yml:217-239`).
- The `SessionStart` hook calls `~/.local/bin/claude-kit converge --quiet` (`roles/ai/files/claude/settings.json:289`).
- `wt add` calls `claude-kit converge --quiet` in a new worktree (`roles/shell/files/fish/functions/wt.fish:163-164`).

### How the pilot installs a release

```yaml
HOSTOF:
  repository: https://github.com/jmanuelrosa/hostof
  release: v0.1.0
  checksum: sha256:32f6d3e...
```

`roles/coreutils/defaults/main.yml:7-10`, with a stat, an assert that refuses to replace an unexpected symlink, removal of the known legacy link, then `ansible.builtin.get_url` to the final path with `mode: "0755"` (`roles/coreutils/tasks/main.yml:25-49`). This design reuses that shape verbatim.

### Runtime dependencies

The package is stdlib-only apart from `dotkit`, reached through a sibling symlink. Runtime imports are `dotkit.ui` and `dotkit.colors` only (14 modules). `dotkit.testing` is a test-only dependency supplying repository paths (`CLAUDE`, `REPO`, `AI_SCRIPTS_DIR`, `force_colour`), which is exactly the kind of helper the pilot ruled out of the runtime asset.

### Where the tests sit against the catalog

The suite is not uniformly portable. Most tests are pure functions over literal dicts, or real symlinks under `tmp_path` with `DOTFILES_DIR` pointed at a fixture repo (`tests/conftest.py:37`). A minority read the real dotfiles tree or assert against dotfiles files: `test_frontmatter.py` scans every real block under `files/claude/`, `test_provision.py:436-440` and `test_converge.py:406` assert the Ansible task's environment and `changed_when` wording, `test_list_format.py:269` and `test_packaging.py:170` run the shim against the real checkout. That split drives the test-ownership decision below.

## Design rules

- **One catalog root, injected, never discovered.** The application resolves a directory holding the registries and artifact stores. It never looks for `dotfiles.yml`, never knows the string `roles/ai/files/claude`, and `repo_root()` ceases to exist.
- **Resolution order is explicit override, then managed default.** `KURA_CATALOG` wins; otherwise `~/.local/share/kura/catalog`. No third source, no upward search.
- **The default is a symlink dotfiles owns.** The `ai` role points `~/.local/share/kura/catalog` at `{{ role_path }}/files/claude`. The application does not care that it is a link.
- **Provisioning never depends on the default.** The role's own `sync` and `converge` calls pass `KURA_CATALOG` explicitly, so task ordering and a broken link cannot make an apply provision from nothing.
- **The rename carries no compatibility layer.** `kura` reads and writes `kura.json`; it does not fall back to the old manifest name, and nothing migrates one. An orphaned manifest is inert, `doctor` reports the project as `untracked-install`, and `adopt` is the existing remedy. The seventeen files on this machine are renamed by hand once the new command is installed.
- **A missing catalog is a refusal, not an empty catalog.** `sync` already exits `DRIFT` rather than pruning to zero on an empty derived set; an unresolvable catalog root must fail before that, with a message naming both the path it tried and the variable that overrides it.
- **The interface is deep.** One resolved path hides catalog discovery, and no command gains a flag. This is deliberately not a per-command `--catalog-root` option: the catalog is a property of the machine, not of an invocation, and a flag would have to be threaded through twelve commands and every consumer that calls them.
- **Dotfiles keeps the catalog, the standalone keeps the application.** Nothing under `files/claude/` moves; nothing under `files/scripts/claude-kit/` stays except what dotfiles itself must assert.
- **Behaviour is frozen across the move.** The extraction ships no feature and fixes no bug. Any behaviour change is separate work after the release lands.

## Design

### 1. Catalog resolution

`paths.py` loses `repo_root()`, `REPO_MARKER`, `FILES_SUBDIR` and `CLAUDE_SUBDIR`, and gains:

```python
ENV_CATALOG = "KURA_CATALOG"
DEFAULT_CATALOG = ".local/share/kura/catalog"

def catalog_root():
    """The directory holding the registries and the artifact stores."""
    override = os.environ.get(ENV_CATALOG)
    if override:
        root = Path(override)
        if not root.is_dir():
            raise SystemExit(f"{ENV_CATALOG} points at {root}, which is not a directory")
        return root
    root = home() / DEFAULT_CATALOG
    if not root.is_dir():
        raise SystemExit(
            f"no artifact catalog at {root}. Link it there, or set {ENV_CATALOG}"
        )
    return root

def claude_dir(root=None):
    return root or catalog_root()
```

`claude_dir()` keeps its name and its optional argument, so all thirteen call sites stay untouched. `home()` is unchanged and stays the reason `HOME` is honoured over `Path.home()`.

`DOTFILES_DIR` is dropped from the application entirely, along with `repo_root()`, `REPO_MARKER`, `CLAUDE_SUBDIR`, the `dotfiles.yml` walk, its row in the README environment table (`README.md:770`) and the fixture seam in `tests/conftest.py:37`. After the move the only environmental inputs are `HOME` and the optional `KURA_CATALOG`.

The two variables are not the same idea renamed. `DOTFILES_DIR` names a dotfiles checkout whose internal layout the application must know, which is precisely the coupling being removed; `KURA_CATALOG` names the catalog directory itself, with no repository, marker file or subpath implied. Anything in dotfiles that still reads `$DOTFILES_DIR` (the Television previews) does so for its own reasons and is not a consumer of this tool.

The two refusals are separate because they are different mistakes and only one of them can be a typo. Neither can return a path that is not a directory, which matters more than it looks: `cat.build_catalog` against a non-existent root reads empty registries, an empty derived set makes every existing link stale, and `sync` then has to catch it through the `DRIFT` guard that exists for a registry which genuinely lost its `global` tags. Refusing at resolution keeps that guard a backstop rather than the first line of defence.

The `normpath` in `scope.py:167` stays, since an override can still arrive unnormalised, but its comment names `DOTFILES_DIR` and needs rewording.

### 2. Catalog layout as a contract

Extraction turns an internal path into an interface, so the standalone repository documents what a catalog root must contain, and it is the shape the current directory already has:

| Entry | Read by | Written by |
|---|---|---|
| `skill-registry.json` | `cat.build_catalog`, `scout` groups, `pull.targets` | `update` (wholesale), `registry` (`updated_at` stamp) |
| `agent-registry.json` | `cat.build_catalog`, dependency resolution | Nothing |
| `skills/` | `add`, `remove`, `sync`, `list` | `update` (atomic swap per skill) |
| `agents/` | same | Nothing |
| `plugins/<name>/.claude-plugin/plugin.json` | Plugin discovery, `pi.converge_agents` | Nothing |

The write column is a second reason the catalog stays in dotfiles. `update` rewrites `skill-registry.json` and swaps skill directories in place, so the catalog is mutable state the tool edits, and those edits belong somewhere they get committed and reviewed: `lib/python/tests/test_review_policy.py:103` exists because a hand-edit to a generated `groups` block is discarded on the next `update`. It also rules out shipping a catalog inside the release asset or mounting it read-only.

A catalog root is not required to be a git repository, to hold a marker file, or to be a symlink. The application checks `is_dir()` and nothing else.

Anything else in the directory (rules, hooks, `settings.json`, `README`) is dotfiles' business and the application neither reads nor validates it. The one apparent exception is `doctor`'s frontmatter check, which scans blocks under the catalog; the sweep over every real block in `files/claude/` is validating dotfiles' content rather than the scanner, which is why section 7 leaves it here.

### 3. The managed default path

A new `ai` role task, ordered before the `sync` call:

```yaml
- name: Ensure the kura data directory exists
  ansible.builtin.file:
    path: "{{ HOME }}/.local/share/kura"
    state: directory
    mode: "0755"

- name: Point kura at the dotfiles artifact catalog
  ansible.builtin.file:
    src: "{{ role_path }}/files/claude"
    dest: "{{ HOME }}/.local/share/kura/catalog"
    state: link
    force: true
```

The parent guard mirrors the existing `~/.local/bin` one (`roles/coreutils/tasks/main.yml:19-23`), which exists because `hostof`'s `get_url` needed its destination directory on a fresh machine. This pair is what makes an interactive `kura list`, the `SessionStart` hook and `wt add` work with no environment at all.

`~/.local/share` rather than `~/.claude` or `~/.config`: `~/.claude` is Claude Code's and is the directory `sync` prunes, so the tool's own pointer has no business inside it; `~/.config` is for configuration a human edits, and this is a machine-managed pointer.

A symlink rather than a copy, because `update` writes into the catalog. A copy would take those writes and never return them to the checkout, and would need syncing on top. The link gives the catalog exactly one home and keeps an uncommitted registry edit live immediately, as it is today.

`force: true` because the link is dotfiles-owned and convergent, so one pointing at a stale checkout is replaced on the next apply. This is deliberately not the treatment the installed command gets in section 4: there the thing being replaced is a command a person might have installed another way, whereas this path is created by this role, named after this tool, and means one thing.

### 4. Installing the pinned release

`roles/ai/defaults/main.yml` drops `claude-kit` from `AI_SCRIPTS` (leaving `tokencost`) and declares:

```yaml
KURA:
  repository: https://github.com/jmanuelrosa/kura
  release: v0.1.0
  checksum: sha256:<recorded at release>
```

`roles/ai/tasks/main.yml` gains the pilot's four-task block (`roles/coreutils/tasks/main.yml:25-49`) before the sync call:

```yaml
- name: Inspect the installed claude-kit command
  ansible.builtin.stat:
    path: "{{ HOME }}/.local/bin/claude-kit"
    follow: false
  register: claude_kit_command

- name: Refuse to replace an unexpected claude-kit symlink
  ansible.builtin.assert:
    that:
      - claude_kit_command.stat.lnk_source == role_path ~ "/files/scripts/claude-kit/claude-kit"
    fail_msg: "Refusing to replace {{ claude_kit_command.stat.lnk_source }} as claude-kit"
  when: claude_kit_command.stat.islnk | default(false)

- name: Remove the legacy claude-kit symlink
  ansible.builtin.file:
    path: "{{ HOME }}/.local/bin/claude-kit"
    state: absent
  when: claude_kit_command.stat.islnk | default(false)

- name: Install the pinned kura release
  ansible.builtin.get_url:
    url: "{{ KURA.repository }}/releases/download/{{ KURA.release }}/kura"
    dest: "{{ HOME }}/.local/bin/kura"
    checksum: "{{ KURA.checksum }}"
    mode: "0755"
```

The rename splits this block's two jobs, which the pilot's version could conflate because the name did not change. The `stat`/`assert`/`absent` trio addresses `~/.local/bin/claude-kit`, the old symlink, which is now removed rather than replaced: nothing is downloaded to that path again, so the old command disappears from `PATH` on the first apply. `get_url` writes a new path, `~/.local/bin/kura`, which has no legacy occupant to inspect.

The pilot verified the three properties this relies on: `get_url` skips the download when the destination already matches the checksum, replaces mismatched content, and does not mutate under check mode.

The `stat`/`assert`/`absent` trio is the one-time migration, and it is deliberately narrow. `follow: false` inspects the link rather than its target. The assert runs only when something is a symlink and passes only for the exact link this role wrote, so the transition is automatic while a hand-installed link from anywhere else fails the play instead of being silently overwritten. After the first successful apply the stat finds a regular file and both middle tasks skip permanently.

One ordering constraint: this block must come after the `AI_SCRIPTS` link loop (`tasks/main.yml:167-182`), or the loop would relink over the downloaded asset on the same apply. Dropping `claude-kit` from the manifest is what actually prevents that; the ordering is the second guard.

### 5. Call-site changes in the `ai` role

| Task | Today | After |
|---|---|---|
| Global sync | `cmd: "{{ role_path }}/files/scripts/claude-kit/claude-kit sync"`, env `DOTFILES_DIR` | `cmd: "{{ HOME }}/.local/bin/kura sync"`, env `KURA_CATALOG: "{{ role_path }}/files/claude"` |
| Pi convergence | `cmd: ".../claude-kit converge --all"`, env `DOTFILES_DIR` | `cmd: "{{ HOME }}/.local/bin/kura converge --all"`, env `KURA_CATALOG: "{{ role_path }}/files/claude"` |

`HOME` and `NO_COLOR` stay pinned for their existing reasons, `check_mode: false` with `--dry-run` stays, and both `changed_when` expressions keep matching `, 0 changes`.

The role passes the catalog explicitly rather than relying on the symlink it just created, for two reasons. Under `--check`, `ansible.builtin.file` with `state: link` creates nothing, so a symlink-only design would make `sync --dry-run` refuse for want of a catalog on a machine that has never been applied. And an explicit path is a statement that this apply provisions from *this* checkout, which the symlink can only promise for as long as nothing else has rewritten it. Interactive use, the `SessionStart` hook and `wt add` set no environment at all.

The swap is clean rather than a rename because the old variable's justification disappears with it: `DOTFILES_DIR` was pinned to stop the tool walking up from wherever the symlink on PATH resolved to, and after extraction there is no symlink and no walk. The comment in `tasks/main.yml` saying so needs replacing with the check-mode reason.

The `, 0 changes` marker is a cross-repository contract after the move. `provision.py:_summary` keeps one shape on both branches specifically so the role can match on it, and a reworded summary makes every play report `changed`. The standalone repository inherits the test that the summary emits it; dotfiles keeps the test that its task reads it. The two debug tasks that print `stdout_lines` when changed (`tasks/main.yml:207-215`, `:233-239`) are untouched, and remain the only place a prune or a missing artifact is explained.

### 6. Consumers, and what the rename costs each

Without the rename every one of these was untouched, since each reads the command name and `list --json` rows and nothing else. The rename turns them into a one-token edit apiece, and nothing more: no consumer reads a registry, a plugin manifest or the catalog path.

| Consumer | Edit |
|---|---|
| `_tv_claude_list.fish`, `_tv_claude_toggle.fish` | The command name in each invocation; the JSON row shape it parses is unchanged |
| `roles/shell/files/television/cable/claude-*.toml` | The command name in the `outdated`/`update` action lines; `$DOTFILES_DIR` previews untouched |
| `wt.fish`, `settings.json` `SessionStart` hook | The command name; the hook keeps `converge --quiet` and its installed-path form |
| `aliases.fish` `claude:skill`/`:agent`/`:plugin` | The wrapped command name, and the wrapper names themselves are worth revisiting since they read as Claude-only |
| `clean_claude.fish` | The command name in its restore hint |
| `lib/python/tests/test_tv_cables.py` | The command name in the strings it asserts the cables contain |
| `roles/ai/files/claude/**` | Nothing. The catalog does not move and is not renamed: it is Claude Code's payload, and `~/.claude` stays Claude Code's directory |

### 7. Test ownership

| Tests | Home | Why |
|---|---|---|
| Command, scope, state, catalog, pi, trust, frontmatter-scanner, help and CLI-shape tests | Standalone | Application behaviour, driven by fixture catalogs |
| `test_provision.py` and `test_converge.py` Ansible assertions | Dotfiles | They assert this repository's task wording, environment and `changed_when` |
| `test_frontmatter.py`'s sweep of real blocks under `files/claude/` | Dotfiles | It validates the catalog, not the scanner |
| `test_packaging.py`, `test_list_format.py` real-checkout runs | Dotfiles, reduced to an installed-command smoke check | The shim and the sibling `dotkit` link stop existing here |
| `lib/python/tests/test_suites.py`, `test_tv_cables.py`, `test_pi_discovery.py`, `test_pi_dialect.py` | Dotfiles, unchanged in intent | Integration and layout guards; the `dotkit` symlink assertion drops one entry |

The dividing question is which repository can break a given test after the move. The four dotfiles-side items each assert a dotfiles fact: the Ansible tasks' own wiring, the catalog's own content, and the shell integration. Everything else is application behaviour driven by fixture catalogs.

The fixture seam edit is smaller than it sounds. `tests/conftest.py:37` and `:67` already build a fake repo under `tmp_path`; they stop appending `roles/ai/files/claude` to reach its catalog and export `KURA_CATALOG` instead of `DOTFILES_DIR`. `test_provision.py:436-440` and `test_converge.py:406` make the same substitution in the opposite direction, asserting the task pins the new variable.

`pytest.ini:18` loses its `roles/ai/files/scripts/claude-kit/tests` entry, and that file's own comment is the reason the retained tests need a real home rather than a stub tree at the old path: a suite reached by no entry silently does not run. **Proposed default: fold them into `lib/python/tests`**, since all four are integration guards over dotfiles' own wiring, which is what that directory already holds, and it adds no new suite root to a file that warns about suite roots. Needs confirmation.

`dotkit.testing` keeps `CLAUDE` and `REPO`. `AI_SCRIPTS_DIR`'s only reader is `kit_helpers.py:1`, which goes standalone, so it gets deleted rather than left as a path nothing reads.

### 8. Release asset

The standalone repository builds one executable containing the package plus private copies of the `ui` and `colors` helpers, preserving their output vocabulary and license, with no `dotkit` import and no sibling requirement. The build is deterministic and its checksum is recorded in the release notes and pinned in dotfiles. `dotkit.testing` is not bundled: it supplies repository paths, which is exactly the class of helper the pilot ruled out of a runtime asset.

Two constraints the build must not quietly break:

- **Stdlib-only at runtime.** With `ui` and `colors` inlined the asset has no third-party import at all. PyYAML stays a test dependency and the oracle for `frontmatter.py`, never the implementation, since the scanner exists precisely because PyYAML's absence made `doctor`'s check report that it had not run.
- **The package stays importable.** The tests drive `kura` as a package rather than the entry point, which is the stated reason this is not a fish function. So the source tree keeps its package layout and bundling happens at build time; a single flattened script that pytest cannot import is not an acceptable release format.
- **The development entry point moves to `bin/kura`.** The command and the package want the same name and one directory cannot hold both, so the shim inserts its parent's parent on `sys.path` instead of its parent. The release asset is a zipapp with its own `__main__.py`, so nothing on an installed machine reads the shim.

The bundling mechanism itself is a standalone-repository concern beyond "one executable file, deterministic, checksum recorded". The pilot has a working answer to copy.

The pilot's isolation bar applies unchanged: the built asset runs from a temporary directory with no `KURA_CATALOG` beyond a fixture path, no dotfiles-specific `PYTHONPATH`, and no symlink back to dotfiles.

## Runtime behaviour matrix

| Situation | Result |
|---|---|
| Provisioned machine, interactive `kura list` | Resolves `~/.local/share/kura/catalog`; identical output to today |
| `ai` role apply | Passes `KURA_CATALOG` explicitly; unaffected by the default path |
| Check-mode apply | `--dry-run` on both calls; no writes; `changed` still read off `, 0 changes` |
| Catalog symlink missing or dangling, no override | Refusal naming the path and `KURA_CATALOG`; no prune, no partial sync |
| Catalog present but registries lose every `global` tag | Unchanged: `sync` exits `DRIFT` and touches nothing |
| Developer working on a clone | `KURA_CATALOG=/path/to/dotfiles/roles/ai/files/claude` against the clone's own `bin/kura` |
| A project still holding `claude-kit.json` | The manifest is inert: `remove` keeps dependencies rather than cascading, `doctor` reports `untracked-install`, and `adopt` rebuilds the record. This repository's own is renamed in this commit; the other sixteen are renamed by hand after the role applies |
| Muscle memory typing `claude-kit` | Command not found. The old symlink is removed rather than replaced, so there is no stale copy silently reading the same catalog |
| Second dotfiles checkout | Whichever checkout the symlink names is the machine's catalog; a one-off run overrides per invocation |
| Upgrade or rollback | Release plus checksum change in `roles/ai/defaults/main.yml`; `get_url` replaces the mismatched file |
| Legacy symlink still on PATH | Asserted as the known dotfiles link, removed, replaced by the asset; an unexpected link fails the play |

## Alternatives considered

- **Keep `DOTFILES_DIR` as the seam.** Smallest diff, but it leaves the application knowing the dotfiles layout, which is the coupling the extraction exists to remove, and gives the installed asset no way to find a catalog without an environment variable set by whoever calls it.
- **Per-command `--catalog-root` flag.** Explicit, but changes the CLI contract, needs threading through twelve commands, and pushes catalog knowledge into Fish, Television, `wt` and the session hook. Rejected against the rule that no consumer contract changes.
- **A config file holding the catalog path.** Considered and set aside: it adds a file format, a parser and a search order to solve a problem one symlink already solves, and the override variable covers the one-off case.
- **Move the catalog into the standalone repository.** Would make the tool self-contained, but the registries, skills and plugins are personal configuration authored in dotfiles and rewritten by `update`; publishing them is a different decision entirely.
- **Publish `dotkit` as a package.** Explicitly ruled out by the initiative.
- **`uv tool install` or a Homebrew tap.** Both remain open for later; the pilot's release asset is the pattern with a working precedent.
- **Leave tests in dotfiles.** Would keep the largest suite in the repository that no longer owns the code, and block an independent test cadence.
- **Extract without renaming.** Every consumer would have been untouched, but the name would keep claiming the tool is Claude Code's when a third of the package serves Pi. Renaming at extraction costs one token per consumer and is the cheapest this will ever be, since nothing is published or pinned yet.
- **Names considered and rejected:** `agentkit` and `harness` (both taken and both overclaim), `skillkit` or any skill-word (narrows to one of three artifact types), `rig` (collides with R's installation manager), `dojo` (Dojo Toolkit), `kanban` (spoken for), `taller` (reads as English "taller"). `waza`, `kumiki`, `dogu` and `bottega` were the shortlist `kura` won against on neutrality and length.
- **A compatibility fallback for `claude-kit.json`.** Rejected: reading the old name keeps a branch alive indefinitely for seventeen files that a `mv` fixes, and `adopt` already exists for exactly the state an unrecognised manifest leaves behind.

## Testing decisions

The boundary is external behaviour: resolved catalog path, command output, JSON rows, exit codes and on-disk links. Catalog resolution gets its own tests in the standalone repository (override wins, default resolves, missing default refuses with both the path and the variable named, override pointing at a non-directory refuses). Existing suites keep their shape and swap the `DOTFILES_DIR` fixture seam for `KURA_CATALOG`, exported for every test by an autouse fixture so no case can read whatever catalog the machine happens to hold. Dotfiles keeps only what asserts dotfiles facts: the two Ansible task assertions, the real-catalog frontmatter sweep, the Television cable guards, and an installed-command smoke check.

## Open questions

- Should a `doctor` check report the resolved catalog root and whether it is the managed symlink, or is that a later change once the release has landed?

**Resolved after the walkthrough:** the pinned checksum was confirmed against the published `v0.1.0` asset; the work landed on `refactor/extract-kura` as #119, rebased onto `main` once the hostof pilot merged as #118; and the Claude-branded consumer names were renamed to `kura:skill` / `kura:agent` / `kura:plugin`, `_tv_kura_list` / `_tv_kura_toggle`, and the `kura-skills` / `kura-agents` cables. `clean_claude` and `clean:claude:*` keep their names, since they clean Claude Code state rather than anything kura owns.

**Decided during the walkthrough:** the dotfiles-side remainder tests fold into `lib/python/tests` rather than a new suite root; `AI_SCRIPTS_DIR` in `dotkit.testing` is deleted once its only reader goes standalone; the command is renamed to `kura`; and the manifest rename carries no fallback and no migration.

## Appendix: affected files

**Read for the extraction**

- `roles/ai/files/scripts/claude-kit/` (package, tests, `README.md`, `ARCHITECTURE.md`, shim, `dotkit` symlink)
- `lib/python/dotkit/ui.py`, `lib/python/dotkit/colors.py`, `lib/python/dotkit/testing.py`
- `roles/coreutils/defaults/main.yml`, `roles/coreutils/tasks/main.yml` (pilot pattern)

**Created in the standalone repository** (built, at `~/Developer/kura`)

- `bin/kura` entry point, `kura/` package with `ui.py` and `colors.py` vendored, `tests/` with a committed fixture catalog under `tests/fixtures/catalog/`, `README.md`, `ARCHITECTURE.md`, `RELEASING.md`, `LICENSE`, `build.py`, `Makefile`, and a CI workflow that runs the suite, builds twice to compare checksums, and runs the asset in isolation

**Modified in dotfiles**

- `roles/ai/defaults/main.yml` (drop from `AI_SCRIPTS`, add `KURA`)
- `roles/ai/tasks/main.yml` (install block, catalog symlink task, both command call sites)
- `pytest.ini` (drop the claude-kit suite entry)
- `lib/python/dotkit/testing.py` (drop `AI_SCRIPTS_DIR` if unclaimed)
- `lib/python/tests/test_suites.py` (drop the removed `dotkit` symlink entry)
- `roles/ai/README.md`, `README.md`, `CLAUDE.md`, `Makefile` comment, `docs/internals/testing-layout.md`, `docs/internals/skill-registry.md`, `docs/internals/pi-harness.md`, `roles/ai/files/claude/GETTING-STARTED.md` (stale references)
- `docs/design/standalone-script-apps-backlog.md` (queue status)

**Removed from dotfiles after approval**

- `roles/ai/files/scripts/claude-kit/` in full, except the retained dotfiles-side assertions relocated per section 7

**Renamed references only, no behaviour change**

- `roles/shell/files/fish/functions/_tv_claude_list.fish`, `_tv_claude_toggle.fish`, `wt.fish`, `clean_claude.fish`
- `roles/shell/files/fish/conf.d/aliases.fish`
- `roles/shell/files/television/cable/claude-skills.toml`, `claude-agents.toml`
- `roles/ai/files/claude/settings.json` (the `SessionStart` hook command)
- `lib/python/tests/test_tv_cables.py` (the strings it asserts)
- `dotfiles/.claude/claude-kit.json`, the one tracked provenance manifest, renamed to `kura.json`

**Deliberately untouched**

- `roles/ai/files/claude/**` (the catalog, which stays Claude Code's payload under its own name)
- `~/.claude` and every project's `.claude/` and `.agents/` layout
