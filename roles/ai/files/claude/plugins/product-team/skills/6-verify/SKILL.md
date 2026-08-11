---
name: 6-verify
description: "Product Team stage 6 - runs pt.py check for the mechanical Definition of Ready items, judges only the four a script cannot decide, and writes the PASS/FAIL report that blocks stage 7. Verifier only, never fixes. No gate."
argument-hint: "[initiative slug, if not inferable from the branch]"
disable-model-invocation: true
model: sonnet
effort: medium
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Bash(python3 *product-lead/scripts/pt.py *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Stage 6: verify the Definition of Ready

A **verifier, not a generator**. Write `06-dor-report.md`; any FAIL blocks `/product-team:7-push-to-board`, and this skill never fixes what it finds (maker/checker).

This stage is pinned to Sonnet at medium effort, and the pin is the point rather than a saving. It used to inherit an Opus session and cost more than research, the PRD and the red team combined, to produce, across three initiatives, one repeated lexical defect. That defect is now a script's job. What is left is four judgments, and they do not need the depth.

First read `../product-lead/references/conventions.md` and the checklist itself, `../product-lead/references/templates/dor-checklist.md`.

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask).
2. Read `docs/strategy/product-team.yml`: in the `solo` profile this stage does not run, so say so and point at `pt.py check {slug}` instead.
3. `pt.py status {slug}`: this stage must read `ready`, which means `05-tasks.md` exists.

## Check

**Run the script first, and do not re-decide what it decided.**

```
python3 .claude/skills/product-team/skills/product-lead/scripts/pt.py check {slug}
```

It owns the eight mechanical items in the checklist: scenario ids resolve, coverage is complete, no requirement has zero scenarios, UX anchors resolve, the design-seat flag is set, size hints and `L` rationales are present, dependencies are declared and acyclic, deferrals are closed. Quote its output verbatim into the report. An item it says it did not check is not an item you check by hand either: it skips a check when the artifact it needs is absent, which is a fact about the initiative rather than a gap in the report.

Then judge the four items the checklist assigns to you, and only those:

- **Scenarios are testable.** Every `THEN` names something observable: a response, a stored record, a rendered state. "Works correctly" is a FAIL. A scenario id that resolves is not the same as a scenario worth having, which is the whole reason this item cannot be scripted.
- **Slices are vertical.** Each story cuts through every layer and is demoable alone.
- **The task list runs from nothing to shipped.** A group for building, one for deploying, one for accepting it where it runs, or an explicit line saying why one does not apply.
- **No unowned open question** in `02-prd.md` touches a requirement this backlog implements.

Verify, don't trust: a pointer you did not open is an item you did not check.

## Report

Write `06-dor-report.md` (metadata header per conventions.md):

- The script's findings, verbatim, under their own heading, with the exit status.
- One line per story: `PASS` or `FAIL` on the model's items, naming which failed.
- For every FAIL, a concrete fix list naming the file and what to change. Fix instructions, not fixes.
- A closing verdict: `ALL PASS - ready for /product-team:7-push-to-board` or `N stories FAIL - stage 7 is blocked`, plus which skill to re-run (`/product-team:5-decompose` for slicing problems, `/product-team:2-write-prd` for a missing scenario, manual edits plus a re-run for wording).

Never mark PASS with any unchecked item; there is no "PASS with notes".

## Handoff

Suggest `/commit` (subject `docs({slug}): stage 6 dor report`) and then `/product-team:7-push-to-board` if the verdict is ALL PASS, or the named fix path if it is not. Then stop.

## Boundaries

- ✅ Always: run `pt.py check` before judging anything and quote it; check every story against every model item; concrete fix lists; fail loudly.
- ⚠️ Ask first: nothing; this stage has no discretionary actions.
- 🚫 Never: re-decide a scripted item by hand; auto-fix stories or edit any backlog file; mark PASS with an unchecked item; write a stage-status row; run `git commit` / `git push` / `gh pr create`.
