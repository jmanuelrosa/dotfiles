# Standalone script apps

**Status:** Hostof pilot landed in #118; `claude-kit` extracted as `kura` in [kura-extraction.md](./kura-extraction.md).
**Backlog:** [standalone-script-apps-backlog.md](./standalone-script-apps-backlog.md)
**Author:** José Manuel Rosa Moncayo
**Date:** 2026-09-09
**Scope:** Extract `hostof` from dotfiles and install an explicitly versioned release through the coreutils Ansible role.

## Goal

Keep dotfiles responsible for machine configuration, installation, and personal integration rather than application development.
Give reusable tools their own tests, documentation, releases, and upgrade cadence.
Work one application at a time, starting with `hostof`.
Do not design or extract another application until the `hostof` pilot is complete and the next application receives explicit approval.

This is primarily an ownership and maintenance improvement, not a disk-space project.
The research snapshot found eight executable applications with approximately 11,345 physical source lines, excluding tests and the shared `dotkit` library.
`claude-kit` accounts for 6,356 of those lines.
The repository footprint excluding `.git`, caches, logs, and `.DS_Store` was approximately 16 MiB, with much of the role content consisting of Markdown-based AI configuration.
These are snapshot measurements, not targets or evidence of historical growth.

## Recommended boundaries

| Tool | Recommendation | Reason and prerequisite |
|---|---|---|
| `hostof` | Extract first into its own repository | Generic network diagnostics, dedicated tests, user-scoped state, and no dotfiles-layout dependency; bundle its shared output helpers. |
| `claude-kit` | Extract second into its own repository | Substantial application with tests and architecture documentation; first separate the application from the artifact catalog and dotfiles discovery. |
| `tokencost` | Extract after the pilot and `claude-kit` | Useful independent CLI and pricing updates; choose a separate repository or a small personal-tools repository before starting. |
| `lokl` | Defer until its configuration boundary is explicit | Reusable Caddy/hosts command, but dotfiles owns the committed site configuration. |
| `weekly-recap` | Optional later extraction | Coherent reporting CLI; authenticated Jira, GitHub, and GitLab integrations are dependencies to document, not by themselves a reason it must stay in dotfiles. |
| `s-db` | Keep for now | Fixed work checkout, database, proxy, and backup assumptions. |
| `s-release` | Keep for now | Organization-specific, temporary workflow with Git-gate integration. |
| `s-task` | Keep for now | Depends on shell helpers, worktree behavior, branch conventions, and Git-gate integration. |

Keep Ansible roles, personal configuration, shell integration, secrets, and selected AI artifacts in dotfiles.
Do not move all skills or hooks merely because they contain executable code.
Do not create a public `dotkit` package as part of the pilot.

## Existing system and constraints

The state at research time, before either extraction. The first three no longer hold: `hostof` and `kura` are installed as pinned release assets, and neither reads this checkout's layout.

- Commands are symlinked from `roles/<role>/files/scripts/<tool>/<tool>` into `~/.local/bin`; see [coreutils installation](../../roles/coreutils/tasks/main.yml), lines 20-37, and [AI installation](../../roles/ai/tasks/main.yml), lines 167-182.
- Five Python applications import shared `dotkit` code through sibling symlinks; see [the helper-link tests](../../lib/python/tests/test_suites.py), lines 177-223.
- `claude-kit` discovers `dotfiles.yml` and derives `roles/ai/files/claude` in its own `paths.py`, by walking up from the executable for a marker file.
- The AI role executes `claude-kit sync` and `converge --all` directly from the checkout; see [AI tasks](../../roles/ai/tasks/main.yml), lines 193-239.
- Fish/Television consumers depend on `claude-kit` command names and JSON output, in the Television list helper and the two cables it feeds.
- Tests live beside each application and are registered in [pytest.ini](../../pytest.ini); the existing [pull-request workflow](../../.github/workflows/pull_request.yml) runs `make test`.
- Package ownership is per-role, and role order matters; preserve the conventions in [AGENTS.md](../../AGENTS.md).

## Proposed installation model

Start with one self-contained executable release asset installed directly at `~/.local/bin/hostof` by Ansible.
There is no managed application checkout and no runtime symlink.
Editable development clones remain independent of the installed command.

The owning role declares the source repository, release label, exact asset URL, and SHA-256 checksum.
Use the release label for human readability and the checksum for reproducible asset identity and integrity.
Normal provisioning must not follow `main`, resolve a moving `latest`, or upgrade unrelated applications.
A version bump should be a small dotfiles change updating the release and checksum, with verification and a documented rollback to the previous pair.
Rollback restores application code, not arbitrary user-state changes, so state compatibility must be checked separately.

Build the runtime `dotkit` helpers needed by `hostof` into the single executable asset as private code, preserving the existing output vocabulary and license.
Do not include repository-path test helpers as runtime dependencies.
The source repository may remain modular, but the installed artifact must require no sibling package or dotfiles checkout.
Reconsider a shared runtime package only if maintaining multiple private copies becomes a demonstrated problem.

This installer is shallow provisioning glue around `ansible.builtin.get_url`, not a new package manager or plugin framework.
The checksum makes repeated provisioning idempotent and replaces a mismatched asset.
Avoid creating a generalized installation abstraction before the pilot establishes what a second application actually needs.

### Alternatives considered

- **`uv tool install`:** promising for packaged Python applications, but requires package metadata and an explicit runtime installation dependency; reconsider after the pilot.
- **Homebrew tap:** useful for wider distribution and mixed runtimes, but adds formula/release maintenance and needs an explicit policy for exact-version installation.
- **Pinned Git checkout plus symlink:** avoids building a release asset, but leaves an application checkout under the user's home and does not satisfy the selected single-file installation boundary.
- **Git submodules inside dotfiles:** preserve source refs but keep application source nested inside dotfiles and add checkout/update mechanics; not the recommended boundary.
- **One repository for all personal commands:** reduces repository administration and helper duplication but couples releases across unrelated domains; retain as an option for the smaller tools, not the default for `claude-kit`.

The installed `ansible-doc` confirms that `ansible.builtin.get_url` verifies a supplied checksum, skips a download when the destination already matches, replaces mismatched content, and sets an explicit file mode.
External documentation lookup through ctx7 failed during research; installer implementation must refresh the relevant documentation and verify behavior rather than treating these notes as a complete installation contract.
No package manager or new dependency is approved by this draft.

## Ordered task checklist

Every task ends with its verification before the next dependent task starts.
Repository publication, pushes, removal of old source, and breaking API changes require explicit approval.

### Phase 1: Confirm the pilot

#### Task 1: Approve repository and release choices

**Depends on:** Nothing.
**Scope:** This document.

- [x] Use `hostof` as the first application in a public `jmanuelrosa/hostof` repository.
- [x] Install a self-contained `v0.1.0` release asset directly at `~/.local/bin/hostof`, with private bundled runtime helpers and a pinned SHA-256 checksum.
- [x] Start from a clean snapshot with provenance and license attribution rather than transferring Git history.

**Verification:** Record the answers in the decisions section below before creating or publishing a repository.

#### Task 2: Record the current `hostof` behavior

**Depends on:** Task 1.
**Scope:** `roles/coreutils/files/scripts/hostof/` and the runtime portions of `lib/python/dotkit/`.

- [x] Capture supported commands, flags, output, exit statuses, environment overrides, cache behavior, and external dependencies, including `dig`.
- [x] Run the existing focused test suite and record its baseline result.
- [x] List the runtime helpers and test fixtures that must move, without unrelated dotfiles code or user state.

**Verification:** The original focused suite passes with 69 tests using `uv run --offline --with pytest pytest -q roles/coreutils/files/scripts/hostof/tests/test_hostof.py`.
The baseline help output matches, Python compilation passes, and behavior-bearing AST matches after normalizing the private runtime import.

### Phase 2: Build a standalone `hostof`

#### Task 3: Prepare the isolated source tree

**Depends on:** Task 2.
**Scope:** New repository's executable, private runtime helpers, tests, and license.

- [x] Copy only the identified application boundary into a local working tree, preserving attribution.
- [x] Replace sibling symlinks into dotfiles with private runtime code and remove test assumptions about the dotfiles layout.
- [x] Produce one executable release asset containing all runtime code, with no adjacent support package required after installation.
- [x] Keep the installed command name, existing interface, and user-state locations unchanged.

**Verification:** The build, checksum verification, deterministic rebuild, Python compilation, baseline help comparison, and isolated executable smoke test pass without `DOTFILES_DIR`, dotfiles-specific `PYTHONPATH`, or symlinks back to dotfiles.
The moved standalone suite passes with 70 tests using `uv run --offline --with pytest pytest -q`.

#### Task 4: Establish release readiness

**Depends on:** Task 3.
**Scope:** New repository's README, test workflow, and release metadata.

- [x] Document supported runtime/platforms, external commands, installation, configuration, development, and testing.
- [x] Add automated tests for the standalone tree and build the self-contained executable asset without adding a `--version` option.
- [x] Prepare release notes, record the asset's SHA-256 checksum, and document a repeatable release checklist; obtain approval before publishing the repository or release.

**Verification:** Test a clean source checkout using only the documented setup steps, then run the built asset alone from a temporary directory and verify its recorded checksum.

### Checkpoint: Standalone application

- [x] The application works without a dotfiles checkout.
- [x] Existing behavior and state locations remain compatible; the original and moved test suites pass.
- [x] The release source is available to the intended installation environment.
- [x] Review the pilot before changing machine provisioning.

### Phase 3: Install the versioned application from dotfiles

#### Task 5: Add the pinned release declaration

**Depends on:** Task 4 and the standalone checkpoint.
**Scope:** `roles/coreutils/defaults/main.yml` and `roles/coreutils/tasks/main.yml`.

- [x] Declare the repository, release label, exact asset URL, SHA-256 checksum, destination `{{ HOME }}/.local/bin/hostof`, and executable mode in the owning role.
- [x] Detect the existing dotfiles-owned symlink and remove only that known legacy link before the first download; refuse to replace an unexpected symlink.
- [x] Download the asset directly to the final command path and define first-install, repeat-run, check-mode, upgrade, rollback, and uninstall behavior for that file.

**Verification:** The installed file is not a symlink and matches the declared checksum; a second apply makes no changes; check mode does not mutate the installation.

#### Task 6: Switch ownership to the installed asset

**Depends on:** Task 5.
**Scope:** Coreutils script manifest/link tasks and `roles/coreutils/README.md`.

- [x] Remove `hostof` from the old source-link loop so no later task replaces the downloaded file with a symlink.
- [x] Document installation, checksum update, development override, rollback, and uninstall steps.
- [x] Confirm unrelated scripts, user caches, and authorization configuration are unchanged.

**Verification:** `~/.local/bin/hostof` is a regular executable file, its SHA-256 matches the pinned `v0.1.0` asset, and its help smoke test passes.
The first upgrade and rollback exercise is deferred until a second release exists.

#### Task 7: Retire the old source after approval

**Depends on:** Task 6 and successful rollback verification.
**Scope:** Old `hostof` directory, `pytest.ini`, and remaining documentation/test references.

- [x] Confirm the released repository contains the runtime, tests, attribution, and documentation needed to maintain the application.
- [x] Obtain approval to remove the old source and obsolete test root; retain shared `dotkit` code still used by other tools.
- [x] Update stale references and leave lightweight dotfiles installation checks rather than duplicating the application test suite.

**Verification:** The relevant packaging and suite-layout tests pass as part of a 909-test focused run, Ansible lint passes, and no live installer or installed asset references the removed source path.
The full repository suite was attempted but unrelated Pi package and sandbox failures remain outside this pilot.

### Checkpoint: Pilot complete

- [x] Role installation, installed checksum, executable shape, and command smoke test have been verified on the configured machine.
- [x] Dotfiles selects a release asset and checksum but no longer contains the application implementation.
- [x] Upgrade and rollback follow the same release-and-checksum change; exercise them when the second release exists.
- [x] Review the maintenance cost before repeating the pattern or replacing it with Python packaging or Homebrew.

## Deferred candidates

The recommendations for `claude-kit`, `tokencost`, `lokl`, and `weekly-recap` remain research findings, not approved tasks.
After the `hostof` pilot is complete, selecting any next candidate requires explicit approval, a separate design document, and its own walkthrough.

## Decisions to confirm

| Decision | Proposed default | Status |
|---|---|---|
| Pilot | `hostof` | Approved |
| Repository owner/name/visibility | Public `jmanuelrosa/hostof` repository | Approved |
| Initial installer | Self-contained release asset installed directly as `~/.local/bin/hostof` with `ansible.builtin.get_url` | Approved |
| Version identity | Initial `v0.1.0` release label plus exact SHA-256 asset checksum; no new `--version` option during extraction | Approved |
| Shared Python helpers | Private runtime code per application; no new public dependency | Approved |
| History transfer | Start from a clean snapshot with provenance and license attribution | Approved |
| Initiative sequencing | Finish `hostof`, then stop until another application receives explicit approval | Approved |

## Execution notes

This document is the single checklist for the `hostof` pilot.
It combines the design and tasks under `docs/design/`, following the requested planning workflow rather than creating duplicate `tasks/plan.md` and `tasks/todo.md` files.
The other candidates are retained only as research context and require separate approval and planning.
No ADR was needed, and the pilot added no runtime dependency or breaking CLI change.
The `hostof` implementation completed on 2026-09-09.
Do not begin another extraction without explicit approval and a separate plan.
