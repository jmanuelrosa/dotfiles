# Implementation Plan: Shoo extraction

## Overview

Extract the existing Fish `port` function into a standalone public repository, preserve its behavior through black-box characterization, and replace the dotfiles-owned implementation with checksum-pinned standalone command `shoo`.
The historical `port v0.1.0` release records the initial extraction; `shoo v0.2.0` is the final renamed command.
The approved contract is `docs/design/port-extraction.md`.
Tasks are tracked in `tasks/todo.md`.

## Architecture decisions

- Retain Fish to avoid turning extraction into a language rewrite.
- Make the checked-in executable the release asset, so source bytes and release bytes are identical.
- Bundle private output helpers and keep the standalone runtime independent of dotfiles.
- Use Python standard-library `unittest` for black-box tests with fake process commands.
- Install through the shell role at `~/.local/bin/shoo` with a release label and exact SHA-256 checksum.
- Remove only the checksum-matched `port v0.1.0` executable during migration.
- Keep publication and old-source removal as explicit human gates.
- Preserve an unexpected Fish function override and fail clearly instead of overwriting it.
- Correct the legacy empty-survivor bug so successful SIGTERM returns 0 and prints the intended success message.

## Dependency graph

```text
Local repository foundation
    |
    v
Characterize basic CLI and output
    |
    v
Standalone entrypoint and private UI
    |
    v
Characterize listing and lookup
    |
    v
Standalone listing and lookup
    |
    v
Characterize detail, Docker, and kill
    |
    v
Complete standalone behavior
    |
    v
Isolation, documentation, CI, checksum
    |
    v
Publication approval -> initial v0.1.0 publication -> shoo v0.2.0 rename
    |
    v
Dotfiles installer tests -> installer implementation
    |
    v
Check-mode and apply verification
    |
    v
Source-removal approval -> retirement and final verification
```

## Task list

### Phase 1: Behavior lock and standalone slices

- [x] Task 1: Create the unpublished standalone repository foundation.
- [x] Task 2: Characterize help, argument handling, dependency checks, and output color.
- [x] Task 3: Implement the standalone entrypoint, private UI, and help path.
- [x] Task 4: Characterize listing and lookup behavior.
- [x] Task 5: Implement standalone listing and lookup behavior.
- [x] Task 6: Characterize long detail, Docker annotation, and safe kill behavior.
- [x] Task 7: Complete standalone detail and kill behavior.

### Checkpoint: Behavior parity

- [x] The same black-box expectations pass against the original function and standalone executable, except for the approved regression that fails against the original.
- [x] Tests never signal a real process or inspect live listeners.
- [x] Fish syntax and the complete standalone suite pass.

### Phase 2: Release readiness

- [x] Task 8: Prove isolation and add standalone documentation and CI.
- [x] Task 9: Prepare the exact `v0.1.0` asset, checksum, and release notes.

### Checkpoint: Publication approval

- [x] The local source tree works without dotfiles and is ready to publish after repository initialization.
- [x] Obtain explicit approval before creating the GitHub repository or release.

### Phase 3: Publication and provisioning

- [x] Task 10: Publish `jmanuelrosa/port` and verify the remote `v0.1.0` asset.
- [x] Task 11: Add failing dotfiles tests for installer ownership and safety.
- [x] Task 12: Implement the checksum-pinned `shoo` installer and lifecycle documentation.
- [x] Task 13: Verify check mode, first apply, repeat apply, checksum, and command resolution.

### Checkpoint: Source-removal approval

- [x] The released asset is installed as a regular executable and the role is idempotent.
- [x] Obtain explicit approval before deleting the old Fish sources.

### Phase 4: Retirement

- [x] Task 14: Remove the old application sources and update extraction records.
- [x] Task 15: Run final standalone and dotfiles verification.

### Approved rename amendment

- [x] Rename the repository and command from `port` to `shoo`.
- [x] Publish the self-contained `shoo v0.2.0` asset and verify its checksum.
- [x] Migrate the shell role from the checksum-matched `port v0.1.0` executable.
- [x] Remove both retired Fish source files and stale autoload links.

### Checkpoint: Complete

- [x] Dotfiles contains installation and integration only.
- [x] The standalone repository owns application behavior, tests, documentation, and releases.
- [x] Upgrade and rollback are documented as release-and-checksum changes.

## Execution discipline

Tasks 2 through 7 use red, green, refactor slices.
Each new behavior group is first asserted against the original function through a temporary wrapper, then shown failing against the incomplete standalone executable, then implemented minimally.
The approved empty-survivor regression is expected to fail against the original and pass only against the standalone executable.
Run focused tests after each code slice and do not repeat an unchanged verification command.
Do not begin dotfiles installer work until the published asset and remote checksum exist.
Do not remove old source until the installed release has passed its checkpoint.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| No existing `port` suite | High | Build deterministic black-box characterization before changing behavior. |
| Legacy successful kill path reports a blank survivor | High | Keep the reproduction red against the original, filter empty values in the standalone executable, and verify the intended success result. |
| Tests signal real processes | High | Replace `lsof`, `ps`, `docker`, and `kill` through a temporary `PATH` and assert recorded calls. |
| Fish function shadows the installed executable | High | Exclude the legacy autoload file during transition, remove only the known role-owned link, and test command resolution in a new Fish process. |
| Release differs from reviewed source | High | Release the checked-in executable itself and compare the downloaded asset checksum. |
| MacPorts also owns the name `port` | Medium | Rename the standalone command to `shoo` and safely remove only the managed legacy executable. |
| `get_url` behaves differently in check mode or on mismatch | Medium | Refresh `ansible-doc`, add retained tests, and exercise check mode, first apply, and repeat apply. |
| Current branch name is non-conventional | Medium | Rename it to a conventional `refactor/extract-shoo` branch before committing. |
| Main checkout has unrelated work | Low | Keep all dotfiles edits in the clean `dotfiles-port` worktree and create the standalone repository separately. |

## Parallelization

The behavior slices are sequential because later implementation depends on earlier characterization.
Standalone README and CI can be prepared together after behavior parity.
Dotfiles documentation and installer implementation can be edited together after the installer tests are red.
No publication, provisioning, or removal step is parallelized across approval gates.

## Open questions

No implementation question remains open.
Upgrade and rollback verification waits for a later release.
