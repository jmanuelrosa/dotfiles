---
name: product-lead
description: Pointer to the Product Team pipeline, which ships as the project-installed `product-team` plugin. Use when asked about the gated product flow, an initiative's status, or which product command comes next, in a repo where the plugin is not installed yet.
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
---

# Product Team: where the pipeline lives

The gated product pipeline is not global. It ships as the `product-team` plugin so it loads only in repos that actually run initiatives, since every stage writes to `docs/initiatives/` and reads `docs/strategy/` in the current repo.

This skill is a signpost. It holds no pipeline mechanics: the conventions, the templates, and the stage skills all live inside the plugin.

## Install it in this repo

```
claude-agent add product-team
```

That symlinks the plugin into `.claude/skills/product-team/`. Two things are required before it loads, and both are easy to miss:

- The workspace must be **trusted**. Accept the trust dialog, or set `hasTrustDialogAccepted` for this project in `~/.claude.json`.
- Claude must be **relaunched** from the repo root afterwards.

## Then use the namespaced commands

Plugin artifacts are namespaced by plugin name, so every command gains a `product-team:` prefix:

| Command | Stage |
|---|---|
| `/product-team:product-lead` | Guide and status board (reads `docs/initiatives/*/STATUS.md`) |
| `/product-team:setup-strategy` | One-time `docs/strategy/` scaffolding |
| `/product-team:0-refine-idea` | Opportunity brief, Gate 0 |
| `/product-team:1-research` | Competitive, user evidence, sizing |
| `/product-team:2-write-prd` | PRD, Gate 1 |
| `/product-team:3-red-team` | Adversarial PRD review |
| `/product-team:4-tech-shape` | Design doc and ADRs, Gate 2 |
| `/product-team:5-decompose` | Epics, stories, acceptance criteria |
| `/product-team:6-gate-check` | Definition of Ready, Gate 3 |
| `/product-team:7-push-to-board` | Push the backlog to the tracker |

Start with `/product-team:product-lead`: it reads `STATUS.md` and names the exact next command.

If the user wants the pipeline and the plugin is not installed, say so and hand them the `claude-agent add` line above. Do not reconstruct a stage from memory: the stage skills own their own contracts, and paraphrasing them produces artifacts the later gates reject.
