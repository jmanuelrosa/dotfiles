# Claude

Management system for Claude Code skills, agents, and MCP servers. Skills and agents live in this directory; `claude-kit` links them into a project or into `~/.claude`.

This document covers how to **use them in a project** and how to **add new skills and agents to the dotfiles repo** itself.

For the worked example (a project from zero, product side then engineering side, with the exact commands and dispatch briefs) read [GETTING-STARTED.md](GETTING-STARTED.md). This file is the reference; that one is the walkthrough. For keeping a session cheap, and for the measured list of things that are not worth optimising, read [CONTEXT-TIPS.md](CONTEXT-TIPS.md).

## Commands

`claude-kit` is the CLI (`roles/ai/files/scripts/claude-kit/`, symlinked into `~/.local/bin` by the `ai` role). It replaced the `claude-skill` / `claude-agent` fish functions, which are gone.

```
claude-kit add    <name>... --type skill|agent|plugin   Install, resolving dependencies
claude-kit remove <name>... --type skill|agent|plugin   Uninstall, cascading to dependencies
claude-kit list            --type skill|agent|plugin   Show artifacts and where they are installed
claude-kit scout                                       Recommend artifacts matched to this project's stack
claude-kit doctor                                      Report drift between registries and disk
claude-kit adopt                                       Rebuild claude-kit.json from what is installed
claude-kit restore                                     Install what claude-kit.json records
claude-kit sync                                        Converge ~/.claude on the artifacts tagged global
claude-kit update   --type skill                       Fetch skills from their upstream repos
claude-kit outdated --type skill                       Report which skills are behind upstream
claude-kit trust                                       Show or change whether this workspace is trusted
```

`--type` is required except on `doctor`, `adopt`, `restore`, `sync` and `scout`, where it narrows an otherwise cross-type result, and on `trust`, which takes none at all. Nothing is inferred from a name, so a name means one artifact of one type. `add` and `remove` also take `--group <tag>` instead of names, and `--global` for an artifact that lands in `~/.claude`. A project is whatever directory you run it in (`$HOME` excepted, since its `.claude` *is* `~/.claude`).

Full reference, worked examples and a corner-case FAQ: [../scripts/claude-kit/README.md](../scripts/claude-kit/README.md). The `claude-skills` and `claude-agents` Television cables drive the same commands interactively.

## Product Team

A two-gate, spec-driven pipeline that takes a raw product idea to an engineering-ready backlog, and then to a living record of what the system actually does. It ships as the `product-team` plugin (see [plugins/product-team/skills/product-lead/SKILL.md](plugins/product-team/skills/product-lead/SKILL.md) for the guide).

The mental model:

- **The filesystem is the orchestrator.** There is no long-running process and no state machine to maintain. Each initiative is a folder under `docs/initiatives/{slug}/`, and which stage comes next is *derived* from the artifacts in it by `scripts/pt.py status`.
- **Documents are the contracts.** Every stage reads the prior stage's artifact from disk and writes its own; nothing depends on chat history.
- **Requirements carry their own scenarios.** `02-prd.md` holds `### R3: {name}` plus a SHALL sentence plus `#### R3.S1` WHEN/THEN blocks. Those ids are what stories claim, tasks cite, the readiness check counts, and the spec merge reads: one place, four consumers.
- **Two gates, answered in the session by default.** Gate 0 (worth building?) and Gate 1 (the right requirements?). `gate_medium: pr` turns them back into PR reviews where real reviewers exist. Kill is a first-class answer to both, and the reason is recorded either way.
- **A script owns what a script can decide.** `pt.py check` handles coverage, id resolution, anchors, deferral closure and size rationales; the model judges only testability, slice verticality, spine completeness and unowned questions.
- **No agent ever commits, pushes, or merges.** You drive git through `/commit` and `/pr`; the skills only write files.

Configuration lives in `docs/strategy/product-team.yml`: the `profile`, the `gate_medium`, the gate owners, and the `roster` of agents each stage dispatches. It is not in CLAUDE.md, because CLAUDE.md is loaded on every turn of every session in the repo.

### Two ways in: new product or new feature

The pipeline always runs inside one repo and scaffolds `docs/` into it; the only real difference between the two cases is how much code stage 4 has to read.

- **New product (greenfield).** Start in an empty repo (`git init`), run `/product-team:setup-strategy` to establish the strategy and scaffold `docs/`, then open the first initiative with `/product-team:0-refine-idea "<idea>"`. Stage 4 has little or no code to explore, so it asks for stack choices rather than inferring them and writes the design from scratch.
- **New feature in an existing project (brownfield).** Run `/product-team:setup-strategy` once to capture the strategy and OKRs the product already implies (skip it if `docs/strategy/` already exists), then treat every feature as its own initiative, `/product-team:0-refine-idea` through `/product-team:8-living-spec`. Stage 4 reads the real codebase, cites `path:line` for every design claim, fits existing patterns, and numbers new ADRs after (or supersedes) the ones already in `docs/adr/`.

Either way `docs/strategy/`, `docs/adr/` and `docs/specs/` are shared across every initiative in the repo, and each initiative's own artifacts live under `docs/initiatives/{slug}/`.

### Pipeline map

| Stage | Reads | Produces | Gate | Agents |
|---|---|---|---|---|
| `/product-team:setup-strategy` (once) | interview (optionally seeded by `/idea-refine`) | `docs/strategy/` incl. `product-team.yml`, CODEOWNERS, repo scaffold | strategy | none |
| `/product-team:0-refine-idea "<idea>"` | interview + strategy | `00-brief.md`, `STATUS.md` | **Gate 0: kill or proceed** | `product-team:strategy-checker` |
| `/product-team:1-research` | brief | `01-research/` (the roster's researchers + `summary.md`) | none | `product-team:competitive-researcher`, `product-team:user-evidence-researcher`, `product-team:market-sizer` (parallel) |
| `/product-team:2-write-prd` | brief + research | `02-prd.md`: SHALL requirements with `R{n}.S{k}` scenarios | none | none |
| `/product-team:3-red-team` | PRD only (fresh eyes) | `03-red-team-report.md`, PRD revision | **Gate 1: the right requirements?** | `product-team:pm-red-team` |
| `/product-team:4-tech-shape` | PRD + this codebase | `04-ux-spec.md`, `04-design-doc.md`, `docs/adr/` | none; ADRs via CODEOWNERS | `ux-shaper`, `product-team:adr-scribe` |
| `/product-team:5-decompose` | PRD + UX spec + design doc | `05-tasks.md`, and `05-backlog/` in the full profile | none | `product-team:ac-writer` |
| `/product-team:6-verify` | tasks + backlog | `06-dor-report.md` | none (full profile only) | none |
| `/product-team:7-push-to-board` | backlog + DoR report | GitHub issues + Project items | dry-run confirm (full only) | none |
| `/product-team:8-living-spec` | tasks + PRD | `docs/specs/{capability}/spec.md`, `docs/LEARNINGS.md` | none, at ship time | none |

A healthy funnel kills most ideas at Gate 0. Killing early is the pipeline working, not failing.

**Why two gates and not four.** The genuinely-open design decisions at stage 4 resolve with no human in the loop, and the ones that do not are reached at implementation whether or not a gate sat there, so a PR gate over the design doc bought a day of wall clock and little else; what it *did* buy is review of the ADRs, which is now a `docs/adr/` line in CODEOWNERS. The readiness gate produced, across three initiatives, one repeated lexical defect (an `L`-sized story with no split rationale), which `pt.py check` now catches for nothing.

**The `solo` profile** drops the board-facing half: no stories, no readiness report, no board export, no PR machinery. It keeps every stage that produces a finding, because research and the red team together are 13% of the cost and produced the decision-changing findings on every initiative that ran.

### Running an initiative

1. `/product-team:setup-strategy` once per repo: interviews you for vision, bets, non-bets, OKRs and the config, then writes `docs/strategy/` and scaffolds the repo. Arrive with a raw idea instead and it first runs `/idea-refine` (the vendored ideation skill), whose one-pager in `docs/ideas/` seeds the interview; the 3-5 bets and human-supplied OKR numbers are still required in full.
2. `/product-team:0-refine-idea "<your idea>"`: writes `00-brief.md`, pre-filling its interview from a matching `docs/ideas/` one-pager when one exists, runs `product-team:strategy-checker` for a fit verdict, and asks **Gate 0**.
3. `/product-team:1-research`: fans out to the roster's researchers in parallel (the only fan-out in the pipeline) and synthesizes `01-research/summary.md`, naming any pass the roster skipped as an evidence gap.
4. `/product-team:2-write-prd`: writes `02-prd.md`, where each requirement is a SHALL with at least one WHEN/THEN scenario, a capability, non-goals, and metrics that name the requirement making them measurable.
5. `/product-team:3-red-team`: `product-team:pm-red-team` attacks the PRD with fresh eyes; agreed fixes are applied by the skill, and then it asks **Gate 1**. That order is deliberate: on a real initiative the gate was answered first and the report then had to amend an already-approved PRD.
6. `/product-team:4-tech-shape`: dispatches `ux-shaper` to write `04-ux-spec.md` (every flow, every surface, every state, and the design-system pieces that do not exist yet), then explores this codebase read-only and writes `04-design-doc.md` against those states, closing every deferral aimed at it and stating where validity is enforced relative to deploy and who can read the deployed thing; `product-team:adr-scribe` extracts decisions into the repo-wide `docs/adr/`. `ux-shaper` is a registry agent rather than a bundled one, so this stage and the architect share one definition of a UX spec: `claude-kit add ux-shaper --type agent --global`.
7. `/product-team:5-decompose`: writes `05-tasks.md`, the whole build in dependency order from an empty repo to accepted, including the toolchain, deploy and acceptance work that could never be a story because no requirement asks for it. In the full profile it also writes thin story headers, and `product-team:ac-writer` fills each one's claimed scenario ids and reports any slice needing a criterion the PRD lacks.
8. `/product-team:6-verify`: runs `pt.py check --strict` (errors and warnings both fail at DoR time), then judges the four items a script cannot, and writes `06-dor-report.md`. Pinned to Sonnet: it used to inherit an Opus session and cost more than research, the PRD and the red team combined.
9. `/product-team:7-push-to-board`: dry-runs, asks Go/Cancel, then creates the GitHub epic and story issues with each story's claimed scenarios expanded into the body, links them, and adds them to the Project.
10. `/product-team:8-living-spec`, at ship time: merges every requirement whose tasks are all checked off into `docs/specs/{capability}/spec.md`, and appends the retrospective to `docs/LEARNINGS.md`. This is the only artifact that outlives the initiative alongside the ADRs.

Run `/product-team:product-lead` at any time for a status board: it runs `pt.py status` over every initiative and prints the exact next command.

### Artifact trail

```
docs/
  ideas/                    # /idea-refine one-pagers, read by stage 0 to pre-fill
  adr/
    NNNN-{slug}.md          # all ADRs, global numbering, immutable, Initiative field links each back
  strategy/
    strategy.md
    okrs.md
    product-team.yml        # profile, gate medium, gate owners, roster
  specs/{capability}/
    spec.md                 # living capability specs, merged at ship time; they outlive the initiative
  LEARNINGS.md              # appended at stage 8, ship time
  initiatives/{slug}/
    STATUS.md               # gate decisions and kills only; stage order is derived by pt.py
    00-brief.md
    01-research/
      competitive.md
      user-evidence.md
      sizing.md
      summary.md
    02-prd.md               # SHALL requirements, each carrying its R{n}.S{k} scenarios
    03-red-team-report.md
    04-ux-spec.md           # every flow, surface and state, written before the design doc
    04-design-doc.md        # its ADR index points at the ADRs in docs/adr/
    05-tasks.md             # the whole build, dependency-ordered, empty repo to accepted
    05-backlog/             # full profile only
      epic-{n}.md
      story-{n.m}.md
    06-dor-report.md        # full profile only
```

The design goal is an unbroken traceability chain: story and task to `R{n}.S{k}` scenario to `R#` requirement to PRD to brief to strategy bet/OKR, verified by `pt.py check` as a set difference and cleared by two human gates (in-session by default, PRs when `gate_medium: pr`) plus the stage-7 dry-run confirm.

### Product agents

Each is single-artifact and least-privilege: it is dispatched only from its owning stage, writes exactly one thing, and cannot reach the human or touch git.

| Agent | Dispatched from | Writes | Role |
|---|---|---|---|
| `product-team:strategy-checker` | `/product-team:0-refine-idea` | nothing (verdict only) | Judges brief fit against strategy + OKRs; blunt proceed/kill verdict |
| `product-team:competitive-researcher` | `/product-team:1-research` | `01-research/competitive.md` | Maps who solves the problem today and where the gaps are |
| `product-team:user-evidence-researcher` | `/product-team:1-research` | `01-research/user-evidence.md` | Collects public user signals, quoting evidence separately from inference |
| `product-team:market-sizer` | `/product-team:1-research` | `01-research/sizing.md` | Rough TAM/SAM sizing with arithmetic shown and every assumption labeled |
| `product-team:pm-red-team` | `/product-team:3-red-team` | `03-red-team-report.md` | Attacks the PRD with fresh eyes, at least 5 severity-labeled challenges |
| `product-team:adr-scribe` | `/product-team:4-tech-shape` | `docs/adr/NNNN-*.md` | Extracts design decisions into numbered, immutable ADRs |
| `product-team:ac-writer` | `/product-team:5-decompose` | edits `05-backlog/story-*.md` | Claims and completes: fills each story's scenario ids from the PRD and reports any slice needing a scenario the PRD lacks |

The pipeline skills are all `disable-model-invocation: true` (human-invoked only). The one exception is `idea-refine`, vendored pristine from `addyosmani/agent-skills` and left model-invocable: `/product-team:setup-strategy` and `/product-team:0-refine-idea` invoke it via the Skill tool as their ideation front-end, and it works standalone too. Install the whole pipeline into a project with `claude-kit add product-team --type plugin`: the seven product agents ship inside the bundle and its `skillDependencies` pulls `idea-refine` alongside. The one agent to add separately is `ux-shaper` (`claude-kit add ux-shaper --type agent --global`), shared with the architect so both read one definition of a UX spec.

## Staff-engineer bench

A separate delegation system for building what Product Team specs out. Each seat detects the project stack first, routes to installed project skills for stack-specific best practices, implements within strict boundaries, self-verifies, and returns a structured completion report. The `architect` is the bridge: given a refined brief it explores the codebase read-only, writes a feature spec to `docs/specs/` with an owner-split work breakdown across these seats, and returns dispatch-ready briefs.

| Agent | Owns | Never |
|---|---|---|
| `architect` | Cross-stack design: feature spec in `docs/specs/`, work split across seats, ADRs for hard-to-reverse choices | Implements, reviews, or dispatches (disallows the Agent tool) |
| `ux-shaper` | UX specification: every flow, every surface, every state each surface can reach, and the design-system pieces that do not exist yet | Implements, generates mockups, or dispatches; never names a component it did not find in the code |
| `frontend-staff-engineer` | UI features, components, styling, state, routing, data fetching | Reviews its own work (the caller owns review) |
| `design-staff-engineer` | Design system: tokens, theming, shared components and variant APIs, typography, color, spacing, motion, responsive/CSS architecture | Data fetching, routing, business logic (the frontend seat); never trades accessibility for aesthetics |
| `mobile-staff-engineer` | Native iOS (SwiftUI), Android (Compose), React Native/Expo screens and flows, offline/sync, persistence, deep links, push, permissions | Web UI (frontend seat), server code (backend seat); never submits to a store or ships an OTA update |
| `backend-staff-engineer` | API endpoints, services, business logic, data models, migrations, queues, jobs | Reviews its own work (the caller owns review) |
| `platform-staff-engineer` | CI/CD, Dockerfiles and compose, app-level K8s/Helm, hooks, task runners | Cloud IaC, SLOs/alerts; never deploys |
| `dx-staff-engineer` | Inner loop: monorepo build graphs and caching, codegen, shared lint/TS config, workspace and dependency health, test velocity, internal CLIs and scaffolding | CI/CD, containers, release (the platform seat), test design (qa); never deploys |
| `cloud-staff-engineer` | Terraform/Pulumi/CDK, networking, IAM, cluster provisioning, cost controls | CI pipelines, alert rules; never `apply`s or mutates live infra |
| `sre-staff-engineer` | SLOs and error budgets, burn-rate alerts, dashboards-as-code, observability, runbooks | CI, IaC; never silences an alert without a root cause |
| `data-staff-engineer` | Orchestrated pipelines (Airflow, Dagster), Spark/batch jobs, ingestion, data contracts | dbt/metrics, OLTP schemas; never runs pipelines/backfills against prod |
| `analytics-staff-engineer` | dbt models and tests, semantic-layer/metric definitions, experiments, notebooks | Ingestion, OLTP schemas; never redefines a metric of record without approval |
| `gtm-staff-engineer` | Web and server GTM containers, dataLayer contracts, tags/triggers/variables, GA4 and Consent Mode, server-side Conversion APIs (Meta CAPI, GA4 Measurement Protocol) | GA4 data modeling and metrics (the analytics seat), provisioning or deploying the tagging server (cloud/platform); never publishes a container version |
| `database-staff-engineer` | Schema design, migrations, indexes, query optimization, replication-aware DDL | Business logic, lakehouse; never runs against a non-disposable environment |
| `qa-staff-engineer` | Unit/integration/e2e tests, test infra, fixtures, flake diagnosis | Modifies application source; reports product bugs back to the caller |
| `security-staff-engineer` | Read-only assessment: STRIDE threat models, dependency audits, secrets hygiene, authn/authz review | Edits files; auto-delegation during coding (diff review is `/security-review`) |

Each seat is a skills-dir plugin under `roles/ai/files/claude/plugins/<discipline>/` that bundles the agent with its `<discipline>-failure-modes` skill (`frontend-failure-modes`, `backend-failure-modes`, and so on): an audited checklist of that domain's common defects the seat consults before it implements. Because the skill lives inside the plugin folder, `claude-kit add <seat> --type plugin` links the whole plugin into the project and the skill travels with it (invoked as `<discipline>:<discipline>-failure-modes`); the seat loads once the workspace is trusted.

Product Team hands off a backlog; then `/feature-team "<brief>"` runs the build side: `architect` writes the spec, you approve the plan, the installed seats implement in parallel, and the skill verifies and returns an integration report. Install a whole discipline with `claude-kit add --group engineering --type plugin` (the 13 seats above except `qa`, which lives under `quality`: add it with `claude-kit add qa --type plugin`), or add individual seats by name. A seat's **plugin name is the bare discipline** (`claude-kit add backend --type plugin`); the namespaced `backend:backend-staff-engineer` is how the agent inside is dispatched, not how it is installed.

The parallel wave runs in **isolated git worktrees** by default (2+ independent slices; pass `--no-isolate` to keep it in the main checkout). One-file-one-owner stays the primary guarantee against source collisions; the worktree is the mechanism underneath it, fencing each seat's build/test side effects (`node_modules`, build output, generated files) and turning any ownership slip into a visible diff instead of a silent clobber. The architect marks each slice `Parallel: yes|no` and `Depends on:`; the wave (all `Parallel: yes`) dispatches with the Agent tool's `isolation: "worktree"`, and the team lead copies each seat's owned files back into the main checkout (seats never commit, so there is nothing to merge). Held/dependent slices run afterward in the main checkout so they read the integrated work. This relies on `worktree.baseRef: "head"` in [settings.json](settings.json) so seats branch from the current feature tip rather than `origin/main`. It is deliberately **not** wired to the `wt` fish helper: the Agent tool can only isolate subagents into `.claude/worktrees/`, and `wt`'s sibling worktrees fall outside the sandbox write root, so `wt` stays the tool you drive by hand.

### From backlog to build

Once `/product-team:6-verify` reports ALL PASS, the durable handoff is `docs/initiatives/{slug}/05-backlog/story-{n.m}.md` (backed by the GitHub Project issues `/product-team:7-push-to-board` created), each story a vertical tracer-bullet slice claiming the PRD scenario ids it satisfies and naming the `05-tasks.md` groups that implement it. Read the story with `02-prd.md` open: the story claims `R3.S1`, and the WHEN/THEN text lives in the PRD. Work **one story at a time**: a story is already the unit `/feature-team` and `architect` are built around, so feed one story per run rather than a whole epic.

The per-story loop:

1. Take the lowest-id PASS story from `06-dor-report.md`.
2. Run `/feature-team "<story title + goal>"`, giving the architect three anchors: the story file (the scenarios it claims are the acceptance bar, and their WHEN/THEN text lives in the PRD), `02-prd.md` (the `R#` source of truth), and `docs/adr/` (immutable constraints).
3. `architect` writes `docs/specs/<feature>.md` with the owner-split work breakdown; you approve at the gate; the seats implement in isolated waves and the skill returns an integration report.
4. `/code-review max`, then `/commit`, then move the issue to Done and pick the next PASS story.

**Two design docs, one decision record.** `/product-team:4-tech-shape` already wrote `04-design-doc.md`, and `architect` writes its own `docs/specs/<feature>.md`. Either point the architect at `04-design-doc.md` so it inherits those decisions, or let it design fresh from the PRD for an independent check. Whichever you choose, `docs/adr/` is the shared, immutable tie-breaker: the spec honors accepted ADRs and supersedes (never edits) if it diverges, continuing the same global numbering both pipelines use.

**One UX spec, though.** The states each surface can reach were reviewed, and possibly rewritten, by the `.github/CODEOWNERS` design owner where the repo names one, so point the architect at `04-ux-spec.md` rather than letting it re-derive them from the PRD and throw that review away. Outside the pipeline there is no spec to read, and a brief touching UI comes back `needs-decision` naming the `ux-shaper` run for you to make: the architect cannot dispatch it, which is the design rather than a limitation.

## The Tracked/Local Rule

Every skill and agent in this repo is either:

- **Tracked** — synced from an upstream GitHub repo, declared under `repos` in [skill-registry.json](skill-registry.json) or [agent-registry.json](agent-registry.json), or
- **Local** — authored (or consolidated) here, declared under `local_skills` / `local_agents` in the matching registry.

**Never both, never neither.** The `local_skills` and `local_agents` arrays are not just "skipped" lists — they're the authoritative inventory of locally-authored items. If a skill or agent exists on disk but doesn't appear in either place, that's a bug.

## Model and effort policy

`model` and `effort` are separate dials and they answer different questions. **Model is capability**: which weights read the problem. **Effort is depth**: how many tokens, tool calls and verification passes the model spends before it comes back. A cheap model at high effort and an expensive one at low effort are both real configurations, and neither substitutes for the other.

Both are set per artifact, in the frontmatter of a `SKILL.md` or an agent `.md`. The session values in [settings.json](settings.json) (`model: sonnet`, `effortLevel: high`) are the baseline for **your own turn**; a delegated skill or agent should not inherit them by accident, because you chose them for what you were doing, not for what it does.

### Effort

Three tiers are in use. `low` and `max` are deliberately unused: `low` trades away tool calls, which is the wrong economy for anything that has to read a diff or a codebase first, and `max` is prone to overthinking on structured work.

| Tier | For | Where it is set today |
|---|---|---|
| `medium` | Template-driven and mechanical work, where the procedure carries the result and the model fills it in | `commit`, `pr`, `jira`, `handoff`, `coderabbit`, `cc-review` |
| `high` | Research, review and read-and-summarize work, where breadth matters more than depth | `security-staff-engineer`, `cc-staff-reviewer`, the five product-team research and scribe agents |
| `xhigh` | Multi-file implementation, cross-stack design, adversarial review | The 14 implementer seats, `architect`, `ux-shaper`, `pm-red-team` |

`high` matches the current `effortLevel`, so setting it explicitly changes nothing today and reads as a no-op. It is not one: it is a **pin**, and its job is to keep that artifact at `high` when you run a session at `xhigh`, `max` or ultracode. Do not delete it as dead config.

### Model

Pins are deliberate and stay. Every staff-engineer seat, `architect` and `ux-shaper` pin `model: opus`, which is a refusal to follow a `/model fable` session: the cost of a delegated implementation stays predictable whatever you are running in the main loop. `commit`, `pr` and the product-team research and scribe agents pin `model: sonnet`, because the judgment intensity does not justify Opus. Everything else omits `model:` and inherits.

Leave `model:` off unless inheriting the caller's model would be wrong for the work.

### Memory

All 15 seats, `architect` and `ux-shaper` carry `memory: project`, giving each one `<project>/.claude/agent-memory/<name>/` so it stops rediscovering the same stack facts on every dispatch. For `ux-shaper` those facts are the design system: which tokens exist, which components have which variants. The directory is committable by design, so a seat records the **shape of the codebase** there and never a secret, a credential, or a security finding's exploit detail. Enabling the field is not enough on its own: each seat also carries a boundary bullet telling it to write there, and the completion report still names the gotchas for the caller.

Authoring guidance for all three lives with the generators, and they are the files to change if this policy changes: [skills/agent-writer/references/seat-agent-anatomy.md](skills/agent-writer/references/seat-agent-anatomy.md) for seats, [skills/skill-writer/references/claude-frontmatter-invocation.md](skills/skill-writer/references/claude-frontmatter-invocation.md) for skills, and [skills/agent-audit/SKILL.md](skills/agent-audit/SKILL.md) for the audit rubric that catches drift.

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

3. Set `effort:` if the skill's work is reliably shallower or deeper than an average turn, and `model:` only if inheriting the caller's model would be wrong. See [Model and effort policy](#model-and-effort-policy). A thin dispatcher that immediately hands off to a subagent gets almost nothing from its own `effort:`; set it on the subagent instead.

### Option B — Track from an upstream repo

1. Add an entry to [skill-registry.json](skill-registry.json) under the appropriate repo key:

   ```json
   {
     "upstream_path": "skills/some-skill",
     "name": "my-local-name",
     "groups": ["engineering", "backend"]
   }
   ```

2. Run `claude-kit update <name> --type skill` to pull it down.

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

3. Set `effort:` from the [Model and effort policy](#model-and-effort-policy) tiers; a delegated agent should never be left on the session default. Add `memory: project` if the agent benefits from carrying stack facts between dispatches, and pair it with a boundary bullet telling the agent to write there. A seat goes through `/agent-writer` instead, which owns the whole frontmatter contract.

### Option B — Track from an upstream repo

1. Add an entry to [agent-registry.json](agent-registry.json) under the appropriate repo key:

   ```json
   {
     "upstream_path": "agents/some-agent.md",
     "name": "my-agent",
     "groups": ["quality", "review"]
   }
   ```

2. Copy the file in by hand and record `updated_at` yourself: `update` and `outdated` cover skills only (`claude-kit update --type agent` refuses), because every agent here is authored in this repo. `repos` is empty today, and this is the reason to think twice before filling it.

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

- **`repos`** — keyed by `owner/repo`. Each repo has a `branch` and a `skills` array. Each skill maps `upstream_path` (path in the upstream repo) to a `name` used by `claude-kit` commands, plus a `groups` tag array consumed by `claude-kit add --group <tag> --type skill`.
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

- **`agents` array** — maps `upstream_path` → `name` (the `.md` filename without extension in `agents/`), plus a `groups` tag array consumed by `claude-kit add --group <tag> --type agent`. An optional `updated_at` is recorded by hand, since `update` covers skills only.
- **`local_agents`** — **authoritative inventory of local agents.** Every locally-authored `.md` under `agents/` must appear here, with its `groups` tags and a `note` documenting why it's local (locally authored, consolidated, etc.).

## Directory Structure

```
roles/ai/files/claude/
  skills/                 # Individual skills (directories with SKILL.md)
  agents/                 # Agent .md files
  rules/                  # User-scope rules, linked into ~/.claude/rules/
  skill-registry.json     # Tracked upstream + local_skills inventory
  agent-registry.json     # Tracked upstream agents
```

Every `.md` in `rules/` is linked into `~/.claude/rules/` and loads at launch in every project, so it is machine-wide the moment the `ai` role runs.
That is the only route a machine-wide review policy has: Claude Code reads a `REVIEW.md` at a repository root only, and only for hosted GitHub Code Review, so the local review never reads one wherever it sits.
See the code review policy section in the repo's root `CLAUDE.md` for why the review bar lives in `rules/`, and why no `REVIEW.md` template is kept here.

## Resources

- https://skills.sh/
