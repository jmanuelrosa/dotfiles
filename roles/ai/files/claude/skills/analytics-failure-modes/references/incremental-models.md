# Incremental models

When to read: the brief or diff touches incremental materializations, uniqueness keys, lookback windows, full-refresh behavior, or schema changes on incremental models.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Wrong or missing uniqueness key.** An incremental merge without a key at the model's grain appends instead of updating; every rerun adds duplicates that inflate downstream metrics.
  Check: the incremental key is the model's declared grain and a uniqueness test asserts it; an append-only strategy states why duplicates cannot occur.
- **Incremental and full refresh disagree.** The incremental path filters, joins, or aggregates differently from the full build, so the numbers depend on which path last ran.
  Check: reason through both paths for the same input; where a dev target exists, build both and compare row counts and key aggregates.
- **Late-arriving data outside the window.** A lookback window shorter than real data latency silently drops or freezes late rows.
  Check: the window is justified against observed or stated latency, not copied from another model; narrowing a window is a data-loss decision, not a tuning knob.
- **Non-deterministic incremental filter.** A predicate keyed on wall-clock time or on the mutable state of another table makes reruns of the same period produce different slices.
  Check: the incremental predicate is deterministic for a given run and safe to rerun for the same period.
- **Schema change strategy unset.** Adding or removing a column on an incremental model without an explicit schema-change behavior either fails the next run or leaves history silently null.
  Check: the schema-change behavior is explicit, and history for new columns is backfilled or its absence stated to consumers.
- **Rebuilt history diverges.** A full refresh recomputes the past with today's logic and today's source state; if sources expire or definitions changed, the same table quietly rewrites history.
  Check: before any full refresh, state what history can change and whether consumers tolerate it; name the snapshots or archived sources where the past must not move.
- **Incremental path never verified.** Tests and CI exercise the full build while the incremental path only ever executes in production.
  Check: verification runs against an incrementally built target where one exists, or the report states the incremental path is production-only-verified.

## Escalation triggers (`needs-decision`)

- A divergence between the incremental and full-refresh paths that needs a full refresh to fix: the cost estimate rides with the proposal (significant-cost runs are an ask-first boundary in the agent).
- Changing the incremental key or grain of a model with history: it rewrites the past; propose the migration.
- Converting a large model between incremental and full-refresh materializations.

## What good looks like

- Rerunning any period produces the same rows: keys carry idempotency, windows cover real latency.
- Incremental is an optimization, not a fork: both paths produce identical numbers.
- Every full refresh is a priced, deliberate event with its history impact stated.
