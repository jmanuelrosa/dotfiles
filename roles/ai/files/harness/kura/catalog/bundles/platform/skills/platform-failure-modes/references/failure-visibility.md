# Failure visibility

When to read: any new or changed pipeline, job, container, or workload; and whenever the brief or diff touches health checks, probes, or how a failure surfaces in CI or at deploy.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The silent skip.** A conditional or path-filtered job that can skip while the merge gate stays green lets broken code through unseen.
  Check: no job can silently skip while leaving the gate green; a required check that does not run is a failure, not a pass.
- **The unreadable pipeline failure.** A job that fails with a buried or cryptic error costs everyone who reads the log.
  Check: failure output names the step and the cause and points at the fix; the failing unit is obvious from the log.
- **The unprobed workload.** A container or deployment with no liveness or readiness probe fails silently and takes traffic while broken.
  Check: workloads carry health probes and resource requests; a failed rollout is detected and reversible, not assumed healthy.
- **Context-free signals.** A pipeline or workload signal with no identity cannot answer the incident's questions.
  Check: emitted signals identify the workflow, job, and environment, and correlate to the deploy or run id.
- **Alert config assumed, not handed off.** The pipeline emits the signal; the alert rule and SLO belong elsewhere.
  Check: deploy and health signals are emitted or wired, and their alert rules, thresholds, and routing are a specified handoff to sre-staff-engineer.

## Escalation triggers (`needs-decision`)

- Changing where pipeline or workload logs and signals go.
- New alerts or health gates someone else is paged on.
- Observability the brief needs that the platform has no pattern for yet.

## What good looks like

- A failing pipeline names the cause and never passes the gate by skipping.
- Every workload declares how it is judged healthy, and a bad rollout is caught and reversible.
- Every question triage asks ("which job, which deploy, when") is answerable from the logs.
- The signal is emitted here; the alert and the SLO are owned by SRE.
