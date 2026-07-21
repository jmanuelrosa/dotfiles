---
name: qa-failure-modes
description: >-
  Failure-mode checklists for test and QA implementation work, split by domain.
  Use when writing or reviewing tests, fixtures, factories, mocks, e2e flows, test infrastructure,
  or when diagnosing flakes and analyzing coverage gaps.
  Read only the reference files whose triggers match the change.
---

# QA failure modes

Checklists of the ways tests go wrong: pass without proving anything, flake, leak state, or erode the suite's signal, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Any new or modified test; assertions, snapshots, negative or error-path expectations | [references/assertion-strength.md](references/assertion-strength.md) |
| Setup and teardown hooks, shared fixtures or module state, network or filesystem access, time and randomness | [references/isolation-and-hermeticity.md](references/isolation-and-hermeticity.md) |
| A flake investigation; async assertions, condition waits, timing-sensitive tests, quarantine proposals | [references/flakiness-and-async.md](references/flakiness-and-async.md) |
| Factories, fixtures, seed data, builders, fake data generators, test databases | [references/test-data-and-fixtures.md](references/test-data-and-fixtures.md) |
| Mocks, stubs, spies, fakes, network interception, contract fixtures, what gets mocked and where | [references/mocking-and-boundaries.md](references/mocking-and-boundaries.md) |
| Any e2e or browser test; selectors, auth or session state, base URLs, cross-test data flow | [references/e2e-and-selectors.md](references/e2e-and-selectors.md) |
| A coverage-gap brief; error paths, boundary values, negative cases, coverage reports | [references/coverage-and-gaps.md](references/coverage-and-gaps.md) |
| Test runner or framework config, shared test utilities, suite speed, parallelism, reporters | [references/suite-health.md](references/suite-health.md) |
| Diagnostic failure messages, false greens, secrets or real data in tests, masked flakes | [references/failure-visibility.md](references/failure-visibility.md) |

Most real changes fire two or three rows (a typical test-writing brief fires at least assertion-strength, isolation-and-hermeticity, and test-data-and-fixtures).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the test lies, flakes, or erodes the suite, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: runner- and framework-specific guidance belongs to the stack skills the caller has installed, not here.
The test-first method belongs to the `test-driven-development` skill; CI pipeline config for flakes (retry settings, merge-gate quarantine) belongs to `platform-failure-modes`.
These files are checks against a diff: the test code side of the line.
