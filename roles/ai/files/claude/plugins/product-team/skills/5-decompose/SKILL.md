---
name: 5-decompose
description: Product Team stage 5 - decomposes the approved design into epics and vertically-sliced stories (each demoable end-to-end), then has product-team:ac-writer add Given/When/Then criteria traced to PRD requirements. No gate; feeds Gate 3.
argument-hint: "[initiative slug, if not inferable from the branch]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Agent
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(git fetch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Stage 5: decompose into epics and stories

Break the PRD + design doc into `05-backlog/epic-{n}.md` and `05-backlog/story-{n.m}.md`, one file per story. No gate; `/product-team:6-gate-check` verifies the result.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask). Precondition: Gate 2 `approved` in STATUS.md (reconcile per conventions.md).
2. Enter the Gate 3 branch per conventions.md Branching (this is Gate 3's first stage: `docs/{slug}-gate-3-dor`, cut fresh from the updated default branch); mark stage 5 `in-progress`.
3. Read `02-prd.md`, `04-ux-spec.md` and `04-design-doc.md` fully.

## Slice

Stories are **tracer bullets**: each one cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) and is demoable or verifiable on its own. Never slice layer-by-layer ("backend for X" + "frontend for X" is one story, not two). Prefactoring that makes the slices easy is its own first story, labeled as such.

- Epics group stories by PRD goal; `epic-{n}.md` carries the goal, its R# coverage, and the ordered story list.
- Every story references the R# ids it implements; a story with no R# reference does not get written.
- Dependencies between stories are flagged explicitly in the Depends-on field; prefer slices that stand alone.
- Size hints: S/M/L. A story trending past L is proposed as a split before writing it (ask).

A story is a flow, and `04-ux-spec.md` is organised by flow, so the two line up: prefer one story per spec flow. Two stories sharing a flow both point at the same anchor; a story spanning two flows is usually two stories.

Fill `../product-lead/references/templates/story.md` per story, leaving the Acceptance criteria section for product-team:ac-writer. Two fields come from the UX spec:

- **Design / UX note**: the anchor of the flow this story implements, which is that flow's heading slugified, e.g. `04-ux-spec.md#export-a-report` for `### Export a report`. When the spec has no `## Flows` section, point every story at its `## No user-facing surface` argument. Verify the anchor resolves against the real heading; stage 6 follows it.
- **Needs design seat**: `yes` when this story's flow draws on the spec's `## New system pieces needed` section, `no` otherwise. Copy that fact, never re-derive it: seat routing is the architect's job, and stage 7 turns this field into a board label so design load is visible before implementation starts.

## Acceptance criteria

Spawn the **product-team:ac-writer** agent: inputs `02-prd.md` and every `05-backlog/story-*.md`; it adds Given/When/Then ACs (ids `AC-{n.m}.{k}`) to each story in place, every AC traceable to an existing R#. It reports any story whose ACs cannot trace; fix the story or the slicing, then re-dispatch for the fixed files.

## Handoff

Update STATUS.md: stage 5 -> `approved`, decided by `n/a (no gate)`, note the epic/story counts. Suggest `/commit` (subject `docs({slug}): stage 5 backlog`) and then `/product-team:6-gate-check`. Then stop.

## Boundaries

- ✅ Always: vertical slices only; R# references on every story; explicit dependency flags; one file per story; a resolvable UX-spec anchor and a set design-seat flag on every story.
- ⚠️ Ask first: any story that looks bigger than L (propose the split); reshaping requirements to fit a slice (that is a PRD change and belongs at Gate 1).
- 🚫 Never: create a story without a PRD requirement reference; write the ACs yourself (product-team:ac-writer owns them); write a freehand "N/A" in a Design/UX note instead of pointing at the UX spec; assign an owning seat to a story (the architect routes seats); run `git commit` / `git push` / `gh pr create`.
