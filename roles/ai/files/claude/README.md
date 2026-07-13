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

## Product Team

A gated, spec-driven pipeline that takes a raw product idea to an engineering-ready backlog on a GitHub Project board. It is a set of locally-authored skills and agents (see [skills/product-lead/SKILL.md](skills/product-lead/SKILL.md) for the guide).

The mental model:

- **The filesystem is the orchestrator.** There is no long-running process. Each initiative is a folder under `docs/initiatives/{slug}/`, and `docs/initiatives/{slug}/STATUS.md` is its state machine.
- **Documents are the contracts.** Every stage reads the prior stage's artifact from disk and writes its own; nothing depends on chat history.
- **Every gate is a human PR review.** A stage opens or updates a PR, and merging it means the gate passed. Stages refuse to run until the prior gate is recorded `approved` in `STATUS.md`. In a repo without an `origin` remote, gates fall back to explicit recorded human decisions (local mode in conventions.md).
- **No agent ever commits, pushes, or merges.** You drive git through `/commit` and `/pr`; the skills only write files.

### Two ways in: new product or new feature

The pipeline always runs inside one repo and scaffolds `docs/` into it; the only real difference between the two cases is how much code stage 4 has to read.

- **New product (greenfield).** Start in an empty repo (`git init`), run `/setup-strategy` to establish the strategy and scaffold `docs/`, then open the first initiative with `/0-refine-idea "<idea>"`. Stage 4 has little or no code to explore, so it asks for stack choices rather than inferring them and writes the design from scratch.
- **New feature in an existing project (brownfield).** Run `/setup-strategy` once to capture the strategy and OKRs the product already implies (skip it if `docs/strategy/` already exists), then treat every feature as its own initiative: a fresh `docs/{slug}` branch carried from `/0-refine-idea` through `/7-push-to-board`. Stage 4 reads the real codebase, cites `path:line` for every design claim, fits existing patterns, and numbers new ADRs after (or supersedes) the ones already in `docs/adr/`.

Either way `docs/strategy/` and `docs/adr/` are shared across every initiative in the repo, and each initiative's own artifacts live under `docs/initiatives/{slug}/`. Small, low-risk features can take the expedited path described below.

### Pipeline map

| Stage | Reads | Produces | Gate | Agents |
|---|---|---|---|---|
| `/setup-strategy` (once) | interview (optionally seeded by `/idea-refine`) | `docs/strategy/strategy.md`, `docs/strategy/okrs.md`, repo scaffold | strategy PR | none |
| `/0-refine-idea "<idea>"` | interview + strategy | `00-brief.md`, `STATUS.md`, branch | Gate 0: kill or proceed | `strategy-checker` |
| `/1-research` | brief | `01-research/` (3 researchers + `summary.md`) | none (feeds Gate 1) | `competitive-researcher`, `user-evidence-researcher`, `market-sizer` (parallel) |
| `/2-write-prd` | brief + research | `02-prd.md` | Gate 1: PM + team | none |
| `/3-red-team` | PRD only (fresh eyes) | `03-red-team-report.md`, PRD revision | none (feeds Gate 1) | `pm-red-team` |
| `/4-tech-shape` | PRD + this codebase | `04-design-doc.md`, `docs/adr/` | Gate 2: tech lead | `adr-scribe` |
| `/5-decompose` | PRD + design doc | `05-backlog/` epics + stories + ACs | none (feeds Gate 3) | `ac-writer` |
| `/6-gate-check` | backlog | `06-dor-report.md` (PASS/FAIL per story) | Gate 3: final | none |
| `/7-push-to-board` | backlog + DoR report | GitHub issues + Project items, `docs/LEARNINGS.md` entry | dry-run confirm | none |

A healthy funnel kills most ideas at Gate 0. Killing early is the pipeline working, not failing. Small, low-risk features may take the expedited path (conventions.md): the human may explicitly skip stages 1 and 3; gates and stages 4-6 are never skipped.

### Running an initiative

1. `/setup-strategy` once per repo: interviews you for vision, bets, non-bets, and OKRs, then writes `docs/strategy/` and scaffolds the repo. Arrive with a raw idea instead and it first runs `/idea-refine` (the vendored ideation skill), whose one-pager in `docs/ideas/` seeds the interview - the 3-5 bets and human-supplied OKR numbers are still required in full. Merge the strategy PR before running any initiative.
2. `/0-refine-idea "<your idea>"`: creates the `docs/{slug}` branch and `00-brief.md`, pre-filling its interview from a matching `docs/ideas/` one-pager when one exists (and offering `/idea-refine` when the idea is still vague), and runs `strategy-checker` for a fit verdict. Then `/commit` and `/pr`; merging the PR passes Gate 0.
3. `/1-research`: fans out to the three researchers in parallel (the only fan-out in the pipeline) and synthesizes `01-research/summary.md`. No gate of its own.
4. `/2-write-prd`: writes `02-prd.md` (numbered `R1..Rn` requirements, non-goals, metrics with baselines) and opens the Gate 1 PR.
5. `/3-red-team`: `pm-red-team` attacks the PRD with fresh eyes; agreed fixes are applied to the PRD by the skill. Both files ride the Gate 1 PR, so merge to pass Gate 1.
6. `/4-tech-shape`: explores this codebase read-only and writes `04-design-doc.md`; `adr-scribe` extracts decisions into the repo-wide `docs/adr/`. Opens the Gate 2 PR.
7. `/5-decompose`: writes epics and vertically-sliced stories; `ac-writer` adds Given/When/Then acceptance criteria, each traced to a PRD requirement.
8. `/6-gate-check`: verifies every story against the Definition of Ready and writes `06-dor-report.md`. Opens the Gate 3 PR; merge only on ALL PASS.
9. `/7-push-to-board`: dry-runs, asks Go/Cancel, then creates the GitHub epic and story issues, links them, adds them to the Project, and appends a retrospective to `docs/LEARNINGS.md`.

Run `/product-lead` at any time for a status board: it reads every `docs/initiatives/*/STATUS.md`, reconciles stale gates against merged PRs, and prints the exact next command.

### Artifact trail

```
docs/
  ideas/                    # /idea-refine one-pagers, read by stage 0 to pre-fill
  adr/
    NNNN-{slug}.md          # all ADRs, global numbering, immutable, Initiative field links each back
  strategy/
    strategy.md
    okrs.md
  LEARNINGS.md              # appended at stage 7
  initiatives/{slug}/
    STATUS.md               # state machine, updated every stage
    00-brief.md
    01-research/
      competitive.md
      user-evidence.md
      sizing.md
      summary.md
    02-prd.md
    03-red-team-report.md
    04-design-doc.md        # its ADR index points at the ADRs in docs/adr/
    05-backlog/
      epic-{n}.md
      story-{n.m}.md
    06-dor-report.md
``` The design goal is an unbroken traceability chain: story to `AC-{n.m}.{k}` to `R#` (PRD requirement) to PRD to brief to strategy bet/OKR, cleared by five human PR gates plus the stage-7 dry-run confirm.

### Product agents

Each is single-artifact and least-privilege: it is dispatched only from its owning stage, writes exactly one thing, and cannot reach the human or touch git.

| Agent | Dispatched from | Writes | Role |
|---|---|---|---|
| `strategy-checker` | `/0-refine-idea` | nothing (verdict only) | Judges brief fit against strategy + OKRs; blunt proceed/kill verdict |
| `competitive-researcher` | `/1-research` | `01-research/competitive.md` | Maps who solves the problem today and where the gaps are |
| `user-evidence-researcher` | `/1-research` | `01-research/user-evidence.md` | Collects public user signals, quoting evidence separately from inference |
| `market-sizer` | `/1-research` | `01-research/sizing.md` | Rough TAM/SAM sizing with arithmetic shown and every assumption labeled |
| `pm-red-team` | `/3-red-team` | `03-red-team-report.md` | Attacks the PRD with fresh eyes, at least 5 severity-labeled challenges |
| `adr-scribe` | `/4-tech-shape` | `docs/adr/NNNN-*.md` | Extracts design decisions into numbered, immutable ADRs |
| `ac-writer` | `/5-decompose` | edits `05-backlog/story-*.md` | Adds Given/When/Then acceptance criteria traced to a PRD `R#` |

The pipeline skills are all `disable-model-invocation: true` (human-invoked only). The one exception is `idea-refine`, vendored pristine from `addyosmani/agent-skills` and left model-invocable: `/setup-strategy` and `/0-refine-idea` invoke it via the Skill tool as their ideation front-end, and it works standalone too. Install the whole pipeline into a project with `claude-skill add --group product` (the group includes `idea-refine`). Its agents span a few tags: `claude-agent add --group product` links the five research and review seats; add the last two by name with `claude-agent add adr-scribe` and `claude-agent add ac-writer`.

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

The parallel wave runs in **isolated git worktrees** by default (2+ independent slices; pass `--no-isolate` to keep it in the main checkout). One-file-one-owner stays the primary guarantee against source collisions; the worktree is the mechanism underneath it, fencing each seat's build/test side effects (`node_modules`, build output, generated files) and turning any ownership slip into a visible diff instead of a silent clobber. The architect marks each slice `Parallel: yes|no` and `Depends on:`; the wave (all `Parallel: yes`) dispatches with the Agent tool's `isolation: "worktree"`, and the team lead copies each seat's owned files back into the main checkout (seats never commit, so there is nothing to merge). Held/dependent slices run afterward in the main checkout so they read the integrated work. This relies on `worktree.baseRef: "head"` in [settings.json](settings.json) so seats branch from the current feature tip rather than `origin/main`. It is deliberately **not** wired to the `wt` fish helper: the Agent tool can only isolate subagents into `.claude/worktrees/`, and `wt`'s sibling worktrees fall outside the sandbox write root, so `wt` stays the tool you drive by hand.

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
