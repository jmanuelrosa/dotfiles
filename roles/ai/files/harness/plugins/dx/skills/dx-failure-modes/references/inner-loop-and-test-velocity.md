# Inner loop and test velocity

When to read: the brief or diff touches watch mode, test selection or sharding, local fixtures and seeds, or anything about inner-loop feedback speed.

This reference owns the speed and tooling of running tests, not what the tests assert: test design and coverage belong to the qa seat.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Whole-suite feedback on every change.** Running the entire suite for a one-package change taxes every save and pushes people to stop running tests locally.
  Check: the inner loop runs only the tests affected by the change (watch plus affected selection); the full suite is a CI concern, not an inner-loop one.
- **Watch mode that misses changes.** A watcher that ignores generated files, linked packages, or config changes gives false-green while the developer edits code it never re-ran.
  Check: watch re-runs on every input that affects the result, including regenerated and cross-package inputs.
- **Non-hermetic local tests.** Tests depending on a shared local database, ambient env, or a running service pass or fail by machine state, not by code.
  Check: local tests provision their own isolated state (ephemeral store, fixtures, fakes); order and parallelism do not change the result.
- **Non-deterministic seeds and fixtures.** Fixtures built from real time, random data, or live network calls flake and cannot be reproduced from a failure.
  Check: seeds are deterministic and reproducible from a recorded seed value; no inner-loop test reaches the network.
- **Startup cost dominating.** A per-test cost that dwarfs the assertion (booting a full app, recompiling from scratch) makes the loop slow regardless of selection.
  Check: expensive setup is shared or precompiled once; the marginal cost of one more test is small.
- **Flake normalized.** A known-flaky test blanket-retried or ignored locally trains people to distrust red, so real failures are waved through.
  Check: flakiness is fixed or quarantined under a tracked owner, never retried into green on the inner loop.
- **Local and CI invocation diverge.** Different runners, flags, or env between local and CI produce pass-locally-fail-in-CI and its reverse.
  Check: local and CI call the same test entry point with the same config; only selection and parallelism differ.
- **No fast path to reproduce a CI failure.** A CI-only failure with no single local command to reproduce it burns cycles in push-and-watch.
  Check: any CI test failure maps to one local command that reproduces it deterministically.

## Escalation triggers (`needs-decision`)

- Changing the test runner or the local test-data and provisioning mechanism (also an ask-first boundary in the agent).
- A change that would weaken what CI enforces in the name of local speed (that gate belongs to qa and platform, not to a speed knob).

## What good looks like

- Save-to-signal on the inner loop is fast because only affected tests run, hermetically.
- Red locally means red in CI and the reverse; one command reproduces any CI failure.
- Flake is owned and quarantined, never retried into a false green.
