# Plan safety and drift

When to read: the brief or diff touches any change about to be planned; plan output, drift, hardcoded IDs, or version pins.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Plan treated as approval.** A plan that exits clean proves syntax and API acceptance, not intent; the destroy and replace lines are where incidents live, and completion pressure is exactly when they go unread.
  Check: read the plan resource by resource; every destroy or replace of an existing resource is expected, explained, or escalated.
- **Innocuous attribute forcing replacement.** Some argument changes update in place; others force destroy-and-create, and which is which is provider knowledge the code diff does not show.
  Check: for each changed argument on a live resource, know whether it updates or replaces; a plan that disagrees with your expectation is a stop, not a shrug.
- **Targeted plan hiding the whole.** Planning with resource targeting limits the plan to the targets and their dependencies, skipping the rest of the graph, so the "small safe plan" and the real next plan disagree.
  Check: targeting is an incident escape hatch, not a workflow; the plan you report covers the whole root, and any targeting is stated with its reason.
- **Apply-time failure the plan cannot see.** A clean plan still fails at apply on name uniqueness, propagation delays, and capacity; the human applying inherits a half-created change.
  Check: name the apply-time risks of the change (globally unique names, cross-service dependencies, capacity) in the report so the applier watches for them.
- **Code assumed to equal reality.** Consoles, scripts, and incident fixes change infrastructure behind the code; a plan against drifted state does things nobody asked for.
  Check: recommend a refresh-only plan before consequential changes; treat surprising plan lines as possible drift to surface, not noise to accept.
- **Drift with no detection story.** Out-of-band changes accumulate silently until the next apply reverts someone's emergency fix at the worst possible time.
  Check: environments you build carry a scheduled drift check (a refresh-only plan with a detailed exit code, or the platform's drift detection); if none exists, flag it as a missing gate.
- **Hardcoded account IDs, regions, and zones.** Literals pin the configuration to one account and one place; reuse, disaster recovery, and multi-region all break on them silently.
  Check: account IDs, regions, zones, and resource identifiers come from variables, data sources, or provider configuration; existing literals in touched files are flagged.
- **Unpinned tool and providers.** Missing tool-version and provider constraints let two machines plan the same commit with different behavior.
  Check: tool and provider versions are pinned; the dependency lockfile is committed and updated with the tool's own command, never by hand.
- **Fork-blind syntax.** Terraform and OpenTofu have diverged (state encryption, provider iteration, evaluation order); a feature valid in one fails or misbehaves in the other.
  Check: detect which fork the project runs and validate with that binary; a feature exclusive to one fork is a deliberate, stated choice.

## Escalation triggers (`needs-decision`)

- A plan destroying or replacing an existing resource the brief did not call for (also an ask-first boundary in the agent).
- Reconciling drift: choosing whether code or live wins is a judgment about someone's intent, not an implementation detail.

## What good looks like

- The plan summary matches the brief's intent: adds where expected, zero unexplained destroys.
- A reviewer can trace every replace to a stated reason.
- Same commit, same plan, on any machine: everything pinned, nothing local.
