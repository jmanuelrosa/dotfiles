---
name: 0-refine-idea
description: "Product Team stage 0 - turns a raw idea into an opportunity brief: creates the initiative branch and folder, interviews you, runs the product-team:strategy-checker, and opens Gate 0 (kill or proceed)."
argument-hint: "\"<raw idea>\" (or the slug of an existing initiative to revise)"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Skill
  - Agent
  - Bash(python3 *product-lead/scripts/pt.py *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(git fetch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
  - Bash(gh api *)
---

# Stage 0: refine idea into opportunity brief

Turn ARGUMENTS (a raw idea) into `docs/initiatives/{slug}/00-brief.md` and open Gate 0, where the human decides kill or proceed. A healthy funnel kills most briefs here; remind the human that killing at Gate 0 is success, not failure.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory); its interview style, slug rule, gate protocol, and hard rules govern this stage.

## Preflight

1. `docs/strategy/strategy.md` must exist; otherwise stop and point at `/product-team:setup-strategy "<the raw idea>"` - passing the idea along so ideation happens there with the idea in hand.
2. Read `docs/strategy/product-team.yml` for `gate_medium` and `profile` (absent -> `session` and `full`).
3. ARGUMENTS empty -> ask for the raw idea before anything else.
4. Slugify the idea. `docs/initiatives/{slug}/` already exists -> this is a **revision**: follow the revision flow in conventions.md against the recorded Gate 0 reason, or its PR under `gate_medium: pr`.
5. New initiative under `gate_medium: pr`: cut `docs/{slug}-gate-0-brief` fresh from the default branch per conventions.md. Under `session`: stay where you are. Dirty tree with unrelated changes -> stop and ask.
6. Instantiate `docs/initiatives/{slug}/STATUS.md` from `../product-lead/references/templates/status.md`.

## Ideation pre-work (optional)

1. Scan `docs/ideas/*.md` for a one-pager matching the idea (match by title; ask the human if ambiguous). Found -> pre-fill the interview from it and confirm each answer instead of asking cold: problem statement -> question 1; target user -> question 2; its assumptions -> question 3 items labeled `assumption`; why-now if captured -> question 4; MVP scope -> seed for question 5; "Not Doing" list -> input to question 6.
2. No one-pager and the idea is vague (no clear problem + user): offer once to run the `idea-refine` skill via the Skill tool first. If accepted, run its full dialogue, then resume HERE (it does not hand control back on its own) and pre-fill per step 1. Default is to skip and stay lean.

## Interview

One question at a time, recommended answer with each, challenging weak answers. Pre-filled answers from ideation pre-work are confirmed, not re-asked. Resolve in order:

1. **What problem**, stated without naming a feature.
2. **Who has it**: precise segment plus a size guess (labeled evidence or assumption).
3. **What evidence exists**: each item labeled `evidence` (with source) or `assumption`. At least one item is mandatory; an all-assumption brief must say "assumption, untested" explicitly.
4. **Why now**.
5. **Cheapest possible test**, including the result that would kill the idea.
6. **Kill criteria**: concrete conditions agreed in advance.

## Write & check

1. Fill `../product-lead/references/templates/brief.md` -> `docs/initiatives/{slug}/00-brief.md`.
2. Spawn the **product-team:strategy-checker** agent with this prompt contract: read `docs/initiatives/{slug}/00-brief.md`, `docs/strategy/strategy.md`, and `docs/strategy/okrs.md`; return the alignment verdict as final text.
3. Paste the verdict verbatim into the brief's Strategy alignment section. Never soften it; a "none - recommend kill" verdict goes in exactly as written.

## Gate 0

Follow the gate protocol in conventions.md with n=0, stage name `opportunity brief`. Frame the decision as kill vs proceed with the strategy-checker verdict quoted, and say plainly that killing here is the pipeline working.

Under `gate_medium: session`, ask with `AskUserQuestion` (proceed / kill / not yet) and write the answer into the STATUS.md Gate 0 row: status, decided by, date, and **one line on what convinced them or which concern they accepted**. That reason is the only record this gate leaves; without it, `approved` is indistinguishable from nobody having read the brief.

Then suggest `/commit` (subject `docs({slug}): gate 0 opportunity brief`) and stop.

## Boundaries

- ✅ Always: label every evidence item; run the product-team:strategy-checker before asking for the gate decision; record the gate reason, not just the verdict.
- ⚠️ Ask first: proceeding when the only evidence is assumptions (requires the explicit "assumption, untested" acknowledgment); reusing a dirty working tree.
- 🚫 Never: proceed without at least one evidence item or the explicit assumption label; soften or summarize the product-team:strategy-checker verdict; write a stage-status row (`pt.py status` derives it); run `git commit` / `git push` / `gh pr create`.
