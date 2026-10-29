# Example: stack run lifecycle

**Goal:** trigger a tracked run on stack `prod-web`, follow it through plan → confirm → apply, and report the result.

This walks through `runTrigger` → polling state → `runConfirm`. Two destructive-op gates: `runTrigger` and `runConfirm`.

## Step 1 - check stack state

```
query stack
  variables: { id: "prod-web" }
  select: "id state isDisabled blocked blocker { id state } trackedCommit { hash authorLogin }"
```

If `isDisabled: true`, stop and ask. If `blocked: true`, report the blocker; the user may want to resolve it before triggering a new run.

## Step 2 - destructive-op gate (trigger)

Read `references/mutations-safety.md`. Then state to the user:

> Trigger a **tracked run** on stack `prod-web` against tracked commit `<hash>`. This will plan and (after your confirm) apply changes to production. Reply `YES` or `CONFIRM` to proceed.

Wait for explicit confirmation.

## Step 3 - trigger

```
mutate runTrigger
  variables: { stack: "prod-web" }
  select: "id state type createdAt"
```

Capture the run `id`. State should be `QUEUED` or `READY`.

## Step 4 - poll until UNCONFIRMED or terminal

```
query run
  variables: { id: "<runId>" }
  select: "id state delta { resourcesAdded resourcesChanged resourcesDeleted } stateSetAt"
```

Backoff: 5s → 10s → 20s → 40s, cap at 60s. Stop when:

- `state == UNCONFIRMED` → continue to step 5
- `state` is terminal (`FINISHED`, `FAILED`, `STOPPED`, `DISCARDED`, `CANCELED`) → report and stop
- `state == CONFIRMED` (autodeploy was on) → skip step 5; poll until terminal

If the stack has `autodeploy: true`, plan auto-confirms; you'll see `CONFIRMED` then `APPLYING` without a user gate. The user has implicitly pre-confirmed via the stack setting; continue without re-prompting.

## Step 5 - destructive-op gate (confirm)

Read the run delta back:

> Run `<runId>` on `prod-web` planned: **+3 resources, ~1 changed, -0 destroyed**. Confirming will apply.
>
> Reply `YES` or `CONFIRM` to apply, or say "discard" to cancel.

Wait. If the user says "discard":

```
mutate runDiscard
  variables: { stack: "prod-web", run: "<runId>", note: "discarded by user" }
  select: "id state"
```

Otherwise, on `YES`/`CONFIRM`:

```
mutate runConfirm
  variables: { stack: "prod-web", run: "<runId>", note: "approved" }
  select: "id state"
```

## Step 6 - poll until terminal

Same backoff. State path: `CONFIRMED` → `APPLYING` → (`PERFORMING`) → `FINISHED` or `FAILED`.

## Step 7 - report

```
query run
  variables: { id: "<runId>" }
  select: "id state delta { resourcesAdded resourcesChanged resourcesDeleted } commit { hash } finished"
```

Surface: final state, delta, duration. If `FAILED`, include logs hint: "use `runStack(runId)` and the Spacelift UI for full logs."

## Pitfalls avoided

- **Wrong-state confirm**: step 4 ensures state is `UNCONFIRMED` before calling `runConfirm`.
- **Tight polling**: exponential backoff caps at 60s; stops re-querying for slow plans.
- **Implicit autodeploy surprise**: explicit handling of `autodeploy: true` so the user isn't asked twice.
- **Forgetting to handle "discard"**: if the plan is bad, the user has a clean off-ramp.
