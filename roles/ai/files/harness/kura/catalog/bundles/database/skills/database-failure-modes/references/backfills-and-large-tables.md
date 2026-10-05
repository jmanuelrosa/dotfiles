# Backfills and large tables

When to read: the brief or diff backfills data, runs a mass UPDATE or DELETE, or moves data between columns or tables.
This seat authors the backfill and its runbook; executing against anything non-disposable is always a human's job.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **One giant transaction.** A single statement over millions of rows holds locks for its whole duration, bloats the table and its indexes (Postgres) or piles up undo (InnoDB), stalls replication, and cannot resume after failure.
  Check: the backfill runs in bounded batches ordered by an indexed key, committing per batch; any index the batch predicate needs ships in an earlier migration, or every batch scans.
- **Not idempotent, not resumable.** A backfill that dies mid-way and cannot tell where it stopped either re-processes or skips rows.
  Check: re-running any batch is harmless, and progress is derivable from the data itself (a predicate like `WHERE new_col IS NULL`) or an explicit checkpoint.
- **No throttle, no abort path.** A backfill saturating IO competes with production traffic and lags replicas; one that cannot be stopped safely turns a bad assumption into an incident.
  Check: the runbook includes pacing between batches, a progress signal a human can watch, and an abort procedure that leaves the data consistent.
- **Racing live writes.** Rows written after the backfill starts miss the transformation unless new writes are already correct.
  Check: the deploy ordering puts dual-writes (or the new write path) live before the backfill starts, with their extra write cost named, and cutover verifies zero remaining untransformed rows.
- **Backfill inside the DDL migration.** Bundling data work into the schema migration holds the DDL's locks until the data work commits, and collides with the migration tool's transaction and timeout assumptions.
  Check: data moves live in a separate, explicitly managed step (script or data migration), never inline in the DDL migration.
- **Mass delete with an unverified predicate.** A wrong WHERE clause is discovered by the rows it deletes; even a correct one leaves bloat behind.
  Check: the runbook counts and samples affected rows before running, states the expected count, and names the vacuum or maintenance follow-up for large deletes.
- **Handed off as an intention.** "Then backfill the column" is not a plan a human can execute.
  Check: the handoff contains exact commands or a script invocation, batch size, expected total, the basis for the duration estimate, a safe window, and the abort procedure.

## Escalation triggers (`needs-decision`)

- Every backfill or mass data change ships as a plan for a human; approval authorizes the files and the runbook, never running anything against a non-disposable environment (also an ask-first boundary in the agent).
- Backfills touching tables other services write to (also an ask-first boundary in the agent).
- A brief that demands the backfill inline in the migration against these checks.

## What good looks like

- New writes are correct before the backfill starts; the backfill only heals history.
- The handoff reads like a runbook: exact commands, expected counts, safe window, abort path.
- Killed at any moment, rerun without harm, no lock held longer than one batch.
