# Assertion strength

When to read: the brief or diff touches any new or modified test; assertions, snapshots, negative or error-path expectations.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Unawaited async assertion.** A promise-returning assertion or action that is not awaited resolves after the test ends; the test passes whatever the outcome (the failure eslint-plugin-jest `valid-expect` and floating-promise lint rules exist to catch).
  Check: every promise-returning assertion and action is awaited or returned; break the behavior and confirm the test actually goes red.
- **Asserting the mock you configured.** The test stubs a return value and then asserts that value came back; it proves the mocking framework works, not the code.
  Check: trace each asserted value to logic in the code under test; if deleting the subject's logic would still pass, rewrite the test.
- **Expect inside a conditional or dead callback.** An assertion behind an `if`, inside a catch that never fires, or in a callback that never runs executes zero assertions and passes (the smell behind jest `no-conditional-expect` and `expect-expect`).
  Check: assertions run unconditionally on the test's main path; error-path tests use the framework's rejects idiom or an assertion count so a missing failure fails the test.
- **Any-throw negative test.** Asserting only that something throws passes on typos, wrong argument counts, and unrelated crashes.
  Check: negative tests pin the specific error type, code, or message fragment the behavior contract promises.
- **Implementation-echo oracle.** Expected values produced by running the code and pasting its output (including values interpolated into inline snapshots) ratify what the code does, not what it should do; the test passes by construction.
  Check: every expected value traces to the brief, a spec, or a contract; when no oracle exists, escalate instead of inventing one from the implementation.
- **Blind snapshot.** A snapshot updated to get green ratifies whatever the code does now, bug included; an unreviewable giant snapshot is asserted by nobody.
  Check: every snapshot change in the diff is read and explainable; prefer small focused snapshots or explicit assertions on the fields that matter.
- **Assertion-free execution.** The test calls the code and asserts nothing beyond "no exception escaped", producing coverage with no verified outcome.
  Check: each test asserts at least one observable outcome of the behavior its title names.
- **Weak matcher.** Truthy, defined, or not-null checks where the exact value is knowable let wrong values pass silently.
  Check: assert the most specific value or shape the contract defines.
- **Title that diagnoses nothing.** "works", "handles data", "test 2" tell the engineer staring at red nothing about which behavior broke.
  Check: the title names the behavior and the expected outcome, so a failure reads as a spec violation.

## Escalation triggers (`needs-decision`)

- The expected behavior is unspecified or the brief contradicts what the code observably does: report the discrepancy with the evidence instead of picking an interpretation silently.
- The only way to make the test able to fail is a testability change in application source, such as an export or an injection seam (also an ask-first boundary in the agent).

## What good looks like

- Every test was seen failing with a message that names the broken behavior before it was seen passing.
- Assertions pin outcomes at the strongest specificity the contract defines.
- A reviewer can read any test and say which defect it exists to catch.
