# Destructive operation safety

Read this **every time** before any `mutate`, `intent create`, `intent update`, `intent delete`, `intent import`, or `intent resume`.

## The protocol

### 1. State the operation in plain prose

Format: `<verb> <resource type> <name/id> in <space/project> with <key change>`.

Examples:
- "Create stack `prod-web` in space `production` with branch `main`."
- "Update intent project `data-platform` to attach worker pool `wp-isolated`."
- "Delete intent resource `aws_s3_bucket.user-uploads` in project `staging-app`."

### 2. Show the concrete diff

For `update`/`mutate`: read current state via `query`/`intent read` first, then show **current → proposed** for each changed field. No "small change" hand-waving.

```
description:        "old text"  →  "new text"
labels:             ["a", "b"]  →  ["a", "b", "c"]
protectFromDeletion: true       →  false
```

For `create`: show the full payload as it will be sent.

For `delete`: see step 3.

### 3. For deletes, enumerate dependents first

Before any `delete` mutation or `intent delete`:

| Target | How to enumerate dependents |
|---|---|
| Stack | `query stack(id) { dependsOn { id } isDependedOnBy { id } scheduledRuns { id } scheduledTasks { id } scheduledDeletes { id } attachedPolicies { id } }` |
| IntentProject | `query intentProject(id) { searchIntentResources(input: { first: 0 }) }` to count, then list a sample if non-empty |
| Intent resource | `searchIntentResources` with predicates for `references.resourceID = <target>` |
| Policy | List `attachedStacks` / `attachedIntentProjects` |
| Context | List `attachedStacks` |
| Worker pool | List stacks/projects that target it (via `searchStacks`, `searchIntentProjects`) |
| Integration | List attachments (`AwsIntegration.attachedStacks`, etc.) |

If dependents exist, **report them and stop**. Ask the user whether to:
- Delete dependents first
- Detach (don't delete dependents)
- Cancel

Never silently cascade.

### 4. Block on explicit confirmation

Accept only **`YES`** or **`CONFIRM`** (case-insensitive). Anything else is a no-go.

- No carryover from prior turns. Each destructive call needs its own fresh confirmation.
- "Sure" / "ok" / "go" / "proceed" do **not** confirm. Push back: "I need an explicit `YES` or `CONFIRM` to proceed."
- If the user authorized a batch ("delete all 5"), still confirm once with all 5 listed - don't request 5 separate confirmations.

### 5. Execute, then verify

After the mutation/op completes:

- For `mutate`: run the corresponding `query` to verify the new state.
- For sync `intent`: read the result.
- For async `intent`: report the `operation_id` and the polling plan.
- For `delete`: confirm absence (`query` returns null / `searchXxx` excludes the entity).

## What counts as destructive

| Operation | Confirmation? |
|---|---|
| `query`, `discover`, `provider search/describe`, `intent read/status` | No |
| `intent refresh` (state read into Spacelift, no cloud change) | Recommended for transparency, not strictly required |
| `mutate` of any kind | **Yes** |
| `intent create`, `update`, `delete`, `import` | **Yes** |
| `intent resume` (executes a deferred op) | **Yes** |
| `runTrigger` (creates a tracked run that will modify infra) | **Yes** |
| `runTrigger` with `runType: PROPOSED` (plan-only, no apply) | State the operation in prose; full `YES`/`CONFIRM` block can be skipped only when the user has explicitly opted into a proposed-only flow this turn |
| `runConfirm` (applies a planned tracked run) | **Yes** |
| `runDiscard`, `runCancel`, `runStop`, `runKill` | Yes - they affect a running operation |

## Idempotency reminders

- **`stackCreate`** with a colliding slug fails. Check `query stack(id: <slug>)` first.
- **`contextCreate`/`policyCreate`** - same; they don't upsert.
- **`intent create`** with a resource_id already in state errors. Use `update` instead.
- **`intent delete`** then re-create produces a new state entry; if you want to re-import, use `import` not `create`.

## When in doubt

Ask. The cost of one extra clarifying turn is far below the cost of a mis-applied destructive op. Pause earlier rather than later.
