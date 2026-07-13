---
name: 2-write-prd
description: Product Team stage 2 - writes the PRD from the approved brief and research summary (never from chat history), with testable R# requirements, mandatory non-goals, and no invented baselines. Opens Gate 1.
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
  - Bash(gh api *)
---

# Stage 2: write the PRD

Produce `docs/initiatives/{slug}/02-prd.md` grounded in the on-disk brief and research, not in conversation memory. The PRD is what Gate 1 approves and what every later stage traces back to.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask). Precondition: STATUS.md stage 1 `approved` (stage 0 approved is implied; reconcile per conventions.md). A Gate 1 PR already open -> **revision mode**: follow the revision flow in conventions.md against its comments.
2. On branch `docs/{slug}`; mark stage 2 `in-progress`.
3. Read `00-brief.md` and `01-research/summary.md` fully; open the detail research files where the summary's confidence or gaps warrant it.

## Write

Fill `../product-lead/references/templates/prd.md` -> `02-prd.md`, honoring every guidance comment. The load-bearing rules:

- **Metrics**: every one has definition, baseline, target. A baseline nobody measured is written exactly as `UNKNOWN -> Open Question #n` with an owner. Inventing a baseline is the cardinal sin of this pipeline.
- **Non-goals**: minimum 3, mandatory.
- **Requirements**: numbered `R1..Rn`, each testable as written, zero implementation detail (that is stage 4's job).
- **Target users**: only segments evidenced in `01-research/`. A segment the human wants anyway needs their explicit sign-off, recorded in the section.
- **Open questions**: numbered, each with an owner; evidence gaps from the research summary land here.

## Gate handoff

Follow the gate protocol in conventions.md with n=1, stage name `prd`: STATUS.md stage 2 -> `gate-open`, commit subject `docs({slug}): gate 1 prd`, PR body pointing reviewers at metrics, non-goals, and R# testability, and noting that `/3-red-team` should run against this PR before it merges. Then stop; the human runs `/commit` and `/pr`.

## Boundaries

- ✅ Always: include non-goals and full metric definitions; ground every section in the on-disk brief and research; number requirements and open questions.
- ⚠️ Ask first: any target segment not evidenced in research; dropping a brief kill-criterion from the PRD.
- 🚫 Never: invent metric baselines; include implementation detail; write the PRD from chat history instead of the artifacts; run `git commit` / `git push` / `gh pr create`.
