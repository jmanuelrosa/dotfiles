# Policies, spaces, role bindings

Three overlapping authorization models. Don't conflate them.

## Spaces

Hierarchical multi-tenant namespaces. Every Stack, Module, Context, IntentProject, Policy, Worker Pool, Integration belongs to exactly one space. Spaces inherit access from parents.

| Mutation | Purpose |
|---|---|
| `spaceCreate(input)` | New space. Subspace creation may be gated by `accountToggleAllowNonRootAdminSpaceCreation`. |
| `spaceUpdate(space, input)` | Rename, re-parent, change description. |
| `spaceDelete(space)` | Delete (must be empty). |

Query via `space(id)`, `spaces(input?)`. Inheritance is "nearest ancestor wins" - a policy in `root/staging` covers `root/staging/feature-x` automatically.

## Policy types (10)

OPA/Rego policies. Multiple of the same type can attach to one entity; each evaluates independently and results combine (typically: any deny wins).

| Type | Purpose | Attaches to |
|---|---|---|
| `LOGIN` | Allow/deny login, grant admin | Account-wide |
| `ACCESS` | Stack-level perms | Stacks (largely replaced by spaces) |
| `APPROVAL` | Who can approve runs, thresholds | Stacks / IntentProjects |
| `NOTIFICATION` | Route + filter notifications | Account-wide |
| `PLAN` | Feedback on Terraform changes during plan | Stacks |
| `PUSH` | Interpret git push/PR events (track / propose / ignore) | Stacks |
| `TRIGGER` | Which stacks trigger when a blocking run finishes | Stacks |
| `INTENT` | Control resource ops in IntentProjects | IntentProjects |
| `INITIALIZATION` | (deprecated) Block runs pre-execution | - |
| `TASK` | (deprecated) Block ad-hoc tasks | - |

Get the input schema for INTENT policies via `intentPolicyInputSchema` query.

## Policy mutations

| Operation | Mutation |
|---|---|
| Create | `policyCreatev2(input)` (preferred) or `policyCreate(...)` |
| Update | `policyUpdatev2(id, input)` |
| Delete | `policyDelete(id, force?)` |
| Attach to stack | `policyAttach(id, stack)` |
| Detach from stack | `policyDetach(id)` |
| Attach to intent project | `policyIntentProjectAttach(id, intentProject)` |
| Detach from intent project | `policyIntentProjectDetach(id)` |
| Simulate | `policySimulatev2(input)` returns Rego eval result |

Auto-attachment: add a label `autoattach:<label>` to a policy; it auto-binds to all stacks in the same space carrying that label. `autoattach:*` matches all.

## Role bindings (newer RBAC)

Three role-binding entity types coexist with policies. Bindings tie a user / group / API key to a role within a space or stack.

| Entity | Mutations |
|---|---|
| `UserRoleBinding` | `userRoleBindingCreate/Update/Delete/BatchCreate` |
| `UserGroupRoleBinding` | `userGroupRoleBindingCreate/Update/Delete/BatchCreate` |
| `ApiKeyRoleBinding` | `apiKeyRoleBindingCreate/Update/Delete/BatchCreate` |
| `StackRoleBinding` | `stackRoleBindingCreate/Update/Delete/BatchCreate` |

Roles are managed via `roleCreate(input)`, `roleUpdate(id, input)`, `roleDelete(id)`. Inspect via `roles`, `role(id)`.

## Three authz models - pick the right one

| Model | When to use |
|---|---|
| **Spaces** + `Space.accessLevel` | Standard org-shape RBAC: who-sees-what by space tree |
| **Role bindings** | Fine-grained per-stack or per-API-key permissions; capability-based |
| **Policies** (`ACCESS`, `LOGIN`, `APPROVAL`) | Programmable rules that depend on run-time state (e.g. only senior eng approves prod) |

A user's effective permission is the **union** of their space access and role bindings, gated by any deny from policies. Don't try to encode RBAC as policies if a role binding fits.

## Policy attachment introspection

- `Stack.attachedPolicies` - currently attached.
- `Stack.attachablePolicies` - candidates in the same space.
- `IntentProject.attachedPolicies` / `attachablePolicies` - same shape.
- `attachablePoliciesInSpace(id)` - candidates in a space.

## Pitfalls

- **`autoattach:` label changes** propagate without explicit attach calls. Don't be surprised.
- **Login policies are global** - they don't honor spaces.
- **Deprecated `ACCESS` policies** still work; don't introduce new ones - use spaces + role bindings.
- **Multiple matching policies of the same type** evaluate independently; combine semantics depend on policy type (read the docs page for that type).
- **Detach mutations take attachment IDs, not entity IDs.** `policyDetach(id)` wants the `PolicyStackAttachment.id`, not the policy ID. Same for `contextDetach`, `awsIntegrationDetach`, `azureIntegrationDetach`. Read `Stack.attachedPolicies { id }` to get the attachment ID first.
