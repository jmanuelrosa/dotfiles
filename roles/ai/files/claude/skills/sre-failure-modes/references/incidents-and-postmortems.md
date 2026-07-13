# Incidents and postmortems

When to read: the brief or diff touches postmortems, incident timelines, severity classification, action items, or on-call handoff docs.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Blame wearing an author's byline.** A postmortem that names who erred, even gently, teaches the organization to hide the next error; the published Google standard is blameless.
  Check: no sentence attributes fault to a person or team; every human action is framed as the system permitting or inviting it (roles like "the on-call engineer" are fine, judgment words are not).
- **Timeline reconstructed from memory.** Invented or rounded times make the detection-to-mitigation math wrong and the lessons unfounded.
  Check: timeline entries carry timestamps traceable to evidence (alerts, deploys, chat records); gaps are marked as gaps, never smoothed over or fabricated.
- **Impact never quantified.** "Users were affected" supports no severity call and no budget accounting; the published Google template quantifies impact in concrete terms.
  Check: impact is stated in user-visible terms (who, how many, how long, which SLO) and the error budget consumed is computed against the SLO it burned.
- **Single root cause where several contributed.** Complex failures are layered; stopping at the first "root cause" leaves the other contributing factors armed.
  Check: the analysis lists contributing factors across trigger, propagation, detection, and mitigation; "human error" is never the final answer.
- **Action items that evaporate.** Items with no owner, no priority, or aspirational scope ("improve monitoring") are never done, and the incident repeats on schedule.
  Check: every action item has a named owner, a concrete deliverable, and a priority or due date; at least one item mechanizes a gate (a test, an alert, a validation) rather than adding a reminder.
- **Severity assigned by vibes.** Without criteria, severity is negotiated during the incident, and cross-incident comparison becomes meaningless.
  Check: the severity matches the project's documented classification (user impact, duration, scope); if no classification exists, flag it in the report as a missing gate.
- **Detection gap unexamined.** If users noticed before the alerts did, that is a finding about the alert set, and it is the one finding this seat can fix directly.
  Check: the postmortem states how the incident was detected and the delay from impact start; a users-noticed-first incident produces an alerting action item.
- **Lessons that never reach the artifacts.** A postmortem filed and forgotten converts nothing; its findings should harden SLOs, alerts, and runbooks.
  Check: findings that invalidate an SLO assumption, a runbook step, or an alert threshold produce edits or escalations to those artifacts, referenced from the action items.

## Escalation triggers (`needs-decision`)

- Severity classification and external communication wording: business decisions, so recommend rather than decide.
- An action item that lands on another seat's surface (application code, CI, IaC): specify it and hand it across.

## What good looks like

- A reader who was not there can reconstruct what users experienced, when, and why, entirely from evidence.
- The follow-up list is short, owned, and mostly mechanization; three months later the items are verifiably done.
- Postmortems are structurally consistent, so repeat patterns surface when anyone compares them.
