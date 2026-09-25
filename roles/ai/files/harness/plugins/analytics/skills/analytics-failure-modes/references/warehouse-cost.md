# Warehouse cost

When to read: the brief or diff touches materialization choices, full refreshes, query cost, or the warehouse spend of a transformation or analysis.
This file prices transformation and analysis choices; pipeline compute and ingestion backfill cost belong to the data seat.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Full refresh as a habit.** Rebuilding a whole table every run where volume justified incremental; cost scales with history instead of with change.
  Check: the materialization matches volume and change rate; a full-refresh choice on a large model states its recurring scan cost and why incremental does not fit; executing a significant-cost build stays ask-first.
- **Unpruned scans.** Transformation and analysis queries reading whole tables to use a few columns or partitions: no partition filter, select-star through wide marts that BI surfaces read.
  Check: reads filter on the partition or cluster keys the tables declare and select only the needed columns; a full scan of a large table is justified or redesigned.
- **Cost invisible at decision time.** A materialization or refresh choice made without stating what it scans per run; the bill arrives as someone else's surprise.
  Check: the report states what each new or changed model scans per run, before anything expensive executes (significant-cost runs are an ask-first boundary in the agent).
- **Untagged spend.** New models ship without the owner or cost-attribution tags the project uses, so their spend can never be traced or challenged.
  Check: new models carry the project's ownership and cost-attribution metadata where that idiom exists.
- **Expensive intermediates recomputed.** The same heavy join or aggregation computed inside several models or several notebook cells.
  Check: expensive intermediates materialize once in the appropriate layer and are consumed from there, consistent with the project's layering.
- **View chains recomputed on every read.** A deep chain of non-materialized models makes each downstream query, and each dashboard viewer, recompute the whole chain at read time.
  Check: heavily reused or compute-heavy nodes in a view chain are materialized, and models feeding exposures or BI surfaces are materialized for read cost.
- **Development at production scale.** Iterating on a model against full production history when a limited slice would answer the question.
  Check: development runs use the project's dev-target or sampling idiom where one exists; full-history verification is a priced, stated step.
- **Freshness nobody reads.** A model refreshed hourly for a dashboard viewed weekly; cost buys latency nobody consumes.
  Check: refresh cadence traces to a stated consumer need; tightening cadence is a cost decision, not a default.

## Escalation triggers (`needs-decision`)

- Full-refresh builds or queries with significant warehouse cost: state the estimated scan and let a human run or approve it (also an ask-first boundary in the agent).
- A cost optimization that would change numbers, freshness, or history consumers rely on.
- Sustained cost growth that needs a materialization strategy change beyond the brief.

## What good looks like

- Cost scales with change, not history: incremental where volume justifies it, full refresh as a priced decision.
- Every expensive choice is stated at decision time, in the report, before anything runs.
- Development iteration is cheap by design; production-scale verification is deliberate.
