# Converge pi's project views automatically, everywhere

## Context

The pi work landed the two project-level views pi needs (`<project>/.agents/skills -> ../.claude/skills`, and per-file `<project>/.agents/agents/<agent>.md` links into each installed plugin), and `claude_kit/pi.py` converges both. But convergence only ever happens as a **side effect of a mutating command**: `add`, `remove`, `adopt`, `restore`, `scout --add`. Every project provisioned before `pi.py` existed is therefore invisible to pi, and nothing fixes it until someone happens to install or remove a skill there.

That is not a corner case. `claude-kit doctor` in this very repo reports both gaps today:

```
this project's skills: pi reads .../dotfiles/.agents/skills, which is missing, so none of them load in pi.
this project's plugin agents: pi reads .../.agents/agents, where 5 of 5 agent link(s) are missing
```

Scale, measured: **28** directories under `~/Developer` hold a `.claude/skills`, and `~/.claude.json` records only 13 of them as projects. So "run `claude-kit restore` in each repo" is not the answer. The answer is a command that converges without installing anything, plus two places it fires on its own.

Intended outcome: opening any repo in Claude Code, or running `make run-role ROLE=ai`, leaves pi seeing exactly the skills and seat agents that Claude Code sees there, with no per-repo chore and nothing new committed into other people's repos.

**One correction to the premise worth recording**: pi *does* read `CLAUDE.md`. Its candidate list is `AGENTS.override.md`, `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`, `CLAUDE.MD`, first match per directory (`core/resource-loader.js:31-51`), walking cwd to the filesystem root. So a repo carrying only a `CLAUDE.md` needs **no** `AGENTS.md` symlink. The only broken case is a repo holding *both*, where pi silently reads one and Claude the other. See Phase 3.

## Phase 1: `claude-kit converge`, the mechanism

New command, in the existing shape: `claude_kit/commands/converge.py` plus registration in [cli.py](../../roles/ai/files/scripts/claude-kit/claude_kit/cli.py) (families are enumerated at `cli.py:84-111`; this belongs beside `doctor` as a project command that also takes `--all`).

```
claude-kit converge [--all] [--root PATH ...] [--dry-run] [--quiet]
```

- **No arguments**: converge the current project only.
- **`--all`**: sweep every discovered project.

The command writes **nothing** but the two `.agents` leaves. It installs nothing, records nothing in `claude-kit.json`, and deletes nothing outside the narrowings `pi.py` already enforces. That is what makes it safe to fire from a hook.

Reuse rather than reimplement, since all of this already exists:

| Need | Existing code |
|---|---|
| The two convergences and their reports | `pi.converge`, `pi.converge_agents`, `pi.report`, `pi.report_agents` in [pi.py](../../roles/ai/files/scripts/claude-kit/claude_kit/pi.py) |
| "Is there anything for pi to see here" | `pi.wanted`, `pi.desired_agents` |
| Home is not a project | `scope.project_root` (`scope.py:101-117`, returns `None` for `$HOME`) |
| Reading `~/.claude.json` without disturbing it | `workspace.load`, `workspace.normalise` (`workspace.py:67-78`) |
| Exit codes | `errors.py:7-22`, with `DRIFT` (9) when any project came back `blocked` |
| Output vocabulary | `dotkit.ui` (`ui.note`, `ui.warn`, `ui.path`) |

New, and the only genuinely new logic: **project discovery**, as a small `claude_kit/projects.py`.

- Sources, unioned: the `projects` keys of `~/.claude.json`, and a glob of `--root` directories (default `~/Developer`) bounded at depth 4 for `.claude/skills` or `.claude/claude-kit.json`.
- Filters: drop `$HOME` (via `scope.project_root`), drop paths that no longer exist (`~/.claude.json` currently holds 2 such keys), and drop anything where `pi.wanted()` is false *and* `pi.desired_agents()` is empty, since those have nothing for pi to miss.
- Neither source alone is enough, and that is the reason for the union: the registry misses repos never opened from their own root, and the glob misses anything outside `~/Developer`.

Reporting: one line per project that changed, silent for a steady-state project, a closing count. `--dry-run` reports the same lines and touches nothing. `--quiet` suppresses everything but warnings, for the hook.

Tests in `roles/ai/files/scripts/claude-kit/tests/test_converge.py`, beside the existing [test_pi.py](../../roles/ai/files/scripts/claude-kit/tests/test_pi.py) whose `DOTFILES_DIR` fixture seam is what makes this testable: home is skipped, a vanished registry key is skipped, a project with no skills and no plugins is skipped, a foreign `.agents/skills` yields `blocked` and exit `DRIFT`, `--dry-run` leaves the tree byte-identical, a second run reports nothing.

## Phase 2: the two triggers

**1. A Claude Code `SessionStart` hook.** Every repo self-heals the moment you open it, which is also the moment it matters, for the cost of one python spawn per session.

- `hooks.SessionStart` in [settings.json](../../roles/ai/files/claude/settings.json) gains `claude-kit converge --quiet`, `timeout: 10`.
- While there: that block currently registers `herdr-agent-state.sh session` **twice**, once as `~/.claude/hooks/...` and once as an absolute path to the same file. Collapse it to one entry.

**2. An Ansible task, after the existing `claude-kit sync`.** This is what clears the 28-repo backlog in one pass and keeps it cleared on every provision.

- New task in [roles/ai/tasks/main.yml](../../roles/ai/tasks/main.yml) directly after the `sync` task at `main.yml:191-209`, copying its shape exactly: same pinned environment (not inherited), `--dry-run` under `ansible_check_mode`, `changed_when` driven by the command's own summary line, and the stdout debug gated on `is changed or stderr`.
- It runs `claude-kit converge --all`, so `make run-role ROLE=ai` and `make check-role ROLE=ai` both do the right thing.

Deliberately **not** a pi-side extension: pi resolves `.agents/skills` at startup, so an extension converging on `session_start` would fix the *next* session, not the one running. The Ansible sweep covers a repo only ever opened in pi.

## Phase 3: the two guards (optional, independently shippable)

Both are *detections*, not fixers, because `claude-kit` deliberately creates no root-level files in any repo ([code-review-policy.md](../internals/code-review-policy.md) records that decision).

- **G21, both context files present.** A repo holding `AGENTS.md` *and* `CLAUDE.md` gives pi the first and Claude the second, silently. `dotfiles-product-team-pipeline` is in exactly this state: a 47-line `AGENTS.md` shadowing a 353-line `CLAUDE.md`. Add a `NOTE` in [checks.py](../../roles/ai/files/scripts/claude-kit/claude_kit/checks.py) beside G19/G20, naming this repo's own fix, which is to fold the two and make `AGENTS.md` a relative symlink to `CLAUDE.md`.
- **`.agents/.gitignore`.** The skills link is relative and portable; the **agent links are absolute paths into this dotfiles checkout** and must never be committed into another repo. When converge creates a leaf it also writes `.agents/.gitignore` holding `skills` and `agents`, if absent. That is a file inside the directory we own rather than a root-level `.gitignore` edit, so a repo keeping other `.agents/` content (six do, for example `3bitslost/play10game/.agents/product-marketing-context.md`) keeps it tracked.

Out of scope, and named so it is not mistaken for done: the 12 **committed absolute** symlinks under this repo's own `.claude/skills/`, recorded in [the PR #71 handoff plan](2026-08-18-read-tmp-handoff-dotfiles-pi-settings-20-agile-rose.md). Different bug, same neighbourhood, its own fix.

## Known limits this does not change

Worth stating because each one is silent, and none is fixable by convergence:

- A repo's own `.claude/settings.json` hooks, `permissions` and `sandbox` blocks reach nothing in pi. Only the user-level derivation in `files/pi/sandbox.json` applies.
- `pi-sandbox`'s `allowWrite` includes `"."`, resolved against the cwd, so a repo whose workflow writes outside its own tree gets prompts in pi that it never got in Claude.
- `allowed-tools:`, `model:` and `effort:` on a project skill are ignored by pi's loader.
- `.claude/commands/` is Claude-only by construction (`3bitslost/yourwaitlist` has nothing but commands, so convergence correctly does nothing there). pi's counterpart is `.pi/prompts/`, which nothing here writes.
- Trust stays two stores. Creating `.agents/skills` is itself what makes pi ask, keyed on the **realpathed cwd** rather than the git root, so each launch directory is accepted once. `claude-kit trust` reports both and writes only Claude's.

## Verification

1. `make test`, where the new `test_converge.py` plus the existing pi suites (`lib/python/tests/test_pi_discovery.py`, `test_pi_dialect.py`, `test_pi_sandbox.py`) must stay green. This is the only unattended target.
2. `claude-kit converge --all --dry-run`, expecting it to name the 28-odd projects it would touch and to write nothing (`git status` clean in this repo, no new `.agents` anywhere).
3. `claude-kit converge --all`, then `claude-kit doctor` in this repo and in `~/Developer/work/addingwell/front`: G19 and G20 must both be gone.
4. A second `claude-kit converge --all` must report zero changes, proving idempotency.
5. `make check-role ROLE=ai` then `make run-role ROLE=ai`: the new task reports `changed` on the first apply and `ok` on the second.
6. Open a Claude Code session in a repo with a hand-deleted `.agents/skills`, confirm the `SessionStart` hook restored it and that session start was not visibly slower.
7. Launch pi in `~/Developer/personal/trakdown`: accept the trust prompt once, then confirm its project skills appear in pi's skill list, and in a repo with seats installed that the staff-engineer subagents are discoverable.
