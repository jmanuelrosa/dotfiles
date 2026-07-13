# Indexes and query plans

When to read: the brief or diff adds or changes indexes, changes queries, or claims anything about query performance.
The general performance method belongs to the performance-optimization skill and request-path behavior to the backend seat; this file covers plan evidence for the queries and indexes in the diff.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Plan evidence from an empty table.** EXPLAIN over ten local rows proves nothing: the planner picks plans it would never pick at production cardinality.
  Check: capture plans on realistic data volume and distribution (seeded or generated), with statistics refreshed (ANALYZE or the engine's equivalent) before measuring.
- **Index defeated by expression or type.** A function or expression wrapped around the indexed column, or a comparison against a value of a different type (implicit cast), silently disqualifies the index.
  Check: predicates match the indexed expression exactly and compare same-typed values; where the query must wrap the column, the index is an expression index on that same expression.
- **Composite order wrong.** A composite index whose column order ignores how the query filters and sorts supports neither the filter nor the sort.
  Check: leading columns carry the equality predicates, range and sort columns follow, and the captured plan confirms the index is chosen.
- **Write amplification unpriced.** Every index taxes every write on the table and competes for cache; a redundant one costs without paying.
  Check: before adding, look for an existing index already serving the pattern via a leftmost prefix; name the write cost in the report, and propose removal of indexes the change makes redundant.
- **Selectivity mismatch.** An index on a low-cardinality column alone rarely changes the plan; skewed access wants partial, filtered, or covering shapes where the engine supports them.
  Check: the index shape matches the measured selectivity of the access pattern, not the column list of the query.
- **Neighboring plans regressed.** A new or swapped index changes the planner's choices for other queries on the same table.
  Check: identify the table's other query call sites; for a swap, verify the replacement serves everything the removed index served.
- **Partition or shard key missing.** In a partitioned or sharded schema, a query without the distribution key in its predicate hits every partition or shard instead of one.
  Check: queries against partitioned or sharded tables carry the partition or shard key, or the scatter is deliberate and stated; DDL on such tables notes the per-shard orchestration in the handoff.
- **Data-trained index built before its data.** Some index types train on existing rows at build time (IVFFlat vector indexes among them); built in a schema migration on an empty table, its clusters train on nothing and recall collapses once data loads.
  Check: indexes that learn from data ship as a post-load step with a stated rebuild trigger, never inside the schema migration.
- **Faster asserted, not measured.** A performance claim without before and after evidence is a story.
  Check: the report shows the before plan, the after plan, and the realistic-volume caveat; if the claim cannot be measured locally, say so and hand the human the exact query to verify.

## Escalation triggers (`needs-decision`)

- A query rewrite that changes result semantics (ordering, duplicates, null handling) to gain speed.
- An index the plan evidence does not justify, or one the brief demands against the evidence.
- Dropping an index on a table other services query (also an ask-first boundary in the agent).

## What good looks like

- Every index in the diff traces to a named query and a plan on realistic volume, write cost acknowledged.
- Claims of faster carry both plans and their numbers.
- The index set stays minimal: nothing redundant, nothing unexplained.
