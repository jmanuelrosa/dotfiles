# Intent projects

An **`IntentProject`** is a Spacelift entity that holds state and policy for cloud resources managed via the `intent` tool. It's the execution context - everything you do with `intent` happens inside one project.

It looks like a stack: has `space`, `workerPool`, `attachedPolicies`, `configElements`, `awsIntegrationIntentProjectAttachment`. Apply the same auth/policy mental model.

## Lifecycle mutations

| Operation | Mutation |
|---|---|
| Create | `intentProjectCreate(name, description?, space, workerPool?)` |
| Update | `intentProjectUpdate(id, name?, description?, space?)` |
| Delete | `intentProjectDelete(id, keepResources?)` - `keepResources: true` leaves cloud infra unmanaged but intact |
| Activate (caller) | `intentProjectActivate(id)` - marks as the caller's "active" project; `intent` ops use it implicitly |
| Disable (READ_ONLY) | `intentProjectDisable(id)` |
| Enable (READ_WRITE) | `intentProjectEnable(id)` |
| Unlock | `intentProjectUnlock(id)` - clears stale lock |

State (`IntentProject.state`): `READ_WRITE`, `READ_ONLY`, plus locking via `isLocked`, `lockedBy`, `lockedUntil`. Locks auto-expire.

## Configuration

`configElements` (env vars + file mounts) are project-scoped. Same shape as stack/context config.

| Operation | Mutation |
|---|---|
| Add | `intentProjectConfigAdd(project, config)` |
| Update | `intentProjectConfigUpdate(project, config)` |
| Delete | `intentProjectConfigDelete(project, config)` |

## Worker pool

Defaults to the public pool. Attach a private pool for isolation:

- `intentProjectAttachWorkerPool(intentProject, workerPool)`
- `intentProjectDetachWorkerPool(intentProject)`

## AWS integration

Attach an AWS integration with read/write scopes and a region:

- `awsIntegrationIntentProjectAttach(intentProject, integration, read, write, awsRegion)`
- `awsIntegrationIntentProjectDetach(intentProject, integration)`

Read via `IntentProject.awsIntegrationIntentProjectAttachment`. Multi-account / multi-region: attach the right integration with the right region per project.

## Policies (Intent type)

Attach `INTENT` policies to govern which resource operations are allowed:

- `policyIntentProjectAttach(id, intentProject)`
- `policyIntentProjectDetach(id)`

Discover the policy input schema once: `query intentPolicyInputSchema { }`.

`IntentProject.attachedPolicies`, `attachablePolicies` for inspection.

## Resources & dependencies

The actual resources managed by a project:

- Search: `searchIntentResources(input)` - same predicate DSL as stacks. Or via `IntentProject.searchIntentResources`.
- Operations history: `searchIntentResourcesOperations(input)`.
- Suggestions / counts: `searchIntentResourcesSuggestions`, `searchIntentResourcesOperationsSuggestions`.
- Resource dependencies (between resources within the project):
  - `intentResourceDependencyAdd(intentProject, fromResourceID, toResourceID, dependencyType, explanation?, fieldMappings?)`
  - `intentResourceDependencyRemove(intentProject, fromResourceID, toResourceID)`
  - **Pattern**: register dependency edges immediately after each resource create, not as a batch at the end.

## Operation reviews

Resource operations may pause for policy review (`PENDING_REVIEW`) before execution:

- `intentResourceOperationReview(intentProject, operationID, decision, note?)` - `decision`: `APPROVE` / `REJECT`.
- After approval, the op moves to `READY_FOR_EXECUTION` and `intent resume` becomes valid.

## Eject / unmanage

Remove a single resource from project state without destroying real infrastructure:

- `intentResourceStateEject(intentProject, resourceID)` - resource still exists in the cloud, but the project no longer manages it.

## Intent → IaC (export)

Two paths to turn intent state into committed IaC:

| Path | Result |
|---|---|
| `IntentProject.hcl(page, pageSize)` query | Returns HCL representation of all resources, paginated. Read-only - copy out, commit yourself. |
| `stackCreateFromIntent(project, importState?, stackName?)` mutation | Creates a Spacelift Stack backed by the project's resources. With `importState: true` the new stack inherits the existing state. |

Use `hcl` when you want to put the Terraform in a repo. Use `stackCreateFromIntent` when you want Spacelift to keep managing it as a stack going forward.

## Common queries

| Need | Query |
|---|---|
| Single project | `intentProject(id)` |
| All projects | `intentProjects` |
| Search | `searchIntentProjects(input)` |
| Counts / facets | `searchIntentProjectsSuggestions(input)` |
| Caller's active project | `intentProjectActive` |
| Conversations | `intentChatConversations(page, perPage, search?)` (history of MCP-driven sessions) |

## Pitfalls

- **`intentProjectDelete` without `keepResources`** destroys real infrastructure. Always confirm twice.
- **Forgetting `intentProjectActivate`** - subsequent `intent` calls operate on whichever project the caller has activated. If unsure, query `intentProjectActive`.
- **Stale locks** can persist if a session crashes; `intentProjectUnlock` clears them, but coordinate with anyone else who might hold it.
- **State is `READ_ONLY`** when disabled. `intent` operations will fail until `intentProjectEnable` is called.
- **Worker pool changes don't migrate in-flight ops** - finish current operations before swapping pools.
- **`stackCreateFromIntent(importState: false)`** creates the stack with empty state - the next run will plan from scratch and may **recreate or destroy resources**. Use `importState: true` unless you specifically want a fresh slate.
