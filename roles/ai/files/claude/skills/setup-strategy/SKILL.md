---
name: setup-strategy
description: One-time Product Team foundation - interviews you for vision, bets, non-bets, and OKRs (optionally seeded by an /idea-refine ideation session when you arrive with a raw idea), then scaffolds docs/strategy/, docs/LEARNINGS.md, CODEOWNERS, and the CLAUDE.md config in the current repo.
argument-hint: "[guidance or revision notes]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
  - Skill
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(git switch *)
  - Bash(gh repo view *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Set up product strategy

Interview the human for the product strategy, write `docs/strategy/strategy.md` + `docs/strategy/okrs.md`, and scaffold the repo for the Product Team pipeline. The strategy is the yardstick every Gate 0 brief gets measured against; vagueness written here becomes bad kill decisions later.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory) and follow its interview style and gate protocol.

## Preflight

1. Must run inside a git repo. With an `origin` remote, resolve `github_repo` via `gh repo view --json nameWithOwner`; without one, continue in **local mode** per conventions.md and record `github_repo | UNSET (local mode)` in the CLAUDE.md config.
2. `docs/strategy/strategy.md` already exists -> this is a **revision**: if a strategy PR is open, follow the revision flow in conventions.md; otherwise interview only about what the user wants changed (ARGUMENTS may say).
3. Switch to branch `chore/product-strategy` (`git switch -c` if new). Dirty tree with unrelated changes -> stop and ask.

## Ideation front-end (idea-driven setups only)

Never in the revision flow. If ARGUMENTS reads as a product idea, or the human confirms a specific idea is driving this setup (ask once when unsure), run ideation before the interview:

1. Invoke the `idea-refine` skill via the Skill tool with the idea as args and run its full dialogue; its one-pager lands in `docs/ideas/{idea-name}.md` per that skill's own save step.
2. Once the one-pager is confirmed, resume HERE (idea-refine does not hand control back on its own). Extract interview seeds from it, confirming each with the human rather than asserting:
   - problem statement + recommended direction -> vision draft (the feature-list pushback below applies to this generalization too);
   - the idea itself -> bet #1 candidate;
   - "Not Doing" list -> non-bets seeds;
   - target user -> segment seed.
3. Seeds pre-fill answers to confirm, never to skip: every interview topic below still runs in full, and OKRs are never seeded - every number and baseline comes from the human.

## Interview

One question at a time, each with a recommended answer, drilling into vagueness. A seeded answer from the ideation front-end is presented for confirmation instead of asked cold. Cover, in order, resolving each before the next:

1. **Vision**: the one-paragraph world this product creates. Push back on feature lists.
2. **Bets**: 3 to 5. For each: the wager, why the team believes it, which OKR it will serve.
3. **Non-bets**: at least 2 attractive things the team is explicitly not doing, and why. These do the killing at Gate 0; refuse to accept an empty set.
4. **Target users**: precise segments. Never assume a market or segment; every one comes from the human.
5. **OKRs**: quarterly objectives with numeric key results. Every target AND baseline comes from the human; never invent, never extrapolate. Missing baseline -> written as `UNKNOWN` with an owner to measure it.
6. **Config**: gate owners (GitHub handles for gates 0/1/3, gate 2, strategy; default all to the repo owner if solo), Project number (may stay UNSET until stage 7), extra codebase paths for stage 4 (default none).

## Write & scaffold

Templates live in `../product-lead/references/templates/` (sibling of this skill's base directory):

1. `docs/strategy/strategy.md` from `strategy.md`, `docs/strategy/okrs.md` from `okrs.md`.
2. `docs/LEARNINGS.md` if absent: a title line plus "Appended by /7-push-to-board after each initiative."
3. `.github/CODEOWNERS` if absent (or missing these lines):
   ```
   /docs/strategy/     {strategy owner}
   /docs/initiatives/  {PM gate owner}
   ```
4. Append `claude-md-section.md` (placeholders filled from the interview) to the repo's CLAUDE.md; create the file if absent. If the section already exists, update values in place.

## Gate handoff

Follow the gate protocol in conventions.md with: commit subject `docs(strategy): product strategy, okrs, and pipeline scaffold`, PR body asking the team to challenge the bets and non-bets specifically. Then stop: the human runs `/commit`, `/pr`, and merges after team review.

## Boundaries

- ✅ Always: one question at a time; recommend an answer with each; confirm every ideation-extracted seed with the human before writing it; record every config value in the CLAUDE.md section.
- ⚠️ Ask first: rewriting an existing strategy section the user did not mention; adding a bet the human did not state.
- 🚫 Never: invent OKR numbers, baselines, markets, or segments; run `git commit` / `git push` / `gh pr create`; proceed past a vague answer without one follow-up.
