---
name: 3-red-team
description: "Product Team stage 3 - spawns a fresh-context product-team:pm-red-team agent that attacks the PRD (reads nothing else), folds the blockers back in, then opens Gate 1: are these the right requirements?"
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
  - Bash(git fetch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Stage 3: red-team the PRD, then Gate 1

Adversarial review with a maker/checker split: the reviewer must not inherit the writer's assumptions, so the product-team:pm-red-team agent gets a fresh context and reads ONLY the PRD. This stage then opens Gate 1, because the requirements worth approving are the ones that have survived an attack.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask).
2. Read `docs/strategy/product-team.yml` for `gate_medium` and `roster.red_team`.
3. `pt.py status {slug}`: this stage must read `ready`, which means `02-prd.md` exists.
4. Under `gate_medium: pr`, enter the Gate 1 branch per conventions.md (`docs/{slug}-gate-1-prd`, cut fresh from the default branch since this is Gate 1's first stage).

## Attack

Spawn the **product-team:pm-red-team** agent. Its dispatch prompt names exactly one input, `docs/initiatives/{slug}/02-prd.md`, and one output, `docs/initiatives/{slug}/03-red-team-report.md`, and forbids reading the brief, the research, or this conversation. Do not summarize the PRD for it; fresh eyes are the point.

With `roster.red_team: inline` there is no agent and you do the pass yourself. Say so in the report, and be harder on yourself than feels comfortable: reviewing what you just wrote, in the context you wrote it in, reliably produces agreement.

The report must contain at least 5 substantive challenges with severity labels (`blocker | concern | note`), or state explicitly why it cannot. If it comes back thinner, re-dispatch once with the shortfall named; still thin -> record that verbatim and move on.

Four classes have actually been missed on real initiatives, so the dispatch names them as required angles:

- **Enforcement gaps**: a rule the PRD states that nothing will be positioned to enforce at the moment it matters.
- **Self-knowledge**: whether the metrics can be measured from what is being built, or whether measurement quietly depends on a person remembering.
- **Unstated states**: a failure, empty or offline condition the requirements assume away.
- **The strongest objection to the whole thing**, in its best form, even when the report goes on to reject it.

## Revise

1. Read the report. Present the blockers (and notable concerns) to the human with `AskUserQuestion`: revise the PRD against them now, or carry them into the gate decision unresolved.
2. If revising: apply the agreed changes to `02-prd.md` yourself (the red-team never rewrites the PRD), and fill the PRD's Red-team status block (report path, blockers raised/resolved, revision date).
3. A blocker that adds behaviour becomes a new requirement with its own scenarios, appended rather than renumbered.

## Gate 1

Follow the gate protocol in conventions.md with n=1, stage name `prd`. The decision is whether these are the right requirements, and kill remains a first-class answer. Point the reviewer at the metrics, the non-goals, the scenario coverage, and every blocker that was not resolved.

Under `gate_medium: session`, ask with `AskUserQuestion` and record status, decider, date and the one-line reason in the STATUS.md Gate 1 row. Then suggest `/commit` (subject `docs({slug}): gate 1 prd and red-team report`) and stop.

## Boundaries

- ✅ Always: fresh context for the red-team with the PRD as its only input; severity labels on every challenge; the four required angles in the dispatch; fill the PRD's red-team status block; record the gate reason.
- ⚠️ Ask first: which blockers to fold into the revision; dropping any challenge from the report.
- 🚫 Never: let the red-team rewrite the PRD or read beyond it; soften a blocker into a note; ask for the gate decision before the report exists; write a stage-status row; run `git commit` / `git push` / `gh pr create`.
