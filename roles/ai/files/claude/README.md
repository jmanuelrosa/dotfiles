# Claude

Management system for Claude Code skills, agents, and MCP servers. Skills and agents live in this directory and are linked into projects via the `claude-skill` and `claude-agent` fish functions.

This document covers how to **use those functions in a project** and how to **add new skills and agents to the dotfiles repo** itself.

## Commands

Both functions are run from the root of a project — they operate on `./.claude/skills/` or `./.claude/agents/` relative to the current directory. They require `jq` (`brew install jq`).

### `claude-skill`

```
claude-skill <list|add|remove|update|outdated> [--group] [name]
```

| Subcommand | What it does |
|---|---|
| `list` | List all skills with status: `✓ linked`, `·` available on disk, `↓ not downloaded`. |
| `list --group` | Same listing, but grouped by the `groups` tags from the registry. |
| `add <name>` | Symlink the skill into `./.claude/skills/`. If it's a tracked skill not yet on disk, fetches it from upstream first. |
| `add --group <group>` | Link every skill belonging to `<group>`, downloading any tracked ones that aren't on disk yet. |
| `remove <name>` | Remove the symlink from `./.claude/skills/`. |
| `remove --group <group>` | Remove all symlinks for skills in `<group>`. |
| `update` | Pull every tracked skill from its upstream repo. Treats upstream as canonical — the local skill dir is wiped and re-extracted, so any file no longer present upstream is removed. One line per skill. Records `updated_at` for each entry it confirmed. |
| `update <name>` | Same, scoped to one skill. Local skills are skipped with a warning — there's no upstream to sync. |
| `outdated` | Fetch upstream for every tracked skill and report what's behind — without writing anything. One line per skill (repo header + name + status + last synced). No file-level detail. |
| `outdated <name>` | Same, scoped to one skill. Local skills emit the same "no upstream" warning. |

### `claude-agent`

```
claude-agent <list|add|remove|update|outdated> [--group] [name]
```

| Subcommand | What it does |
|---|---|
| `list` | List all agents with status: `✓ linked`, `·` available on disk, `↓ not downloaded`. |
| `list --group` | Same listing, but grouped by the `groups` tags from the registry. |
| `add <name>` | Symlink the agent into `./.claude/agents/`. Fetches from upstream first if not on disk. |
| `add --group <group>` | Link every agent belonging to `<group>`, downloading any tracked ones that aren't on disk yet. |
| `remove <name>` | Remove the symlink from `./.claude/agents/`. |
| `remove --group <group>` | Remove all symlinks for agents in `<group>`. |
| `update` | Pull every tracked agent from upstream. Records `updated_at` in the registry for each entry it confirmed. |
| `update <name>` | Same, scoped to one agent. Local agents are skipped with a warning — there's no upstream to sync. |
| `outdated` | Fetch upstream for every tracked agent and report what's behind — without writing anything. Shows `last synced` from the registry. |
| `outdated <name>` | Same, scoped to one agent. Local agents emit the same "no upstream" warning. |

## Staff-engineer bench

A separate delegation system for building what Product Team specs out. Each seat detects the project stack first, routes to installed project skills for stack-specific best practices, implements within strict boundaries, self-verifies, and returns a structured completion report. The `architect` is the bridge: given a refined brief it explores the codebase read-only, writes a feature spec to `docs/specs/` with an owner-split work breakdown across these seats, and returns dispatch-ready briefs.

| Agent | Owns | Never |
|---|---|---|
| `architect` | Cross-stack design: feature spec in `docs/specs/`, work split across seats, ADRs for hard-to-reverse choices | Implements, reviews, or dispatches (disallows the Agent tool) |
| `frontend-staff-engineer` | UI features, components, styling, state, routing, data fetching | Reviews its own work (the caller owns review) |
| `design-staff-engineer` | Design system: tokens, theming, shared components and variant APIs, typography, color, spacing, motion, responsive/CSS architecture | Data fetching, routing, business logic (the frontend seat); never trades accessibility for aesthetics |
| `mobile-staff-engineer` | Native iOS (SwiftUI), Android (Compose), React Native/Expo screens and flows, offline/sync, persistence, deep links, push, permissions | Web UI (frontend seat), server code (backend seat); never submits to a store or ships an OTA update |
| `backend-staff-engineer` | API endpoints, services, business logic, data models, migrations, queues, jobs | Reviews its own work (the caller owns review) |
| `platform-staff-engineer` | CI/CD, Dockerfiles and compose, app-level K8s/Helm, hooks, task runners | Cloud IaC, SLOs/alerts; never deploys |
| `cloud-staff-engineer` | Terraform/Pulumi/CDK, networking, IAM, cluster provisioning, cost controls | CI pipelines, alert rules; never `apply`s or mutates live infra |
| `sre-staff-engineer` | SLOs and error budgets, burn-rate alerts, dashboards-as-code, observability, runbooks | CI, IaC; never silences an alert without a root cause |
| `data-staff-engineer` | Orchestrated pipelines (Airflow, Dagster), Spark/batch jobs, ingestion, data contracts | dbt/metrics, OLTP schemas; never runs pipelines/backfills against prod |
| `analytics-staff-engineer` | dbt models and tests, semantic-layer/metric definitions, experiments, notebooks | Ingestion, OLTP schemas; never redefines a metric of record without approval |
| `gtm-staff-engineer` | Web and server GTM containers, dataLayer contracts, tags/triggers/variables, GA4 and Consent Mode, server-side Conversion APIs (Meta CAPI, GA4 Measurement Protocol) | GA4 data modeling and metrics (the analytics seat), provisioning or deploying the tagging server (cloud/platform); never publishes a container version |
| `database-staff-engineer` | Schema design, migrations, indexes, query optimization, replication-aware DDL | Business logic, lakehouse; never runs against a non-disposable environment |
| `qa-staff-engineer` | Unit/integration/e2e tests, test infra, fixtures, flake diagnosis | Modifies application source; reports product bugs back to the caller |
| `security-staff-engineer` | Read-only assessment: STRIDE threat models, dependency audits, secrets hygiene, authn/authz review | Edits files; auto-delegation during coding (diff review is `/security-review`) |

Each seat is paired with a `<discipline>-failure-modes` skill (`frontend-failure-modes`, `backend-failure-modes`, `mobile-failure-modes`, and so on) - an audited checklist of that domain's common defects that the seat consults before it implements. The skill is the agent's declared dependency, so `claude-agent add <seat>` pulls the matching failure-modes skill into the project automatically.

Product Team hands off a backlog; then `/feature-team "<brief>"` runs the build side: `architect` writes the spec, you approve the plan, the installed seats implement in parallel, and the skill verifies and returns an integration report. Install a whole discipline with `claude-agent add --group engineering` (all seats above except `qa-staff-engineer`, which lives under `quality`: add it with `claude-agent add qa-staff-engineer`), or add individual seats by name.

## The Tracked/Local Rule

Every skill and agent in this repo is either:

- **Tracked** — synced from an upstream GitHub repo, declared under `repos` in [skill-registry.json](skill-registry.json) or [agent-registry.json](agent-registry.json), or
- **Local** — authored (or consolidated) here, declared under `local_skills` / `local_agents` in the matching registry.

**Never both, never neither.** The `local_skills` and `local_agents` arrays are not just "skipped" lists — they're the authoritative inventory of locally-authored items. If a skill or agent exists on disk but doesn't appear in either place, that's a bug.

## Adding Skills

### Option A — Local skill

1. Create the directory with a `SKILL.md`:

   ```
   roles/ai/files/claude/skills/my-skill/
     SKILL.md
   ```

2. Declare it in `local_skills` in [skill-registry.json](skill-registry.json) with its groups and a note:

   ```json
   { "name": "my-skill", "groups": ["productivity"], "note": "Locally authored" }
   ```

   Common notes: `"Locally authored"`, `"Consolidated from multiple sources"`, `"No external source"`.

### Option B — Track from an upstream repo

1. Add an entry to [skill-registry.json](skill-registry.json) under the appropriate repo key:

   ```json
   {
     "upstream_path": "skills/some-skill",
     "name": "my-local-name",
     "groups": ["engineering", "backend"]
   }
   ```

2. Run `claude-skill update <name>` to pull it down.

## Adding Agents

### Option A — Local agent

1. Create the file directly:

   ```
   roles/ai/files/claude/agents/my-agent.md
   ```

2. Declare it in `local_agents` in [agent-registry.json](agent-registry.json) with its groups and a note:

   ```json
   { "name": "my-agent", "groups": ["quality"], "note": "Locally authored" }
   ```

   Common notes: `"Locally authored"`, `"Consolidated from multiple sources"`, `"No external source"`.

### Option B — Track from an upstream repo

1. Add an entry to [agent-registry.json](agent-registry.json) under the appropriate repo key:

   ```json
   {
     "upstream_path": "agents/some-agent.md",
     "name": "my-agent",
     "groups": ["quality", "review"]
   }
   ```

2. Run `claude-agent update <name>` to pull it down.

## Registry Format

### skill-registry.json

```json
{
  "version": 2,
  "repos": {
    "owner/repo": {
      "branch": "main",
      "skills": [
        {
          "upstream_path": "skills/some-skill",
          "name": "local-name",
          "groups": ["engineering", "backend"],
          "updated_at": "2026-05-12T10:23:45Z"
        }
      ]
    }
  },
  "local_skills": [
    { "name": "skill-name", "groups": ["productivity"], "note": "Locally authored" }
  ]
}
```

- **`repos`** — keyed by `owner/repo`. Each repo has a `branch` and a `skills` array. Each skill maps `upstream_path` (path in the upstream repo) to a `name` used by `claude-skill` commands, plus a `groups` tag array consumed by `claude-skill add --group <name>`.
- **`updated_at`** — ISO 8601 UTC timestamp, automatically maintained by `update`. Records the last time `update` confirmed this entry against upstream — whether or not files changed. `outdated` reads it to show "last synced" alongside the diff. Missing on tracked entries that have never been synced after this field was introduced.
- **`local_skills`** — **authoritative inventory of local skills.** Every local skill directory under `skills/` must appear here, with its `groups` tags and a `note` documenting why it's local (locally authored, consolidated, etc.).

### agent-registry.json

```json
{
  "version": 2,
  "repos": {
    "owner/repo": {
      "branch": "main",
      "agents": [
        {
          "upstream_path": "agents/some-agent.md",
          "name": "my-agent",
          "groups": ["quality", "review"],
          "updated_at": "2026-05-12T10:23:45Z"
        }
      ]
    }
  },
  "local_agents": [
    { "name": "agent-name", "groups": ["quality"], "note": "Locally authored" }
  ]
}
```

- **`agents` array** — maps `upstream_path` → `name` (the `.md` filename without extension in `agents/`), plus a `groups` tag array consumed by `claude-agent add --group <name>`. An optional `updated_at` is maintained by `update` (same semantics as for skills).
- **`local_agents`** — **authoritative inventory of local agents.** Every locally-authored `.md` under `agents/` must appear here, with its `groups` tags and a `note` documenting why it's local (locally authored, consolidated, etc.).

## Directory Structure

```
roles/ai/files/claude/
  skills/                 # Individual skills (directories with SKILL.md)
  agents/                 # Agent .md files
  skill-registry.json     # Tracked upstream + local_skills inventory
  agent-registry.json     # Tracked upstream agents
```

## Resources

- https://skills.sh/
