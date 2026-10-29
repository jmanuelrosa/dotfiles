# Stacks

A **Stack** = source code + state + configuration. Independent unit of IaC management. One Stack per project root.

## Lifecycle mutations

| Operation | Mutation | Notes |
|---|---|---|
| Create | `stackCreate(input, manageState, stackObjectID?, slug?)` | `manageState` controls whether Spacelift owns the state file. `stackObjectID` only for handing existing state to Spacelift. |
| Create from blueprint | `blueprintCreateStack(id, input)` | Increasingly preferred path for repeatable provisioning. |
| Create from intent | `stackCreateFromIntent(project, importState?, stackName?)` | Promotes an `IntentProject` to a stack. |
| Update | `stackUpdate(id, input)` | Full input object - merge with current state via `query` first. |
| Delete | `stackDelete(id, destroyResources?)` | `destroyResources: true` runs a destroy plan first. **Destructive.** |
| Disable / enable | `stackDisable(id)` / `stackEnable(id)` | Disabled stacks can't create runs. |
| Lock / unlock | `stackLock(id, note)` / `stackUnlock(id)` | Mutual-exclusion lock for manual ops. |
| Reslug | `stackReslug(id)` | **Recreates Terraform resources** that reference this stack by ID. Avoid unless intentional. |
| Sync commit | `stackSyncCommit(id)` | Refresh `trackedCommit` from VCS - the tracked commit can drift behind silently. |
| Set commit | `stackSetCurrentCommit(id, sha)` | Pin the stack to a specific SHA. |

## Settings (via `stackUpdate`)

`StackInput` is large. Common fields: `name`, `description`, `branch`, `repository`, `provider`, `projectRoot`, `additionalProjectGlobs`, `runnerImage`, `terraformVersion`, `vendorConfig`, `space`, `labels`, `autodeploy`, `autoretry`, `protectFromDeletion`, `localPreviewEnabled`, `enableWellKnownSecretMasking`. Always run `discover { type: "type", name: "StackInput" }` for the current shape.

## Dependencies

Stacks can depend on each other to chain runs and pass outputs:

- `stackDependencyCreate(input)` - one dependency.
- `stackDependenciesCreateInBatch(input)` - multiple at once.
- `stackDependenciesAddReference(stackDependencyID, reference)` - wire output → input.
- `stackDependenciesUpdateReference` / `stackDependenciesDeleteReference`.
- `stackDependencyDelete(id)`.

Inspect via `stack.dependsOn`, `stack.isDependedOnBy`, `stack.dependenciesFullGraph` (transitive).

## Drift detection

Stacks have a `DriftDetectionIntegration` (one per stack):

- `stackIntegrationDriftDetectionCreate(stack, input)` - schedule + reconcile flag.
- `stackIntegrationDriftDetectionUpdate` / `Delete`.

`stack.isDrifted` and `stack.driftDetectedBy` (run ULID) report current state. Reconcile mode auto-applies; non-reconcile just reports.

## Scheduling

Three independent cron-shaped entities per stack:

| Entity | Mutation set | Purpose |
|---|---|---|
| `ScheduledRun` | `stackScheduledRunCreate/Update/Delete` | Trigger runs on schedule. |
| `ScheduledTask` | `stackScheduledTaskCreate/Update/Delete` | Run an ad-hoc command on schedule. |
| `ScheduledDelete` | `stackScheduledDeleteCreate/Update/Delete` | Delete the stack at a future time. |

Read via `stack.scheduledRuns`, `scheduledTasks`, `scheduledDeletes`.

## Vendor migration

`stackMigrateVendor(id, targetVendor, config)` - bidirectional Terraform ↔ native Terragrunt migration. Read the config schema via `discover` before invoking.

## Common queries

| Need | Query | Hint |
|---|---|---|
| Single stack | `stack(id)` | `id` is the slug |
| All stacks | `stacks` | No pagination - small accounts only. Otherwise use `searchStacks`. |
| Search with predicates | `searchStacks(input)` | See `api-discovery.md` for predicate DSL. |
| Suggestions / counts | `searchStacksSuggestions(input)` | Cheap aggregate access. |
| Recent runs | `stack(id) { runs(before: ID) { ... } }` | Connection paginated by `before` (cursor). |

## Pitfalls

- `stackReslug` recreates Terraform-provider resources that reference the stack by ID. Confirm twice.
- `manageState: false` on `stackCreate` means you must supply state externally; new users often miss this.
- After `stackUpdate`, runtime config changes apply to the **next** run, not retroactively.
- `protectFromDeletion: true` blocks `stackDelete` - flip it first if intentional.
