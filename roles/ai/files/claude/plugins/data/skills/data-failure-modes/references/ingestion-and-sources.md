# Ingestion and sources

When to read: the brief or diff touches new or changed sources, extraction logic, CDC, watermarks, or late or out-of-order data.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Source schema drift unhandled.** The source adds, renames, or retypes a column and the pipeline crashes, silently drops it, or maps it wrong.
  Check: behavior on unexpected columns and type changes is explicit (fail, quarantine, or additive accept), not whatever the parser happens to do.
- **Schema inferred from a sample.** Inference over the first batch locks in types the tail of the data violates: columns that go null, numerics that widen, mixed date formats.
  Check: schemas for landed data are declared, not inferred; where inference bootstrapped a schema, it is reviewed and pinned before consumers attach.
- **Late and out-of-order data dropped.** Windows close on wall-clock and events arriving after their window silently vanish.
  Check: a watermark or lateness policy exists and is stated: how late is accepted, and where later-than-that goes (reconciled, quarantined, or dropped with a metric); windowing and partitioning declare their time semantics (event time vs arrival time) and match what consumers expect.
- **CDC applied as inserts.** Change streams carry updates, deletes, and out-of-order commits; naive appends resurrect deleted rows and freeze stale values.
  Check: CDC handling applies operations by key in commit order (merge), deletes and tombstones propagate, and out-of-order commits are handled by the declared ordering column.
- **Duplicates at the edge.** Source retries, connector restarts, and overlapping extraction windows deliver the same record twice.
  Check: dedup at ingestion keys on a source-provided identity (primary key plus version, offset, file plus position), not on full-row equality hope.
- **Extraction window gaps and overlaps.** An incremental cursor on an updated-at column misses rows updated during the run, or double-reads boundary timestamps.
  Check: cursor boundaries are inclusive or exclusive by design, overlap deliberately with dedup, or use a strictly monotonic source column; the boundary case is tested.
- **Full re-pull where incremental was implied.** Re-extracting the whole source every run hammers the source system and hides the missing cursor design.
  Check: extraction is incremental where the source allows it; a full pull is a stated decision with source load and cost acknowledged (see cost-and-efficiency).
- **Credentials and sensitive fields at the edge.** New connectors are where credentials leak and sensitive fields first enter the platform.
  Check: credentials come from the project's secret mechanism, the landed fields are enumerated, and sensitive ones follow pii-and-retention.

## Escalation triggers (`needs-decision`)

- Adding a new external source or vendor connector (also an ask-first boundary in the agent).
- A source that cannot provide the identity or ordering correctness requires: propose the reconciliation, don't guess.
- A source system whose extraction load limits are unknown and the pull is heavy.

## What good looks like

- Landed data has a declared schema, a lateness policy, and a documented identity key.
- The pipeline notices source drift before consumers do.
- Reading the source twice is safe for both sides.
