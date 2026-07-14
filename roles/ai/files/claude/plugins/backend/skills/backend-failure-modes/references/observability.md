# Observability

When to read: always for new endpoints, jobs, and consumers; and whenever the brief or diff touches logging, metrics, tracing, alerts, or error tracking.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The invisible new path.** A new endpoint, job, or consumer without the RED signals its neighbors have (rate, errors, duration) fails silently until a user reports it.
  Check: the new path emits the same metrics, logs, and spans as the nearest comparable path, wired through the project's existing instrumentation, not a parallel one.
- **Broken trace continuity.** A trace that dies at a queue boundary or an outbound call makes the next incident undebuggable across services.
  Check: trace context propagates through outbound calls and into message headers, and async handlers resume the trace, matching how the project already propagates it.
- **Swallowed failures.** A catch block that logs and continues where the caller needed the failure converts errors into silent data corruption; log-and-rethrow at every layer produces one incident logged five times.
  Check: every catch either handles meaningfully or propagates; new failure paths reach the error tracker with enough context to act on.
- **Cardinality explosion.** A metric label holding user IDs, raw paths, or any unbounded value multiplies time series until the metrics backend degrades or drops data.
  Check: every new metric label has a small, closed value set; unbounded identifiers go in logs and traces, never labels.
- **Secrets and PII in telemetry.** Tokens, passwords, and personal data in logs or error-tracker context are a breach with excellent replication.
  Check: redaction covers every new log statement and error context; dump whole objects nowhere.
- **Renamed signal, orphaned alert.** Metrics, log lines, and label values have consumers you cannot see: dashboards, alerts, SLO burn rates, log-based billing.
  Check: renaming or removing any existing signal is a contract change; find its consumers or escalate.
- **Alert on cause, not symptom.** Alerts on internal mechanics (CPU, queue depth of an internal buffer) page people for non-problems and miss real user impact.
  Check: if the change adds a new critical failure mode, the alert that catches it measures user-facing symptoms (error rate, latency, freshness) against the SLO.
- **Log level noise.** Errors logged for expected conditions (validation failures, 404s) bury real incidents; INFO spam makes the log stream unreadable and expensive.
  Check: level reflects required action: ERROR pages someone, WARN needs eventual attention, INFO tells the story of a request.

## Escalation triggers (`needs-decision`)

- Removing or renaming any metric, log line, or label that existing dashboards or alerts may reference.
- Adding a new alert or changing thresholds someone else will be paged on.
- Instrumentation the brief calls for that the project has no pattern for yet.

## What good looks like

- Every question the next incident will ask ("when did it start, which tenant, which dependency") is answerable from existing signals.
- State transitions are logged as old-to-new with the actor, so the audit trail reconstructs itself.
- One event in production is one line in the logs, one span in the trace, and one increment in the metrics, correlated by IDs.
- Telemetry cost stays boring: bounded labels, sampled traces, leveled logs.
