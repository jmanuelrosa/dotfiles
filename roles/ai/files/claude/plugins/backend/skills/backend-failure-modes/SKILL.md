---
name: backend-failure-modes
description: Failure-mode checklists for backend implementation work, split by domain. Use when implementing or reviewing backend changes that touch API contracts, schema migrations, queues and background jobs, cross-service calls, authn/authz, caching, telemetry, or query performance. Read only the reference files whose triggers match the change.
---

# Backend failure modes

Checklists of the ways backend changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Endpoint shape, request/response contracts, validation, status codes, versioning, OpenAPI/GraphQL/protobuf artifacts | [references/api-design.md](references/api-design.md) |
| Schema migrations, transactions, backfills, constraints, multi-step writes | [references/data-safety.md](references/data-safety.md) |
| Message consumers or producers, queues, topics, background jobs, schedulers, webhooks | [references/events-and-async.md](references/events-and-async.md) |
| Outbound HTTP/gRPC calls, service clients, gateway or LB config, health checks, connection pools, shutdown | [references/service-resilience.md](references/service-resilience.md) |
| Any new endpoint, permission checks, tokens or sessions, tenant scoping, user-supplied IDs | [references/authn-authz.md](references/authn-authz.md) |
| Adding or touching any cache layer, or mutating data that something else caches | [references/caching.md](references/caching.md) |
| Any new endpoint, job, or consumer; logging, metrics, tracing, alerts, error tracking | [references/observability.md](references/observability.md) |
| Queries, serialization of large collections, request-path IO, long-lived memory, anything labeled "slow" | [references/performance.md](references/performance.md) |

Most real changes fire two or three rows (a new endpoint fires at least api-design, authn-authz, and observability).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: framework- and library-specific guidance belongs to the stack skills the caller has installed, not here.
