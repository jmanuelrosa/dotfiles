# Dashboards as code

When to read: the brief or diff touches dashboard JSON or jsonnet, panels, queries, template variables, or dashboard provisioning.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Panel querying a phantom metric.** A query against a metric or label nothing emits renders an empty panel that reads as "no problems" during the incident that needed it.
  Check: every panel query references metrics and labels that exist in the project's instrumentation or recording rules; render or dry-run each new query against real data where a dev stack exists.
- **Averages where the SLO is a tail.** A mean-latency panel shows calm while the p99 the SLO promises burns.
  Check: latency panels show the percentile the SLO is defined on; if an average appears, it is labeled and sits next to the tail, never instead of it.
- **Dashboard drifted from the rules.** A dashboard computing the SLI differently from the recording rule or alert expression shows green while the alert fires, and the responder distrusts both.
  Check: panels that display SLI or SLO state query the same recording rules the alerts use, not a hand-rewritten approximation.
- **Decoration over diagnosis.** A wall of panels nobody can prioritize slows the incident it was built for.
  Check: the dashboard leads with user-facing symptom panels (the SLO's own SLIs, or rate, errors, duration), with cause-level detail below or linked, so "is it broken, since when, for whom" is the first screen.
- **Unscoped template variables.** A variable defaulting to all services, or a datasource or environment hardcoded where a template variable belongs, renders wrong or explodes query cost the moment someone else opens it.
  Check: datasource, environment, and scope come from template variables with sane defaults, and the dashboard renders correctly for values other than the author's test case.
- **UID and provisioning collisions.** Provisioned dashboards without stable identifiers duplicate on every apply; a reused identifier overwrites someone else's board.
  Check: dashboards carry stable, unique identifiers and provisioning is idempotent: re-applying changes nothing.
- **Broken links in the incident path.** Alerts and runbooks link into dashboards; a renamed dashboard or panel breaks the path responders follow under pressure.
  Check: everything that links to this dashboard (alert annotations, runbooks, other panels) still resolves after the change; renames are contract changes.
- **Queries that punish the datastore.** A panel with an unbounded range, no aggregation, or a high-cardinality group-by can degrade the monitoring stack exactly when everyone is looking at it.
  Check: queries are bounded and aggregated to what the panel actually shows; expressions repeated across panels become recording rules.

## Escalation triggers (`needs-decision`)

- Deleting or renaming a dashboard or panel that alerts, runbooks, or other teams link to (also an ask-first boundary in the agent).
- A dashboard that needs metrics that do not exist yet: specify what the implementer seats must emit.

## What good looks like

- An on-call who has never seen the service answers "is it broken, since when, for whom" in under a minute from the top row.
- Dashboards are provisioned from code, idempotent, and reviewed like code; nobody edits them live.
- Every number a responder sees traces to the same expressions the alerts use.
