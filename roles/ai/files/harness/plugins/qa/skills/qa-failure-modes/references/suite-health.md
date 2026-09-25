# Suite health

When to read: the brief or diff touches test runner or framework config, shared test utilities, suite speed, parallelism, or reporters.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Config change with suite-wide blast radius.** A runner config edit (setup files, environment, globals, transforms) changes the semantics of every test, not just the ones in the brief.
  Check: state the intended effect of each config change and run the full affected suite, not only the tests you were working on.
- **Silent test discovery loss.** A glob, match, or ignore change that quietly stops collecting some tests keeps CI green while coverage vanishes.
  Check: compare collected test counts before and after any discovery-affecting change; the difference must equal what you intended.
- **Slow suite eroding signal.** Expensive setup repeated per test and independent tests run serially turn minutes into the reason people stop running the suite.
  Check: expensive immutable setup is shared through the framework's fixture mechanism; mutable state stays per test; independent tests can run in parallel.
- **Parallel-unsafe speedup.** Enabling workers or shards without checking for port, database, or filesystem collisions converts speed into flakes.
  Check: before enabling parallelism, verify shared resources are isolated per worker: unique ports, databases, namespaces, temp dirs.
- **Duplicated helpers.** A second render wrapper, assertion helper, or setup utility beside an existing one forks conventions and doubles maintenance.
  Check: extend the existing utility, keeping it shallow enough that what is asserted stays visible at the call site; if two already exist, flag the fork in the report rather than adding a third.
- **Global setup as dumping ground.** Setup files loading seeds, mocks, and polyfills only some tests need make every test pay for all of it and couple everything to everything.
  Check: global setup holds only what every test truly needs; anything else moves to targeted fixtures.
- **Swallowed diagnostics.** Reporters or helpers that truncate errors, hide output, or rethrow without context make CI failures undebuggable.
  Check: a deliberately failed test shows the assertion diff, the test name, and enough context to diagnose without a local rerun.
- **Focused or skipped tests committed.** A committed focus marker (`.only` and equivalents) makes CI silently skip everything else; skipped, todo, and commented-out tests linger as coverage holes with no owner.
  Check: no focus marker anywhere in the diff; inventory the skips already present in touched suites and list them in the report; never add one yourself outside the quarantine path.
- **Many behaviors in one test.** A test asserting several unrelated behaviors obscures which one failed and reads as one undiagnosable red.
  Check: one behavior per test; when a test accumulates unrelated assertions, split it so a failure names its cause.

## Escalation triggers (`needs-decision`)

- A config change whose blast radius exceeds the suites the brief names: report the affected scope with a recommendation.
- Adding a new reporter, plugin, or runner dependency (also an ask-first boundary in the agent).
- Sharding or parallelizing the CI test jobs themselves: propose it; the platform seat applies the pipeline change (also an ask-first boundary in the agent).

## What good looks like

- The suite runs fast enough that running it is never the reason to skip it.
- One way to do everything: one render wrapper, one factory idiom, one assertion helper.
- A CI failure is diagnosable from its output alone.
