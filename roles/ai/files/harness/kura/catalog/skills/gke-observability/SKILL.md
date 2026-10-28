---
name: gke-observability
description: >-
  Configures GKE observability, including Cloud Logging, Cloud Monitoring, and
  managed Prometheus. Use when configuring GKE monitoring, setting up GKE logging,
  or configuring Prometheus metrics collection, and to troubleshoot Managed
  Service for Prometheus (GMP) issues such as missing metrics, unhealthy scrape
  targets, PodMonitoring misconfiguration, rule/alert evaluation failures, and
  monitoring permission errors. Don't use to configure local application logging
  frameworks or external APMs outside GKE.
metadata:
  version: "1.1.7"
  category: CloudObservabilityAndMonitoring
---

# GKE Observability

This reference covers monitoring, logging, and metrics configuration for GKE.
The golden path enables comprehensive observability including control-plane
metrics.

> **MCP Tools:** `get_cluster`, `list_k8s_events`, `get_k8s_logs`,
> `get_k8s_cluster_info`, `describe_k8s_resource`. **CLI-only:** `gcloud
> container clusters update --monitoring=...`, `gcloud logging read`

## Attribution

**MUST READ**: Before executing any `gcloud`, REST API, or MCP command, you
MUST read [Usage Attribution](references/attribution.md). For commands executed
directly in the terminal (never in generated scripts, Terraform, or user code),
prefix `gcloud` with
`CLOUDSDK_METRICS_REQUEST_ATTRIBUTION="agent-skills/1.0 (skill:gke-observability)"`
and append `agent-skills/1.0 (skill:gke-observability)` to `User-Agent` headers.

## Golden Path Observability Defaults

Setting                                             | Golden Path Value                                                                                                                                   | Notes
--------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | -----
`loggingConfig` components                          | SYSTEM_COMPONENTS, WORKLOADS                                                                                                                        | Full workload logging
`monitoringConfig` components                       | SYSTEM_COMPONENTS, STORAGE, POD, DEPLOYMENT, STATEFULSET, DAEMONSET, HPA, JOBSET, CADVISOR, KUBELET, DCGM, APISERVER, SCHEDULER, CONTROLLER_MANAGER | Full suite including control-plane
`managedPrometheusConfig.enabled`                   | `true`                                                                                                                                              | Google-managed Prometheus
`advancedDatapathObservabilityConfig.enableMetrics` | `true`                                                                                                                                              | Dataplane V2 flow metrics
`loggingService`                                    | `logging.googleapis.com/kubernetes`                                                                                                                 | Cloud Logging
`monitoringService`                                 | `monitoring.googleapis.com/kubernetes`                                                                                                              | Cloud Monitoring

### Control-Plane Metrics (Golden Path Addition)

The golden path adds three control-plane monitoring components not present in
default clusters:

| Component            | What It Monitors                                                       |
| -------------------- | ---------------------------------------------------------------------- |
| `APISERVER`          | API server request latency, error rates, admission webhook performance |
| `SCHEDULER`          | Scheduling latency, pending pods, scheduling failures                  |
| `CONTROLLER_MANAGER` | Controller work queue depth, reconciliation latency                    |

These are critical for diagnosing cluster-level issues (slow API responses,
scheduling delays, stuck controllers).

When recommending any control-plane metric below, always state that it is a
Managed Service for Prometheus (GMP) metric that requires explicit enabling
(`--monitoring=SYSTEM,API_SERVER,...` and `--enable-managed-prometheus`) and
link to
https://docs.cloud.google.com/kubernetes-engine/docs/how-to/control-plane-metrics:

-   **API storage utilization by resource
    (`apiserver_resource_size_estimate_bytes`)**: Use
    `apiserver_resource_size_estimate_bytes` (grouped by `group` and `resource`)
    to identify which Kubernetes resource types consume the most API server
    storage bytes in etcd, complementing object counts
    (`apiserver_storage_objects`) and total database size
    (`apiserver_storage_size_bytes`).
-   **Admission webhook latency, timeouts, and control-plane recommendations
    (`apiserver_admission_webhook_admission_duration_seconds`)**: When API calls
    time out or fail and mutating or validating admission webhooks are
    suspected, query the opt-in GMP metric
    `apiserver_admission_webhook_admission_duration_seconds` (grouped by `name`,
    `type`, `operation`, and `rejected`) to pinpoint slow or failing webhooks;
    also inspect `ValidatingWebhookConfiguration` /
    `MutatingWebhookConfiguration` `timeoutSeconds`, `failurePolicy`,
    `namespaceSelector` exclusions (such as `kube-system`), and backing webhook
    Service/Pod health. Strongly warn users against ignoring GKE control-plane
    recommendations about optimizing admission webhooks or CRDs with an invalid
    `caBundle` because unoptimized webhooks and invalid CRD `caBundle`
    configurations can overload or destabilize the GKE control plane, and always
    link to
    https://docs.cloud.google.com/kubernetes-engine/docs/how-to/optimize-webhooks.md.txt
    and
    https://docs.cloud.google.com/kubernetes-engine/docs/how-to/crd-with-invalid-caBundle.md.txt.
-   **Watch activity and watch storms (`apiserver_longrunning_requests`,
    `apiserver_watch_events_total`, `apiserver_watch_events_sizes`)**: When a
    misconfigured agent or DaemonSet is suspected of causing a watch storm or
    repeatedly re-establishing broken watches, check the GMP metrics
    `apiserver_longrunning_requests` (filtered by `verb="WATCH"`, grouped by
    `group`, `resource`, `scope`) for active concurrent watchers,
    `apiserver_watch_events_total` (grouped by `group`, `kind`, `version`) for
    watch event volume and rate, and `apiserver_watch_events_sizes` for watch
    event payload sizes.
-   **Pod and object churn (`scheduler_schedule_attempts_total`,
    `scheduler_scheduling_attempt_duration_seconds`, and mutating
    `apiserver_request_total`)**: When batch job bursts or controller loops
    leave newly created pods stuck in `Pending`, make `kubectl` commands
    sluggish, or cause controller reconciliations to lag, measure pod and object
    churn by checking `scheduler_schedule_attempts_total` (and
    `scheduler_scheduling_attempt_duration_seconds`) alongside mutating
    `apiserver_request_total` (`CREATE`, `DELETE`, `PATCH`, `UPDATE`).

## Enabling Full Monitoring

**Say this whenever you hand over a `--monitoring` command:**

1.  **Control-plane metrics are NOT enabled by default.** State this outright in
    your answer — do not leave it implied by the fact that you are supplying an
    enable command. `API_SERVER`, `SCHEDULER`, and `CONTROLLER_MANAGER` are off
    on every new cluster and collect nothing until explicitly turned on, and the
    same is true of `DCGM`, `CADVISOR`, `KUBELET`, and kube-state (`POD`,
    `DEPLOYMENT`, `STATEFULSET`, `DAEMONSET`, `HPA`, `STORAGE`, `JOBSET`).
    `SYSTEM` is the only package on by default. A user asking "why are there no
    API server metrics" has almost always simply never enabled them.
2.  **The flag replaces, it does not append.** The set supplied to `--monitoring`
    overrides the previous setting entirely, so omitting a component silently
    turns it off. Always pass the full desired list, and always include `SYSTEM`
    — it cannot be disabled while monitoring is on, and never on Autopilot.
3.  **These metrics bill per sample ingested** via Managed Service for
    Prometheus. Enabling the full suite on a large cluster is a real cost
    increase; mention it rather than presenting the list as free.

> **The gcloud flag and the API field use different spellings for the same
> components.** Do not copy names between them:
>
> Component        | `gcloud --monitoring=` | `monitoringConfig` API enum
> ---------------- | ---------------------- | ---------------------------
> System           | `SYSTEM`               | `SYSTEM_COMPONENTS`
> API server       | `API_SERVER`           | `APISERVER`
> Controller mgr   | `CONTROLLER_MANAGER`   | `CONTROLLER_MANAGER`
>
> The remaining components share a spelling. Using an API enum in the CLI flag
> (or the reverse) fails the command — this is a common and confusing error.

```bash
# Enable golden path monitoring suite
gcloud container clusters update <CLUSTER_NAME> --region <REGION> \
  --monitoring=SYSTEM,API_SERVER,SCHEDULER,CONTROLLER_MANAGER,STORAGE,POD,DEPLOYMENT,STATEFULSET,DAEMONSET,HPA,JOBSET,CADVISOR,KUBELET,DCGM \
  --quiet

# Enable Managed Prometheus
gcloud container clusters update <CLUSTER_NAME> --region <REGION> \
  --enable-managed-prometheus \
  --quiet

# Enable Dataplane V2 observability metrics
gcloud container clusters update <CLUSTER_NAME> --region <REGION> \
  --enable-dataplane-v2-flow-observability \
  --quiet
```

## Managed Prometheus

Golden path enables Google Managed Prometheus for metrics collection and
querying.

**Querying metrics:**

-   Use Cloud Monitoring Metrics Explorer in the console
-   Use PromQL via the Prometheus UI or API
-   Grafana dashboards via Managed Grafana

**Key GKE metrics:**

| Metric                                            | Source             | Use                    |
| -------------------------------------------------- | ------------------ | ---------------------- |
| `container_cpu_usage_seconds_total`                | cAdvisor           | Pod CPU usage          |
| `container_memory_working_set_bytes`               | cAdvisor           | Pod memory usage       |
| `kube_pod_status_phase`                            | kube-state-metrics | Pod lifecycle          |
| `apiserver_request_duration_seconds`               | API Server         | Control plane latency  |
| `scheduler_scheduling_attempt_duration_seconds`    | Scheduler          | Scheduling performance |
| `kubernetes.io/node/cpu/core_usage_time`           | Cloud Monitoring   | Node CPU               |
| `DCGM_FI_DEV_GPU_UTIL`                             | DCGM               | GPU utilization        |

## Live Resource Usage (kubectl-only)

No MCP or gcloud equivalent exists for live resource usage. Use `kubectl top`:

```bash
kubectl top pods --all-namespaces --sort-by=cpu
kubectl top nodes
kubectl top pods --containers -n <NAMESPACE>  # per-container breakdown
```

## Cloud Logging (gcloud-only)

**Querying cluster logs** (no MCP equivalent — use `gcloud logging read`):

```bash
# System component logs
gcloud logging read \
  'resource.type="k8s_cluster" AND resource.labels.cluster_name="<CLUSTER_NAME>"' \
  --project <PROJECT_ID> --limit 50 \
  --quiet

# Workload logs for a specific namespace
gcloud logging read \
  'resource.type="k8s_container" AND resource.labels.cluster_name="<CLUSTER_NAME>" AND resource.labels.namespace_name="<NAMESPACE>"' \
  --project <PROJECT_ID> --limit 50 \
  --quiet

# Audit logs (who did what)
gcloud logging read \
  'resource.type="k8s_cluster" AND logName:"cloudaudit.googleapis.com"' \
  --project <PROJECT_ID> --limit 50 \
  --quiet
```

-   **Hot-object write contention and `409 Conflict` storms**: When frequent
    `409 Conflict` errors and high API server load suggest runaway controllers
    are fighting over or excessively patching a single Kubernetes object, query
    GKE Cloud Audit Logs (`cloudaudit.googleapis.com/activity`) grouped by
    `protoPayload.resourceName` and `protoPayload.methodName` (`update` or
    `patch`) to identify the specific object being hammered, and check
    `protoPayload.authenticationInfo.principalEmail` or
    `protoPayload.requestMetadata.callerSuppliedUserAgent` (or `kube-apiserver`
    component logs) to identify the responsible controller.
-   **End-to-end pod startup lifecycle timeline**: To determine whether a
    slow-starting pod was delayed during controller creation, scheduling,
    `kubelet` pickup, or container startup, reconstruct its timeline in Cloud
    Logging by correlating Kubernetes Events (`resource.type="k8s_pod"` or
    `k8s_event`) with Cloud Audit Logs (`cloudaudit.googleapis.com/activity`),
    optional control-plane component logs (`kube-scheduler`,
    `kube-controller-manager`, and `kube-apiserver` under
    `resource.type="k8s_control_plane_component"`), and node `kubelet` logs
    (`resource.type="k8s_node"`).

## Diagnostic Settings

For security monitoring and troubleshooting, enable control-plane audit logs:

```bash
# View current logging config
gcloud container clusters describe <CLUSTER_NAME> --region <REGION> \
  --format="yaml(loggingConfig)" \
  --quiet
```

### Control-Plane Component Logs & Slow Request Traces

`kube-apiserver` component logs (`API_SERVER`) are an **optional feature that is
not enabled by default** and must be explicitly turned on
(`--logging=SYSTEM,WORKLOADS,API_SERVER`); always mention this and link to
https://docs.cloud.google.com/kubernetes-engine/docs/how-to/view-logs#control_plane_logs
when recommending `apiserver` log analysis.

To diagnose which specific `kube-apiserver` requests were slow and why:

1.  **Search for `trace` or `Trace` entries**: Query `apiserver` component logs
    (`resource.type="k8s_control_plane_component" AND
    resource.labels.component_name="apiserver"`) for `trace` or `Trace` (for
    example, `textPayload:"Trace["`).
2.  **How to interpret trace logs**: `kube-apiserver` uses the upstream
    [`k8s.io/utils/trace`](https://github.com/kubernetes/utils/blob/master/trace/README.md)
    package (`trace.go`) to log requests that exceed a latency threshold
    (typically 500ms). Each trace header records the operation (`"List"`,
    `"Get"`, `"Create"`, `"Patch"`), `url`, `user-agent`, `audit-id`, `client`
    IP, start timestamp, and `total time`. Below the header, nested sub-traces
    appear in brackets `[...]` and sequential steps exceeding the step threshold
    appear as `---"<StepName>" <duration>ms`.
3.  **Example trace logs for typical problems**:
    -   **Slow etcd / storage read or write** (`List(recursive=true) etcd3` or
        `GuaranteedUpdate etcd3` dominates `total time`):
        ```text
        I1015 11:36:56.835120      10 trace.go:236] Trace[123456789]: "List" url:/api/v1/pods,user-agent:my-controller/v1.0.0,audit-id:11111111-2222-3333-4444-555555555555,client:10.0.0.1 (15-Oct-2026 11:36:49.460) (total time: 7374ms):
        Trace[123456789]: ["List(recursive=true) etcd3" 6890ms (11:36:49.461)]
        Trace[123456789]: ---"Objects listed" 6891ms (11:36:56.352)
        Trace[123456789]: ---"SerializeObject" 480ms (11:36:56.832)
        ```
    -   **Slow client / response streaming bottleneck** (`"Objects listed"` is
        fast, but `"SerializeObject"` and `---"Write call succeeded"` or
        `---"Write call failed"` dominate `total time` because a slow or
        bandwidth-constrained client takes seconds to read a large response
        payload):
        ```text
        I1015 11:40:12.104512      10 trace.go:236] Trace[987654321]: "List" url:/api/v1/pods,user-agent:slow-watcher/v0.1,audit-id:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee,client:10.0.0.2 (15-Oct-2026 11:40:01.002) (total time: 11102ms):
        Trace[987654321]: ---"Objects listed" 45ms (11:40:01.047)
        Trace[987654321]: ["SerializeObject" 11055ms (11:40:01.047)]
        Trace[987654321]: ---"Write call succeeded" 11054ms (11:40:12.101)
        ```
4.  **Upstream documentation & future evolution (always cite both)**: Always
    link to https://github.com/kubernetes/utils/blob/master/trace/README.md as
    the upstream OSS documentation for `trace.go`, and mention
    https://github.com/kubernetes/enhancements/tree/master/keps/sig-instrumentation/647-apiserver-tracing
    (KEP-647: APIServer Tracing) as a possible future change to how
    `kube-apiserver` traces are generated (via OpenTelemetry).

### Identifying Heavy API Server Clients from HTTP Access Logs

To identify which clients are generating the most load on `kube-apiserver`,
analyze the `httplog.go` HTTP access entries in `apiserver` component logs (an
**optional feature that must be explicitly enabled** via
`--logging=SYSTEM,WORKLOADS,API_SERVER`; always state this and link to
https://docs.cloud.google.com/kubernetes-engine/docs/how-to/view-logs#control_plane_logs):

1.  **Very stable `httplog.go` log structure (always mention this stability and
    show an example log line)**: Explicitly advise the user that the structure
    of `kube-apiserver` `httplog.go` logs is **very stable** across Kubernetes
    releases (making regex extraction and Log Analytics queries reliable), and
    include this example log line:
    ```text
    I1015 11:36:56.835535      10 httplog.go:137] "HTTP" verb="GET" URI="/api/v1/namespaces/default/pods" latency="7.374935s" userAgent="my-controller/v1.0.0 (linux/amd64)" audit-ID="11111111-2222-3333-4444-555555555555" srcIP="10.0.0.1:12345" apf_pl="workload-low" apf_fs="everybody" apf_iseats=1 apf_fseats=0 apf_additionalLatency="0s" apf_execution_time="7.374765s" resp=200
    ```
2.  **Key fields for client load analysis**:
    -   **`user_agent`** (`userAgent` in raw log text): Identifies the client
        binary, controller, or operator issuing the requests.
    -   **`verb`**: Distinguishes expensive request types (such as cluster-wide
        `LIST` or mutating `PATCH`/`UPDATE` calls) from lightweight `GET` calls.
    -   **`apf_iseats`** (along with `apf_fseats` and `apf_execution_time`):
        Reports the API Priority and Fairness (APF) initial concurrency seats
        occupied by the request; weighting or summing `apf_iseats *
        apf_execution_time` by `user_agent` and `verb` reveals which clients
        consume the most API server concurrency capacity.

## Alerting

Set up alerts for critical conditions:

Condition               | Metric                                              | Threshold
----------------------- | --------------------------------------------------- | ---------
High API server latency | `apiserver_request_duration_seconds`                | P99 > 5s
Pod crash loops         | `kube_pod_container_status_restarts_total`          | > 5 in 10min
Node not ready          | `kube_node_status_condition`                        | condition=Ready, status!=True
High GPU utilization    | `DCGM_FI_DEV_GPU_UTIL`                              | > 95% sustained
PVC near capacity       | `kubelet_volume_stats_used_bytes / capacity`        | > 85%
Scheduling failures     | `scheduler_schedule_attempts_total{result="error"}` | > 0

> **Prerequisite:** The `kube_*` series above (e.g., `kube_pod_status_phase`,
> `kube_pod_container_status_restarts_total`, `kube_node_status_condition`)
> come from **kube-state-metrics**, which GKE does not collect by default.
> Deploy the Managed Prometheus kube-state-metrics package first.

### Proposing Dashboards & Alerts (Production Rules)

When designing or proposing alerting and dashboard strategies for GKE:

1.  **Always explicitly name Google Cloud Monitoring** as the platform to
    implement these alerts and dashboards.
2.  **Always include API server latency** (via
    `apiserver_request_duration_seconds` metric) on the dashboard as a critical
    indicator of control plane health, alongside node CPU/Memory and pod crash
    loops.

### Node Health (Production Rules)

A comprehensive assessment of node health relies on analyzing these two metrics together:

1.  **`kubernetes.io/node/status_condition`** (filtered by `status_condition="Ready"`): Use this to track healthy nodes. Note that it will only report values for nodes that have successfully bootstrapped.
2.  **`compute.googleapis.com/instance_group/size`** (filtered by `instance_group_name="gke-<cluster_name>-.*"`): Use this to track the total number of nodes in a specific cluster. Note that it does not differentiate between healthy and unhealthy nodes.

### Control Plane Health (Production Rules)

To check whether Google considers a GKE cluster's control plane healthy, use the
**`kubernetes.io/cluster/kcp_healthchecks`** system metric (on the `k8s_cluster`
monitored resource, included in the default `SYSTEM` metrics package):

1.  **Metric semantics**: `kubernetes.io/cluster/kcp_healthchecks` is an
    incremental (`DELTA` / `CUMULATIVE` counter) metric sampled every 60 seconds
    that counts Google-internal control plane probes, labeled by boolean
    `success` (`"true"` or `"false"`).
2.  **Charting health ratio**: Because the metric is an incremental counter
    rather than a boolean gauge, chart control plane availability by dividing
    the rate of successful checks (`success="true"`) by the overall rate of
    checks across all `success` values:

```promql
sum by (project_id, location, cluster_name) (
  rate(
    kubernetes_io:cluster_kcp_healthchecks{
      monitored_resource="k8s_cluster", success="true"
    }[5m]
  )
)
/
sum by (project_id, location, cluster_name) (
  rate(
    kubernetes_io:cluster_kcp_healthchecks{
      monitored_resource="k8s_cluster"
    }[5m]
  )
)
```

## Cost Considerations

Monitoring and logging have associated costs:

-   **Cloud Logging**: Charged per GiB ingested beyond free tier (50
    GiB/project/month)
-   **Cloud Monitoring**: Free for GKE system metrics; custom metrics charged
    per time series
-   **Managed Prometheus**: Charged per samples ingested

To reduce costs in non-production:

```bash
# Reduce to system-only monitoring
gcloud container clusters update <CLUSTER_NAME> --region <REGION> \
  --monitoring=SYSTEM \
  --quiet
```

## Distributed Tracing & Continuous Profiling (Recommended)

**Not golden path defaults** — recommended for production microservice
architectures and performance-sensitive workloads.

-   **Cloud Trace**: Add OpenTelemetry SDK to your app with the
    `opentelemetry-operations-go` (or equivalent) exporter. Traces appear in
    Cloud Trace console. Identifies cross-service latency bottlenecks.
-   **Cloud Profiler**: Add the Cloud Profiler agent to your app. Profiles CPU
    and memory usage in production with low overhead. Identifies hotspots and
    compares across versions.

**Recent additions:**

-   **Managed OpenTelemetry for GKE (Preview)**: Managed in-cluster OTLP
    endpoint plus auto-instrumentation for traces, metrics, and logs. Requires
    GKE 1.34.1-gke.2178000+; enable with `gcloud beta container clusters
    update ... --managed-otel-scope=COLLECTION_AND_INSTRUMENTATION_COMPONENTS`.
-   **PSI (Pressure Stall Information) metrics**: cAdvisor
    `container_pressure_{cpu,memory,io}_{waiting,stalled}_seconds_total` series
    (beta in Kubernetes 1.34) can be collected via a Managed Prometheus
    `ClusterNodeMonitoring` resource; GKE's documented collection path requires
    GKE 1.35+.

## LQL Query Examples

Common Logging Query Language patterns for GKE troubleshooting:

```
# Error logs for a specific container
resource.type="k8s_container" AND resource.labels.container_name="my-app" AND severity>=ERROR

# OOMKilled events
resource.type="k8s_event" AND jsonPayload.reason="OOMKilling"

# Pod scheduling failures
resource.type="k8s_event" AND jsonPayload.reason="FailedScheduling"

# Audit logs (who did what)
resource.type="k8s_cluster" AND logName:"cloudaudit.googleapis.com"
```

## Troubleshooting Managed Prometheus (GMP)

Diagnose GMP ingestion, rule, and query problems. Stay read-only (`kubectl get`
/ `describe` / `logs`) and propose config changes; do not mutate live resources
directly.

### First: split ingestion-side vs query-side

Before anything else, query the `up` metric in the **Metrics Explorer PromQL
tab** in Cloud Monitoring. If `up` returns data, ingestion works and the problem
is query-side (Grafana / PromQL / permissions). If `up` is empty, the problem is
ingestion-side (collectors, scrape config, or write permission).

### Ingestion-side

1.  **Check GMP system pods.** They run in `gmp-system` on Standard clusters and
    `gke-gmp-system` on Autopilot. Look for `gmp-operator`, `collector`
    (DaemonSet), and `rule-evaluator` not `Running` or with high restarts:

    ```bash
    kubectl get pods -n gmp-system            # gke-gmp-system on Autopilot
    kubectl logs -n gmp-system -l app.kubernetes.io/name=collector -c prometheus
    ```

    A collector in `CrashLoopBackOff` with `OOMKilled` usually means high metric
    cardinality - drop unneeded series/labels (see cost section below) or apply a
    VPA to the collector.

2.  **Check PodMonitoring / ClusterPodMonitoring.** The three classic mistakes:
    - `spec.selector.matchLabels` does not match the target Pod labels.
    - A `PodMonitoring` only discovers targets **in its own namespace** - use
      `ClusterPodMonitoring` for cluster-wide scope.
    - `spec.endpoints.port` must reference the **named** container port (e.g.
      `port: web`), not the port number.

3.  **Enable target status for scrape errors.** Propose patching
    `OperatorConfig` in `gmp-public` with `features.targetStatus.enabled: true`;
    once applied, `kubectl describe podmonitoring <name>` and read `Active Targets`,
    `Unhealthy Targets`, and `Last Error` (for example `connection refused`, HTTP 404,
    `context deadline exceeded`). Disable it again when done - it can OOM the
    operator on large clusters.

### Permissions (403 / no data written)

GMP components inherit the **node service account**. Ingestion needs
`roles/monitoring.metricWriter` (error `Permission monitoring.timeSeries.create
denied` in collector logs); the `rule-evaluator` and query paths need
`roles/monitoring.viewer` (403 / `PermissionDenied`). If a query app (like
Grafana) uses Workload Identity, the bound Google service account also needs
`roles/monitoring.viewer`.

### Rule and alert evaluation

Rule scope is decided by the resource kind: `Rules` (single namespace),
`ClusterRules` (whole cluster), and `GlobalRules` (all data in the metrics
scope). You **must** use `GlobalRules` to write rules against Cloud Monitoring
metrics - a `Rules`/`ClusterRules` resource silently returns no data for them.
Check `rule-evaluator` logs (`-c evaluator`) for parse/permission errors.

### Query-side (Grafana / PromQL)

-   **Data source** must point at the GMP frontend query proxy, not
    `localhost:9090`, and the HTTP **Method must be GET** - `POST` fails with
    `no match[] parameter provided`.
-   **Grafana template variables:** use the two-argument form
    `label_values(<metric>, <label>)`; the single-argument
    `label_values(<label>)` is not supported by the GMP API.
-   **Cloud Monitoring metrics** that exist for multiple resource types need a
    `monitored_resource` label matcher, otherwise the query fails with
    `series selector must specify a label matcher on monitored resource name`.

### Cost, cardinality, and quota

Use the Cloud Monitoring **Metrics Management** page to find the metrics driving
billable samples and high cardinality. Reduce them with `metricRelabeling` in
the `PodMonitoring` (`action: drop` for whole metrics, `action: labeldrop` for
unbounded labels like `user_id`/`request_id`) or by raising the scrape
`interval`. `429` / `RESOURCE_EXHAUSTED` errors mean you have hit the Cloud
Monitoring API ingestion or query quota - optimize first, then request a quota
increase.

## Supporting Links

-   [GKE system metrics](https://docs.cloud.google.com/monitoring/api/metrics_kubernetes)
-   [GKE Observability Documentation](https://cloud.google.com/kubernetes-engine/docs/concepts/observability)
-   [Google Cloud Managed Service for Prometheus](https://cloud.google.com/stackdriver/docs/managed-prometheus)
-   [Troubleshoot Managed Service for Prometheus](https://docs.cloud.google.com/stackdriver/docs/managed-prometheus/troubleshooting.md.txt)
-   [Rule evaluation (Rules / ClusterRules / GlobalRules)](https://docs.cloud.google.com/stackdriver/docs/managed-prometheus/rules-managed.md.txt)
-   [Cloud Logging Query Language (LQL)](https://cloud.google.com/logging/docs/view/logging-query-language)
-   [Google Cloud Monitoring Alerts](https://cloud.google.com/monitoring/alerts)
