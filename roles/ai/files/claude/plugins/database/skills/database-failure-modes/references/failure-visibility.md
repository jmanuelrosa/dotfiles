# Failure visibility

When to read: any new migration, backfill, or DDL against an existing table; and whenever the brief or diff touches how a failure surfaces to the operator running it.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The opaque migration failure.** A migration that fails midway without saying which step or why leaves the database in an unknown state.
  Check: failure output names the failing step and the cause; the down path was run locally (up, down, up); a partial apply is recoverable.
- **The silent backfill.** A long backfill with no progress or failure signal cannot be trusted or resumed.
  Check: the backfill logs progress and failures with the row range or batch key, is idempotent and resumable, and is handed off with exact commands for a human.
- **Context-free errors.** A failure with no identity is unactionable.
  Check: reported context answers what, why, and when: the migration or script, the table, and the batch or run id that correlates the logs.
- **Invisible slow paths.** A new query pattern or a lock that degrades production silently is a latent incident.
  Check: query and index claims carry before and after plans on realistic volume; lock impact is stated; the signal that would catch a regression exists.
- **Alert config assumed, not handed off.** Emitting the signal is this seat's job; the alert rule is not.
  Check: slow-query, replication-lag, or error signals are emitted or identified, and their alert rules are a specified handoff to sre-staff-engineer.

## Escalation triggers (`needs-decision`)

- Changing how migrations report or where their logs go.
- New alerts on query latency, locks, or replication that someone is paged on.
- Observability the brief needs that the project has no pattern for yet.

## What good looks like

- A failed migration or backfill says exactly where it stopped and how to resume.
- Every question triage asks ("which migration, which table, when") is answerable from the logs.
- A slow query or a lock regression is caught by a signal, not by a user.
- The signal is emitted here; the alert that reads it is owned by SRE.
