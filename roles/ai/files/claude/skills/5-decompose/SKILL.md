---
name: 5-decompose
description: Product Team stage 5 - decomposes the approved design into epics and vertically-sliced stories (each demoable end-to-end), then has ac-writer add Given/When/Then criteria traced to PRD requirements. No gate; feeds Gate 3.
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
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Stage 5: decompose into epics and stories

Break the PRD + design doc into `05-backlog/epic-{n}.md` and `05-backlog/story-{n.m}.md`, one file per story. No gate; `/6-gate-check` verifies the result.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask). Precondition: Gate 2 `approved` in STATUS.md (reconcile per conventions.md).
2. On branch `docs/{slug}`; mark stage 5 `in-progress`.
3. Read `02-prd.md` and `04-design-doc.md` fully.

## Slice

Stories are **tracer bullets**: each one cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) and is demoable or verifiable on its own. Never slice layer-by-layer ("backend for X" + "frontend for X" is one story, not two). Prefactoring that makes the slices easy is its own first story, labeled as such.

- Epics group stories by PRD goal; `epic-{n}.md` carries the goal, its R# coverage, and the ordered story list.
- Every story references the R# ids it implements; a story with no R# reference does not get written.
- Dependencies between stories are flagged explicitly in the Depends-on field; prefer slices that stand alone.
- Size hints: S/M/L. A story trending past L is proposed as a split before writing it (ask).

Fill `../product-lead/references/templates/story.md` per story, leaving the Acceptance criteria section for ac-writer.

## Acceptance criteria

Spawn the **ac-writer** agent: inputs `02-prd.md` and every `05-backlog/story-*.md`; it adds Given/When/Then ACs (ids `AC-{n.m}.{k}`) to each story in place, every AC traceable to an existing R#. It reports any story whose ACs cannot trace; fix the story or the slicing, then re-dispatch for the fixed files.

## Handoff

Update STATUS.md: stage 5 -> `approved`, decided by `n/a (no gate)`, note the epic/story counts. Suggest `/commit` (subject `docs({slug}): stage 5 backlog`) and then `/6-gate-check`. Then stop.

## Boundaries

- ✅ Always: vertical slices only; R# references on every story; explicit dependency flags; one file per story.
- ⚠️ Ask first: any story that looks bigger than L (propose the split); reshaping requirements to fit a slice (that is a PRD change and belongs at Gate 1).
- 🚫 Never: create a story without a PRD requirement reference; write the ACs yourself (ac-writer owns them); run `git commit` / `git push` / `gh pr create`.
