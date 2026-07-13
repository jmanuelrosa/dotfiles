# Coverage and gaps

When to read: the brief is a coverage-gap analysis, or the diff touches error paths, boundary values, negative cases, or coverage reports.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Coverage theater.** Lines executed with no assertion on their outcome raise the number and verify nothing; coverage measures execution, not verification.
  Check: for each newly covered path, ask which mutation of its logic some test would catch; if none, the path is executed, not tested.
- **Happy-path-only coverage.** Error, empty, null, and partial-failure branches are where incidents live and where coverage is thinnest.
  Check: each behavior touched has its failure and empty cases tested, not just success.
- **Boundary blindness.** Defects cluster at edges: zero, negative, empty collections, maximum sizes, off-by-one on limits.
  Check: inputs with a documented or implied range are tested at, just below, and just above the boundary.
- **Missing negative cases.** A validator or guard tested only with accepted input proves nothing about what it rejects.
  Check: every acceptance test has rejection counterparts pinning the specific promised failure (specificity rules live in assertion-strength).
- **Gaming the threshold.** Trivial tests on easy lines satisfy a coverage gate while the risky branch stays dark.
  Check: coverage additions target the riskiest uncovered behavior; the report names what remains uncovered and why.
- **Testing the framework.** Verifying that the language, ORM, or library behaves as documented burns budget without covering this project's decisions.
  Check: each test exercises a decision this codebase made.
- **Duplicated coverage across layers.** A higher-level test re-verifying a behavior a lower level already proves adds runtime and maintenance with no new confidence.
  Check: confirm the behavior is not already covered one level down before adding a test; propose removing redundant higher-level tests through the ask-first path.
- **Change-detector tests.** A test mirroring the implementation line by line fails on every edit and catches nothing; it verifies that the code is the code.
  Check: the test still passes under any refactor that preserves the behavior its title names.
- **Contrived-input coverage.** Unreachable branches covered via inputs production can never produce inflate the number and confuse readers.
  Check: inputs are producible by real callers; an unreachable branch is reported as possible dead code for an implementer seat, not covered by force.

## Escalation triggers (`needs-decision`)

- A meaningful gap cannot be covered without a testability change in application source: specify it for an implementer seat (also an ask-first boundary in the agent).
- Adding or changing a coverage threshold in CI config: propose it; the platform seat or caller applies it (also an ask-first boundary in the agent).
- Gap analysis reveals dead code or an unhandled error path in the product: report the finding; the fix belongs to an implementer seat.

## What good looks like

- Coverage work is prioritized by risk, not by the easiest uncovered lines.
- Every newly covered branch has an assertion a mutation of that branch would trip.
- The report is honest about what stays uncovered and why.
