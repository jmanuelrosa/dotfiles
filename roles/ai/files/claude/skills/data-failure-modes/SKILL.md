---
name: data-failure-modes
description: >-
  Failure-mode checklists for data pipeline implementation work, split by domain.
  Use when implementing or reviewing changes that touch pipeline idempotency and backfills,
  orchestration and scheduling, ingestion and sources, streaming at the pipeline level,
  lakehouse table schemas and storage, data contracts for pipeline outputs, quality gates,
  PII and retention in data movement, or pipeline cost and efficiency.
  Read only the reference files whose triggers match the change.
---

# Data failure modes

Checklists of the ways data pipeline changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Reruns, backfills, dedup keys, partition overwrites, anything keyed on time | [references/idempotency-and-replay.md](references/idempotency-and-replay.md) |
| DAG or asset dependencies, schedules, sensors, retries, catchup, run overlap, timezones | [references/orchestration-and-scheduling.md](references/orchestration-and-scheduling.md) |
| New or changed sources, extraction logic, CDC, watermarks, late or out-of-order data | [references/ingestion-and-sources.md](references/ingestion-and-sources.md) |
| Streaming jobs or pipeline-level consumers, offsets, checkpoints, reprocessing, lag | [references/streaming.md](references/streaming.md) |
| Lakehouse table schemas, partitioning, compaction, retention, time travel, catalogs | [references/lakehouse-schema-and-storage.md](references/lakehouse-schema-and-storage.md) |
| Pipeline output schemas, contract files, freshness or SLA declarations, output versioning | [references/contracts-and-consumers.md](references/contracts-and-consumers.md) |
| Expectations, quality checks, quarantine paths, validation steps, anomaly detection | [references/quality-gates.md](references/quality-gates.md) |
| Sensitive fields, new sinks for existing data, masking, retention, deletion | [references/pii-and-retention.md](references/pii-and-retention.md) |
| Full-refresh vs incremental choices, scan- or shuffle-heavy transforms, storage growth, backfill cost | [references/cost-and-efficiency.md](references/cost-and-efficiency.md) |

Most real changes fire two or three rows (a typical new-pipeline brief fires at least idempotency-and-replay, orchestration-and-scheduling, and quality-gates).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: orchestrator- and engine-specific guidance belongs to the stack skills the caller has installed, not here.
