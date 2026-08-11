---
name: product-lead
description: Pointer to the Product Team pipeline, which ships as the project-installed `product-team` plugin. Use when asked about the product flow, an initiative's status, or which product command comes next, in a repo where the plugin is not installed yet.
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
---

# Product Team: where the pipeline lives

The product pipeline is not global. It ships as the `product-team` plugin so it loads only in repos that actually run initiatives, since every stage writes to `docs/initiatives/` and reads `docs/strategy/` in the current repo.

This skill is a signpost. It holds no pipeline mechanics: the conventions, the templates, and the stage skills all live inside the plugin.

## Install it in this repo

```
claude-kit add product-team --type plugin
```

That symlinks the plugin into `.claude/skills/product-team/`. Two things are required before it loads, and both are easy to miss:

- The workspace must be **trusted**. Accept the trust dialog, or set `hasTrustDialogAccepted` for this project in `~/.claude.json`.
- Claude must be **relaunched** from the repo root afterwards.

## Then use the namespaced commands

Plugin artifacts are namespaced by plugin name, so every command gains a `product-team:` prefix:

| Command | Stage |
|---|---|
| `/product-team:product-lead` | Guide and status board |
| `/product-team:setup-strategy` | One-time `docs/strategy/` scaffolding, including the config |
| `/product-team:0-refine-idea` | Opportunity brief, **Gate 0** |
| `/product-team:1-research` | Competitive, user evidence, sizing |
| `/product-team:2-write-prd` | PRD: SHALL requirements with WHEN/THEN scenarios |
| `/product-team:3-red-team` | Adversarial PRD review, then **Gate 1** |
| `/product-team:4-tech-shape` | UX spec, design doc and ADRs |
| `/product-team:5-decompose` | The task list, and stories in the full profile |
| `/product-team:6-verify` | Definition of Ready report |
| `/product-team:7-push-to-board` | Push the backlog to the tracker |
| `/product-team:8-living-spec` | At ship time: capability specs and the retrospective |

Two gates, not four, and they are answered in the session unless the repo's `docs/strategy/product-team.yml` sets `gate_medium: pr`.

Start with `/product-team:product-lead`: it derives each initiative's state from the artifacts on disk and names the exact next command.

If the user wants the pipeline and the plugin is not installed, say so and hand them the `claude-kit add` line above. Do not reconstruct a stage from memory: the stage skills own their own contracts, and paraphrasing them produces artifacts the later gates reject.
