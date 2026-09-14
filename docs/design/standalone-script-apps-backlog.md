# Standalone script apps backlog

**Status:** `hostof`, `kura`, `shoo`, and `lns` extractions complete.
**Updated:** 2026-09-14
**Full design:** [standalone-script-apps.md](./standalone-script-apps.md)

## Why extract

Dotfiles should own machine configuration, installation, and personal integration. Reusable CLIs should get their own tests, docs, releases, and upgrade cadence.

This is an ownership split, not a disk-space project. The research snapshot found eight executable applications (~11,345 source lines, excluding tests and shared `dotkit`). `claude-kit` alone is ~6,356 lines.

Work one application at a time. Do not start another extraction without explicit approval and a separate plan.

## Installation pattern (from `hostof` pilot)

- Single self-contained release asset at `~/.local/bin/<tool>`
- Pin `release` label plus exact SHA-256 checksum in the owning Ansible role
- Use `ansible.builtin.get_url`; no managed checkout, no runtime symlink
- Bundle private runtime helpers per app; do not publish shared `dotkit`
- Application tests and release ownership live in the standalone repository

Reference: [jmanuelrosa/hostof](https://github.com/jmanuelrosa/hostof) at `v0.1.0`.

## Backlog

| Tool | Verdict | Lines (approx.) | Why |
|---|---|---:|---|
| `hostof` | Done | ~1,100 | Generic network diagnostics; clean boundary; pilot complete |
| `claude-kit` | Done, as `kura` | ~6,356 | Largest app; released at `v0.1.0` and installed by checksum; source removed from this repo |
| `port` | Done, as `shoo` | ~575 | Generic macOS port diagnostics; renamed to avoid MacPorts and installed from `v0.2.0` |
| `lns` | Done | ~350 | Generic symlink discovery and safe removal; dotfiles pinned to `v0.1.0` |
| `tokencost` | Next candidate | small | Useful standalone CLI; pricing updates have their own cadence |
| `lokl` | Defer | medium | Reusable Caddy/hosts command, but dotfiles owns committed site configuration |
| `weekly-recap` | Optional later | medium | Coherent reporting CLI; Jira/GitHub/GitLab auth is the main coupling |
| `s-db` | Keep | n/a | Fixed work checkout, database, proxy, and backup assumptions |
| `s-release` | Keep | n/a | Organization-specific, temporary, Git-gate integration |
| `s-task` | Keep | n/a | Shell helpers, worktrees, branch conventions, Git-gate integration |

## Queue (ordered)

### 1. `hostof` - complete

- [x] Standalone repo published: https://github.com/jmanuelrosa/hostof
- [x] Release `v0.1.0` with checksum-pinned install in coreutils role
- [x] Old source removed from dotfiles; packaging tests updated
- [x] Local verification: `make run-role ROLE=coreutils`, `make verify`
- [ ] Dotfiles PR merged (`refactor/extract-hostof`)
- [ ] Upgrade/rollback exercise when `v0.1.1` (or next) release exists

### 2. `claude-kit` - in progress, renamed to `kura`

Design: [kura-extraction.md](./kura-extraction.md).

- [x] Explicit approval to plan extraction
- [x] Separate design walkthrough (discovery, sync/converge, Fish/TV consumers)
- [x] Split application from artifact catalog and dotfiles path discovery: `KURA_CATALOG`, else `~/.local/share/kura/catalog`, no marker-file walk
- [x] Renamed `kura`, since a third of the package serves Pi rather than Claude Code
- [x] Standalone repository built at `~/Developer/kura`: 876 tests pass with no dotfiles checkout, against a committed fixture catalog
- [x] Deterministic single-file release asset, verified running in isolation
- [x] Published `jmanuelrosa/kura` at `v0.1.0`
- [x] Dotfiles installer (pinned release and checksum, legacy link removed, catalog symlink), both call sites on `KURA_CATALOG`, consumer renames, retained tests in `lib/python/tests/test_kura_role.py`
- [x] Old source removed; `pytest.ini` entry dropped
- [ ] Confirm the pinned checksum against the published asset
- [ ] `make run-role ROLE=ai`, then `make verify`
- [ ] Rename the remaining sixteen `.claude/claude-kit.json` manifests

The blockers named here are resolved rather than open: the role's two calls become a
path and a variable change, and the Fish and Television consumers read the command
name and `list --json` only, so the rename is one token each.

### 3. `port` - complete, renamed to `shoo`

Design: [port-extraction.md](./port-extraction.md).

- [x] Explicit approval and separate extraction design
- [x] Initial `port` release retained as historical `v0.1.0`
- [x] Standalone repository renamed: https://github.com/jmanuelrosa/shoo
- [x] Renamed `shoo` executable published as checksum-verified `v0.2.0`
- [x] Shell role installer pinned to the release and SHA-256 checksum
- [x] Legacy Fish function and checksum-matched `port` executable handled safely
- [x] Old Fish source removed from dotfiles
- [x] Local install resolves to `~/.local/bin/shoo`; managed `port` artifacts are absent
- [ ] Dotfiles PR merged
- [ ] Upgrade/rollback exercise when the next release exists

### 4. `lns` - complete

Design: [lns-extraction.md](./lns-extraction.md).

- [x] Explicit approval to extract into `~/Developer/personal/lns`
- [x] Original behavior characterized with 20 black-box tests
- [x] Self-contained Fish release candidate with 22 passing tests
- [x] Documentation, local verification, and pull-request workflow prepared
- [x] Published `jmanuelrosa/lns` and `v0.1.0`
- [x] Downloaded asset and checksum file verified against the local release bytes
- [x] Shell-role installer pinned to the release and SHA-256 checksum
- [x] Role-owned legacy Fish links handled safely and old source retired
- [x] `make run-role ROLE=shell`, then `make verify`
- [ ] Upgrade/rollback exercise when the next release exists

### 5. `tokencost` - not started (needs approval)

- [ ] Explicit approval after `lns`
- [ ] Choose repo boundary (standalone vs small personal-tools monorepo)
- [ ] Standalone repo, release asset, dotfiles installer

### 6. `lokl` - deferred

- [ ] Define configuration boundary (command vs committed Caddy site files in dotfiles)
- [ ] Explicit approval before any extraction work

### 7. `weekly-recap` - optional

- [ ] Document authenticated integration dependencies
- [ ] Explicit approval if pursued

### Keep in dotfiles (no extraction planned)

- `s-db`, `s-release`, `s-task`: work-specific or tightly coupled to dotfiles conventions

## Rules

- One app at a time; no parallel extractions without explicit approval
- Clean snapshot repos; no Git history transfer
- No new `--version` flag required during extraction (identify by tag/checksum)
- Do not create a public `dotkit` package as part of this initiative
- Do not move skills, hooks, or config merely because they contain executable code

## Next step

Pick the next candidate and approve a separate plan. `tokencost` remains next in the queue.
