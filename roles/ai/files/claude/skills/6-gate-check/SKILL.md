---
name: 6-gate-check
description: Product Team stage 6 - runs the Definition of Ready checklist against every story, verifier only (never fixes), writes the PASS/FAIL report that blocks stage 7, and opens Gate 3.
argument-hint: "[initiative slug, if not inferable from the branch]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Stage 6: Definition of Ready gate check

A **verifier, not a generator**. Run the DoR checklist against every story and write `06-dor-report.md`. The report fails loudly: any FAIL blocks `/7-push-to-board`, and this skill never fixes what it finds (maker/checker).

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory) and the checklist itself, `../product-lead/references/templates/dor-checklist.md`.

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask). Precondition: stage 5 `approved` in STATUS.md and `05-backlog/` non-empty. A Gate 3 PR already open -> revision mode per conventions.md (typically re-checking after fixes).
2. On branch `docs/{slug}`; mark stage 6 `in-progress`.

## Check

For every `05-backlog/story-*.md`, evaluate each checklist item against the actual file contents, cross-referencing `02-prd.md` (do R# ids exist? do open questions touching them have owners?) and the backlog (dependency cycles). Verify, don't trust: an AC id present but untestable ("works correctly") is a FAIL on that item.

Write `06-dor-report.md` (metadata header per conventions.md):

- One line per story: `PASS` or `FAIL`, with the checklist items that failed.
- For every FAIL: a concrete fix list naming the file and what to change (fix instructions, not fixes).
- A closing verdict: `ALL PASS - ready for /7-push-to-board` or `N stories FAIL - stage 7 is blocked`, plus which skill to re-run (`/5-decompose` for slicing problems, manual edits + re-run `/6-gate-check` for wording).

Never mark PASS with any unchecked item; there is no "PASS with notes".

## Gate handoff

Follow the gate protocol in conventions.md with n=3, stage name `definition of ready`: STATUS.md stage 6 -> `gate-open`, commit subject `docs({slug}): gate 3 dor report`, PR body summarizing the PASS/FAIL tally. A failing report still opens the gate PR (the team sees the state), but say plainly that stage 7 stays blocked until a re-run reports ALL PASS. Then stop; the human runs `/commit` and `/pr`.

## Boundaries

- ✅ Always: check every story against every item; concrete fix lists; fail loudly.
- ⚠️ Ask first: nothing; this stage has no discretionary actions.
- 🚫 Never: auto-fix stories or edit any backlog file; mark PASS with an unchecked item; run `git commit` / `git push` / `gh pr create`.
