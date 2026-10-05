# Migrations and deploy ordering

When to read: the brief or diff adds or edits migrations, renames or drops schema objects, or sequences a schema change across multiple steps.
Transaction semantics inside application code belong to the backend seat's data-safety reference; this file covers the DDL and the order it ships in.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **In-place rename.** Renaming a table or column breaks every deployed app version still reading the old name; deploys are not atomic.
  Check: a rename ships as add, dual-write, backfill, switch reads, drop later; an in-place rename on a live table escalates.
- **N-1 incompatibility.** During every rollout and rollback, old code runs against the new schema and new code against the old one; a change correct for only one side breaks the other.
  Check: walk both directions (new schema with previous code, old schema with new code); anything requiring a lockstep deploy is an explicit coordinated plan, escalated.
- **Drop before the last reader is gone.** A column or table dropped while a running version, replica consumer, or report still reads it fails at query time, not review time.
  Check: contract-phase drops name the condition proving the last reader is gone (release deployed, query log clean); search the codebase for consumers before dropping anything.
- **Untested down path.** A down migration written but never run restores nothing when the deploy goes bad.
  Check: run up, down, up against the local database; where the down destroys data, it says so explicitly and the report flags it.
- **Shipped migration edited.** Editing or reordering a migration that may have been applied elsewhere desynchronizes every environment's migration state.
  Check: shipped migrations are immutable and fixes ship as a new forward migration; where the brief demands touching applied history, escalate with a plan a human executes.
- **Migration importing application code.** A migration importing app models or helpers replays differently once that code changes; a fresh environment then fails on migrations that once passed.
  Check: migrations are self-contained (raw SQL or the tool's schema operations, with any needed logic inlined); nothing imported from the application.
- **Shared-table change scoped to one repo.** A table other services read follows expand-contract across all of its consumers, not just the code in this repository.
  Check: enumerate consuming services and their deploy cadence; a change to a shared table escalates with the cross-service ordering spelled out.

## Escalation triggers (`needs-decision`)

- Dropping tables or columns, narrowing types, or any lossy contract-phase change (also an ask-first boundary in the agent).
- Changes to tables other services or teams consume (also an ask-first boundary in the agent).
- A brief that requires touching migration history applied beyond local dev: propose the plan, a human executes it (also an ask-first boundary in the agent; editing applied files stays in its never tier).

## What good looks like

- Every change deploys in both directions against running code, versions N-1 and N.
- Renames and drops are multi-release sequences with named checkpoints, never single statements.
- The down path is tested locally, and where it cannot restore data, that is written down before it matters.
