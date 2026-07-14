# Metrics and cardinality

When to read: the brief or diff touches new or changed metrics, labels, histogram buckets, metric naming, or anything about cardinality or metric cost.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Unbounded label.** A label holding user IDs, request IDs, emails, or raw URLs multiplies time series without limit until the backend degrades, drops data, or bills accordingly.
  Check: every new label has a small, closed value set you can enumerate; unbounded identifiers belong in logs and traces, never in metric labels.
- **Cardinality multiplication nobody computed.** Labels multiply rather than add: 10 endpoints by 5 status codes by 20 pods is 1000 series for one metric, and each label looked innocent alone.
  Check: state the expected series count for each new or relabeled metric (values per label, multiplied) and compare it against the project's scale before shipping.
- **Wrong instrument type.** A gauge where a counter belongs loses increments between reads; a counter queried like a gauge cannot be rated; both corrupt the SLI math built on top later.
  Check: monotonically increasing quantities are counters, point-in-time states are gauges, distributions are histograms, and the type matches how the SLI or dashboard will query it.
- **Buckets that miss the boundary that matters.** Default histogram buckets rarely align with the SLO threshold, so the one number the SLO needs cannot be computed (see the SLO reference); a missing top catch-all bucket makes quantile math return NaN.
  Check: bucket boundaries include each threshold an SLO or alert compares against, the top bucket sits above the realistic tail or timeout with a catch-all present, and the bucket count stays small because every bucket is a full extra series per label combination.
- **Naming outside the convention.** A metric that ignores the project's naming idiom (unit suffixes, base units, namespace prefixes) is unfindable and gets re-created under another name.
  Check: new metric names follow the project's existing pattern, state their unit, and use base units consistently with their neighbors.
- **Redefined or recycled name.** Reusing an existing metric or recording rule name with a different meaning or label set silently corrupts every existing consumer.
  Check: search for the name first; a changed meaning or label set on an existing name is a contract change, so find its consumers or escalate.
- **Emission absorbed by this seat.** The fix for a missing or wrong metric often lives in application source, and that is the implementer seats' surface.
  Check: relabeling, recording rules, and scrape config are yours; emission changes in app code become a specified handoff (metric name, type, labels, buckets), not your edit.

## Escalation triggers (`needs-decision`)

- Removing or renaming a metric or label that dashboards, alerts, or SLOs may consume (also an ask-first boundary in the agent).
- A metric whose expected cardinality is large or unknown at the project's scale: that is a cost decision.
- Instrumentation changes inside application source beyond config and wiring (also an ask-first boundary in the agent): specify what to emit and hand it across.

## What good looks like

- Every metric's series count is boring and predictable; nobody discovers a cardinality bomb from the bill.
- The SLI queries the SLOs need are computable directly from the buckets and labels that exist.
- Names and labels follow one convention, so the next engineer finds the metric instead of duplicating it.
