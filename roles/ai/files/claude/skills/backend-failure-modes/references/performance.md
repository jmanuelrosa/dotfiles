# Performance

When to read: the brief or diff touches queries, serialization of large collections, request-path IO, long-lived process memory, or anything the brief labels "slow".

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **N+1 queries.** A query inside a loop, or a lazy relation touched during serialization, turns one request into hundreds of round trips; it is invisible on a dev dataset of ten rows.
  Check: read the ORM or query log for one request end to end; relations consumed by the response are batch-loaded, joined, or dataloader-ed.
- **Unbounded reads.** A query without a limit against a growing table, or filtering in application code what SQL could filter, works until the table does not fit the assumptions.
  Check: every list query has a bound; filtering, aggregation, and sorting happen in the database when the database can do them.
- **Missing or wrong index.** A new query pattern without a supporting index does sequential scans that an empty dev database will never reveal; a composite index in the wrong column order supports nothing.
  Check: run the query plan against realistic data volume; the index's column order matches the query's equality-then-range predicates; if no index is justified, say why in the report.
- **Deep offset pagination.** `OFFSET 100000` scans and discards 100000 rows on every page; latency grows linearly with page number.
  Check: deep or unbounded pagination uses keyset/cursor pagination on an indexed, unique ordering.
- **Sequential IO that could be parallel.** Awaiting three independent calls one after another adds their latencies; request latency is the sum of a chain that should be a fan-out.
  Check: independent reads in a request are issued concurrently; the critical path contains only genuinely dependent calls.
- **Over-fetching.** `SELECT *` for three fields, serializing entire aggregates for a summary view, or loading a full result set into memory for a count moves bytes nobody reads.
  Check: queries select what the code consumes; large exports and reports stream rather than buffer.
- **Blocking the worker.** Synchronous CPU work (compression, crypto, huge JSON, image processing) on the request path stalls the event loop or pins the thread pool, degrading every concurrent request, not just this one.
  Check: CPU-heavy work moves off the request path (job, worker pool) or is bounded and measured.
- **Accumulating memory.** Arrays, maps, or listeners that grow with traffic in a long-lived process are a slow-motion crash; so is buffering an unbounded upstream response.
  Check: everything that grows has a bound or a lifecycle; large payloads stream through, never fully materialize.
- **Optimizing on vibes.** A speedup with no baseline measurement is a complexity increase with a story attached; caches and micro-optimizations added speculatively rot into liabilities.
  Check: there is a before measurement (profile, query plan, benchmark) and an after measurement, and the report shows both.

## Escalation triggers (`needs-decision`)

- Performance work the brief requests without a measurable target or baseline.
- An optimization that changes semantics (staleness, ordering, precision) to gain speed.
- Capacity problems (the dependency is simply too slow or too small) masquerading as code problems.

## What good looks like

- Latency budgets are known per path, and the change's effect on them is measured, not guessed.
- The database does set operations; the application does business logic; neither does the other's job.
- Every optimization carries its evidence in the report and its regression guard in a check.
