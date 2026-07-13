# E2e and selectors

When to read: the brief or diff touches any e2e or browser test; selectors, auth or session state, base URLs, or cross-test data flow.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Unjustified e2e.** A defect catchable in a unit or integration test written as e2e pays browser runtime and flake surface on every CI run forever.
  Check: each new e2e test states why a lower pyramid level cannot catch the defect; "more realistic" alone does not qualify.
- **Styling-coupled selectors.** Selecting on CSS classes, DOM structure, or positional indexes breaks on any restyle with no behavior change.
  Check: selectors use the project's stable strategy (roles and accessible names, or its test-id convention); no selector depends on presentation.
- **Inter-test data dependence.** A test consuming a record another test created breaks mysteriously under sharding, filtering, or an upstream failure.
  Check: each e2e test creates or seeds everything it needs and can run alone and first.
- **UI-driven setup.** Building preconditions by clicking through screens multiplies runtime and flake surface for state the test does not verify.
  Check: preconditions arrive via the fastest trusted channel (API calls, seeded fixtures, stored session state); only the behavior under test goes through the UI.
- **Login in every test.** Authenticating through the UI per test is slow and makes the auth flow a dependency of the whole suite.
  Check: tests reuse the framework's session or storage-state mechanism; the login flow itself has its own dedicated test.
- **Hardcoded environment.** Base URLs, hosts, or accounts inlined in tests break every environment but one and risk pointing at production.
  Check: environment comes from the framework's config and env wiring; nothing in a test names a production host or a real account.
- **Assertions on incidental content.** Pinning exact copy, dates, or counts that legitimately change makes the suite red on every content edit.
  Check: assertions pin the behavior's contract, such as an element's state or a value derived from data the test created, not incidental text.
- **Unawaited action or navigation.** Unawaited async e2e calls interleave with the assertions that follow: green locally, racy in CI.
  Check: every promise-returning action is awaited; floating-promise linting covers the e2e tree.

## Escalation triggers (`needs-decision`)

- The flow needs a test account, credential, or environment that does not exist: name it and its purpose; a human provisions it (also an ask-first boundary in the agent).
- The journey under test is genuinely broken in the product: report it under Product bugs found with the failing test; the fix belongs to an implementer seat.
- Covering the flow below e2e needs a component or API seam that does not exist: specify it for an implementer seat (also an ask-first boundary in the agent).

## What good looks like

- The e2e suite is small, and every test in it can say why it must be end-to-end.
- Any test runs alone, first, and in parallel, against any configured environment.
- Selectors read like the user's view of the page: roles, names, labeled test ids.
