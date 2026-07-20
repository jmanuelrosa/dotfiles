# Errors and observability

When to read: any new or changed pipeline, task, job, or consumer; and whenever the brief or diff touches error handling, logging, run alerting, or the error tracker.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The silent task failure.** A task that dies or degrades without reaching the error tracker is invisible until a consumer notices stale data.
  Check: operational failures (exceptions, timeouts, partial writes) reach the error tracker (Sentry) with enough context to act on, wired through the project's existing instrumentation, not a parallel one.
- **Context-free failures.** A stack trace with no run identity is unactionable.
  Check: error context answers what, why, when, and to whom: the DAG or job, the task, the logical run window, the upstream source, and a run or trace id that correlates logs, retries, and the tracked event.
- **Swallowed exceptions.** An `except` that logs and continues where downstream needed the failure turns an error into silent data corruption.
  Check: every handler either handles meaningfully or propagates; a retried step is idempotent; a poison record dead-letters rather than looping.
- **Data-quality failure mistaken for none.** A quality check that warns without failing the run lets bad data propagate. (See quality-gates.md.)
  Check: expectation failures fail the run and are distinguishable in the tracker from operational errors, so triage routes correctly.
- **Secrets and PII in telemetry.** Rows, tokens, and personal fields in logs or tracker context are a breach with excellent replication.
  Check: redaction covers every new log statement and error context; log identifiers and counts, never payloads.
- **Freshness invisible.** A pipeline that silently stops leaves consumers reading yesterday's data.
  Check: lag and freshness are observable; the alert that catches a stall measures user-facing freshness against the SLA. Alert-rule and telemetry-pipeline config is a handoff to sre-staff-engineer, not this seat's edit.

## Escalation triggers (`needs-decision`)

- Adding or changing the error tracker or alerting integration.
- New freshness or failure alerts, or thresholds someone else is paged on.
- Instrumentation the brief needs that the project has no pattern for yet.

## What good looks like

- Every question the next incident asks ("when did it start, which run, which source") is answerable from existing signals.
- One failed run is one tracked event, one set of logs, and one lag signal, correlated by run id.
- Operational errors and data-quality failures are told apart at a glance.
- Telemetry cost stays boring: bounded context, redacted payloads, leveled logs.
