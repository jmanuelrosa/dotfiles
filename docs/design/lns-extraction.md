# lns extraction

**Status:** Complete (`v0.1.0` published, installed, and retired from dotfiles source)
**Date:** 2026-09-14
**Parent design:** [Standalone script apps](./standalone-script-apps.md)
**Backlog:** [Standalone script apps backlog](./standalone-script-apps-backlog.md)
**Scope:** Extract the `lns` Fish application from dotfiles as a standalone command and install an explicitly versioned release through the shell Ansible role.

## Objective

Move `lns` behavior, tests, documentation, and releases into a clean standalone repository.
Keep dotfiles responsible for installing an exact release and integrating it into Fish.
Preserve the command name, interface, output, exit statuses, target-resolution behavior, skip list, and removal safety.

The standalone repository is published as [`jmanuelrosa/lns`](https://github.com/jmanuelrosa/lns) with release `v0.1.0`.
Dotfiles installs that exact release and no longer contains the original `lns` implementation.

## Original application boundary

The original command is composed from:

- `roles/shell/files/fish/functions/lns.fish`, which owns discovery, filtering, reporting, and removal.
- `_lns_usage.fish` and `_lns_target.fish`, which own help and one-hop target normalization.
- `_clean_claude_excludes.fish`, whose skip list and `CLEAN_CLAUDE_EXCLUDES` extension are reused by `lns`.
- `_clean_claude_confirm.fish`, whose yes-or-abort prompt is reused by `lns`.
- The runtime portions of `_ui.fish`, which own output kinds, colors, glyphs, path rendering, and `NO_COLOR` / `FORCE_COLOR` behavior.

The shared clean-up and UI helpers remain in dotfiles because other shell commands consume them.
The standalone executable privately bundles only the behavior `lns` needs.

## Compatibility contract

The extraction preserves:

```text
lns [ROOT] [--contains STRING] [--broken] [--remove] [--dry-run] [--yes] [--all]
```

- `ROOT` defaults to the current directory.
- Discovery includes hidden and ignored symlinks, never follows them, and sorts their absolute paths.
- Relative targets are normalized against each link's parent without resolving the rest of a symlink chain.
- `--contains` matches target paths, not link names.
- `--broken` selects links for which `test -e` fails and composes with `--contains`.
- Dependency, cache, and build trees are skipped unless `--all` is given.
- `CLEAN_CLAUDE_EXCLUDES` continues to add names to the skip list for compatibility.
- `--remove` lists first and confirms once unless `--yes` is given.
- `--dry-run` with `--remove` stops before confirmation or mutation.
- Removal uses a link check and removes only links, including broken links.
- Help, status output, color behavior, and exit statuses remain unchanged.

Required runtime remains macOS, Fish, `fd`, and the macOS `readlink`, `sort`, `seq`, and `rm` commands.
The application writes no configuration, cache, or state.

## Standalone repository

The clean snapshot contains:

```text
lns/
├── .github/workflows/pull_request.yml
├── tests/test_lns.py
├── AGENTS.md
├── LICENSE
├── Makefile
├── README.md
└── lns
```

The checked-in `lns` file is the self-contained release asset.
It bundles private `_lns_*` helpers and the private `_ui` family, and it does not read runtime code from dotfiles or adjacent files.
There is no generated build step and no new runtime dependency.
The Python standard-library suite exercises the public CLI against temporary filesystem trees.

The characterization suite passed 20 behavior tests against the original Fish functions.
The standalone suite passes those 20 tests plus two distribution checks for executable shape and isolated execution.
Fish syntax, the full suite, and the isolated help smoke test run through `make check` locally and in GitHub Actions.
The published executable, its checksum asset, and the local reviewed bytes all have SHA-256 `ce88ce79923e1589873aa91b37d8be41a22c433ba743ce1daced3bde3df963f0`.

## Dotfiles installation

After the downloaded `v0.1.0` asset and checksum matched the reviewed bytes, the shell role was updated to:

- Declare the repository, release label, exact asset URL, and SHA-256 checksum in `roles/shell/defaults/main.yml`.
- Inspect `~/.local/bin/lns` without following it and refuse to replace any object that is not a regular file.
- Install the exact asset at `~/.local/bin/lns` with mode `0755` through `ansible.builtin.get_url`.
- Inspect the autoloaded `lns.fish`, `_lns_usage.fish`, and `_lns_target.fish` paths without following them.
- Remove only links that point to the known role-owned source files, and refuse unexpected overrides.
- Remove the old source after the published asset, checksum file, and reviewed local bytes match.
- Retain `_ui.fish`, `_clean_claude_excludes.fish`, and `_clean_claude_confirm.fish` for their remaining consumers.
- Replace application behavior tests in dotfiles with lightweight installer and retirement checks.

A running Fish process may retain the autoloaded `lns` function after provisioning.
Starting a new shell or running `functions -e lns` switches command resolution to the installed executable.

## Verification

### Standalone

```sh
make check
make checksum
```

The release candidate must pass syntax, all black-box tests, executable mode, and isolated execution without a dotfiles checkout.

### Dotfiles after publication

```sh
make test
make syntax
make check-role ROLE=shell
make run-role ROLE=shell
make verify
```

Credentialed Ansible commands follow the repository instructions.
The local role apply installed a regular checksum-matched executable and removed the three legacy Fish links.
`make verify` passed with `lns` resolving to the release asset.

## Boundaries

### Always

- Preserve the compatibility contract unless a difference is approved and documented first.
- Keep the executable self-contained and the tests confined to temporary directories.
- Verify the exact remote asset checksum before changing dotfiles ownership.
- Keep each transition idempotent and rollback-friendly.

### Ask first

- Publishing the repository or a release.
- Adding a runtime or development dependency.
- Changing flags, output, exit statuses, environment variables, skip-list behavior, or removal semantics.
- Updating the dotfiles installer to consume a release.
- Removing the original `lns` source files from dotfiles.

### Never

- Follow symlinks while walking.
- Remove a symlink target.
- Traverse or mutate paths outside test temporary directories in automation.
- Follow a moving branch or `latest` release during provisioning.
- Replace an unexpected Fish function or command.
- Publish shared `_ui` or clean-up helpers as a separate package.

## Delivery sequence

1. Characterize the original function with deterministic temporary-directory tests.
2. Build the self-contained Fish executable and prove behavior parity and isolation.
3. Add repository documentation, local verification, and pull-request CI.
4. Stop for publication approval.
5. Publish `jmanuelrosa/lns` and the reviewed `v0.1.0` asset, then verify the downloaded checksum.
6. Stop for dotfiles integration approval.
7. Add the checksum-pinned shell-role installer and migration safety tests.
8. Verify check mode, repeat apply, checksum, and command resolution.
9. Stop for source-removal approval.
10. Retire the three private Fish source files, update documentation, and run full verification.
11. Exercise upgrade and rollback when a later release exists.

## Decisions

| Decision | Choice | Status |
|---|---|---|
| Candidate | Extract `lns` | Approved by the explicit request |
| Local repository | `~/Developer/personal/lns` clean snapshot | Complete |
| Command name | Retain `lns` | Approved |
| Implementation | Retain Fish in one self-contained executable | Approved by the requested existing pattern |
| Release shape | Checked-in `lns` file, no generated build | Complete at `v0.1.0` |
| Runtime dependencies | Retain Fish, `fd`, and macOS commands only | Complete; no dependency added |
| Tests | Python standard-library black-box suite over temporary symlink trees | Complete |
| Compatibility environment | Retain `CLEAN_CLAUDE_EXCLUDES` | Complete |
| CI | macOS pull-request workflow using the same pinned checkout action as `shoo` | Complete |
| Publication | Public `jmanuelrosa/lns` with initial `v0.1.0` | Complete |
| Installer | Shell role, exact release and checksum at `~/.local/bin/lns` | Complete and verified |
| Source retirement | Remove only `lns.fish`, `_lns_usage.fish`, and `_lns_target.fish` | Complete |
