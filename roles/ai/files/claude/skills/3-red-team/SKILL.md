---
name: 3-red-team
description: Product Team stage 3 - spawns a fresh-context pm-red-team agent that attacks the PRD (reads nothing else), then offers a revision against its blockers. No separate gate; feeds the open Gate 1 PR.
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

# Stage 3: red-team the PRD

Adversarial review with a maker/checker split: the reviewer must not inherit the writer's assumptions, so the pm-red-team agent gets a fresh context and reads ONLY the PRD. Output feeds the open Gate 1 PR as a revision, not a separate gate.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask). `02-prd.md` must exist and stage 2 must be `gate-open` or `approved`; otherwise stop.
2. On branch `docs/{slug}`; mark stage 3 `in-progress`.

## Attack

Spawn the **pm-red-team** agent. Its dispatch prompt names exactly one input, `docs/initiatives/{slug}/02-prd.md`, and one output, `docs/initiatives/{slug}/03-red-team-report.md`, and forbids reading the brief, the research, or this conversation. Do not summarize the PRD for it; fresh eyes are the point.

The report must contain at least 5 substantive challenges with severity labels (`blocker | concern | note`), or state explicitly why it cannot. If it comes back thinner, re-dispatch once with the shortfall named; still thin -> record that verbatim in the report and move on.

## Revise

1. Read the report. Present the blockers (and notable concerns) to the human via AskUserQuestion: revise the PRD against them now, or send the report to the gate unanswered.
2. If revising: apply the agreed changes to `02-prd.md` yourself (the red-team never rewrites the PRD), and fill the PRD's Red-team status block (report path, blockers raised/resolved, revision date).
3. Update STATUS.md: stage 3 -> `approved`, decided by `n/a (no gate)`, note how many blockers were raised and resolved.

## Handoff

Both files ride the open Gate 1 PR: suggest `/commit` (subject `docs({slug}): red-team report and prd revision`) then `/pr` (same branch updates the open PR). Remind the gate owner to re-review the diff before merging Gate 1. Then stop.

## Boundaries

- ✅ Always: fresh context for the red-team with the PRD as its only input; severity labels on every challenge; fill the PRD's red-team status block.
- ⚠️ Ask first: which blockers to fold into the revision; dropping any challenge from the report.
- 🚫 Never: let the red-team rewrite the PRD or read beyond it; soften a blocker into a note; run `git commit` / `git push` / `gh pr create`.
