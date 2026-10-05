# Failure visibility

When to read: any new or changed resource, module, or environment; and whenever the brief or diff touches health checks, alarms, logging, or the monitoring of what you provision.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The unmonitored resource.** A new service, function, or queue without the health checks, alarms, and log sinks its neighbors carry fails silently in production.
  Check: the new resource wires the same monitoring, log destination, and health probe as the nearest comparable resource, not a parallel one.
- **The unreadable apply failure.** An apply that fails halfway with a cryptic provider error leaves the operator guessing.
  Check: failure output names the resource and the cause; the plan shows no unexplained destroy or replace; a partial apply is recoverable.
- **Context-free signals.** A metric or log with no identity cannot answer the incident's questions.
  Check: emitted signals answer what, why, when, and to whom: the resource, the environment, and an identifier that correlates the alarm, the log, and the trace.
- **Secrets and PII in telemetry.** Tokens or personal data in logs, alarms, or dashboards are a breach with long retention.
  Check: sensitive outputs are marked and redacted; nothing user-identifying flows into a log or metric label.
- **Alert config assumed, not handed off.** Provisioning the plumbing without the alert rule leaves a blind spot; owning the alert rule oversteps the seat.
  Check: the resource emits the signal, and the alert rule, threshold, and routing are a specified handoff to sre-staff-engineer, not this seat's edit.

## Escalation triggers (`needs-decision`)

- Adding or changing a monitoring, logging, or alerting integration others depend on.
- New alarms or thresholds someone else is paged on.
- Observability the brief needs that the environment has no pattern for yet.

## What good looks like

- Every resource is as observable as its neighbors the day it ships.
- Every question the next incident asks ("which resource, which environment, when did it start") is answerable from existing signals.
- The failure of an apply or a resource is loud, legible, and recoverable.
- The signal is emitted here; the alert that reads it is owned by SRE.
