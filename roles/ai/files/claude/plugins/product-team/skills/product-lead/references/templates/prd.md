---
initiative: "{slug}"
stage: 2-prd
status: draft
authors: ["{human}", "2-write-prd"]
date: "{YYYY-MM-DD}"
sources: ["00-brief.md", "01-research/summary.md"]
---

# PRD: {initiative name}

## Context & problem

<!-- Two short paragraphs max. Link 00-brief.md and the research summary; do not restate them. -->

## Goals & success metrics

<!-- Every metric needs all four columns. A baseline you do not have is written exactly as `UNKNOWN -> Open Question #n`; inventing one is the cardinal sin of this pipeline. Each row also names the requirement that makes it measurable, or says who measures it by hand: a target nothing in the build can report on is a target nobody will ever check. -->

| Metric | Definition | Baseline | Target | Measured by |
|---|---|---|---|---|
|  |  |  |  | R{#} \| manual ({who}) |

## Non-goals

<!-- Mandatory, minimum 3. What this initiative deliberately does not do, so scope arguments happen here and not in code review. -->

1.
2.
3.

## Target users

<!-- Only segments evidenced in 01-research/. A segment without research backing needs explicit human sign-off, recorded here. -->

## Capabilities

<!-- The durable names this initiative's requirements belong to, kebab-case, one per line. A capability outlives the initiative: it is the file its requirements are merged into at ship time (docs/specs/{capability}/spec.md), so name the lasting behaviour ("data-export") and never the project ("q3-export-work"). Every requirement below names one of these. -->

- {capability-name}

## Requirements

<!-- One block per requirement, numbered R1..Rn, and each one is a contract plus the scenarios that would fail if it broke.

The SHALL sentence is the obligation. The scenarios are how anyone tells whether it holds, and they are written HERE rather than in a story because a requirement and its test are one thought: split across two stages and three files, what happens is that the ceiling on a value, the survival of data through a restart, or the state a surface reaches when empty is agreed by nobody and implemented by nobody. Ids are stable (`R3.S2`) and are what stories, tasks and the DoR check all claim.

A constraint is a requirement. If a value is unbounded, if a field has no ceiling, if data must survive something the platform can do to it (eviction under storage pressure, a cold start, a revoked permission), that is a SHALL with a scenario, not a note in prose.

No implementation detail: that is stage 4's job. -->

### R{n}: {short name}

{The system} SHALL {observable obligation}.
Capability: {capability-name}

#### R{n}.S1

- **WHEN** {condition or input}
- **THEN** {observable outcome}

## User flows

<!-- Step-by-step happy path plus the failure paths that matter. Reference requirements by R#. -->

## Deferrals

<!-- A question this PRD deliberately does not answer, handed to a later artifact that will. Only forwards: the resolver must be an artifact that runs after this one (04-ux-spec.md, 04-design-doc.md, 05-tasks.md), because nothing upstream will run again to pick it up. The resolving artifact must mention the id and settle it, and pt.py check fails the initiative if it does not. Delete this section when there are none: an empty table reads as an unanswered question. -->

| id | Question | Resolved by |
|---|---|---|
| D1 |  | 04-design-doc.md |

## Open questions

<!-- Numbered, each with an owner. Unknown baselines from the metrics table land here. An open question differs from a deferral in who closes it: a deferral is closed by the next artifact, an open question by a person. -->

| # | Question | Owner | Status |
|---|---|---|---|
| 1 |  |  | open |

## Dependencies & risks

<!-- Teams, systems, decisions this depends on; risks with likelihood/impact one-liners. -->

## Red-team status

<!-- Filled after /product-team:3-red-team runs. -->

| Field | Value |
|---|---|
| Report | PENDING (03-red-team-report.md) |
| Blockers raised / resolved |  |
| Revision date |  |
