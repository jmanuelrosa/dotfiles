# SQL correctness

When to read: the brief or diff contains any non-trivial SQL: joins, aggregations, window functions, date or timezone logic, type casts.
This file targets warehouse transformation and analysis queries; OLTP query correctness against application databases belongs to the database seat.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Fan-out join.** A join whose other side is not unique on the join key duplicates rows silently; every downstream sum and count inflates.
  Check: state each join's expected cardinality; verify row counts before and after every join that could change the grain, and aggregate or dedupe deliberately where fan-out is intended.
- **NULLs silently excluded.** Inner joins drop unmatched rows, aggregates skip nulls, and `NOT IN` against a set containing null matches nothing; totals shrink without an error.
  Check: for each join and aggregate, state what happens to unmatched and null rows and confirm that is the metric's intended semantics; where absence matters, use outer joins with explicit handling.
- **Timezone and date-boundary drift.** Truncating timestamps in the wrong timezone shifts events across day boundaries; daily metrics disagree with the source system by exactly the boundary traffic.
  Check: the timezone of every truncation and date comparison is explicit and matches the metric's definition; behavior at midnight and DST transitions is considered where it matters.
- **Window frame defaults.** An unpartitioned window, or the default frame with ordering ties, computes something other than the running or ranked value intended.
  Check: window functions state partition, order, and frame explicitly wherever the default is not provably right; tie behavior is considered for range-based frames.
- **Silent type coercion.** Implicit casts between strings, numbers, and dates compare lexically or truncate; filters pass rows they should drop.
  Check: comparisons happen between matching types; casts are explicit and state their format and failure behavior.
- **Integer and zero division.** Integer division truncates (a rate below one becomes zero); a zero denominator errors or yields null depending on the engine.
  Check: ratios cast to a non-integer type explicitly, and zero denominators have a stated result.
- **Counting the wrong entity.** `COUNT(*)` where distinct entities were meant, or a sum over rows fanned out upstream, presents duplication as growth.
  Check: each count and sum states the entity it measures, and distinctness matches the grain of its input at that point in the query.
- **Average of ratios.** A rate or ratio computed by averaging pre-aggregated rows instead of dividing summed numerator by summed denominator; the number shifts with the grouping, and a sliced view quietly changes the denominator population.
  Check: ratios recompute from base measures at the readout's grain; non-additive measures (ratios, distinct counts) are never summed or averaged across groups, and sliced metrics state their denominator.
- **Ambiguous column binding.** An unqualified column in a multi-table query binds to whichever table the engine resolves, then breaks or silently rebinds when an upstream adds a same-named column.
  Check: every column in a query touching more than one table is qualified (a SQL linter mechanizes this where installed).
- **Filter placement flips the join.** A null-rejecting condition on the nullable side placed in `WHERE` instead of the join's `ON` clause silently converts an outer join to inner.
  Check: conditions on the nullable side of outer joins live in the `ON` clause, or the conversion to inner is intended and stated.

## Escalation triggers (`needs-decision`)

- A correctness fix that changes historical numbers consumers have already seen: the fix is right, the rollout is a decision.
- Semantics the definition of record leaves ambiguous (which timezone, which rounding, which dedupe): propose, never pick silently.
- An upstream data defect the SQL could paper over: patching downstream hides it; hand it to the owning seat.

## What good looks like

- Every join states its cardinality and every aggregate its entity; row counts are verified, not assumed.
- Null, timezone, and type behavior is explicit enough that a reviewer needs no engine manual.
- The query reads as the metric's definition, not as a clever reconstruction of it.
