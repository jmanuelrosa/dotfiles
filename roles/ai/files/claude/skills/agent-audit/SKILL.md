---
name: agent-audit
description: Audit Claude Code agent definitions for craft quality: delegation triggers, tool and model fit, context economy, reliability contracts. Reviews the agent .md files themselves, not the overall setup.
disable-model-invocation: true
---
Craft review of Claude Code agent definitions. Scope boundary: /cc-review asks "should this
agent exist, and is an agent the right primitive?" This skill asks "given it exists, is the
definition well-crafted?". Do not re-litigate existence or primitive choice here; hand those
findings to /cc-review instead.

Advisory-first: produce the report, then offer to apply fixes. Never edit before the user
accepts findings.

## Step 0: Refresh knowledge (every run)

WebFetch https://code.claude.com/docs/en/sub-agents and confirm the currently honored
frontmatter fields and their valid values. Training-data knowledge of agent frontmatter is
stale. Never flag or recommend a field you did not just verify. If the fetch fails, say so
and limit frontmatter findings to fields observed working in the repo.

## Step 1: Discover and classify

1. Collect agent files from project `.claude/agents/` and global `~/.claude/agents/`.
   When run inside the dotfiles repo, use the source of truth instead:
   `roles/ai/files/claude/agents/` plus `roles/ai/files/claude/agent-registry.json`.
2. Classify each agent:
   - **local**: under registry `local_agents`, or no registry entry. Fixes may be applied.
   - **upstream-synced**: under a registry `repos` entry. REPORT-ONLY: in-place edits are
     silently reverted by `claude-agent update`. Remedies to offer: contribute the fix
     upstream, or fork to local (copy the file, move its registry entry to `local_agents`).
3. Note registry ↔ disk drift (registered but missing, on disk but unregistered) as findings.

## Step 2: Score each agent

| Dimension | Check |
|---|---|
| Delegation surface | `description` is written for the router: when to delegate, when NOT to, non-goals naming the sibling agent that owns that seat; "Use PROACTIVELY" only where auto-delegation is truly wanted |
| Cost: model fit | `model:` matches the judgment intensity of the work; flag heavy tiers on mechanical tasks and a missing `model:` where inheriting the caller's model is wrong |
| Context economy | `tools:` is a minimal allowlist (omission = inherit everything); every prompt section earns its tokens; a bounded output contract caps what flows back to the caller |
| Reliability | Bounded self-correction (retry limit, then stop), explicit failure statuses (`blocked`, `needs-decision`), honest-reporting rules (never claim an unrun check) |
| Latency | Independent lookups prompted as parallel tool calls; no prescribed re-reads of content the agent already holds |
| Frontmatter validity | Only fields verified in Step 0, with valid values; flag silently-ignored fields |
| Registry hygiene | `groups` tags come from the controlled vocabulary in the repo CLAUDE.md; drift findings from Step 1 |

## Step 3: Cross-agent checks

- Trigger collisions: two descriptions that fire on the same delegation phrasing.
- Seat overlap: two agents claiming the same responsibility without naming each other as
  the non-goal.
- Fleet consistency: model tiers and output contracts that differ without a reason.

## Step 4: Report

1. One-line fleet health summary, then what each agent already does well. Do not
   manufacture findings to look thorough.
2. Findings prioritized P0-P2. Each: **What** (one line, quoting the exact file and
   frontmatter key or section) / **Why** / **How** (the exact change).
3. Per-agent verdict table: agent | local or upstream-synced | top finding | fix path
   (apply / fork-to-local / contribute upstream).
4. Offer to apply accepted fixes: local agents only, one agent at a time.
