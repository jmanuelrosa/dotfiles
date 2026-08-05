# Date-stamp plan files and track them in git

## Context

Plan mode writes through `plansDirectory: "docs/plans"` ([settings.json:308](../../roles/ai/files/claude/settings.json)), and Claude Code, not this repo, picks the filename: a slugified prompt prefix plus a random adjective/noun pair, e.g. `right-now-we-save-glimmering-sun.md`. Two problems follow.

The names carry no date, so a directory of them has no chronology. `how-can-i-do-optimized-sunbeam.md` and `if-i-run-tv-jiggly-moonbeam.md` sort alphabetically into meaningless order, and nothing but `stat` says which plan came first. This repo already solved the same problem once: `.claude/state/research/` uses `YYYY-MM-DD-<kind>-<slug>.md`, and `docs/cc-setup-review-2026-07-25.md` carries a date too.

And `docs/plans/` is untracked but not ignored. `git log -- docs/plans/` is empty across every branch, and nothing in `.gitignore` mentions it, so eight plan files sit in the main checkout by accident rather than by decision. The intent is to track them, giving a searchable trail of past design decisions alongside the ADR-style docs.

Outcome: every approved plan lands as `YYYY-MM-DD-<original-slug>.md`, committed, with no manual rename step to forget.

## Approach

A `PostToolUse` hook on `ExitPlanMode` renames the finalized plan file. `ExitPlanMode` is the one point where "this file is final" is true: the plan file is written and edited repeatedly during planning, so renaming on `Write` would break every later `Edit` against the original path.

The path is recovered from the transcript, because `ExitPlanMode` accepts no parameters at all (verified against its loaded schema: it reads the plan from the file and passes nothing). The transcript carries an authoritative record instead. A top-level `type: "attachment"` event holds:

```json
{"type": "plan_mode", "reminderType": "full", "isSubAgent": false,
 "planFilePath": "/abs/path/docs/plans/<slug>.md", "planExists": false}
```

This is the load-bearing find, and it simplifies the hook in three ways:

- `planFilePath` is **absolute**, so the hook never parses `plansDirectory` out of `settings.json`, needs no `docs/plans` fallback, and needs no `HOME` test seam for path resolution.
- `isSubAgent` is a **real boolean**, replacing a filename heuristic (subagent plans get an `-agent-<hash>` suffix, but matching on that string is guessing where a field states the fact).
- One attachment is injected per plan session, so taking the **last** one handles plan mode being re-entered.

Reading the transcript at `transcript_path` follows the established precedent in [skill-recap.sh](../../roles/ai/files/claude/hooks/skill-recap.sh), which parses the same JSONL for `tool_use` blocks. The attachment is written at session start, so it is long flushed by the time `ExitPlanMode` fires.

## Changes

### 1. New hook: `roles/ai/files/claude/hooks/plan-date-stamp.sh`

Python with a `#!/usr/bin/env python3` shebang, `.sh` extension retained per the convention documented in [em-dash-gate.sh](../../roles/ai/files/claude/hooks/em-dash-gate.sh) and [skill-recap.sh](../../roles/ai/files/claude/hooks/skill-recap.sh) (settings.json and the `~/.claude/hooks` symlink reference that name; the shebang decides execution). Stdlib only, matching every other hook.

Logic:

1. Read the event JSON from stdin, take `transcript_path`.
2. Parse the JSONL line by line, skipping unparseable lines exactly as `skill-recap.sh` does, collecting events where `attachment.type == "plan_mode"`. Keep the last.
3. Skip silently (exit 0, no output) when: no `plan_mode` attachment exists; `isSubAgent` is true; the file is missing on disk; the basename already matches `^\d{4}-\d{2}-\d{2}-` (idempotent, so a plan revised and re-approved is not double-dated); or the destination already exists (never clobber).
4. Otherwise `os.replace(old, new)` to `f"{date.today().isoformat()}-{basename}"`. Atomic, same directory.
5. Emit `{"systemMessage": "📅 Plan dated: <new-name>", "suppressOutput": true}`. That pairing is what shows the user a line while adding nothing to model context, and it carries no `decision`/`reason`/`additionalContext`, so the turn is never disrupted.

Fail-open throughout: any exception exits 0 with no output. The rename is cosmetic and must never block an approved plan.

### 2. Register it in `roles/ai/files/claude/settings.json`

Add a `PostToolUse` group inside `hooks` (line 46). No such group exists yet. It sorts before `PreToolUse` at line 47, matching the file's existing key order.

```json
"PostToolUse": [
  {
    "hooks": [
      { "command": "~/.claude/hooks/plan-date-stamp.sh", "type": "command" }
    ],
    "matcher": "ExitPlanMode"
  }
]
```

No Ansible change: [roles/ai/tasks/main.yml:85](../../roles/ai/tasks/main.yml) symlinks hooks by globbing `files/claude/hooks/*` with `isfile` filtering, so a new file is picked up and `hooks/tests/` stays unlinked.

### 3. Tests: `roles/ai/files/claude/hooks/tests/test_plan_date_stamp.py`

Mirrors [test_git_skill_gate.py](../../roles/ai/files/claude/hooks/tests/test_git_skill_gate.py): a `HOOK = Path(__file__).resolve().parents[1] / "plan-date-stamp.sh"` constant and a fixture that writes a fake `transcript.jsonl` into `tmp_path`, creates a plan file, and drives the hook via `subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), ...)`. Assertions are on filesystem state and stdout JSON rather than exit code, since this hook always exits 0.

Cases: a plan file gets today's date prefixed; an already-dated file is untouched; `isSubAgent: true` is untouched; no `plan_mode` attachment is a no-op; a missing plan file on disk is a no-op; a pre-existing destination is not clobbered; a malformed transcript fails open. No `pytest.ini` change needed, `roles/ai/files/claude/hooks/tests` is already a `testpaths` root.

### 4. Docs

- [roles/ai/files/claude/CLAUDE.md](../../roles/ai/files/claude/CLAUDE.md), on the existing "Planning documents go in the repo's `docs/plans/`" bullet: note that approved plans are date-prefixed automatically.
- This repo's `CLAUDE.md`, near the hooks discussion: record that plan files are git-tracked, and why the hook exists rather than a manual rename (Claude Code owns the filename, so the repo can only rename after the fact, and `ExitPlanMode` is the only moment the file is final).

No `.gitignore` change. `docs/plans/` is already unignored, so tracking it just means future `/commit` runs include it.

## Verification

1. `make test` covers the new suite. It is the only unattended target: no vault, no become password, no network.
2. End-to-end, which is what actually proves the wiring, since the tests only exercise the script: `make run-role ROLE=ai` to link the hook and deploy settings.json, restart Claude Code, then run a throwaway plan session in this repo and approve it. Confirm the file in `docs/plans/` gained a `YYYY-MM-DD-` prefix and that the `📅 Plan dated:` line appeared.
3. Re-approving a plan in the same session must not double-date it.
4. Confirm a subagent plan (any session where an Explore or Plan agent runs) leaves its `-agent-<hash>` file unrenamed.

## Open risks

- **`PostToolUse` firing for `ExitPlanMode` is unconfirmed.** The event/matcher pair is the correct one by design, but no hook here currently uses `PostToolUse`, so step 2 of verification is what establishes it. If it does not fire, the fallback is a `Stop` hook gated on the plan file existing and the session no longer being in plan mode, which is strictly worse (it runs every turn and risks renaming mid-planning).
- **A plan edited after approval would reference the old path.** Post-approval plan edits are outside the normal flow, so this is unlikely rather than impossible; the rename is announced in the `systemMessage` and the new name is in the transcript, so recovery is a re-read, not a loss. A "file not found" followed by Claude recreating the plan at the old path would leave two files.
- **The eight existing plan files stay undated.** They live in the main checkout at `~/Developer/dotfiles/docs/plans/`, a different worktree from this one, and two of them (`claude-kit-restore.md`, `desktop-staff-engineer-seat.md`) are hand-named rather than auto-generated. Backfilling dates from `git log` is impossible since they were never committed, so any date would come from mtime. Left as a separate cleanup.
- **No `docs/plans/INDEX.md`.** The `.claude/state/research/` precedent has one, but a dated filename already sorts chronologically, and an index is a second thing to keep in sync.
