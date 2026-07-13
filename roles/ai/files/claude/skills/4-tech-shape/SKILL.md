---
name: 4-tech-shape
description: Product Team stage 4 - shapes the approved PRD into a design doc (alternatives, risks, rollout, security) grounded in read-only exploration of this codebase, then has adr-scribe extract the decisions into numbered ADRs. Opens Gate 2.
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

# Stage 4: tech shaping

Turn the approved PRD into `04-design-doc.md` plus immutable ADRs under `docs/adr/`. Design, don't implement: the artifacts are what Gate 2 (tech lead) approves.

First read `../product-lead/references/conventions.md` (sibling of this skill's base directory).

## Preflight

1. Resolve the initiative (ARGUMENTS, branch, or ask). Precondition: Gate 1 `approved` in STATUS.md (reconcile per conventions.md). A Gate 2 PR already open -> revision mode per conventions.md.
2. On branch `docs/{slug}`; mark stage 4 `in-progress`.
3. Read `02-prd.md` fully.

## Explore (read-only)

Feasibility comes from code actually read, never assumption. Explore this repo (and any `extra_codebase_paths` from the CLAUDE.md Product Team config): stack and lockfiles, contract idiom (OpenAPI/GraphQL/types), data layer and migrations, the modules in the feature's blast radius. Cite `path:line` for every design claim. Stack choices not visible in the codebase are asked, not assumed.

## Write

Fill `../product-lead/references/templates/design-doc.md` -> `04-design-doc.md`. Load-bearing rules:

- At least one rejected alternative per major decision, with why-rejected.
- Security & privacy argued, not waved off; rollout AND rollback concrete; estimations as ranges with what drives the spread.
- Scope comes from the PRD's R# set; anything beyond it goes to technical non-goals.

## Extract ADRs

Spawn the **adr-scribe** agent: input `docs/initiatives/{slug}/04-design-doc.md`, output one `docs/adr/NNNN-{decision-slug}.md` per significant decision (template `adr.md`), numbered sequentially after any existing ADRs repo-wide so numbers stay globally unique, plus the design doc's ADR index filled. Existing ADRs are never edited; a changed decision gets a new ADR that supersedes the old one.

## Gate handoff

Follow the gate protocol in conventions.md with n=2, stage name `tech shaping`: STATUS.md stage 4 -> `gate-open`, commit subject `docs({slug}): gate 2 design doc and adrs`, PR body pointing the tech lead at the alternatives, risks, and ADRs. Then stop; the human runs `/commit` and `/pr`.

## Boundaries

- ✅ Always: ground claims in code read (cite paths); at least one rejected alternative per major decision; include security/privacy and rollout/rollback.
- ⚠️ Ask first: stack choices not visible in the codebase; reading anything outside this repo beyond the configured `extra_codebase_paths`.
- 🚫 Never: edit an existing ADR (supersede instead); modify application source, tests, or config; run `git commit` / `git push` / `gh pr create`.
