# Test data and fixtures

When to read: the brief or diff touches factories, fixtures, seed data, builders, fake data generators, or test databases.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Parallel data idiom.** Hand-rolled object literals beside an established factory (or a new factory beside established literals) fork the data conventions; the next schema change misses one side.
  Check: new test data goes through the project's existing factory or fixture idiom; extend it rather than bypass it.
- **Irrelevant data noise.** A test that builds thirty fields to assert on two hides which inputs the behavior depends on.
  Check: the test body states only the fields the behavior depends on; everything else comes from factory defaults.
- **Factory drift from real shapes.** Defaults that no longer match what production produces (missing new required fields, retired enum values, impossible combinations) make tests pass on data that cannot exist.
  Check: factory output validates against the current schema, type, or contract; fix drifted defaults instead of loosening assertions around them.
- **Fixture coupling.** Many tests sharing one broad fixture means any fixture change ripples through unrelated tests; DRY in test data trades away diagnosability.
  Check: shared fixtures hold only genuinely invariant setup; behavior-specific data lives in the test that needs it.
- **Hidden magic values.** Assertions that depend on a fixture value defined three files away make failures unreadable.
  Check: values asserted on are visible in or traceable from the test body, via named constants or factory overrides at the call site.
- **Assumed seed state.** Tests that rely on a dataset nothing in their setup chain creates work only on machines where someone ran the seed script.
  Check: every dataset a test needs is created by the test's own setup chain: fixture, factory, or a seed the suite itself invokes.
- **Colliding identifiers.** Tests reusing the same email, ID, or filename collide under parallel runs and reruns.
  Check: identifiers are unique per test invocation and per worker, via UUIDs or values namespaced by worker and run; a fixed seed or a per-process sequence reproduces the same identifiers in parallel and on rerun.
- **Real user data in fixtures.** Copied production records put personal data in the repo and tie tests to records that change.
  Check: fixtures are synthetic; anything resembling a real person or account is replaced.

## Escalation triggers (`needs-decision`)

- The project has no data idiom and one must be chosen; introducing a factory library is a new dependency (also an ask-first boundary in the agent).
- Contract-valid data needs a schema or generated artifact that is stale or missing; regenerating it touches application source, so specify the fix for an implementer seat (also an ask-first boundary in the agent).

## What good looks like

- A reader sees exactly which data the behavior depends on and nothing else.
- Factories produce contract-valid objects by default; tests override only what they test.
- Any test runs in parallel with itself without data collisions.
