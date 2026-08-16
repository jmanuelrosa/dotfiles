---
name: 8-living-spec
description: "Product Team stage 8 - at ship time, merges the requirements whose tasks are all complete into docs/specs/{capability}/spec.md and appends the docs/LEARNINGS.md retrospective. Run it when work lands, not when the backlog is written."
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
  - Bash(git log *)
---

# Stage 8: living capability specs

Everything else this pipeline produces is initiative-scoped and starts going stale the day the last task lands. `docs/adr/` survives because an ADR is about a decision rather than a state. This stage is what makes the *behaviour* survive too: the requirements that actually shipped are merged into `docs/specs/{capability}/spec.md`, which describes what the system does now, not what one initiative once proposed.

Run it when work lands. It is idempotent, so running it after each story merges is better than saving it up.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask).
2. `pt.py status {slug}` reports how many shipped requirements are not yet in `docs/specs/`. Zero and nothing else outstanding -> say so and stop.

## Merge

```
python3 .claude/skills/product-team/skills/product-lead/scripts/pt.py spec-merge {slug}
```

A requirement ships when **every task claiming one of its scenarios is checked off** in `05-tasks.md`, which is why those checkboxes are load-bearing; a `Removes:` block has no scenarios, so it ships when every task citing its bare R# is checked instead. The script applies each shipped requirement to its capability's spec at requirement level, preserving every other requirement in that file: a capability accumulates behaviour across initiatives, so a merge that rewrote the file from one PRD would delete what the others added.

It speaks the PRD's change vocabulary. A plain block upserts; a `Modifies:` block replaces the named requirement under its own heading, which is also how a rename lands; a `Removes:` block deletes it. A plain upsert that would drop a scenario the spec already holds is **refused by name** and the run exits non-zero, because that scenario may be another initiative's: the fix is a `Modifies:` line in `02-prd.md` when the drop is intended, never a hand edit here.

Run it with `--dry-run` first if the initiative is large, and read what it would write.

Two things it will tell you rather than guess:

- **A shipped requirement naming no capability** has nowhere to go. Add the `Capability:` line to `02-prd.md` and re-run; do not invent a capability name here, because the name outlives the initiative.
- **A capability spec with a `## Purpose` heading and nothing under it** is a hole the script cannot fill. Write one or two sentences on what the capability is for. This is the one part of the merge that is not mechanical, and leaving it empty is how a living spec becomes a wall of contracts nobody can navigate.

## Retrospective

Append to `docs/LEARNINGS.md`: the date, the initiative, what the agents got wrong this run, which template sections caused friction, and what to change before the next initiative.

This lives here rather than in stage 7 for two reasons. A retrospective written at board-export time is written before a single line has shipped, so it can only report on the paperwork. And the `solo` profile never runs stage 7, so every solo initiative used to produce no retrospective at all.

## Handoff

Report which specs were written and which requirements are still outstanding, then suggest `/commit` (subject `docs({slug}): living capability specs and retrospective`). Then stop.

## Boundaries

- ✅ Always: merge through `pt.py spec-merge` rather than by hand; fill a new capability's Purpose; append the retrospective.
- ⚠️ Ask first: writing a `Capability:` line into `02-prd.md` for a shipped requirement that lacks one.
- 🚫 Never: edit a requirement block in `docs/specs/` by hand (change `02-prd.md` and re-merge, so the two cannot disagree); delete a requirement another initiative put there; mark a task complete to make a requirement ship; run `git commit` / `git push` / `gh pr create`.
