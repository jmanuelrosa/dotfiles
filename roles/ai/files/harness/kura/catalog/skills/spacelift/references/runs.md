# Runs

A **Run** is the unit of execution for a stack. Four kinds:

| Kind | Trigger | Purpose |
|---|---|---|
| **Tracked** | `runTrigger` (default) | Modifies infrastructure state. |
| **Proposed** | `runTrigger(runType: PROPOSED)`, PR events, `proposeWithOverrides` | Plan-only preview. |
| **Task** | `taskCreate(stack, command)` | Free-form shell command in the stack runner. |
| **Module test case** | `versionProposeLocalWorkspace`, etc. | Module validation; not stack-scoped. |

## State machine

Non-terminal: `QUEUED`, `READY`, `PREPARING`, `INITIALIZING`, `PLANNING`, **`UNCONFIRMED`**, `CONFIRMED`, `APPLYING`, `PERFORMING`, `DESTROYING`.

Terminal: `FINISHED`, `FAILED`, `STOPPED`, `DISCARDED`, `CANCELED`.

A stack serializes one run at a time via lock; queued runs wait their turn. (`READY_FOR_EXECUTION` / `PENDING_REVIEW` are **intent operation** statuses, not run states - see `intent-operations.md`.)

## State-changing actions

| Action | Mutation | Valid when |
|---|---|---|
| Trigger tracked run | `runTrigger(stack, commitSha?, runType?, runtimeConfig?, forceApply?)` | Any time the stack is enabled |
| Trigger proposed (PR-style) | `runTrigger(stack, runType: PROPOSED)` or `proposeWithOverrides` | Same |
| Confirm | `runConfirm(stack, run?, note?)` | State is `UNCONFIRMED` (or omit `run` to confirm the blocker) |
| Discard | `runDiscard(stack, run?, note?)` | State is `UNCONFIRMED` or queued |
| Discard all | `runDiscardAll(stack, note?)` | Bulk-clear discardable runs |
| Cancel | `runCancel(stack, run, note?)` | Run hasn't started yet |
| Stop | `runStop(stack, run, note?, state?)` | Run is `INITIALIZING` / `PLANNING` |
| Kill | `runKill(stack, run, note?, state?)` | After `runStop` if process didn't exit; SIGKILL |
| Retry | `runRetry(stack, run)` | Finished proposed run |
| Replan (targeted) | `runTargetedReplan(stack, run, targets)` | Re-plan with `-target` |
| Promote proposed → tracked | `runPromote(stack, run)` | Proposed run in `FINISHED` state that you want to apply |
| Comment | `runComment(stack, run, body)` | Any |
| Review | `runReview(stack, run?, decision, note?)` | Decision = `APPROVE` / `REJECT` |
| Prioritize (boolean flag) | `runPrioritizeSet(stack, run, prioritize)` | Queued runs only - simple "go first" toggle |
| Set priority preset | `runPrioritySet(stack, run, preset)` | Queued runs only - named preset (`RunPriorityPreset` enum) |
| External dep done | `runExternalDependencyMarkAsCompleted(dependency, status)` | Experimental |

## Inspecting runs

| Need | Query |
|---|---|
| Single run (no stack ID needed) | `run(id)` |
| Stack's recent runs | `stack(id) { runs(before: ID) { ... } }` (cursor pagination) |
| Proposed runs only | `stack(id) { proposedRuns }` |
| Tasks | `stack(id) { tasks } ` |
| Range by time | `stack(id) { runsInRange(start, end) }` (max 8 days) |
| Run's stack (when you only have run ID) | `runStack(runId)` |
| Run state summary | `summarizeRun(stack, run)` produces `RunSummary` |

## Common query selections

```
id state type createdAt updatedAt branch commit { hash authorLogin }
delta { resourcesAdded resourcesChanged resourcesDeleted }
```

## Pitfalls

- **`runConfirm` on the wrong state** silently fails or returns a clarifying error. Always read `state` first.
- **`UNCONFIRMED` blocks the stack.** Other runs queue. Resolve (confirm or discard) before triggering more.
- **`runStop` doesn't always stop.** If the worker doesn't honor SIGTERM, follow up with `runKill`. Check state before re-issuing.
- **Proposed run promotion**: `runPromote` is the right move - don't trigger a new tracked run for the same SHA.
- **Forced apply** (`forceApply: SKIP_PLAN_AND_CONFIRM`) bypasses the plan/confirm gate. Treat as destructive: confirmation required even though it's a `runTrigger`.
- **Tasks count as runs** - they take the stack lock. Don't dispatch a task while a tracked run is in progress.
- **External dependencies**: a run can wait on `RunExternalDependency`; mark complete via `runExternalDependencyMarkAsCompleted` - don't poll.
