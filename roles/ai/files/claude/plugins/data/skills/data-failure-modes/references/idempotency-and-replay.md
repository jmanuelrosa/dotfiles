# Idempotency and replay

When to read: the brief or diff touches reruns, backfills, dedup keys, partition overwrites, or anything keyed on time.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Wall-clock time where the logical date belongs.** `now()` or today inside a transform makes every rerun compute the current day; a backfill recomputes today's data for every historical window (the top idempotency rule in Airflow's own best-practices doc).
  Check: every time reference derives from the run's logical date or window parameter, never from the clock at execution time, and rerunnable steps carry no other non-determinism (unseeded random, unstable ordering).
- **Append without a dedup key.** A retried run appends its rows again, and the duplicates flow into every downstream aggregate.
  Check: writes are overwrite-by-partition, merge or upsert on a declared key, or carry a dedup step a named owner runs; a rerun of any task produces identical output.
- **Non-atomic partition writes.** A job that dies mid-write leaves partial files a consumer can read as a complete partition.
  Check: output lands in a staging location and commits atomically (table-format transaction, rename, atomic overwrite), never file-by-file into the live path.
- **Rerun consumes moved state.** A task that reads "whatever is in the inbox", or deletes its input when done, sees different input on the second run.
  Check: input selection is deterministic from the run's window, never "read the latest available", and source data survives the run (archive, never delete).
- **Overwrite wider than the window.** A partition overwrite whose predicate or mode can replace partitions the run did not produce silently deletes neighboring data.
  Check: the set of partitions a run may replace is exactly its logical window, dynamic-overwrite semantics are stated, and an empty extract never overwrites a populated partition.
- **Time-varying inputs replayed anachronistically.** Historical windows joined against current dimension tables, lookups, or feature flags produce output that never existed.
  Check: for each time-varying input, the replay semantics are stated (as-of join vs recompute-with-current); silently time-dependent lookups are flagged.
- **Partial backfill invisible.** A backfill that fails midway leaves a mix of old and new data with nothing recording which windows completed.
  Check: backfills run per window, idempotently and resumably; any window can be rerun without harm and progress is observable.
- **Side effects replayed.** A pipeline that sends notifications, calls external APIs, or triggers downstream systems re-fires them on every rerun and every backfilled window.
  Check: side effects are guarded by an idempotency key or explicitly excluded from replay and backfill paths.

## Escalation triggers (`needs-decision`)

- Scheduling any backfill or reprocessing: propose the exact command and window for a human (also an ask-first boundary in the agent).
- A rerun the brief requires whose output cannot be made deterministic (external API lookups, current-state joins).
- A sink that cannot support idempotent writes (no keys, no atomic overwrite): propose the dedup mechanism, don't hope.

## What good looks like

- Any run, rerun, or backfill window produces identical output for the same inputs.
- Time enters the pipeline exactly once, as the run's logical window.
- A backfill is boring: per-window, resumable, costed, and proposed to a human before anything executes.
