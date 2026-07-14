# Metric definitions and consumers

When to read: the brief or diff touches metric or KPI definitions, semantic-layer models, exposures, or renames or removes models or columns consumers read.
This file covers metric definitions and the downstream surfaces that consume them; contracts on pipeline outputs upstream of the warehouse belong to the data seat.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Metric re-derived ad hoc.** A dashboard, notebook, or one-off query recomputes a metric from raw tables instead of consuming the definition of record; the copies drift the day the definition changes.
  Check: metrics are consumed from the semantic layer or metrics model; any re-derivation in the diff is replaced with a reference to the source, or its persistence is escalated.
- **Silent redefinition.** Changing a filter, grain, or formula inside an existing metric quietly changes every number downstream while the metric name stays the same.
  Check: the change preserves the recorded definition; any change to meaning is a `needs-decision` carrying before and after values on recent periods.
- **Same name, different numbers.** Two surfaces show "revenue" computed two ways, and consumers reconcile by trusting whoever presented last.
  Check: search existing definitions before adding one; a new metric overlapping an existing name states how it differs, or extends the existing definition instead.
- **Invisible consumers assumed absent.** Declared exposures are a floor, not a census: scheduled reports, ad hoc queries, and BI layers bind to model and column names without telling you.
  Check: before renaming or removing anything, enumerate consumers (exposures, BI-as-code references, warehouse query history where available); finding none is not evidence of none, escalate anyway.
- **Breaking change disguised as additive.** Retyping a column, changing its unit or timezone, or repointing its upstream while the name survives; every consumer keeps working and every number is wrong.
  Check: existing columns keep name, type, and meaning; semantic changes ride a new column or model version with a deprecation path for the old one.
- **Consumption declared nowhere.** A dashboard or report the change introduces binds to models without a declared exposure, so the next rename breaks it invisibly.
  Check: new downstream consumers the change creates are declared in the project's exposure idiom.
- **Definition undocumented.** A metric ships with a formula but no stated grain, filters, or units, so every consumer guesses the edge cases differently.
  Check: new metric definitions state grain, filters, units, and what null or zero means.

## Escalation triggers (`needs-decision`)

- Redefining an existing metric of record, however small the change looks (also an ask-first boundary in the agent).
- Renaming or removing a model or column with declared exposures or unknown consumers (also an ask-first boundary in the agent).
- Two conflicting definitions already live in production: reconciling them is an owner decision; propose one with evidence.

## What good looks like

- Every metric has exactly one definition of record, and every surface consumes it from there.
- Evolution is additive; a redefinition is a scheduled, announced event with before and after numbers.
- The consumer list is enumerated before any breaking change, and exposures grow with each new consumer.
