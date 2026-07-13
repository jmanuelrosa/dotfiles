---
name: analytics-failure-modes
description: >-
  Failure-mode checklists for analytics engineering and data science work, split by domain.
  Use when implementing or reviewing changes that touch metric and semantic-layer definitions,
  transformation model layering, incremental models, warehouse SQL correctness, model tests
  and source freshness, experiment design and readouts, analysis notebooks, or warehouse cost.
  Read only the reference files whose triggers match the change.
---

# Analytics failure modes

Checklists of the ways analytics changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Metric or KPI definitions, semantic-layer models, exposures, renaming or removing models or columns consumers read | [references/metric-definitions-and-consumers.md](references/metric-definitions-and-consumers.md) |
| New models, logic moving between layers, staging/intermediate/mart boundaries, cross-model references | [references/transformation-layering.md](references/transformation-layering.md) |
| Incremental materializations, uniqueness keys, lookback windows, full-refresh behavior, schema changes on incremental models | [references/incremental-models.md](references/incremental-models.md) |
| Any non-trivial SQL: joins, aggregations, window functions, date or timezone logic, type casts | [references/sql-correctness.md](references/sql-correctness.md) |
| Model or source tests, test severity, source freshness, columns consumers depend on | [references/tests-and-freshness.md](references/tests-and-freshness.md) |
| Experiment design, launch or stop or extend decisions, readouts, significance claims | [references/experiments-and-readouts.md](references/experiments-and-readouts.md) |
| Analysis notebooks, ad hoc analyses, any conclusion a human will act on | [references/notebooks-and-reproducibility.md](references/notebooks-and-reproducibility.md) |
| Materialization choices, full refreshes, query cost, warehouse spend of a transformation | [references/warehouse-cost.md](references/warehouse-cost.md) |

Most real changes fire two or three rows (a typical model brief fires at least transformation-layering, sql-correctness, and tests-and-freshness).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: dbt-, warehouse-, and platform-specific guidance belongs to the stack skills the caller has installed, not here.
