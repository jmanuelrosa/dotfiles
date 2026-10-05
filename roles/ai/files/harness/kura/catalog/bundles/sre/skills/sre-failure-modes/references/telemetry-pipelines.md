# Telemetry pipelines

When to read: the brief or diff touches collector or agent configs, exporters, receivers, processors, pipeline wiring, or telemetry egress.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Component defined but not wired.** A receiver, processor, or exporter declared in config but absent from a pipeline's chain does nothing, silently, while the config validates.
  Check: every declared component appears in exactly the pipelines that should use it; trace the path from each receiver to its exporter by hand.
- **Missing or misordered safety processors.** A collector without memory protection ordered first (memory_limiter, in OTel terms) OOMs under load spikes and drops everything, exactly when telemetry matters most.
  Check: resource-protection and batching processors exist and are ordered per the collector's documented requirements.
- **Silent loss at the exporter.** Default queue and retry settings drop data on backend backpressure without an error anyone sees.
  Check: exporter queue size, retry policy, whether the queue survives a restart, and the behavior when the queue is full are stated choices, and the pipeline's own health metrics (throughput, drops, queue depth) feed an alert.
- **Sampler dropping the wrong traffic.** A pipeline-level sampler configured for volume rather than value drops error traces and tail latency (see the tracing reference); samplers stacked at SDK and pipeline multiply.
  Check: end-to-end sampling across SDK and pipeline is computed as one number, and error and latency retention survives the whole chain.
- **Tail sampling with a broken topology.** Tail sampling only works if every span of a trace reaches the same collector instance with time to decide; per-instance sampling or missing trace-ID-aware routing yields incomplete, wrong decisions.
  Check: tail sampling runs at a single gateway tier fed by trace-ID-aware load balancing, with an explicit decision wait; per-agent tail sampling escalates.
- **Aggregation that erases the SLI.** A processor that drops labels, converts histogram types, or pre-aggregates can make downstream SLO math impossible.
  Check: transformations preserve the labels and bucket boundaries that SLOs, alerts, and dashboards consume downstream.
- **Egress nobody priced.** Duplicating signals to a second backend, or enabling a verbose signal, changes the bill and the data-residency story.
  Check: new exporters and signal fan-outs state their cost and data-destination implications; adding a vendor, exporter, or agent escalates.
- **Pipeline change that orphans consumers.** Renaming, re-namespacing, or rerouting telemetry breaks every dashboard, alert, and SLO that consumed the old shape.
  Check: anything that changes metric names, label sets, or destinations enumerates its downstream consumers or escalates.
- **Config that parses but cannot start.** Collector configs that validate as YAML still fail at boot on unknown keys or missing credentials, taking the whole telemetry path down with them.
  Check: validate with the collector's own dry-run or validate command where one exists; state in the report how the first real deploy will be watched.

## Escalation triggers (`needs-decision`)

- Adding a new observability vendor, exporter, or agent (also an ask-first boundary in the agent).
- Sampling or aggregation changes that discard data (also an ask-first boundary in the agent).
- Rerouting telemetry to a different backend or changing what leaves the network.

## What good looks like

- The pipeline is monitored like a service: its own throughput, drop, and queue metrics feed an alert someone owns.
- Every point of data loss is a decision with a name on it, never a default.
- One readable config (or diagram) shows each signal's path from SDK to backend, and reality matches it.
