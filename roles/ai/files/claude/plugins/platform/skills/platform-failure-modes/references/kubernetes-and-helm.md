# Kubernetes and Helm

When to read: the brief or diff touches Kubernetes manifests, Helm charts, kustomize overlays, or values files.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Workload without probes.** A pod with no readiness probe takes traffic before it can serve; no liveness probe means a wedged process stays wedged forever.
  Check: readiness and liveness probes exist, are distinct, and test something meaningful; slow-booting services get a startup probe instead of inflated delays.
- **Unsized workload.** Containers without resource requests cannot be scheduled sensibly and evict neighbors; a surprise limit OOM-kills the service under normal load.
  Check: every container declares requests; limits are a deliberate, stated choice, not a copy-paste.
- **Workload with default privileges.** A container running as root with a writable filesystem hands any process compromise the whole pod, and cluster defaults will not stop it.
  Check: the security context drops to non-root with a read-only root filesystem where the app allows, and every exception is stated.
- **Template that renders wrong instead of failing.** A missing values key renders as an empty string; the manifest applies cleanly with silently wrong config.
  Check: required values fail the render explicitly (required functions or a values schema); string values are quoted so numeric-looking and boolean-looking values do not coerce; the rendered output is inspected, not assumed.
- **Values drift across environments.** Per-environment values files that diverge structurally let a key renamed in one environment silently keep its stale default in another.
  Check: environment files share one structure and differ only in values; a new or renamed key is reflected in every environment or defaulted deliberately.
- **Immutable field changes.** Edits to immutable fields (label selectors, volume claims, job templates) fail mid-apply or force delete-and-recreate with downtime.
  Check: diff the change against the live object, or against the previously rendered manifest, for known-immutable fields; a required change to one escalates with a migration plan.
- **Mutable image tags in manifests.** An image on `latest` makes rollback meaningless and lets pods on the same spec run different code after restarts.
  Check: manifests reference immutable image refs: a digest or a unique, never-reused tag.
- **Rollout that allows an outage.** No disruption budget permits zero healthy pods during a node drain; a recreate strategy or a single-replica stateful workload does the same during a deploy.
  Check: replica count, update strategy, and disruption budget together match the availability the service claims to offer.
- **Names hardcoded into the chart.** A chart that hardcodes release names or namespaces breaks the second install and collides in shared clusters.
  Check: names and namespaces derive from the release context; nothing assumes it is the only install.
- **Chart contract drift.** A chart changed without a version bump, or values renamed without deprecation, breaks pinned consumers at their next upgrade.
  Check: any chart change bumps the chart version; renamed or removed values carry a deprecation path in the chart notes.

## Escalation triggers (`needs-decision`)

- Any change to an immutable field on a live workload, or to a chart's public values contract.
- Resource sizing with no stated basis; sizing derived from SLOs belongs to the SRE seat, hand it across.

## What good looks like

- Rendered manifests validate against the target cluster's API schema on stable API versions, and both a fresh install and an upgrade succeed.
- Every workload declares how it is probed, sized, and rolled; nothing rides on cluster defaults.
- Charts version like libraries: consumers upgrade deliberately and nothing breaks them silently.
