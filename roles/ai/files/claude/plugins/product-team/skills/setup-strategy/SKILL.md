---
name: setup-strategy
description: One-time Product Team foundation - interviews you for vision, bets, non-bets, and OKRs (optionally seeded by an /idea-refine ideation session when you arrive with a raw idea), then scaffolds docs/strategy/ including product-team.yml, docs/LEARNINGS.md, CODEOWNERS, and a three-line CLAUDE.md pointer.
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

First read `../product-lead/references/conventions.md` and `../product-lead/references/gates.md` (siblings of this skill's base directory); the second carries the gate protocol the handoff follows.

## Preflight

1. Must run inside a git repo. With an `origin` remote, resolve `github_repo` via `gh repo view --json nameWithOwner`; without one, write `github_repo: UNSET`, which is what makes stage 7 refuse later.
2. `docs/strategy/strategy.md` already exists -> this is a **revision**: if a strategy PR is open, follow the revision flow in gates.md; otherwise interview only about what the user wants changed (ARGUMENTS may say).
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

One question at a time, each with a recommended answer, drilling into vagueness: a number with no source, a segment with no size, an "everyone" audience all get a follow-up, not a nod. Facts findable in the repo or on disk are looked up, never asked; decisions are the human's, never filled in. A seeded answer from the ideation front-end is presented for confirmation instead of asked cold. Cover, in order, resolving each before the next:

1. **Vision**: the one-paragraph world this product creates. Push back on feature lists.
2. **Bets**: 3 to 5. For each: the wager, why the team believes it, which OKR it will serve.
3. **Non-bets**: at least 2 attractive things the team is explicitly not doing, and why. These do the killing at Gate 0; refuse to accept an empty set.
4. **Target users**: precise segments. Never assume a market or segment; every one comes from the human.
5. **OKRs**: quarterly objectives with numeric key results. Every target AND baseline comes from the human; never invent, never extrapolate. Missing baseline -> written as `UNKNOWN` with an owner to measure it.
6. **Config**, which is `docs/strategy/product-team.yml` and is the one place these live:
   - **profile**: `full` or `solo`. Recommend `solo` when the answer to "will anyone other than you read the backlog" is no: it drops stories, the DoR report, the board export and all PR machinery, roughly half the cost and nearly all of the latency, and gives up no stage that produces a finding. Recommend `full` when there is a board and a team.
   - **gate_medium**: `session` or `pr`. Recommend `session` unless real reviewers will read a PR; a session gate takes seconds and a PR gate takes a day.
   - **gate_owners**: handles for Gate 0, Gate 1 and strategy. Default all to the repo owner if solo. Ask for those three and no others: two gates is the whole set.
   - **roster**: which researchers run, whether the UX spec comes from `ux-shaper` or inline, whether the red team is the agent or inline. Recommend the full roster, and name the one case worth dropping: a tool with no market has nothing for `market-sizer` to find.
   - **project_number** (may stay UNSET until stage 7) and **extra_codebase_paths** for stage 4 (default none).

## Write & scaffold

Templates live in `../product-lead/references/templates/` (sibling of this skill's base directory):

1. `docs/strategy/strategy.md` from `strategy.md`, `docs/strategy/okrs.md` from `okrs.md`.
2. `docs/strategy/product-team.yml` from `config.yml`, every value filled from the interview.
3. `docs/LEARNINGS.md` if absent: a title line plus "Appended by /product-team:8-living-spec as each initiative ships."
4. `.github/CODEOWNERS` if absent (or missing these lines):
   ```
   /docs/strategy/     {strategy owner}
   /docs/initiatives/  {PM gate owner}
   /docs/initiatives/*/04-ux-spec.md  {design gate owner}
   /docs/adr/          {tech lead}
   ```
   Keep that order: CODEOWNERS applies the **last** matching pattern, so a specific line must follow the general one or the PM owns the UX spec too. The single `*` matches exactly the slug level, which is what the initiative layout needs. Omit the UX line entirely when there is no design gate owner.

   The `docs/adr/` line is load-bearing rather than tidiness: with no design gate it is the only review an ADR gets, and ADRs are the one artifact class this pipeline treats as immutable and hard to reverse. Ask for a tech lead handle even in a solo repo, where it is the repo owner: the line then costs nothing and starts working the day someone else joins.
5. Append `claude-md-section.md` to the repo's CLAUDE.md; create the file if absent. It is three lines and holds no configuration, because CLAUDE.md is loaded on every turn of every session in the repo and the config belongs in a file the stages open when they run. If an older, longer Product Team section is already there, replace it wholesale rather than updating values in it.

## Handoff

Follow the gate protocol in gates.md for the chosen `gate_medium`, with commit subject `docs(strategy): product strategy, okrs, and pipeline scaffold`. Under `pr`, the body asks the team to challenge the bets and non-bets specifically. Under `session`, ask the strategy owner directly and record their answer. Then stop: the human runs `/commit`.

## Boundaries

- ✅ Always: one question at a time; recommend an answer with each; confirm every ideation-extracted seed with the human before writing it; record every config value in `docs/strategy/product-team.yml`; write the `docs/adr/` CODEOWNERS line.
- ⚠️ Ask first: rewriting an existing strategy section the user did not mention; adding a bet the human did not state.
- 🚫 Never: invent OKR numbers, baselines, markets, or segments; put configuration in CLAUDE.md; run `git commit` / `git push` / `gh pr create`; proceed past a vague answer without one follow-up.
