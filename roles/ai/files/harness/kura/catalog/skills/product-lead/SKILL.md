---
name: product-lead
description: Pointer to the Product Team pipeline, which ships as the project-installed `product-team` bundle. Use when asked about the product flow, an initiative's status, or which product command comes next, in a repo where the bundle is not installed yet.
model: cursor/composer-2-5
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
---

# Product Team: where the pipeline lives

The product pipeline is not global. It ships as the `product-team` bundle so it loads only in repos that actually run initiatives, since every stage writes to `docs/initiatives/` and reads `docs/strategy/` in the current repo.

This skill is a signpost. It holds no pipeline mechanics: the conventions, the templates, and the stage skills all live inside the `product-team` bundle.

## Availability in this repo

Install the bundle with `kura add product-team --type bundle` in an initialized project. If it is not present, report that the pipeline is unavailable until the project adds the bundle.

When the link exists, two things are required before it loads:

- The workspace must be **trusted**. Accept the trust dialog or run `kura trust --on` in an initialized project.
- Claude must be **relaunched** from the repo root afterwards.

## Then use the stage commands

Kura links bundled skills and agents under their bare names:

| Command | Stage |
|---|---|
| `/product-lead` | Guide and status board |
| `/setup-strategy` | One-time `docs/strategy/` scaffolding, including the config |
| `/0-refine-idea` | Opportunity brief, **Gate 0** |
| `/1-research` | Competitive, user evidence, sizing |
| `/2-write-prd` | PRD: SHALL requirements with WHEN/THEN scenarios |
| `/3-red-team` | Adversarial PRD review, then **Gate 1** |
| `/4-tech-shape` | UX spec, design doc and ADRs |
| `/5-decompose` | The task list, and stories in the full profile |
| `/6-verify` | Definition of Ready report |
| `/7-push-to-board` | Push the backlog to the tracker |
| `/8-living-spec` | At ship time: capability specs and the retrospective |

Two gates, not four, and they are answered in the session unless the repo's `docs/strategy/product-team.yml` sets `gate_medium: pr`.

Start with `/product-lead`: it derives each initiative's state from the artifacts on disk and names the exact next command.

If the user wants the pipeline and the bundle is not installed, say to run `kura add product-team --type bundle`. Do not reconstruct a stage from memory: the stage skills own their own contracts, and paraphrasing them produces artifacts the later gates reject.
