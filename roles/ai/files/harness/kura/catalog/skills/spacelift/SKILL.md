---
name: spacelift
description: Use when working with Spacelift - managing stacks, runs, modules, policies, spaces, contexts, worker pools, blueprints, VCS/cloud integrations, role bindings, audit trail, scheduled runs/tasks; or managing actual infrastructure via intent (create/update/delete/refresh/import resources, intent projects). Wraps the spacelift-local MCP (discover/query/mutate/provider/intent tools). Trigger on terms - spacelift, stack, run, intent, IaC platform, GraphQL Spacelift API, infrastructure resource lifecycle, deploy, provision, tear down, OpenTofu, Terraform managed by Spacelift, Terragrunt, Pulumi.
---

# Spacelift

Procedural guide for the spacelift MCP. Two surfaces share one MCP - the Spacelift control plane (GraphQL: stacks, runs, policies, spaces, integrations) and Intent (lifecycle of actual cloud resources via OpenTofu providers). Most tasks touch both.

## Tool map

| Tool | Purpose |
|---|---|
| `discover` | Browse the GraphQL schema. Modes: `queries`, `mutations`, `type`. Always run **before** `query`/`mutate`. |
| `query` | Execute a read-only GraphQL operation. `select` uses GraphQL selection-set syntax. |
| `mutate` | Execute a GraphQL mutation. **Modifies state** - requires explicit confirmation (see below). |
| `provider` | Inspect OpenTofu providers + resource schemas. Modes: `search`, `describe`, `resources-describe`, `datasources-describe`. **Mandatory** before `intent create`/`update`/`import`. |
| `intent` | Manage real infrastructure: `create`, `update`, `delete`, `refresh`, `import`, `read`, `resume`, `status`. Supports `async=true`. |

## Decision tree

| User wants to... | Start with |
|---|---|
| Read/list/inspect Spacelift entities (stacks, runs, policies, ...) | `discover` → `query` |
| Modify a Spacelift entity (create/update/delete/attach) | `discover` → `mutate` (gated, see below) |
| Create/update real cloud infra (EC2, S3, GCS, ...) | `provider` → `intent` (gated, see below) |
| Import existing cloud infra into intent state | `provider search` → `intent import` |
| Detect drift on managed cloud infra | `intent refresh` |
| Trigger / confirm / discard a stack run | `mutate` with `runTrigger` / `runConfirm` / `runDiscard` |

## Reference selector

Load only the file that matches the question. **Do not preload references.**

| Question / task | Load |
|---|---|
| GraphQL syntax, pagination, search predicates, selection sets | `references/api-discovery.md` |
| Stack lifecycle, settings, dependencies, drift, scheduling, blueprints | `references/stacks.md` |
| Run state machine, plan/confirm/discard/apply, retry, cancel, tasks | `references/runs.md` |
| Policy types (10 of them), role bindings, spaces, attachment rules | `references/policies-spaces.md` |
| AWS/Azure/GCP integrations, VCS providers, contexts, worker pools | `references/integrations.md` |
| Creating an intent project, configElements, attaching policies/AWS/worker pool, exporting to IaC | `references/intent-projects.md` |
| `intent` operation mechanics: provider workflow, async polling, resume gating | `references/intent-operations.md` |
| About to mutate or delete? Read this every time | `references/mutations-safety.md` |

End-to-end recipes: `examples/01-read-only-audit.md`, `examples/02-stack-run-lifecycle.md`, `examples/03-intent-end-to-end.md`.

## Mandatory ordering rules

1. **Always `discover` before `query`/`mutate`.** Don't guess operation names or argument shapes.
2. **Always `provider resources-describe` before `intent create`/`update`/`import`.** Skipping causes "expected X arguments" errors. Provider schemas drift; do not cache across sessions.
3. **Always read `references/mutations-safety.md` before any `mutate` or `intent delete/update`.**

## Destructive-operation gate

Before any `mutate`, `intent create`, `intent update`, or `intent delete`:

1. **State the operation, target, and concrete diff** (current → proposed) in plain prose.
2. **For `intent delete`**: enumerate dependents first (use `searchIntentResources` or `provider resources-describe` linkage).
3. **Block on `YES` or `CONFIRM`** (case-insensitive). No other token confirms. No carryover from prior turns - each destructive call needs a fresh confirmation.

Read-only operations (`query`, `discover`, `provider search`/`describe`, `intent read`/`status`/`refresh`) need no confirmation.

## Async polling pattern (intent)

Some `intent` operations take 10-30 minutes. Use `async=true`, then poll with `intent status`:

- Backoff: 2s → 4s → 8s → 16s → 32s → cap at 60s.
- **Never re-dispatch** a slow operation - the worker is already running.
- If `status` returns `PENDING_REVIEW`, do not call `resume`. Wait for `READY_FOR_EXECUTION`, then `resume` after explicit human approval.

## Pitfalls catalog

Each is real and frequent. Apply the mitigation by default.

| Pitfall | Mitigation |
|---|---|
| User asks "how many X do I have?" - listing every entity is slow and pollutes context | Use `searchXxxSuggestions` with predicates and select `filteredCount` - returns the count without entities |
| Deleted context still attached to stacks - runs fail with missing env var | Before `contextDelete`, list `attachedStacks`; either detach or warn |
| Worker pool deleted while runs queued - orphaned runs | Drain workers (`workerDrainSet`), wait for queue to clear, then delete |
| `stackDelete(destroyResources: true)` runs a destroy plan - destroys real infra | Treat as the most destructive operation; require `CONFIRM` and enumerate dependents |
| `variables` passed as JSON-encoded string (`"{\"id\":\"x\"}"`) | Pass as a JSON object: `{"id": "x"}` |
| Calling `runConfirm` on a run not in `UNCONFIRMED` | Read `state` first; only `UNCONFIRMED` accepts confirm |
| `intent resume` on `PENDING_REVIEW` | Only resume when status is `READY_FOR_EXECUTION` |
| Stale provider schema → "expected X arguments" | Run `provider resources-describe` before each `intent create`/`update` |
| Async over-polling burns tokens / triggers rate limits | Exponential backoff capped at 60s; never re-dispatch |
| Selection-set bloat (`name description createdAt updatedAt ...`) | Request only fields you'll use this turn |
| Pagination forgotten - missing entries on accounts with >50 entities | Use `first`/`after` with `pageInfo.hasNextPage`; loop until exhausted or stop early |
| Mutations are not idempotent (slug collisions on `stackCreate`) | `query` for existence first; handle 409-shaped errors as "already exists" |
| Deprecated fields silently hidden by `discover` | Pass `includeDeprecated: true` only when truly needed |
| Tracked commit drifts behind remote silently | `stackSyncCommit` to refresh; do not assume `trackedCommit` is current |
| Treating `IntentProject` as separate from Spacelift entities | It has `space`, `workerPool`, `attachedPolicies` like a stack - use the same auth/policy mental model |

## Outside this skill

When concepts go beyond what's here (vendor-specific behaviors, billing edge cases, integration-test setups, custom blueprint authoring), consult `https://docs.spacelift.io/sitemap.xml` to find the relevant page, then `WebFetch`.
