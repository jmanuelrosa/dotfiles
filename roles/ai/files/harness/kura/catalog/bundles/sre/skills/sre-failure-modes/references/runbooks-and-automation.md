# Runbooks and automation

When to read: the brief or diff touches runbooks, operational docs, alert annotations, or automation scripts replacing manual steps.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Narrative where a procedure belongs.** Prose that explains the system but never says what to do leaves the responder synthesizing a plan at 3am; a bare command dump without the decisions is the same failure from the other side.
  Check: the runbook is keyed to the alert that fires it and encodes the diagnosis path (symptom, checks, escalation) as numbered steps, each with an exact command or click path and an expected-output check before the next step.
- **Commands that do not exist.** A runbook referencing scripts, dashboards, hosts, or flags that were renamed or never existed fails on first real use, which is by definition during an incident.
  Check: every command, script path, dashboard link, and query in the runbook is verified to exist in the current repo and stack; a broken reference blocks done.
- **No rollback or abort path.** A procedure that only moves forward strands the responder halfway when step 4 fails.
  Check: each mutating step states how to undo it or when to stop; the escalation contact or channel for aborting is named.
- **Author-context assumptions.** Steps that presume tribal knowledge (which cluster, which account, where the tool runs) are executable only by the person who never needed the runbook.
  Check: a competent engineer who has never operated this service could execute it; preconditions and required access are stated up front.
- **Toil codified instead of automated.** A runbook whose steps are deterministic commands with no judgment is a script wearing a document costume; the SRE book calls this toil.
  Check: mechanical step sequences become a script the runbook calls; the runbook keeps the judgment (when to run, what to verify), the script keeps the keystrokes.
- **Automation that acts on production.** Scripts this seat writes are proposals: a script that restarts, scales, or mutates production is for humans or deploy pipelines to run.
  Check: nothing you add executes mutations as part of your work; mutating scripts ship documented, reviewed, and unrun (production mutation is a never boundary in the agent).
- **Stale on arrival.** A runbook not linked from the alert that needs it, or filed outside the team's runbook location, might as well not exist.
  Check: the runbook lives in the project's established operational-docs location, and the alerts it serves link to it.
- **Untested procedure.** A runbook nobody has walked through is a hypothesis, not a procedure.
  Check: walk every step in a dev stack where feasible; where not, mark the runbook as unexercised and state how its first drill should be conducted.

## Escalation triggers (`needs-decision`)

- Automating a step with a large blast radius (mass restarts, data deletion, failover): propose the script and its guardrails; a human decides and runs it first.
- A brief that asks you to perform the recovery actions a runbook describes: production mutation is a never boundary in the agent, so the decision you return is who else performs it, never whether you do.

## What good looks like

- The page links the runbook; the runbook's first block states impact, preconditions, and abort criteria; every step is check-then-act.
- Deterministic toil is a tested script, and the runbook is the judgment wrapper around it.
- Runbooks are reviewed and dated like code, and each drill or real use feeds edits back.
