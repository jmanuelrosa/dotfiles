# Intent operations

Lifecycle operations on real cloud resources via the `intent` tool. Each operation goes through provider planning, policy evaluation, and state persistence.

## Operations

| Operation | Mutates state? | Args |
|---|---|---|
| `read` | No | `provider`, `provider_version`, `type`, `config` |
| `refresh` | Reads provider; updates Spacelift state | `resource_id` |
| `create` | Yes (gated) | `provider`, `provider_version`, `type`, `resource_id`, `config` |
| `update` | Yes (gated) | `resource_id`, `config` |
| `delete` | Yes (gated, **destructive**) | `resource_id` |
| `import` | Yes (registers existing infra) | `provider`, `provider_version`, `type`, `destination_id`, `import_id` |
| `resume` | Executes a deferred op | `operation_id` (only when status = `READY_FOR_EXECUTION`) |
| `status` | No | `operation_id` |

## Mandatory provider preflight

Before `create`, `update`, or `import`:

1. `provider search { query: "<name>" }` - confirm provider namespace and versions.
2. `provider resources-describe { provider, provider_version, type }` - get the **current** schema.
3. Build `config` strictly to that schema. Skipping this causes "expected X arguments" errors.

For data sources / `read`: `provider datasources-describe` instead of `resources-describe`.

Provider schemas drift between versions - **do not cache** schemas across sessions.

## Sync vs async

Default is sync: the call blocks until complete. Some ops take 10-30 minutes; use `async=true` to dispatch and poll.

```
intent create --async=true ... → returns operation_id
intent status operation_id     → poll
```

`async` is supported only for `create`, `update`, `delete`.

### Polling cadence

Exponential backoff: **2s → 4s → 8s → 16s → 32s → cap 60s**. Never re-dispatch a slow op - the worker is already running. Re-dispatch produces a duplicate operation.

If the polling window will exceed the conversation, save the `operation_id`; you can resume polling later.

## Status transitions

| Status | Meaning | Next |
|---|---|---|
| `RUNNING` / `IN_PROGRESS` | Worker executing | Poll `status` |
| `PENDING_REVIEW` | Paused for policy / human review | Approve via `intentResourceOperationReview` mutation; **do not call `resume` yet** |
| `READY_FOR_EXECUTION` | Approved, awaiting execute | `intent resume operation_id` (after explicit confirmation) |
| `COMPLETED` / `SUCCEEDED` | Done | Read the resource via `query` or `intent read` |
| `FAILED` | Worker error | Read errors; consider `refresh` to verify state |

Always inspect `searchIntentResourcesOperations` for full operation history when debugging.

## Resume - the most-mistaken call

`intent resume`:

- Valid **only** when `status == READY_FOR_EXECUTION`.
- Calling on `PENDING_REVIEW` returns an error and does nothing useful.
- Treat as a write op - go through the destructive-op gate before resuming.

## Import workflow

Importing existing cloud infra into project state:

1. `provider search` - confirm provider.
2. `provider resources-describe` - get expected `id` shape.
3. Look up the existing infra's natural ID (e.g. AWS S3 bucket name, EC2 instance ID).
4. `intent import` with:
   - `provider`, `provider_version`, `type`
   - `destination_id` - the name you want in state (e.g. `my-bucket`)
   - `import_id` - the provider-specific ID (e.g. the bucket name as it exists in AWS)
5. After import, `intent refresh` to populate state.

## Refresh & drift

`intent refresh resource_id` queries the provider for actual state and updates the project's stored state. Drift is reported in the operation summary. **Refresh doesn't change cloud state**, but the report tells you whether `update` is needed.

## Eject (un-manage)

Use the `intentResourceStateEject` mutation (not the `intent` tool) to drop a single resource from state without destroying it:

```
mutate intentResourceStateEject { intentProject, resourceID }
```

Real infra remains. Spacelift stops managing it.

## Reading from data sources

`intent read` uses provider **data sources** (read-only lookups). Schema via `provider datasources-describe`. Useful for "find the latest AMI" or "look up a VPC ID" before creating.

## Pitfalls

- **Skipping provider preflight** → "expected X arguments" - the #1 mistake.
- **Provider version drift** between sessions - re-describe.
- **`intent resume` on `PENDING_REVIEW`** → no-op error. Approve first.
- **Polling tighter than 2s** wastes calls; looser than exponential wastes wall time.
- **Re-dispatching a slow async op** doubles work; check `status` first.
- **Forgetting `intent refresh` after manual cloud changes** leaves Spacelift state stale; subsequent `update`s plan against bad state.
- **`intent delete` without enumerating dependents** - check `searchIntentResources` for resources that reference this one before deleting.
- **Async ops ID lifetime** - operation IDs persist across sessions; you can poll later.
