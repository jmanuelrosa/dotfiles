# DX metrics and feedback

When to read: the brief or diff touches build/typecheck/test timing, cache hit rates, flake and queue signals, or adoption or regression of the paved road.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Vanity metric over felt pain.** A number that does not map to a developer-felt wait (tasks defined, lines of config) optimizes the wrong thing.
  Check: each metric ties to a concrete wait (save-to-feedback, clean build, CI queue) or a concrete failure, not to activity volume.
- **Averages hiding the tail.** A mean build time hides the p95 that actually drives frustration and context-switching.
  Check: latency metrics report the distribution, not just the mean; the tail is visible.
- **Cache effectiveness uncontextualized.** A cache hit-rate reported without the miss cost or the population makes a regression invisible.
  Check: cache effectiveness is reported with the baseline and the cost of a miss, so a drop reads as time lost.
- **Measurement wired to ranking.** A metric attached to individual or team ranking gets gamed and destroys trust in the whole program.
  Check: DX metrics measure the system, not the person; they are not attached to individual performance.
- **No regression signal.** Build and typecheck times tracked but never alerted mean a slowdown is found by complaint, not by the metric.
  Check: a meaningful regression in a tracked latency triggers a signal, with the change window attached.
- **Instrumentation taxing the loop.** Collection that itself slows the inner loop or blocks a command defeats its own purpose.
  Check: collection is asynchronous, sampled if needed, and never on the critical path of a developer command.
- **Adoption assumed, not measured.** A tool declared "the standard" without measuring uptake hides that everyone bypasses it.
  Check: adoption of the blessed path is measured; a low rate is treated as evidence the path is worse than the bypass, not that people are wrong.
- **Single-metric optimization.** Optimizing one number (build time, PR throughput, cache hit-rate) without its guardrail invites gaming, and a metric that becomes a target stops measuring what it once did.
  Check: a speed or throughput metric is reported with its counter-metric (correctness, review quality, flakiness), never in isolation; no metric is optimized alone.
- **Framework as the goal.** Adopting a named model (SPACE, DORA, DX Core 4) as a dashboard without the decision it should inform produces numbers no one acts on.
  Check: each metric exists to answer a specific decision (is this investment paying off, where is the worst wait); published frameworks are cited for definition, not treated as the goal.

## Escalation triggers (`needs-decision`)

- Standing up a new DX-metrics collection pipeline or wiring developer telemetry (also an ask-first boundary in the agent; the telemetry backend is the sre seat's and raises privacy questions).
- Any metric that could be read as individual developer surveillance.

## What good looks like

- Every metric maps to a felt wait or a real failure, reported as a distribution, measuring the system not the person.
- Regressions signal automatically with the change window attached.
- Adoption is measured, and a low number indicts the tool, not the team.
