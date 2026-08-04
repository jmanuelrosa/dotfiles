---
name: 4-tech-shape
description: Product Team stage 4 - has ux-shaper spec the user-facing behaviour (flows, surfaces, every state) into a UX spec, shapes the approved PRD into a design doc (alternatives, risks, rollout, security) grounded in read-only exploration of this codebase, then has product-team:adr-scribe extract the decisions into numbered ADRs. Opens Gate 2.
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

# Stage 4: tech shaping

Turn the approved PRD into `04-ux-spec.md` and `04-design-doc.md`, plus immutable ADRs under `docs/adr/`. Design, don't implement: the artifacts are what Gate 2 approves, the tech lead on the design doc and the design gate owner on the UX spec.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask). Precondition: Gate 1 `approved` in STATUS.md (reconcile per conventions.md). A Gate 2 PR already open -> revision mode per conventions.md.
2. Enter the Gate 2 branch per conventions.md Branching (this is Gate 2's first stage: `docs/{slug}-gate-2-design`, cut fresh from the updated default branch); mark stage 4 `in-progress`.
3. Read `02-prd.md` fully.

## Explore (read-only)

Feasibility comes from code actually read, never assumption. Explore this repo (and any `extra_codebase_paths` from the CLAUDE.md Product Team config): stack and lockfiles, contract idiom (OpenAPI/GraphQL/types), data layer and migrations, the modules in the feature's blast radius. Cite `path:line` for every design claim. Stack choices not visible in the codebase are asked, not assumed.

## Shape the UX

Spawn the **ux-shaper** agent before writing the design doc: input `docs/initiatives/{slug}/02-prd.md`, output `docs/initiatives/{slug}/04-ux-spec.md` from template `ux-spec.md`. It always runs, including for an initiative with no UI: the absence is argued per R# in the spec's `## No user-facing surface` section, which is what stage 6 checks instead of a bare N/A.

It runs first because states drive the data contract: a paginated empty state changes the API sketch below, an optimistic interaction changes the mutation contract.

`ux-shaper` is a registry agent, not bundled in this plugin. If it is not available, stop and tell the human to run `claude-kit add ux-shaper --type agent --global`, then re-run this stage. Never skip it silently and never write the UX spec yourself.

## Write

Fill `../product-lead/references/templates/design-doc.md` -> `04-design-doc.md`. Load-bearing rules:

- At least one rejected alternative per major decision, with why-rejected.
- Security & privacy argued, not waved off; rollout AND rollback concrete; estimations as ranges with what drives the spread.
- Scope comes from the PRD's R# set; anything beyond it goes to technical non-goals.
- Read `04-ux-spec.md` alongside the PRD. The Data & API sketch must support the states it specifies: pagination for a partial state, an error shape the error state can render, whatever an optimistic interaction needs. A sketch that contradicts a specified state is the failure running ux-shaper first exists to prevent.

## Extract ADRs

Spawn the **product-team:adr-scribe** agent: input `docs/initiatives/{slug}/04-design-doc.md`, output one `docs/adr/NNNN-{decision-slug}.md` per significant decision (template `adr.md`), numbered sequentially after any existing ADRs repo-wide so numbers stay globally unique, plus the design doc's ADR index filled. Existing ADRs are never edited; a changed decision gets a new ADR that supersedes the old one.

## Gate handoff

Follow the gate protocol in conventions.md with n=2, stage name `tech shaping`: STATUS.md stage 4 -> `gate-open`, commit subject `docs({slug}): gate 2 ux spec, design doc and adrs`, PR body pointing the tech lead at the alternatives, risks, and ADRs. Then stop; the human runs `/commit` and `/pr`.

Two of the PR body's reviewer checklist items cover the UX spec: every surface has all states specified or struck with a reason, and every component the spec names exists at its cited path.

The design gate owner in `.github/CODEOWNERS` is a required approver on `04-ux-spec.md` and may revise it in place on the PR rather than only commenting: it is their document. Gate 2 still records one decider in STATUS.md, because GitHub enforces that approval and the gate protocol needs no second cell. A repo with no design gate owner line behaves exactly as it did before.

## Boundaries

- ✅ Always: ground claims in code read (cite paths); at least one rejected alternative per major decision; include security/privacy and rollout/rollback; spawn ux-shaper before writing the design doc.
- ⚠️ Ask first: stack choices not visible in the codebase; reading anything outside this repo beyond the configured `extra_codebase_paths`.
- 🚫 Never: edit an existing ADR (supersede instead); modify application source, tests, or config; write `04-ux-spec.md` yourself or skip ux-shaper when it is missing (ux-shaper owns it); run `git commit` / `git push` / `gh pr create`.
