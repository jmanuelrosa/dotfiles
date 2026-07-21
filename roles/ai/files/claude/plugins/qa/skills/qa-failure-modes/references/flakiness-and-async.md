# Flakiness and async

When to read: the brief is a flake investigation, or the diff touches async assertions, condition waits, timing-sensitive tests, or quarantine proposals.
This file owns the test-code side of flakes; retry settings and merge-gate quarantine in pipeline config belong to the platform seat and `platform-failure-modes`.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Sleep where a condition wait exists.** A fixed sleep is simultaneously too long (slows every run) and too short (flakes under load).
  Check: every wait targets a condition (element state, predicate, event), never a duration; replace sleeps you find in touched tests with the condition they were approximating.
- **Timeout bump as a fix.** Raising a timeout hides the race and converts a fast failure into a slow one.
  Check: any timeout change traces to a measured cause, such as an operation that legitimately got slower, never to an unexplained flake.
- **Race between action and assertion.** Asserting immediately after triggering async work reads intermediate state: green on a fast laptop, red in CI.
  Check: assertions use the framework's retrying idiom against the settled state; a value sampled once and then asserted is a race.
- **Fire-and-forget work escaping the test.** Unawaited async work in the subject lands after the test finishes, failing the next test or logging unhandled rejections.
  Check: the test drains pending work (timer flush, event-loop tick, explicit hook) before teardown.
- **Re-run into green.** Rerunning a flaky test until it passes ships the race; frequency is not a fix.
  Check: a flake gets a named root cause (race, leaked state, timing assumption, external dependency) in writing before any other action.
- **Quarantine without evidence.** Skipping a flaky test with no reason, owner, or reproduction leaves a silent coverage hole forever.
  Check: a quarantine proposal carries the failure output, the suspected root cause, the reproduction rate over n runs, the project's flake analytics where they exist, and the coverage lost; the decision belongs to a human (also an ask-first boundary in the agent).
- **Flake masking a product bug.** Some flakes are real races in the application; stabilizing the test around one hides the defect.
  Check: decide whether the nondeterminism lives in the test or the subject; a subject race becomes a Product bugs found entry with the failing evidence, not a test tweak.
- **Repeat run never attempted.** First-order flakiness is detectable locally with the runner's repeat flag; CI should not be the discovery mechanism.
  Check: new e2e and integration tests ran more than once before handoff, as the agent's Stability gate requires.

## Escalation triggers (`needs-decision`)

- Quarantining or deleting an existing flaky test: bring the evidence; a human decides (also an ask-first boundary in the agent).
- The root cause is a race in application source: report it as a product bug proven by the test; the fix belongs to an implementer seat.
- The flake originates in CI infrastructure (runner resources, sharding, retry config): propose the pipeline change for the platform seat to apply (also an ask-first boundary in the agent).

## What good looks like

- Every wait in the suite names the condition it waits for.
- A flake investigation ends in exactly one of: a test-code fix, a product-bug report, or an evidence-backed quarantine proposal.
- Nothing in the diff makes a failure less likely to be seen; only less likely to occur.
