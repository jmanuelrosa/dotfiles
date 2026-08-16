---
name: 4-tech-shape
description: Product Team stage 4 - has ux-shaper spec the user-facing behaviour (flows, surfaces, every state) into a UX spec, shapes the approved PRD into a design doc (alternatives, risks, rollout, security) grounded in read-only exploration of this codebase, then has product-team:adr-scribe extract the decisions into numbered ADRs. No gate; the ADRs it writes are reviewed through CODEOWNERS.
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

# Stage 4: tech shaping

Turn the approved PRD into `04-ux-spec.md` and `04-design-doc.md`, plus immutable ADRs under `docs/adr/`. Design, don't implement.

There is no gate here (conventions.md carries why); what the old gate was actually buying, review of the immutable ADRs, now rides the `docs/adr/` CODEOWNERS line on the commit the human makes anyway.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask).
2. Read `docs/strategy/product-team.yml` for `roster.ux_spec` and `extra_codebase_paths`.
3. `pt.py status {slug}`: this stage must read `ready` or `partial`. Gate 1 must read `approved` in STATUS.md, or stop and say what unblocks it.
4. Read `02-prd.md` fully.

## Explore (read-only)

Feasibility comes from code actually read, never assumption. Explore this repo (and any `extra_codebase_paths` from `docs/strategy/product-team.yml`): stack and lockfiles, contract idiom (OpenAPI/GraphQL/types), data layer and migrations, the modules in the feature's blast radius. Cite `path:line` for every design claim. Stack choices not visible in the codebase are asked, not assumed.

## Shape the UX

Spawn the **ux-shaper** agent before writing the design doc: input `docs/initiatives/{slug}/02-prd.md`, output `docs/initiatives/{slug}/04-ux-spec.md` from template `ux-spec.md`. It always runs, including for an initiative with no UI: the absence is argued per R# in the spec's `## No user-facing surface` section, which is what the stories point at instead of a bare N/A.

It runs first because states drive the data contract: a paginated empty state changes the API sketch below, an optimistic interaction changes the mutation contract.

`ux-shaper` is a registry agent, not bundled in this plugin. If it is not available, stop and tell the human to run `claude-kit add ux-shaper --type agent --global`, then re-run this stage. With `roster.ux_spec: inline` you write the spec yourself against the template and say so in it; there is no setting that skips the artifact, because "no UI" asserted in passing is how a surface with three unhandled states reaches implementation.

## Write

Fill `../product-lead/references/templates/design-doc.md` -> `04-design-doc.md`. Load-bearing rules:

- At least one rejected alternative per major decision, with why-rejected.
- Security & privacy argued, not waved off; rollout AND rollback concrete; estimations as ranges with what drives the spread.
- Scope comes from the PRD's R# set; anything beyond it goes to technical non-goals.
- Read `04-ux-spec.md` alongside the PRD. The Data & API sketch must support the states it specifies: pagination for a partial state, an error shape the error state can render, whatever an optimistic interaction needs. A sketch that contradicts a specified state is the failure running ux-shaper first exists to prevent.
- **Close every deferral** aimed at this document by `02-prd.md` and `04-ux-spec.md`, in the `## Deferrals settled here` table: name the id and decide it, or restate it as an owned open question. `pt.py check` fails the initiative on one that is never mentioned.
- **State the two decisions this stage reliably leaves implicit**, in `## Enforcement and access`. Where validity is enforced relative to deploy (which command runs the check, and whether a failure blocks publishing or merely reports), and who can read the deployed thing (the posture, and the alternative rejected). Both were missed on a real initiative: a validation that only ever ran on a developer's machine read as though it protected production, and a publicly readable deployment was never surfaced as a decision at all.

## Extract ADRs

Spawn the **product-team:adr-scribe** agent: input `docs/initiatives/{slug}/04-design-doc.md`, output one `docs/adr/NNNN-{decision-slug}.md` per significant decision (template `adr.md`), numbered sequentially after any existing ADRs repo-wide so numbers stay globally unique, plus the design doc's ADR index filled. Existing ADRs are never edited; a changed decision gets a new ADR that supersedes the old one.

## Handoff

Print the files written, then suggest `/commit` (subject `docs({slug}): stage 4 ux spec, design doc and adrs`) and `/product-team:5-decompose`. Then stop.

Say plainly in the handoff that the ADRs are now under CODEOWNERS review, and name two things worth a reader's eye before the commit lands: every surface in the UX spec has all its states specified or struck with a reason, and every component the spec names exists at its cited path.

Where a design gate owner is listed in `.github/CODEOWNERS` for `04-ux-spec.md`, that approval is GitHub's to enforce on the commit; it is their document and they revise it in place rather than only commenting. A repo with no such line simply has none.

## Boundaries

- ✅ Always: ground claims in code read (cite paths); at least one rejected alternative per major decision; include security/privacy and rollout/rollback; spawn ux-shaper before writing the design doc.
- ⚠️ Ask first: stack choices not visible in the codebase; reading anything outside this repo beyond the configured `extra_codebase_paths`.
- 🚫 Never: edit an existing ADR (supersede instead); modify application source, tests, or config; skip the UX spec artifact under any setting; write `04-ux-spec.md` yourself while `roster.ux_spec` names an agent that is merely missing (install it); leave a deferral aimed here unmentioned; write a stage-status row; run `git commit` / `git push` / `gh pr create`.
