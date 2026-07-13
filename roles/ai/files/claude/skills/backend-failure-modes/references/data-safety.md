# Data safety: migrations, transactions, backfills

When to read: the brief or diff touches schema migrations, transactions, backfills, constraint changes, or any multi-step write.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Locking migration.** Adding an index without `CONCURRENTLY` (Postgres) or an online algorithm (MySQL), changing a column type, or adding `NOT NULL` on a large table can take a full-table lock and stop production writes.
  Check: know the lock each DDL statement takes on this engine and version; anything that rewrites or locks a big table needs an online strategy or a `needs-decision`.
- **Deploy-order breakage.** During rollout, old code runs against the new schema and new code may run against the old one; a rename or drop in one step breaks one side.
  Check: expand-and-contract only: add the new column or table, dual-write, backfill, switch reads, and drop in a later change; never rename in place.
- **No down path.** A migration that cannot be reversed turns a bad deploy into an incident with no exit.
  Check: the down migration exists and actually restores the prior state; if irreversible by nature (data-destroying), that is an explicit `needs-decision`.
- **Monolithic backfill.** A single `UPDATE` over millions of rows locks, bloats, and replicates badly, and cannot resume after failure.
  Check: backfills run in bounded batches, are idempotent and resumable from a checkpoint, are throttled, and emit progress.
- **External calls inside a transaction.** An HTTP call or queue publish inside a DB transaction holds locks for the call's duration, and the commit-versus-publish pair is not atomic anyway: one can succeed while the other fails.
  Check: transactions contain only DB statements; coordinate side effects with an outbox or publish after commit with reconciliation.
- **Check-then-act race.** Reading to test uniqueness or a balance, then writing, is a duplicate or overdraft under concurrency.
  Check: enforce invariants with unique constraints, conditional updates, or row locks, and handle the violation path in code.
- **Retry duplicates state transitions.** A retried job or replayed message that re-executes a write charges twice or double-transitions state.
  Check: writes are idempotent via a key, upsert, or state-machine guard (`WHERE status = 'pending'`).
- **Precision and time traps.** Money in floats accumulates rounding errors; naive timestamps shift with server timezone.
  Check: money in integer minor units or decimal types; timestamps stored in UTC with timezone-aware columns.

## Escalation triggers (`needs-decision`)

- Any migration or backfill beyond what the brief explicitly asked for (also an ask-first boundary in the agent).
- Destructive or irreversible operations on real data, however wrapped.
- Changing constraint or cascade semantics that other code may rely on.

## What good looks like

- Every schema change is deployable in both directions relative to the running code.
- Invariants live in constraints, not in application-level hope.
- A backfill can be killed at any moment and rerun without harm.
