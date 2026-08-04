# Starting from zero

The worked example. [README.md](README.md) is the reference (what every piece is, how it is registered, why it is shaped that way); this file is the walkthrough (what you actually type, in what order, and what lands on disk).
Read this one first when you come back to this setup after six months away.

Everything below was run against this repo's catalogue, so the commands are literal.

## The two halves

There are two systems here and they meet at exactly one artifact, a story.

```
  idea
    │
    │   PRODUCT SIDE  -  what to build and why      (product-team plugin, per repo)
    ▼
  strategy → brief → research → PRD → red team → design doc → epics + stories → DoR → board
    │                                                            │
    │                                          docs/initiatives/{slug}/05-backlog/story-1.2.md
    ▼                                                            │
  ENGINEERING SIDE  -  how to build it                           │  one story at a time
    │                                                            ▼
    └─→ /feature-team → architect writes docs/specs/*.md → you approve → seats implement
                                                                 │
                                                                 ▼
                                                    /code-review → /commit → /pr
```

Three rules hold across both halves, and they are the ones to remember:

- **The filesystem is the orchestrator.** No process is long-running. Each stage reads the previous stage's file from disk and writes its own, so a session that dies loses nothing.
- **Every gate is a human.** A product gate is a merged PR; the engineering gate is you approving the architect's spec before any seat is dispatched.
- **No agent ever commits, pushes, or merges.** Agents write files. You run `/commit` and `/pr`.

## What you already have in every repo

`claude-kit sync` links everything tagged `global` into `~/.claude`, so these need no install and work in any directory:

| Command or agent | Use it for |
|---|---|
| `/feature-team "<brief>"` | The whole engineering pipeline: architect spec, approval gate, parallel seat dispatch, integration report |
| `architect` agent | Design only: writes `docs/specs/<feature>.md` plus ADRs, dispatches nothing |
| `ux-shaper` agent | UI only: writes a UX spec (flows, surfaces, every state, the design-system pieces that are missing) for the architect or a stage to design against |
| `/grill-me "<idea>"` | A relentless interview that sharpens a fuzzy brief before it costs you a bad spec |
| `/grill-with-docs` | The same, with the library docs pulled in |
| `/research "<question>"` | Multi-source research write-up |
| `/commit`, `/pr` | The only supported git write paths (a hook enforces this) |
| `/handoff` | Compact a dying session into a doc the next one can pick up |
| `/cc-review`, `agent-audit`, `skill-writer`, `agent-writer` | Maintaining this setup itself |
| `/product-lead` | A signpost that tells you the pipeline is a plugin and hands you the install line |

Everything else is opt in, per project. That is deliberate: the product pipeline writes into `docs/` of whatever repo it runs in, and a seat you never dispatch is context you pay for on every turn.

## Step 0: bootstrap a repo

```console
$ mkdir ledger && cd ledger && git init
$ claude
```

Accept the trust dialog. Then let the catalogue tell you what belongs here:

```console
$ claude-kit scout
```

`scout` fingerprints the directory and ranks the catalogue against it, with the evidence printed beside each row (`react@19.0.0 in package.json`, `no test directory and no test files`). An empty repo has no fingerprint yet, so on a true greenfield you install by intent instead:

```console
$ claude-kit add product-team --type plugin      # the product pipeline
$ claude-kit add --group engineering --type plugin  # 13 staff-engineer seats
$ claude-kit add qa --type plugin                 # qa is tagged quality, not engineering
```

Install fewer if you know the shape of the work: `claude-kit add frontend backend database --type plugin` is the common trio. Seats are cheap to add later, and `/feature-team` tells you exactly which one is missing when the spec needs it.

**Two things every plugin install needs, and both are easy to forget:**

1. The workspace must be **trusted**.
2. Claude must be **relaunched from the repo root** afterwards.

Until both hold, `/product-team:setup-strategy` does not exist and `claude plugin list` shows nothing. `claude-kit add` prints this hint on every plugin install.

After the relaunch, re-run scout once the repo has a `package.json` (or `go.mod`, or `pyproject.toml`) so it can see the stack and offer the matching skills:

```console
$ claude-kit scout --type skill
$ claude-kit scout --add        # installs the strong tier only
```

## Scenario 1: a new product, from nothing

Greenfield. You have an idea and an empty repo. Running example: *Ledger*, a subscription-spend tracker for small teams.

### Product side

**1. Strategy, once per repo.**

```
/product-team:setup-strategy
```

It interviews you one question at a time for vision, 3-5 bets, non-bets, and OKRs, then writes `docs/strategy/strategy.md` and `docs/strategy/okrs.md` and scaffolds the repo. Arrive with a raw idea instead of a strategy and it runs `/idea-refine` first, whose one-pager in `docs/ideas/` seeds the interview. The numbers are always yours: it will not invent a baseline.

Then `/commit`, then `/pr`. Merge before running any initiative.

**2. Open the initiative.**

```
/product-team:0-refine-idea "let a team see every subscription they pay for in one place"
```

Creates the branch, writes `docs/initiatives/subscription-visibility/00-brief.md` and `STATUS.md`, and dispatches `product-team:strategy-checker` for a blunt fit verdict against the strategy you just wrote. `/commit`, `/pr`, merge. Merging is Gate 0.

A healthy funnel kills most ideas here. Killing at Gate 0 is the pipeline working.

**3. Research, PRD, red team.**

```
/product-team:1-research      # 3 agents in parallel: competitive, user evidence, sizing
/product-team:2-write-prd     # 02-prd.md, requirements numbered R1..Rn
/product-team:3-red-team      # pm-red-team attacks the PRD, fixes fold back in
```

All three ride one branch. `/commit`, `/pr`, merge passes Gate 1. On a small, low-risk feature you may explicitly skip 1 and 3; that skip is yours to call, never the skill's, and it gets recorded in `STATUS.md`.

**4. Technical shape, then decompose, then the readiness gate.**

```
/product-team:4-tech-shape    # 04-ux-spec.md + 04-design-doc.md + ADRs  → Gate 2
/product-team:5-decompose     # 05-backlog/ epics + vertically-sliced stories + ACs
/product-team:6-gate-check    # 06-dor-report.md, PASS/FAIL per story    → Gate 3
```

Merge only on ALL PASS.

**5. Push to the board.**

```
/product-team:7-push-to-board
```

Dry-runs first and waits for your Go, then creates the GitHub epic and story issues, links them, adds them to the Project, and appends a retrospective to `docs/LEARNINGS.md`.

Lost at any point:

```
/product-team:product-lead
```

reads every `docs/initiatives/*/STATUS.md`, reconciles stale gates against merged PRs, and prints the exact next command.

### Engineering side

The handoff is the story file, not the epic. Work **one story at a time**: a story is already the unit `/feature-team` and `architect` are built around.

**6. Take the lowest-id PASS story and run the team.**

```
/feature-team "Story 1.2 - export the subscription list as CSV.
Story: docs/initiatives/subscription-visibility/05-backlog/story-1.2.md (its AC-* are the acceptance bar)
Requirements: docs/initiatives/subscription-visibility/02-prd.md (the R# source of truth)
Constraints: docs/adr/ (accepted ADRs are immutable)"
```

Three anchors, always: the story, the PRD, the ADR directory. What happens next:

1. It restates the brief and confirms scope. If it is fuzzy it stops and suggests `/grill-me` first.
2. It inventories the installed seats (`.claude/agents/`, `~/.claude/agents/`, `claude plugin list`) and names any missing one with the exact `claude-kit add` line.
3. It dispatches `architect`, which explores read-only and writes `docs/specs/csv-export.md` with an owner-split work breakdown, exact cross-slice contracts, and ADRs for hard-to-reverse choices.
4. **It stops at the approval gate** and shows you the objective, acceptance criteria, owner split, and decision items. Nothing is implemented until you say so. It is cheaper to fix a bad plan than bad code.
5. On approval it dispatches every slice marked `Parallel: yes` in one message so they run concurrently, in isolated git worktrees when there are 2+ of them.
6. It integrates the wave back into the main checkout, runs the held slices in dependency order, and returns an integration report: per-seat status, criteria met and unmet, pending ask-first items, gotchas worth adding to `CLAUDE.md`.

**7. Close the loop.**

```
/code-review          # on the combined diff
/commit
/pr
```

Then move the issue to Done and pick the next PASS story.

**Two design docs, one decision record.** `4-tech-shape` already wrote `04-design-doc.md` and the architect writes its own `docs/specs/<feature>.md`. Either point the architect at the design doc so it inherits those decisions, or let it design fresh from the PRD as an independent check. `docs/adr/` is the shared tie-breaker either way: a spec honors an accepted ADR and supersedes it, never edits it.

**One UX spec, though.** Point the architect at `04-ux-spec.md` rather than letting it ask for a second one: the states a surface can reach were reviewed and possibly rewritten by the design owner at Gate 2, so re-deriving them from the PRD throws that review away. Outside the pipeline the architect has no UX spec to read, and for a brief touching UI it returns `needs-decision` asking you to run `ux-shaper` first. It cannot dispatch the agent itself, by design: orchestration stays with you.

## Scenario 2: a new feature in an existing product

Same pipeline, less of it. The only real difference is that stage 4 has a real codebase to read.

1. `claude-kit scout` in the repo, install what it suggests, plus `product-team` if the repo runs initiatives.
2. `/product-team:setup-strategy` **once**, if `docs/strategy/` does not exist yet. Skip it forever after.
3. Every feature is its own initiative: `/product-team:0-refine-idea` through `/product-team:7-push-to-board` on a fresh `docs/{slug}` branch.
4. Stage 4 reads the real code, cites `path:line` for every design claim, fits the existing patterns, and numbers new ADRs after the ones already in `docs/adr/`.
5. Engineering side is identical: one story, `/feature-team`, review, commit.

`docs/strategy/` and `docs/adr/` are shared across every initiative in the repo. Only `docs/initiatives/{slug}/` is per-feature.

## Scenario 3: one engineering task, no pipeline

Most work is this. A single seat, dispatched directly, no architect and no `/feature-team`.

> `/feature-team` earns its overhead when the work spans two or more seats or needs a spec first. Below that, it is a tax.

Ask for the seat by name in the conversation:

```
Dispatch backend:backend-staff-engineer with this brief:

Goal: add cursor pagination to GET /subscriptions, which currently returns every row.
Owns: src/routes/subscriptions.ts, src/services/subscription-list.ts, and their tests.
Acceptance:
  1. `?cursor=&limit=` with limit defaulting to 50 and capped at 200.
  2. Response carries `nextCursor`, null on the last page.
  3. Existing callers with no cursor param keep working unchanged.
Note: pre-authorized to add an index migration if the sort key needs one.
```

The name matters. A seat installed as a plugin is namespaced by the plugin, so the agent is `backend:backend-staff-engineer`, not `backend-staff-engineer`. `claude plugin list` shows the plugins (`backend@skills-dir`); the agent inside carries the prefix.

A brief that works has four parts, and they are the same four the architect emits per slice:

| Part | Why it matters |
|---|---|
| **Goal**, one sentence | The seat restates it back; a goal it cannot restate is a goal it will invent |
| **Owns**, explicit paths | One file, one owner. This is the whole collision story in a parallel wave, and it keeps a solo dispatch from wandering |
| **Acceptance**, numbered | It is what the seat self-verifies against, and what its report maps to line by line |
| **Note**, pre-authorizations | Schema changes, new dependencies, and backfills sit behind a seat's ask-first boundary. Say yes in the brief or it stops and asks |

What comes back is a **completion report**, not a chat reply: status (`done` / `blocked` / `needs-decision`), stack detected, changes per file, verification with real command output, decisions and rejected alternatives, pending ask-first items, and discovered gotchas. Read the Verification section. `not runtime-verified` is an honest answer and it means the check is yours.

Then `/code-review`, `/commit`.

Which seat owns what is the table in [README.md](README.md#staff-engineer-bench). Fourteen ship: analytics, backend, cloud, data, database, design, dx, frontend, gtm, mobile, platform, qa, security, sre. Two are not implementers:

- **`security:security-staff-engineer`** is read-only and advisory: threat models, dependency audits, authn/authz review. It never edits. For a pending diff use `/security-review` instead.
- **`architect`** designs and never implements.

## Scenario 4: an engineering task managed by the architect

Between Scenario 1 and Scenario 3. The work is real design work but there is no PRD behind it, or you want the spec without the automatic dispatch.

Dispatch the architect alone:

```
Dispatch the architect agent: design the migration from our session cookies to
short-lived JWTs with refresh rotation. Read src/auth/ and docs/adr/. I want the
spec and the owner split; do not dispatch anyone.
```

It returns a design report of about 40 lines pointing at `docs/specs/<feature>.md`, plus dispatch-ready briefs per seat. Three things to check before you act on it:

1. **Status.** `needs-decision` means it hit a foundational fork (an answer that would change the data model, the owner split, or the feature's meaning) and refused to write a speculative spec. Answer the fork and re-dispatch.
2. **Decision items.** Minor ambiguities it resolved itself, each with the recommendation and the default the spec was built on. This is where a wrong assumption is cheapest to catch.
3. **Contracts.** Every cross-slice interaction written verbatim in the project's own idiom. If two seats are going to build against it in parallel, this is the section that has to be right.

Then dispatch the briefs yourself, one seat per message for a serial build, or all the `Parallel: yes` ones in a single message to run them concurrently. You are doing by hand what step 6 of `/feature-team` does; the difference is only that you chose to hold the wheel.

The architect **cannot** dispatch: the Agent tool is disallowed in its frontmatter. That is the design, not a limitation to work around.

## Scenario 5: a bug fix

No pipeline, no architect, often no seat.

- One file, obvious cause: just fix it in the main conversation, then `/commit`.
- A Sentry issue: `/fix-sentry-issues`.
- Non-obvious cause, or a fix that spans a module: dispatch the owning seat with a Scenario 3 brief where the acceptance criterion is the failing behaviour.
- Missing or flaky tests around it: `qa:qa-staff-engineer` owns test infra and flake diagnosis, and never modifies application source (it reports product bugs back to you).

## Choosing the entry point

| Situation | Start with |
|---|---|
| An idea, no repo, no strategy | `/product-team:setup-strategy` |
| A strategy exists, a new idea arrives | `/product-team:0-refine-idea` |
| A PASS story on the board | `/feature-team "<story>"` |
| A clear feature spanning 2+ seats, no PRD | `/feature-team "<brief>"` |
| Design needed, dispatch not wanted | `architect` alone |
| One seat's worth of work | Dispatch that seat directly |
| The brief is fuzzy | `/grill-me` first, always |
| A diff needs review | `/code-review`, or `/security-review` for the security lens |
| A security assessment of the system, not a diff | `security:security-staff-engineer` |
| Context is running out mid-task | `/handoff` |

## Gotchas

**Plugins.** `--type` is required on `add`, `remove` and `list`; nothing is inferred from a name. A plugin needs workspace trust plus a relaunch before it loads. The plugin name is the discipline (`qa`), while the agent inside carries the namespace (`qa:qa-staff-engineer`); `claude-kit add` takes the former.

**`~/.claude` is owned by the registries.** `claude-kit add --global` on an artifact not tagged `global` is a scratch change: it survives until the next `claude-kit sync` and no longer. To make something durably global, tag it `global` in the registry. Removing a global link by hand is undone the same way.

**Worktrees.** A parallel wave runs in `.claude/worktrees/`, branched from committed HEAD. Uncommitted work in the feature's blast radius is invisible to it, so `/feature-team` checks `git status --porcelain` first and offers `/commit` or `--no-isolate`. This needs `worktree.baseRef: "head"` in [settings.json](settings.json), which is set. The `wt` fish helper is deliberately not wired in: its sibling worktrees fall outside the sandbox write root.

**One file, one owner.** If two dispatch briefs claim the same file, fix the split before dispatching. The worktree fences build side effects; it does not resolve two seats writing the same source file.

**Agents do not commit.** Not the seats, not the architect, not the product stages. If something needs to land in git, that is `/commit` and `/pr` in the main conversation.

**Gates block on `STATUS.md`.** A product stage refuses to run until its predecessor's row reads `approved`. If a PR was merged outside the session, the next stage reconciles it against GitHub itself; you do not hand-edit the file.

**Local mode.** A repo with no `origin` remote runs the whole product pipeline with no PR machinery: same stages, same artifacts, gate decisions recorded directly in `STATUS.md`, single branch. Stage 7 is the one that refuses, since it needs a real repo and Project number.

## Where each thing is defined

| Thing | File |
|---|---|
| The reference for all of this | [README.md](README.md) |
| Product pipeline mechanics (gates, branching, local mode, expedited path) | [plugins/product-team/skills/product-lead/references/conventions.md](plugins/product-team/skills/product-lead/references/conventions.md) |
| The engineering pipeline, step by step | [skills/feature-team/SKILL.md](skills/feature-team/SKILL.md) |
| The spec contract and the ADR rules | [agents/architect.md](agents/architect.md) |
| The UX spec contract (flows, surfaces, the state matrix) | [agents/ux-shaper.md](agents/ux-shaper.md), [plugins/product-team/skills/product-lead/references/templates/ux-spec.md](plugins/product-team/skills/product-lead/references/templates/ux-spec.md) |
| A seat's anatomy, boundaries and report contract | `plugins/<discipline>/agents/<discipline>-staff-engineer.md` |
| A seat's failure-mode checklists | `plugins/<discipline>/skills/<discipline>-failure-modes/` |
| `claude-kit` full reference and FAQ | [../scripts/claude-kit/README.md](../scripts/claude-kit/README.md) |
| Which artifacts are global, and the group vocabulary | [skill-registry.json](skill-registry.json), [agent-registry.json](agent-registry.json) |
