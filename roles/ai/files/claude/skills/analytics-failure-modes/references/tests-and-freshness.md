# Tests and freshness

When to read: the brief or diff touches model or source tests, test severity, source freshness declarations, or columns consumers depend on.
This file covers tests on transformation models; quality gates inside ingestion pipelines belong to the data seat.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Untested grain.** A model without uniqueness and not-null tests on its grain lets fan-out and merge bugs arrive silently as duplicate rows.
  Check: every new or touched model tests uniqueness and not-null on its declared grain.
- **Enum drift unhandled.** Status and category columns accept new upstream values; downstream conditional logic silently buckets them as null or other.
  Check: enum-like columns carry accepted-values tests, and conditional logic handles the unexpected-value branch deliberately.
- **Warn-only theater.** Tests set to warn never fail a build; a broken invariant scrolls past in logs while the build stays green.
  Check: tests on invariants consumers depend on fail the build; any warn severity states why propagation is acceptable.
- **Decorative coverage.** A not-null test on an id stands guard while the measures, timestamps, and join columns dashboards aggregate go unvalidated.
  Check: the columns consumers depend on (keys, join columns, measures, timestamps) carry model tests matching what downstream assumes about them.
- **Referential drift untested.** Foreign keys to dimensions go unasserted; fact rows silently lose their match and drop out of joined reports.
  Check: relationship tests exist on the joins marts rely on, or the gap is flagged in the report.
- **Freshness promised nowhere.** Consumers assume the mart is current; when an upstream stalls, stale numbers present as real ones.
  Check: sources carry freshness declarations where an SLA exists, with thresholds traced to a consumer need, not a guess.
- **Threshold widened to green.** A failing test "fixed" by loosening its threshold, downgrading severity, or shrinking its scope, with no evidence the data legitimately changed.
  Check: any loosening carries evidence of a legitimate data change; weakening a failing test to get green is a never boundary in the agent, so even a justified recalibration escalates instead.

## Escalation triggers (`needs-decision`)

- Removing a test or loosening its threshold or severity (also an ask-first boundary in the agent).
- Declaring a freshness SLA the current schedule and upstreams cannot meet.
- A test the brief demands that would fail on data conditions outside this layer's control.

## What good looks like

- Coverage follows what consumers depend on: grain, keys, measures, enums, and the joins between them.
- A red test stops the build, and green means the invariants consumers rely on actually held.
- Freshness declarations trace to stated needs and are checked, not hoped.
