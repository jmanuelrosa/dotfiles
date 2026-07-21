# Quality gates

When to read: the brief or diff touches expectations, quality checks, quarantine paths, validation steps, or anomaly detection.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Warning theater.** Checks that log or alert but never fail the run; bad data propagates while the pipeline looks diligent.
  Check: expectations run as pipeline steps whose failure stops downstream tasks; any warn-only check states why propagation is acceptable.
- **Gate after publication.** Quality checks run after the output is visible, so consumers read bad data during the gap.
  Check: gates sit between compute and publish (write-audit-publish, staging then swap); the published location only ever holds validated data.
- **Trivial coverage.** A row-count-above-zero check stands guard while keys, amounts, and timestamps go unvalidated.
  Check: the columns consumers depend on (keys, join columns, money, timestamps, aggregated measures) carry type, nullability, uniqueness, range, and referential or valid-set expectations.
- **Silent null flood.** A bad join or source drift turns a column mostly null; every check passes because null is technically valid.
  Check: null-rate expectations (absolute or against history) exist on critical columns, not just not-null on required ones.
- **Volume anomaly unwatched.** A run that processes a hundred rows where yesterday processed a million passes every row-level check; the failure is upstream.
  Check: volume expectations compare against history or declared bounds, and a breach blocks or quarantines rather than only alerting.
- **Duplicate keys tolerated.** Uniqueness of the declared identity keys is never asserted, so idempotency regressions arrive silently as double rows.
  Check: declared identity and dedup keys carry a uniqueness expectation.
- **Quarantine as black hole.** Rejected rows land in a quarantine location nobody monitors or replays, converting loud failures into silent drops.
  Check: quarantine has a depth metric, an owner, and a replay path, and the quarantine-vs-fail choice is stated per gate.
- **Gate loosened to pass.** A failing expectation "fixed" by widening the threshold until it goes green.
  Check: any loosening carries evidence the data legitimately changed; weakening a failing gate to get green is a never boundary in the agent, so a legitimate recalibration escalates instead.

## Escalation triggers (`needs-decision`)

- Removing or loosening an existing quality gate (also an ask-first boundary in the agent).
- A gate the brief demands that would block on data conditions outside the pipeline's control.
- Thresholds that need domain knowledge the code lacks: propose values with reasoning, ask.

## What good looks like

- Bad data stops inside the pipeline; consumers only ever see validated output.
- Every gate is a step that can fail the run, with quarantine as a deliberate, monitored alternative.
- Coverage follows what consumers depend on, not what is convenient to check.
