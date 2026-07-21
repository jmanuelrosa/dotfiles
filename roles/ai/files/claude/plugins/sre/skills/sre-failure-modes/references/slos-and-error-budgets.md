# SLOs and error budgets

When to read: the brief or diff touches SLI definitions, SLO targets and windows, error budgets, burn-rate math, or SLO tooling configs.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **SLI on a machine signal, not user experience.** An SLO on CPU, memory, or restarts guards the infrastructure while users see errors it never counts.
  Check: the SLI measures what a user experiences (success ratio, latency at a percentile, freshness), from a vantage point as close to the user as the stack allows.
- **Unmeasurable SLO.** A target with no named query is a wish; nobody can compute compliance or budget burn.
  Check: every SLO states its exact SLI query or measurement, the target, and the window; the implied error budget is written out (allowed bad events or bad minutes per window).
- **Average where the SLO speaks percentile.** A mean-latency SLI reports health while the p99 the SLO promises is on fire; means on skewed distributions lie by design.
  Check: the SLI aggregation matches the SLO's stated percentile; averages appear nowhere in the compliance math.
- **Buckets that cannot compute the target.** A latency histogram with no bucket boundary at the SLO threshold makes the SLI uncomputable; interpolation quietly invents compliance.
  Check: a histogram bucket boundary sits exactly at each SLO threshold, or the SLI derives from a source that records exact values.
- **Budget with no policy.** An error budget nobody acts on is decoration; the point is a pre-agreed consequence when it empties.
  Check: the SLO definition or its doc states what happens at budget exhaustion (feature freeze, reliability work first) and who enacts it, or the report flags the missing policy as a gap; you surface budget status, humans enact the consequence.
- **100% or copy-paste target.** A target of 100%, or one inherited from another service, has no cost-of-nines reasoning behind it and will be either violated immediately or met trivially.
  Check: the target traces to user needs or a measured baseline; the recommendation carries the math (current performance, cost of the next nine).
- **SLO blind to low traffic.** Ratio SLIs over sparse traffic swing wildly; one bad request at 3am burns a day of budget and pages someone for nothing.
  Check: the window and alerting math account for real traffic volume; low-traffic services get longer windows, event-based budgets, or synthetic traffic, stated explicitly.
- **SLI computed downstream of lossy telemetry.** An SLI built on sampled, aggregated, or delayed data measures the pipeline, not the service.
  Check: the SLI's data source is complete for the events it counts; any sampling or aggregation upstream of it is stated and justified.

## Escalation triggers (`needs-decision`)

- Setting or changing an SLO target or window (also an ask-first boundary in the agent): bring the recommendation with the math.
- An SLI the current telemetry cannot compute: specify what the implementer seats must emit; do not add app instrumentation yourself.
- A budget-exhaustion policy decision (what ships or freezes when the budget empties).

## What good looks like

- Each SLO reads in one place, whatever the format: service, SLI query, target, window, budgeting method, implied budget, and the policy at exhaustion, defensible in a review.
- The SLI would move if users suffered and stay flat if only machines did.
- SLO tooling (OpenSLO, Sloth, vendor SLO configs) generates the recording and alert rules from the definition, so the math lives in exactly one place.
