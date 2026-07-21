# Failure visibility

When to read: any new or changed build task, cache, codegen step, script, or internal CLI; and whenever the brief or diff touches how a failure is reported to the developer or CI.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The swallowed script error.** A script or task that continues past a failed step, or masks a non-zero exit, ships a broken toolchain that looks green.
  Check: every step propagates its failure and exits non-zero; no `|| true`, ignored error, or masked pipe hides a real failure.
- **The cryptic failure.** A build or CLI that fails with no actionable message wastes every developer who hits it.
  Check: failure output says what broke, why, and where, and points at the fix; the message is written for the next developer, not for you.
- **The silent green.** A cache hit, a skipped affected-task, or a filtered job that lets a real failure pass keeps the gate green over broken code.
  Check: a cache hit reproduces a cache miss; affected-task selection cannot skip a failing test; no job silently skips while the merge gate stays green.
- **Undetected drift.** Generated output that has drifted from source, checked in by hand, breaks consumers with no warning.
  Check: drift is caught by a check that fails loudly, not by a human noticing later.
- **Context-free CI logs.** A failure with no identity in a large matrix is hard to trace.
  Check: logs identify the package, task, and input so the failing unit is obvious.

## Escalation triggers (`needs-decision`)

- Adding or changing a reporter, log destination, or CI annotation others depend on.
- Introducing a build-metrics or developer-telemetry pipeline (privacy and backend reach beyond this seat).
- Feedback the brief needs that the toolchain has no pattern for yet.

## What good looks like

- A red build tells the developer what broke and how to fix it, first try.
- A green build means green: no swallowed error, no silently skipped work.
- Drift, flake, and cache mismatches surface as failing checks, not as folklore.
- The inner loop fails fast and legibly, so the paved road stays trusted.
