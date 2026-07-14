---
name: database-failure-modes
description: >-
  Failure-mode checklists for database implementation work, split by domain.
  Use when implementing or reviewing changes that touch schema migrations and deploy ordering,
  locks and online DDL, indexes and query plans, constraints and integrity, column types and
  semantics, backfills and large tables, transactions and connection poolers, or ORM schema
  artifacts and drift. Read only the reference files whose triggers match the change.
---

# Database failure modes

Checklists of the ways database changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| New migrations, renames or drops, deploy sequencing, anything applied in more than one step | [references/migrations-and-deploy-ordering.md](references/migrations-and-deploy-ordering.md) |
| Any DDL against an existing table: index builds, column or default changes, type changes, constraint adds | [references/locks-and-online-ddl.md](references/locks-and-online-ddl.md) |
| New or changed indexes, query changes, plan evidence, anything labeled "slow" | [references/indexes-and-query-plans.md](references/indexes-and-query-plans.md) |
| Foreign keys, unique constraints, NOT NULL, checks, cascade rules, invariants enforced in app code | [references/constraints-and-integrity.md](references/constraints-and-integrity.md) |
| Column types chosen or changed, timestamps, money, text and charsets, IDs and sequences | [references/data-types-and-semantics.md](references/data-types-and-semantics.md) |
| Backfills, mass UPDATE or DELETE, moving data between columns or tables | [references/backfills-and-large-tables.md](references/backfills-and-large-tables.md) |
| Transaction wrapping of migrations, isolation assumptions, locking reads, connection poolers | [references/transactions-and-concurrency.md](references/transactions-and-concurrency.md) |
| ORM schema files, generated clients or types, migration state, multiple heads, drift | [references/schema-drift-and-artifacts.md](references/schema-drift-and-artifacts.md) |

Most real changes fire two or three rows (a typical schema-change brief fires at least migrations-and-deploy-ordering, locks-and-online-ddl, and schema-drift-and-artifacts).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are engine-agnostic on purpose: engine behavior is named only where the failure mode is engine-defined (transactional DDL, `CONCURRENTLY` semantics); ORM- and tool-specific guidance belongs to the stack skills the caller has installed, not here.
Transaction semantics and data safety inside application code belong to the backend seat's data-safety reference; lakehouse and analytical tables belong to the data seat: these files own OLTP DDL mechanics, migration ordering, lock behavior, and plan evidence.
