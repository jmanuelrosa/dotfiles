---
name: product-lead
description: Product Team guide and status board - explains the two-gate product pipeline, runs pt.py status over every initiative in the current repo, and tells you the exact next command to run.
argument-hint: "[initiative slug]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(python3 *product-lead/scripts/pt.py *)
  - Bash(git status *)
  - Bash(git branch *)
  - Bash(gh pr list *)
  - Bash(gh pr view *)
---

# Product Team

A spec-driven pipeline that takes a raw product idea to an engineering-ready backlog, and then to a living record of what the system actually does. Every artifact is markdown committed to the repo you run the skills in, and documents are the inter-agent contracts: each stage reads the prior stage's artifact from disk and writes its own.

Two things decide how a stage behaves, and both are read rather than assumed. `docs/strategy/product-team.yml` holds the profile, the gate medium and the roster. Stage order is derived from the artifacts on disk by `scripts/pt.py`, so nothing maintains a state table and nothing can disagree with reality about what has happened.

Shared mechanics live in [references/conventions.md](references/conventions.md); authoritative artifact formats live in [references/templates/](references/templates/).

## Pipeline map

| Order | Skill | Reads | Produces | Gate |
|---|---|---|---|---|
| once | `/product-team:setup-strategy` | interview (optionally seeded by `/idea-refine`) | `docs/strategy/` incl. `product-team.yml`, CODEOWNERS, repo scaffold | strategy |
| 0 | `/product-team:0-refine-idea "<idea>"` | interview + strategy | `00-brief.md`, `STATUS.md` | **Gate 0: kill or proceed** |
| 1 | `/product-team:1-research` | brief | `01-research/` (the roster's researchers, in parallel) | none |
| 2 | `/product-team:2-write-prd` | brief + research | `02-prd.md`: SHALL requirements, each with `R{n}.S{k}` scenarios | none |
| 3 | `/product-team:3-red-team` | PRD only (fresh eyes) | `03-red-team-report.md`, PRD revision | **Gate 1: the right requirements?** |
| 4 | `/product-team:4-tech-shape` | PRD + this codebase | `04-ux-spec.md`, `04-design-doc.md`, `docs/adr/` | none (ADRs via CODEOWNERS) |
| 5 | `/product-team:5-decompose` | PRD + UX spec + design | `05-tasks.md`, and `05-backlog/` in the full profile | none |
| 6 | `/product-team:6-verify` | tasks + backlog | `06-dor-report.md` | none (full profile only) |
| 7 | `/product-team:7-push-to-board` | backlog + DoR report | GitHub issues + Project items | dry-run confirm (full only) |
| 8 | `/product-team:8-living-spec` | tasks + PRD | `docs/specs/{capability}/spec.md`, `docs/LEARNINGS.md` | none, run at ship time |

A healthy funnel kills most ideas at Gate 0. Killing early is the pipeline working, not failing.

Two gates, not four. The design gate went because the open design decisions at stage 4 resolve unaided, and the Definition of Ready gate because across three initiatives it produced one repeated lexical defect, which `pt.py check` now catches for nothing. `docs/adr/` under CODEOWNERS is what keeps the hard-to-reverse half of stage 4 reviewed.

Gates are answered **in the session** by default (seconds); `gate_medium: pr` in the config turns them back into branch-and-PR reviews for a repo with real reviewers. Either way the decision, the decider and **the reason** land in the initiative's `STATUS.md`, because a gate that records only "approved" is indistinguishable from one nobody read.

The `solo` profile drops the board-facing half (stories, `6-verify`, `7-push-to-board`, PR machinery) and keeps every stage that produces a finding. Nothing else is skippable, and a skip is a human decision recorded in STATUS.md.

## When invoked

1. **No `docs/strategy/strategy.md` in this repo:** print the pipeline map and tell the user to start with `/product-team:setup-strategy`. Stop.
2. **Otherwise, report status.** Run `python3 .claude/skills/product-team/skills/product-lead/scripts/pt.py status <slug>` for each initiative under `docs/initiatives/` (or just the slug in ARGUMENTS; if the current branch is `docs/{slug}-…`, focus that one). It prints each stage as done, partial, ready or blocked, the gate rows, any shipped requirement not yet merged into `docs/specs/`, and the next command. Relay it; do not re-derive any of it by reading files yourself.
3. **Reconcile a PR-medium gate.** Only when the config says `gate_medium: pr` and a gate row has a PR url but no decision: check it with `gh pr list --head docs/{slug}-gate-{n}-{label} --state all` and `gh pr view <url> --json state,mergedAt`, and report a merged-but-unrecorded gate. The next stage skill records it, or update the row now if the user asks.
4. **Answer questions** about the flow from conventions.md and the templates; never paraphrase a template from memory, read it.

## Boundaries

- ✅ Always: derive stage state through `pt.py status`; read the config for the profile and gate medium before advising.
- ⚠️ Ask first before editing STATUS.md during a status report (recording a gate result is the only legitimate edit here).
- 🚫 Never run a pipeline stage from this skill; tell the user which skill to invoke instead. Never merge PRs. Never write a stage-status row.
