# Mocking and boundaries

When to read: the brief or diff touches mocks, stubs, spies, fakes, network interception, contract fixtures, or decisions about what gets mocked and where.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Mocking the subject.** Stubbing part of the unit under test means the real logic never runs; the test asserts your stub.
  Check: nothing inside the unit under test is mocked or monkeypatched, private internals included; if that seems necessary, the boundary is wrong or a seam is missing in source, which is a specification for an implementer seat.
- **Over-mocking internals you own.** Mocking your own collaborators pins the current call graph: tests go red on refactors and stay green on real defects, teaching people to ignore red.
  Check: mock at boundaries the team does not control (network, clock, filesystem, third-party SDKs); let owned code run real.
- **Bypassing the project's interception layer.** A one-off global fetch stub beside an established MSW, nock, or WireMock setup forks the mocking idiom and skips its contract checks.
  Check: network interception goes through the project's established layer; per-test behavior uses that layer's own override mechanism.
- **Mock-contract drift.** Hand-written responses that no longer match what the real dependency returns keep the suite green against a service that will fail in production.
  Check: every mock's shape traces to a source of truth (recorded fixture, schema, contract test, provider types); update drifted mocks rather than bending assertions to fit them.
- **Fantasy error paths.** Stubbing a failure the real dependency cannot produce (wrong error type, shape, or status) verifies a path production will never take.
  Check: stubbed failures match the dependency's documented failure modes.
- **Spy assertions as behavior.** Asserting "was called with X" instead of the observable outcome couples the test to wiring.
  Check: prefer outcome assertions; interaction assertions only at true side-effect boundaries (emails sent, events published), pinning the payload contract.
- **Leaky module mocks.** File-level module mocks are hoisted and shared; tests in the same file that wanted the real module silently get the fake.
  Check: module mocks are restored or scoped per test; tests needing the real implementation live in a file without the mock or explicitly unmock.
- **Fake that got smart.** An in-memory fake accumulating its own logic drifts from the real dependency and now needs tests of its own.
  Check: fakes stay dumb; behavior that matters is also covered by an integration test against the real thing somewhere in the pyramid.

## Escalation triggers (`needs-decision`)

- Introducing a new mocking or interception library (also an ask-first boundary in the agent).
- The correct boundary requires a seam in application source, such as an injection point or an exported factory: specify the exact change for an implementer seat (also an ask-first boundary in the agent).
- A drifted mock turns out to reflect a real provider contract break: that is an integration finding for the caller, not a mock touch-up.

## What good looks like

- Mocks sit at boundaries the team does not own; everything owned runs real in some test.
- Every mock's shape has a named source of truth.
- Tests survive refactors that preserve behavior and fail on contract breaks.
