# Lakehouse schema and storage

When to read: the brief or diff touches lakehouse table schemas, partitioning, compaction, retention, time travel, or catalogs.
OLTP schemas and migrations belong to the database seat; this file covers analytical table formats and their storage layout.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **In-place breaking schema change.** Dropping, renaming, or retyping a column breaks readers mid-deploy, and in some formats corrupts time travel over the change.
  Check: evolution is additive (new nullable columns, widening the format supports); renames rely on the format's id-tracked column mapping, never drop-then-add; flags that relax schema validation (merge-schema, overwrite-schema) are deliberate; rename, retype, or drop on a consumed table escalates.
- **Partitioning that fights the queries.** Partitioning on high-cardinality or rarely-filtered columns yields a sea of tiny partitions and full scans anyway.
  Check: the partition scheme matches the dominant query filters and expected file sizes; high-cardinality keys use the format's clustering or bucketing instead.
- **Hand-derived partition values.** A partition column computed by the writer (a date string from a timestamp) with the wrong source column, format, or timezone buckets rows into the wrong partition: incorrect results, not failures.
  Check: partitioning uses the format's derived or hidden partitioning from the true source column; where a manual partition column is unavoidable, its derivation (source column, format, timezone) is asserted by a test.
- **Small-files explosion.** Frequent small writes (streaming sinks, per-run appends) accumulate thousands of files per partition until planning and metadata choke.
  Check: the write pattern states its file-size outcome, and compaction or optimize maintenance exists for tables written frequently.
- **Partition scheme as a casual choice.** Changing partitioning later means rewriting the table; picking it by habit locks the cost in.
  Check: new tables state why the partition scheme fits the read pattern; repartitioning an existing table is a costed decision that escalates at large-table scale, and old data stays in the old layout until rewritten, so plan for both layouts to coexist.
- **Overwrite semantics misunderstood.** Static vs dynamic partition overwrite confusion silently deletes partitions the run did not produce.
  Check: the overwrite mode is explicit, and the set of partitions a run may replace is exactly its logical window.
- **Snapshot cleanup breaks readers and rollback.** Vacuum or snapshot expiration removes files a long-running query, time-travel reader, or rollback still needs.
  Check: snapshot retention is deliberate and longer than the longest legitimate reader and the rollback window; destructive maintenance on shared tables escalates.
- **Time travel treated as backup.** Recovery plans lean on snapshot history while retention silently expires it.
  Check: recovery expectations and snapshot retention agree, and immutable raw remains the rebuild path of record.
- **Catalog and storage drift.** Tables written but not registered where readers look, registered with a stale schema, or registered in two catalogs that disagree.
  Check: the table is registered in the catalog of record, its schema there matches storage, and exactly one catalog owns it and enforces its access policy (grants do not port across catalogs).

## Escalation triggers (`needs-decision`)

- Schema changes to a table other pipelines or teams consume (also an ask-first boundary in the agent).
- Changing snapshot or data retention, or running destructive maintenance that shortens time travel (retention changes are also an ask-first boundary in the agent).
- Repartitioning or rewriting a large existing table: propose it for a human (executing the rewrite is a backfill, an ask-first boundary in the agent).

## What good looks like

- Schema evolution is boring: additive, catalog-synced, old and new readers both work.
- Partitioning matches how the table is read, and compaction keeps file sizes in the format's happy range.
- Retention, time travel, and recovery expectations tell one consistent story.
