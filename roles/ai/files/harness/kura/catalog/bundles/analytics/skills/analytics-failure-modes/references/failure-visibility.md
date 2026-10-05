# Failure visibility

When to read: any new or changed model, test, or scheduled build; and whenever the brief or diff touches how a run failure or a data-quality failure surfaces.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The warning that never fails.** A test or expectation that warns without failing the build lets bad data reach consumers while looking diligent.
  Check: quality expectations run as build steps that fail the run; a check that only warns is escalated, not shipped.
- **The opaque run failure.** A failed build with no identity forces triage to guess.
  Check: failure output answers what, why, and when: the model, the test, and the run id that correlates the logs and the compiled SQL.
- **The stale-but-silent table.** A model that silently stops refreshing leaves consumers reading old data.
  Check: freshness is declared where an SLA exists and is observable; a stall surfaces a signal rather than passing quietly.
- **Quality failure mistaken for operational, or the reverse.** Triage routes wrongly when the two look the same.
  Check: a data-quality failure (a failed test) is distinguishable from an operational failure (a broken build) at a glance. (See tests-and-freshness.md.)
- **Secrets and PII in logs.** Personal fields or credentials in build logs or artifacts are a breach.
  Check: logs carry identifiers and counts, never row payloads; sensitive columns never land in a log or a fixture.
- **Alert config assumed, not handed off.** Declaring freshness is this seat's job; paging on it is not.
  Check: freshness and failure signals are emitted or declared, and their alert rules are a specified handoff to sre-staff-engineer or the platform owner.

## Escalation triggers (`needs-decision`)

- Adding or changing a run-alerting or monitoring integration.
- New freshness or failure alerts someone else is paged on.
- Observability the brief needs that the project has no pattern for yet.

## What good looks like

- A failed test fails the build; bad data does not reach a consumer looking diligent.
- Every question triage asks ("which model, which test, when did it start") is answerable from the run.
- Operational failures and data-quality failures are told apart at a glance.
- The signal is declared here; the alert that reads it is owned by SRE or platform.
