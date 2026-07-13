# The paired failure-modes skill

When to read: authoring `<seat>-failure-modes/`.
The living exemplars are `backend-failure-modes/` and `platform-failure-modes/`.

## Shape

A thin-router `SKILL.md` (~40 lines) plus ~8 reference files of 40-55 lines each, one per domain.
The domains come from Step 4's confirmed answer, refined by the researcher reports.
The skill is `dependency_only: true` in the registry: it exists to be shipped with its agent, and browsing surfaces hide it.

## SKILL.md router

```markdown
---
name: <seat>-failure-modes
description: >-
  Failure-mode checklists for <discipline> work, split by domain.
  Use when implementing or reviewing changes that touch <the 8 domains, comma-run>.
  Read only the reference files whose triggers match the change.
---

# <Seat> failure modes

Checklists of the ways <discipline> changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| <triggers> | [references/<file>.md](references/<file>.md) |

Most real changes fire two or three rows (a typical <discipline> brief fires at least <two or three named files>).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: <tool-class>-specific guidance belongs to the stack skills the caller has installed, not here.
```

## Reference file template (exact)

```markdown
# <Domain title>

When to read: the brief or diff touches <triggers, matching the router row>.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **<Failure name>.** <How it breaks and what it costs, one or two sentences, present tense.>
  Check: <a verification you can actually perform against the diff; end with the fix direction when short>.

(8-10 items)

## Escalation triggers (`needs-decision`)

- <A condition that is a decision, not implementation> (also an ask-first boundary in the agent).

## What good looks like

- <3-4 bullets of the positive pattern, for calibration.>
```

## Content bar

Every item is a check against a diff, never a tutorial paragraph.
Failure names are bold, specific, and mechanism-first ("Cache key missing its inputs", not "Bad caching").
No arbitrary numeric gates ("80% coverage"); published standards are fine with the source named.
The "(also an ask-first boundary in the agent)" annotation appears only where literally true, at the boundary's exact breadth (see `coherence-rules.md`).
Advisor seats change the intro sentence pair and the escalation heading (see `advisor-adaptation.md`).
