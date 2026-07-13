---
name: product-lead
description: Product Team guide and status board - explains the gated product pipeline, reads docs/initiatives/*/STATUS.md in the current repo, and tells you the exact next command to run.
argument-hint: "[initiative slug]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Product Team

A gated, spec-driven pipeline that takes a raw product idea to an engineering-ready backlog on a GitHub Project board. Every artifact is markdown committed to the repo you run the skills in. Every stage gate is a human decision, implemented as a PR review. Documents are the inter-agent contracts: each stage reads the prior stage's artifact from disk and writes its own. `docs/initiatives/{slug}/STATUS.md` is the state machine; the filesystem is the orchestrator. Humans advance stages by invoking the next skill; nothing runs unattended, no agent ever merges a PR.

Shared mechanics live in [references/conventions.md](references/conventions.md); authoritative artifact formats live in [references/templates/](references/templates/).

## Pipeline map

| Order | Skill | Reads | Produces | Gate |
|---|---|---|---|---|
| once | `/setup-strategy` | interview (optionally seeded by `/idea-refine`) | `docs/strategy/strategy.md`, `docs/strategy/okrs.md`, repo scaffold | strategy PR |
| 0 | `/0-refine-idea "<idea>"` | interview + strategy | `00-brief.md`, STATUS.md, branch | Gate 0: kill or proceed |
| 1 | `/1-research` | brief | `01-research/` (3 parallel researchers + summary) | none (feeds Gate 1) |
| 2 | `/2-write-prd` | brief + research | `02-prd.md` | Gate 1: PM + team |
| 3 | `/3-red-team` | PRD only (fresh eyes) | `03-red-team-report.md`, PRD revision | none (feeds Gate 1) |
| 4 | `/4-tech-shape` | PRD + this codebase | `04-design-doc.md`, `docs/adr/` | Gate 2: tech lead |
| 5 | `/5-decompose` | PRD + design doc | `05-backlog/` epics + stories + ACs | none (feeds Gate 3) |
| 6 | `/6-gate-check` | backlog | `06-dor-report.md` (PASS/FAIL per story) | Gate 3: final |
| 7 | `/7-push-to-board` | backlog + DoR report | GitHub issues + Project items, docs/LEARNINGS.md entry | dry-run confirm |

A healthy funnel kills most ideas at Gate 0. Killing early is the pipeline working, not failing.

Two documented variations live in conventions.md: **local mode** (no `origin` remote: gates become explicit recorded human decisions instead of PR reviews, stage 7 unavailable) and the **expedited path** (small, low-risk features may skip stages 1 and 3 by explicit human decision; gates are never skipped).

## When invoked

1. **No `docs/strategy/strategy.md` in this repo:** print the pipeline map and tell the user to start with `/setup-strategy`. Stop.
2. **Otherwise, report status.** Read every `docs/initiatives/*/STATUS.md` (or just the slug given in ARGUMENTS; if the current branch is `docs/{slug}`, focus that one). For each initiative print: name, current stage, status, and the exact next command.
3. **Reconcile stale gates.** For any stage row marked `gate-open`, check the PR with `gh pr list --head docs/{slug} --state all` and `gh pr view <url> --json state,mergedAt`. Report merged-but-unrecorded gates; the next stage skill records them, or update STATUS.md now if the user asks. In local mode (no `origin` remote) skip the `gh` checks entirely; STATUS.md is the only record.
4. **Answer questions** about the flow from conventions.md and the templates; never paraphrase a template from memory, read it.

## Boundaries

- ✅ Always read STATUS.md fresh from disk; it outranks anything remembered from the conversation.
- ⚠️ Ask first before editing STATUS.md during a status report (recording a gate result is the only legitimate edit here).
- 🚫 Never run a pipeline stage from this skill; tell the user which skill to invoke instead. Never merge PRs.
