# Alert rules

When to read: the brief or diff touches alert rule expressions, thresholds, `for` durations, burn-rate alerts, or recording rules.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Paging on a cause, not a symptom.** CPU, queue depth, and restart counts page humans for states users never see, and sleep through user pain with novel causes.
  Check: every paging alert's expression measures user-visible impact (error ratio, latency percentile, freshness); cause signals demote to tickets or dashboard context.
- **Single static threshold on an SLO signal.** One threshold either fires too late on a fast burn or flaps for weeks on a slow one; both failure modes are real.
  Check: SLO-based paging uses multi-window multi-burn-rate pairs, each long window with a short companion around 1/12 of it (the Google SRE workbook's published rows: 1h/5m at 14.4x and 6h/30m at 6x page, 3d/6h at 1x tickets, with 24h/2h at 3x as the common fourth-window extension); page versus ticket follows burn speed, not a guessed severity.
- **Zero-duration trigger.** An alert with no `for` duration (or the stack's equivalent) fires on a single scrape blip and resolves before a human loads a dashboard.
  Check: every alert carries a deliberate duration matched to its urgency; a zero duration is justified in writing or removed.
- **Expression against a metric that may not exist.** A query referencing a metric or label nothing emits returns empty, and an empty result silently never fires.
  Check: every metric and label in the expression exists in the project's instrumentation or recording rules; absence of data has an explicit answer (an absent-data alert, or a written reason it is safe).
- **Aggregation that drops a label routing needs.** A sum without the right grouping loses the labels the routing tree, notification template, or histogram math needs (aggregating away `le` breaks every quantile downstream).
  Check: labels consumed downstream (route matchers, templates, runbook parameters, `le` in histogram math) survive the expression's aggregation.
- **Recording rule collision or convention drift.** Reusing an existing recording rule name silently redefines it for every consumer; naming outside the project's convention makes rules unfindable.
  Check: new recording rule names are unique in the rule set and follow the project's existing level:metric:operation convention.
- **Alert with no owner or runbook.** A page that arrives with no next step and no responsible team burns responder trust and gets ignored.
  Check: every alert carries the annotations and labels its neighbors carry: severity, owner or team, and a runbook link that resolves.
- **Rule that parses but was never exercised.** Syntax checks prove valid names, not semantics: they miss rating a gauge, wrong firing timing, and labels that never materialize.
  Check: rules pass the stack's linter or dry-run (promtool, pint, vendor validation); where rule unit-test tooling exists, the firing and non-firing cases are covered, including the pending-to-firing timing.

## Escalation triggers (`needs-decision`)

- Deleting or rewriting an existing alert (also an ask-first boundary in the agent).
- Promoting an alert to a page beyond what the brief or the SLO's alerting policy calls for: new paging load is a decision, not a default.
- A brief demanding a paging alert on a cause metric with no user-visible symptom to tie it to.

## What good looks like

- A responder woken by the page can tell from its name and annotations what users are experiencing and where the runbook is.
- Burn-rate pairs cover fast and slow burns, firing while budget remains rather than after it is gone.
- Rule files pass lint and unit tests in CI, so a broken expression is a red check, not a silent gap.
