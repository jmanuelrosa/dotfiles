# Failure visibility

When to read: any new or changed test, fixture, helper, or test-infra change; and whenever the brief or diff touches how a test reports its failure.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The mute failure.** A test that fails with a bare assertion and no message forces the next engineer to reverse-engineer the intent.
  Check: every new test was watched failing with a diagnostic message before it passed; the message names what broke and the expected-versus-actual.
- **The false green.** A test that cannot fail (over-mocked, asserting a stubbed value, swallowing the error under test) reports safety that is not there.
  Check: every assertion pins an outcome of the code under test; a `try/catch` in a test never hides the failure it should surface.
- **Secrets and real data in tests.** Tokens, personal data, or production dumps in fixtures or logs are a breach that travels with the repo.
  Check: no secret or real user data in fixtures, snapshots, or logs; test data is synthetic and controlled.
- **The masked flake.** A sleep, retry, or timeout bump hides a timing defect instead of surfacing it.
  Check: no sleep, retry, or timeout bump in the diff; a flake is investigated as a defect. (See flakiness-and-async.md.)
- **Context-free infra failure.** A test-infra or fixture error that fails opaquely blocks the whole suite with no lead.
  Check: fixtures and helpers fail loudly with an actionable message, not a null reference three layers deep.

## Escalation triggers (`needs-decision`)

- Changing the reporter, snapshot format, or CI annotation others depend on.
- A product bug that a test now surfaces (report it, do not fix application source).
- A diagnostic the brief needs that the suite has no pattern for yet.

## What good looks like

- Every failing test explains itself: what broke, expected versus actual, and where.
- A green suite means the behavior holds; a red one points straight at the defect.
- No secret, no real user data, and no hidden flake rides in the test code.
- Failures are loud and legible, so the suite stays a trusted signal.
