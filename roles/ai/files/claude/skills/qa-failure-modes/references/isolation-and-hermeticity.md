# Isolation and hermeticity

When to read: the brief or diff touches setup and teardown hooks, shared fixtures or module state, network or filesystem access, time and randomness.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Unrestored global.** Fake timers, module mocks, env vars, or monkey-patched globals left in place leak into whichever test runs next; failures then appear in innocent files.
  Check: everything a test alters is restored in that test's own teardown, and restoration runs even when the test fails.
- **Shared state by reference.** A fixture object defined once at module level and mutated per test couples tests through hidden state.
  Check: mutable fixtures are rebuilt fresh per test; module-level test data is frozen or copied before use.
- **Order dependence hidden by sequential runs.** Tests that pass in file order fail the day the runner shuffles, shards, or parallelizes, which is exactly when CI changes.
  Check: run the touched suite shuffled or in random order where the runner supports it; no test reads state a previous test wrote.
- **Real network or filesystem.** A test that hits a live service or a shared path flakes on someone else's uptime and risks real data.
  Check: network is intercepted at the project's mocking boundary; file IO goes to a per-test temp dir that teardown removes.
- **Wall-clock time.** Now, timezones, and date arithmetic make tests fail at midnight, month ends, and DST changes.
  Check: time is faked or injected; timezone-sensitive assertions pin an explicit zone; no test depends on real elapsed duration.
- **Unseeded randomness.** Random generators without a fixed or logged seed produce failures nobody can reproduce.
  Check: randomness is seeded and the seed surfaces in failure output.
- **Persistent state across runs.** Tests writing to a shared database or cache without per-test isolation pass once and fail on rerun or in parallel.
  Check: each test isolates its writes (transaction rollback, unique namespace or keys) and can run twice in a row and alongside itself.
- **Suite-scoped setup mutated by tests.** Resources created once per suite and mutated by individual tests turn execution order into an invariant.
  Check: suite-level setup holds only immutable resources or resets them between tests.

## Escalation triggers (`needs-decision`)

- Isolation requires infrastructure the project lacks, such as a network interception layer or a disposable test database (a new library is also an ask-first boundary in the agent).
- Existing tests you must touch depend on execution order; untangling them is a suite-wide change beyond the brief.

## What good looks like

- Any single test runs green alone, twice in a row, and inside a shuffled full-suite run.
- Teardown mirrors setup: nothing survives a test except its evidence.
- Time, randomness, and network are inputs the test controls, not ambient conditions.
