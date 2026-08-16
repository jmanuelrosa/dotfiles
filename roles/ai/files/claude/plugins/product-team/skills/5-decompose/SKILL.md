---
name: 5-decompose
description: "Product Team stage 5 - turns the design into 05-tasks.md (the whole build, dependency-ordered from empty repo to accepted) and, in the full profile, thin story headers claiming PRD scenario ids. No gate."
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
  - Bash(python3 *product-lead/scripts/pt.py *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Stage 5: decompose into tasks, and stories for the board

Write `05-tasks.md` always, and `05-backlog/` only in the `full` profile. No gate; `/product-team:6-verify` checks the result.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask).
2. Read `docs/strategy/product-team.yml` for `profile`.
3. `pt.py status {slug}`: this stage must read `ready` or `partial`.
4. Read `02-prd.md`, `04-ux-spec.md` and `04-design-doc.md` fully.

## Tasks

Fill `../product-lead/references/templates/tasks.md` -> `05-tasks.md`. This layer exists because stories must trace to requirements and no requirement asks for a toolchain, so the build spine could never become stories.

- **Dependency order**, so following the list top to bottom works.
- **One line per task**, one session's work, verifiable: you can tell when it is done.
- **Each task names what it serves**: a scenario id (`R3.S1`) for behaviour, a design decision (`D5`) for a technical choice, or `(infrastructure)` for the spine. A task that can name none of the three is scope nobody asked for.
- **From nothing to accepted.** A group for getting it built, a group for getting it deployed, a group for accepting it where it actually runs. A project that already exists says so on one line rather than deleting the group.
- **Close the deferrals aimed here.** Read the `## Deferrals` tables of `02-prd.md`, `04-ux-spec.md` and `04-design-doc.md`; every deferral naming `05-tasks.md` as its resolver is closed by a task line citing its id (`- [ ] 2.3 Choose the encoder (D1)`). `pt.py check` fails the initiative on one left unclosed.
- `- [ ]` is load-bearing: `pt.py spec-merge` reads the checkboxes to decide which requirements have shipped.

Every scenario in the PRD is claimed by some task or some story. `pt.py check` reports any that is not, and a scenario nobody claims is a requirement nobody implements.

## Stories (full profile only)

In the `solo` profile, skip this section entirely: `05-tasks.md` already carries the work and a story exists to be put on a board.

Stories are **tracer bullets**: each cuts a narrow but COMPLETE path through every layer and is demoable or verifiable on its own. Never slice layer-by-layer ("backend for X" + "frontend for X" is one story, not two).

Fill `../product-lead/references/templates/story.md` per story, one file each, and keep them thin: the story claims scenario ids rather than restating them, because the scenario already exists in `02-prd.md` and two copies drift. The whole file is a header, and the template's own comments are the authority on each field; do not re-derive them from memory. Epics group stories by PRD goal; `epic-{n}.md` carries the goal, its scenario coverage, and the ordered story list.

Three field rules are stage behaviour rather than format: a story claiming no scenario does not get written; the Design / UX anchor must be verified to resolve (and points at the spec's `## No user-facing surface` argument when there are no flows); and **Needs design seat** is copied from whether the flow draws on the spec's `## New system pieces needed` section, never re-derived, because seat routing is the architect's job.

A story is a flow and `04-ux-spec.md` is organised by flow, so prefer one story per flow.

## Acceptance criteria

Spawn **product-team:ac-writer** with `02-prd.md` and every `05-backlog/story-*.md`. Its job is now to **claim and complete**, not to invent: it fills each story's Scenarios row from the PRD and reports any slice needing a criterion no scenario covers. That report is a PRD gap, and the fix is a scenario added by `/product-team:2-write-prd`, never one invented in a story.

Skip the dispatch in the `solo` profile; there are no stories to fill.

## Handoff

Suggest `/commit` (subject `docs({slug}): stage 5 tasks and backlog`) and then `/product-team:6-verify` in the full profile, or `pt.py check {slug} --strict` in solo, where that run is the Definition of Ready. Then stop.

## Boundaries

- ✅ Always: a dependency-ordered task list covering build, deploy and acceptance; every task naming a scenario, a decision or infrastructure; vertical story slices; a resolvable UX anchor and a set design-seat flag on every story; a split rationale on every `L`.
- ⚠️ Ask first: any story that looks bigger than L (propose the split); reshaping requirements to fit a slice (that is a PRD change and belongs at Gate 1).
- 🚫 Never: write a story that claims no scenario; write acceptance criteria yourself where a PRD scenario would serve (ac-writer claims them, 2-write-prd authors them); write a freehand "N/A" in a Design/UX note; assign an owning seat to a story (the architect routes seats); write a stage-status row; run `git commit` / `git push` / `gh pr create`.
