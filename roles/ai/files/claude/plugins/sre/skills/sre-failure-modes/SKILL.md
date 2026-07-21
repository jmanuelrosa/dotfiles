---
name: sre-failure-modes
description: >-
  Failure-mode checklists for site reliability and observability implementation work, split by domain.
  Use when implementing or reviewing changes that touch SLOs and error budgets, alert rules,
  alert routing and on-call, dashboards as code, metrics and cardinality, tracing and logging config,
  telemetry pipelines, runbooks and automation, or incidents and postmortems.
  Read only the reference files whose triggers match the change.
---

# SRE failure modes

Checklists of the ways reliability and observability changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| SLI definitions, SLO targets and windows, error budgets, burn-rate math, SLO tooling configs | [references/slos-and-error-budgets.md](references/slos-and-error-budgets.md) |
| Alert rule expressions, thresholds, `for` durations, burn-rate alerts, recording rules | [references/alert-rules.md](references/alert-rules.md) |
| Routing trees, receivers, severity labels, inhibition rules, silences, escalation policies, on-call load | [references/alert-routing-and-oncall.md](references/alert-routing-and-oncall.md) |
| Dashboard JSON or jsonnet, panels, queries, template variables, dashboard provisioning | [references/dashboards-as-code.md](references/dashboards-as-code.md) |
| New or changed metrics, labels, histogram buckets, metric naming, anything about cardinality or metric cost | [references/metrics-and-cardinality.md](references/metrics-and-cardinality.md) |
| Trace sampling config, context propagation setup, structured log schema, PII scrubbing, retention settings | [references/tracing-and-logging.md](references/tracing-and-logging.md) |
| Collector or agent configs, exporters, receivers, processors, pipeline wiring, telemetry egress | [references/telemetry-pipelines.md](references/telemetry-pipelines.md) |
| Runbooks, operational docs, alert annotations, automation scripts replacing manual steps | [references/runbooks-and-automation.md](references/runbooks-and-automation.md) |
| Postmortems, incident timelines, severity classification, action items, on-call handoff docs | [references/incidents-and-postmortems.md](references/incidents-and-postmortems.md) |

Most real changes fire two or three rows (a typical SLO-and-alerting brief fires at least slos-and-error-budgets, alert-rules, and metrics-and-cardinality).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: monitoring-vendor- and tool-specific guidance belongs to the stack skills the caller has installed, not here.
