# Locks and online DDL

When to read: the brief or diff runs any DDL against an existing table: index builds, column or default changes, type changes, constraint adds.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Lock queue behind an ALTER.** Even an instant ALTER needs an exclusive lock; waiting behind one long-running query, it queues every later statement on the table, readers included: a full outage on a hot table.
  Check: every ALTER against a live table sets a lock acquisition timeout (`lock_timeout` on Postgres, the tool's equivalent elsewhere) with a retry plan, and the report states what the statement locks and what queues behind it.
- **Blocking index build.** A plain CREATE INDEX blocks writes for the whole build on Postgres, and on MySQL depends on which algorithm the version picks.
  Check: index builds on live tables use the engine's online path (`CONCURRENTLY` on Postgres, an online algorithm on MySQL); a blocking build is acceptable only with a stated size assumption.
- **Concurrent build caveats unhandled.** On Postgres, `CREATE INDEX CONCURRENTLY` cannot run inside a transaction, waits for every open transaction before finishing, and a failed build leaves an INVALID index that still taxes writes.
  Check: the migration disables its transaction wrapper for the concurrent build, and the runbook includes detecting and dropping an INVALID leftover before retrying.
- **Full-table rewrite hiding in a one-liner.** A column type change, or adding a column with a volatile default, rewrites the whole table under an exclusive lock on most engines; metadata-only paths exist but are engine- and version-specific.
  Check: establish whether each statement is metadata-only or a rewrite on the detected engine and version (on MySQL, assert the algorithm explicitly so it errors instead of silently copying); a rewrite of a large table takes the expand-backfill-contract path or escalates.
- **Constraint validation under lock.** Adding NOT NULL, CHECK, or a foreign key validates every existing row while holding a lock strong enough to block writes.
  Check: on engines that support it, add the constraint unvalidated first and validate in a separate step under the weaker lock; NOT NULL has no unvalidated form on Postgres and rides a validated check constraint instead (the constraints reference has the mechanics).
- **Replication lag from bulk DDL.** A table rewrite or large index build replicates as one burst: replicas lag, stale reads follow, and some replication setups stall replay entirely.
  Check: bulk DDL on replicated tables states its replication impact, and long operations are proposed to a human with a safe window.
- **Online tooling assumed but absent.** A plan that says "run it with gh-ost, pt-osc, or pgroll" fails if the project has no such tool wired in.
  Check: the migration works with the project's actual toolchain; if safe DDL genuinely requires an online schema-change tool the project lacks, escalate with the recommendation.

## Escalation triggers (`needs-decision`)

- Long-running index builds or rewriting DDL on large tables: propose the exact commands, batch sizes, and safe window for a human (also an ask-first boundary in the agent).
- DDL whose lock or replication impact cannot be established for the detected engine and version.
- Adopting an online schema-change tool the project does not already use (adding a dependency is also an ask-first boundary in the agent).

## What good looks like

- Every migration states what it locks, for how long, and what queues behind it.
- Index builds and validations take the engine's online path by default; blocking is a stated, sized exception.
- A lock timeout with a retry plan makes the worst case a failed migration, never a stalled application.
