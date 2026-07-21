# Cost and efficiency

When to read: the brief or diff touches full-refresh vs incremental choices, scan- or shuffle-heavy transforms, storage growth, or backfill cost.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Full refresh as a default.** Rebuilding the whole table every run where incremental was implied; cost scales with history instead of with change.
  Check: processing is incremental where volume justifies it; a full refresh states its cost and why incremental does not fit.
- **Backfill cost unestimated.** A backfill over months of partitions proposed without a size estimate; the bill and the cluster contention arrive later.
  Check: backfill proposals state window count, data volume, and expected compute, and that estimate rides with the exact command handed to a human.
- **Scan-heavy reads.** Transforms that read whole tables to use a few columns or partitions: no partition filter, select-star over wide tables.
  Check: reads are pruned by partition or cluster keys and select only needed columns; a full scan of a large table is justified or redesigned.
- **Recompute instead of reuse.** The same expensive intermediate computed by several pipelines, or several times within one run.
  Check: expensive intermediates are materialized once and shared, consistent with the project's layering.
- **Skew and stragglers.** One hot key holds a shuffle hostage; the job costs one straggler times the whole cluster.
  Check: known skewed keys get a stated strategy (salting, broadcast, split), and heavy transforms are checked for straggler patterns when touched.
- **Storage growth unbounded.** Every run adds snapshots, staging files, logs, and quarantine rows, and nothing expires.
  Check: staging and intermediate locations have cleanup, snapshot retention is set (see lakehouse-schema-and-storage), and growth is estimated for new high-frequency outputs.
- **Resources sized by copy-paste.** Cluster or task resources copied from the biggest existing job, so every small pipeline pays big-job rates.
  Check: resource requests reflect the job's measured or estimated need, not the template it was copied from.
- **Freshness beyond need.** An output refreshed far more often than any consumer reads it; cost buys latency nobody consumes.
  Check: refresh cadence traces to a stated consumer need (the contract's freshness), not to "more often is safer".

## Escalation triggers (`needs-decision`)

- Scheduling a backfill: the cost estimate rides with the exact command and window proposed for a human (also an ask-first boundary in the agent).
- A cost-motivated change that would loosen freshness or drop history consumers may rely on.
- Sustained growth in volume or lag that needs bigger infrastructure rather than better code.

## What good looks like

- Cost scales with change, not with history: incremental by default, full refresh as a decision.
- Every backfill proposal reads like a quote: windows, volume, compute, and the exact command.
- Storage and freshness both trace to stated needs, and the estimate is in the report before anything runs.
