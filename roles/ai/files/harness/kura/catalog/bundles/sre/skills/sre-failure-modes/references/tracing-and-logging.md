# Tracing and logging

When to read: the brief or diff touches trace sampling config, context propagation setup, structured log schema, PII scrubbing, or retention settings.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Sampling that discards the evidence.** Uniform head sampling keeps a flat percentage of everything, which is that same percentage of the rare error traces the next incident needs.
  Check: the sampling strategy states what it keeps, and errors plus SLO-threshold-violating latency are kept preferentially (tail-based or rule-based), or the trade-off is written down.
- **Propagation config that cuts traces.** Mismatched propagation formats between services, or a propagator list missing the format a neighbor emits, ends every trace at that hop.
  Check: the propagation format matches what adjacent services and the collector expect end to end; where a dev stack exists, a synthetic request's trace survives the full path.
- **Schema drift in structured logs.** A renamed or retyped log field breaks the queries, alerts, and log-based metrics built on it, silently.
  Check: changes to log schema config preserve existing field names and types or their consumers are found; new fields follow the project's schema idiom.
- **PII and secrets in telemetry.** Tokens, emails, and personal data in spans, logs, or baggage are a breach with excellent replication and long retention.
  Check: scrubbing and redaction config covers every new attribute and field; nothing user-identifying flows into span attributes or baggage a third-party backend receives.
- **Retention set by default, not decision.** Default retention silently discards the data the postmortem needs, or hoards data at a cost and liability nobody approved.
  Check: retention for each signal is a stated choice matching incident and compliance needs; a change that shortens retention or discards data escalates.
- **Log level policy that pages or spams.** Config that promotes expected conditions to ERROR feeds false pages; DEBUG left on in production drowns the signal and multiplies cost.
  Check: level configuration matches the project's response contract (ERROR means someone acts), and production defaults are deliberate.
- **Instrumentation absorbed by this seat.** Adding spans, log statements, or context fields inside application source belongs to the implementer seats.
  Check: SDK configuration, processors, and scrubbers are yours; code-level emission becomes a specified handoff (span names, attributes, log fields), not your edit.

## Escalation triggers (`needs-decision`)

- Sampling, retention, or aggregation changes that discard data (also an ask-first boundary in the agent).
- Sending a new signal or attribute set to a third-party backend: a data-egress and privacy decision.
- Instrumentation changes inside application source beyond config and wiring (also an ask-first boundary in the agent).

## What good looks like

- The traces that exist are the ones incidents need: the errors, the slow requests, and a defensible sample of normal traffic.
- One user-visible event correlates across log line, span, and metric through shared IDs.
- Someone can state what each signal costs and when it is deleted, and both numbers were chosen on purpose.
