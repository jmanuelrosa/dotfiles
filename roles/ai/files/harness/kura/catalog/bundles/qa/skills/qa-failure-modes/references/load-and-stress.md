# Load and stress

When to read: the brief or diff touches a load, stress, spike, soak, or benchmark script; throughput or latency targets; or a performance claim that needs measured evidence under concurrency.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Wrong test type for the question.** A soak question answered with a ten-minute run, or a capacity question answered with a smoke run, produces a confident number about something nobody asked.
  Check: the script names its question and the type that answers it: smoke (the script works at minimal load), load (expected peak meets its targets), stress (where and how it breaks), spike (a sudden surge and the recovery after it), soak (degradation over hours: leaks, pool exhaustion, growing queues).
- **Closed model hiding latency.** A fixed pool of virtual users or connections waits for each response before sending the next, so when the server slows the offered load drops with it, and the tail latency real users would see is never measured (coordinated omission).
  Check: arrival-driven traffic (independent users, public APIs, webhooks) is modelled with a constant or ramping arrival rate; a fixed pool is used only for a genuinely bounded client population, and the report says which model and why.
- **Load generator as the bottleneck.** A saturated generator caps throughput and inflates latency, so the run measures the client instead of the system under test.
  Check: generator CPU, memory, and network stay well clear of saturation during the run, and the tool reports no dropped iterations or exhausted virtual users; otherwise reduce the rate or distribute the generator.
- **Averages and cold starts.** A mean hides the tail users feel, and a run that includes JIT, cache, and pool warm-up reports a startup cost as steady state.
  Check: results report p95 and p99 latency, the maximum, and the error rate, measured after a warm-up period that thresholds exclude.
- **Thresholds invented in the script.** A pass/fail number picked to fit the first run turns the test into a recording of whatever the system did that day.
  Check: every threshold traces to an SLO, a written requirement, or a recorded baseline from the same environment, and the script or report names its source.
- **Errors counted as throughput.** A fast 500, 429, or empty body inflates requests per second and lowers latency, so a failing system reads as a fast one.
  Check: each response is validated for status and a body property the behavior promises; error rate is a threshold of its own; rate-limited responses are counted and reported separately.
- **Unrealistic traffic shape.** One endpoint, one id, one user hammered in a loop measures a warm cache and a single hot row, not production.
  Check: ids, users, and payloads are parameterized from data shaped like production; the endpoint mix is weighted to observed traffic where it is known; think time exists where real clients pause.
- **Number with nothing to compare.** A single figure from an unrecorded machine and data volume proves nothing and cannot detect a regression.
  Check: results are compared against a baseline taken with the same script version, environment, and data volume, and the environment and data volume are recorded beside the results.
- **Run with no stop condition.** A stress or spike run that breaks the target and keeps going turns a test into an outage, and an open-ended soak never finishes in CI.
  Check: every scenario has a fixed duration or iteration cap and aborts early when the error-rate threshold is breached.
- **Hardcoded target or credentials.** A host or token inlined in the script points every run at one environment, possibly production.
  Check: target URL, rate, duration, and credentials come from environment or config; the default target is a local or ephemeral environment.

## Escalation triggers (`needs-decision`)

- The run targets anything other than a local or ephemeral environment the run itself started (shared dev, staging, production, a third-party API): name the target, peak rate, duration, and who shares it; a human approves and schedules it (also an ask-first boundary in the agent).
- No SLO, requirement, or baseline exists to derive thresholds from: propose numbers with the reasoning; the SRE seat or the caller owns the target.
- The run exposes a product defect (errors under load, a leak, pool or connection exhaustion): report it under Product bugs found with the scenario and rate that reproduce it; the fix belongs to an implementer seat.
- Making a load run a CI job or merge gate: propose the job; the platform seat applies it (also an ask-first boundary in the agent).

## What good looks like

- Each script states its question, its workload model, and where every threshold comes from.
- The same script, data, and environment produce comparable numbers, stored beside the baseline they are judged against.
- A stress run ends in one sentence: the first resource that saturated, and the load at which it did.
