---
name: verify
description: How to drive this repo's tooling for verification. Ansible dotfiles with no app to launch, so the surface is always a CLI (claude-kit, weekly-recap, s-task, s-db) or an Ansible dry-run.
---

# Verifying changes in this repo

There is no application to boot. Every change reaches a user through one of:

| Change touches | Drive it with |
|---|---|
| `roles/*/files/scripts/**` | the CLI itself: `claude-kit …`, `weekly-recap …`, `s-task …` |
| `roles/*/tasks/*.yml` | `make check-role ROLE=<role>` and read the diff |
| `roles/ai/files/claude/skills/*/scripts/*` | run the script directly with a stub CLI on `PATH` |
| `roles/ai/files/claude/hooks/*` | pipe a PreToolUse JSON event to it on stdin |

## Getting a handle

`~/.local/bin/claude-kit` is a symlink **into this checkout**, so the installed
command already runs your working tree. No build, no install step:

```bash
export PATH="$HOME/.local/bin:$PATH"
claude-kit --help
```

`make test` is unattended. `make lint` and `make syntax` need the vault password,
so they cannot run headless: ask the user to run `! make lint`.

## Isolating a run

Two environment variables are the only seams, and they are enough to test almost
anything without touching the real machine:

- `HOME` decides where `~/.claude` is.
- `DOTFILES_DIR` decides which checkout the registries are read from.

So to test registry or tag behaviour, copy the registries, patch the copy, and
point `DOTFILES_DIR` at it. This is the highest-leverage trick here:

```bash
mkdir -p /tmp/dots/roles/ai/files
cp -R roles/ai/files/claude /tmp/dots/roles/ai/files/claude
# patch /tmp/dots/roles/ai/files/claude/skill-registry.json, then:
DOTFILES_DIR=/tmp/dots claude-kit scout --type skill
```

Used this way you can prove *why* an artifact is or is not offered: cut the
dependency edge that pulls it into the global set and watch it reappear.

## Flows worth driving for claude-kit

- `scout` in a synthetic project: a `package.json` with real dependencies is all
  the fingerprint reads (plus `Package.swift`/`*.xcodeproj` for Swift).
- `scout --add` writes into `<cwd>/.claude` only. Run it in a throwaway dir, then
  read `.claude/claude-kit.json` for provenance (`direct` vs `dep-of:<parent>`).
- Re-run any `add` to check idempotency; the summary line adapts.
- `$HOME` is the one directory that cannot be a project: expect exit 6.
- A `global`-tagged artifact refuses a project install without `--global`: exit 4.
- `sync --dry-run` prints `, 0 changes`, which the `ai` role reads for `changed`.

## Gotchas

- **Never run `--add` or `sync` without `--dry-run` against your real `HOME`**
  unless that is the point; `sync` deletes links it does not recognise.
- Exit codes are the contract (`errors.NAMES`), not message text. In zsh, `$?`
  after a pipeline is the *last* command's status: capture with
  `out=$(cmd 2>&1); code=$?` instead, and note `pipestatus` is 1-indexed.
- If uv fails with `Failed to initialize cache at ~/.cache/uv`, set
  `UV_CACHE_DIR` somewhere writable rather than escalating sandbox permissions.
- A real directory under `.claude/skills/` (like this one) is never mistaken for
  an installed artifact: classification follows where a *symlink* resolves to.
