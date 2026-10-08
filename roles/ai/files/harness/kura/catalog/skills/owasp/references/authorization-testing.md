# Authorization Testing

When to read: the brief, diff, or assessed surface touches authorization tests, an authorization or permission matrix, test fixtures for roles or tenants, OpenAPI `securitySchemes`/`security` declarations, API scope enforcement, or the CI checks that gate merges on access-control tests; also when a diff adds or changes an endpoint, role, or tenant-scoped query without touching any authorization test.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Authorization Regression Testing](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Regression_Testing_Cheat_Sheet.html), [Authorization Testing Automation](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Testing_Automation_Cheat_Sheet.html), [Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [Insecure Direct Object Reference Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)

## Regression patterns the suite must contain

- **No multi-user replay test for object access (horizontal escalation).** Missing server-side ownership checks are the root cause of IDOR and regress silently.
  Check: a test authenticates as User A, creates a resource, then as User B (same role, different account) attempts read, update and delete (plus create, export and admin actions that take object references); it asserts `403` or `404`, never `200`, whether the identifier is predictable or unguessable. Owner: `qa`. Source: Authorization Regression Testing, IDOR.
- **No role demotion test for privileged endpoints (vertical escalation).** Hiding admin functions in the UI does not stop direct API calls.
  Check: a suite iterates every non-administrative role, including unauthenticated, against each administrative endpoint and asserts the API explicitly rejects the request. Owner: `qa`. Source: Authorization Regression Testing, Authorization Testing Automation.
- **No cross-tenant boundary test.** Caching and query changes leak data across tenants without anyone noticing.
  Check: the test environment provisions two tenants, seeds data in one, runs broad read queries as a user of the other, and asserts zero records or identifiers from the first tenant appear; a single leaked identifier fails the build. Owner: `qa`. Source: Authorization Regression Testing.
- **Authorization logic untested at unit and integration level.** Small logic or configuration errors in access control have severe consequences.
  Check: tests confirm the permissions mapped at design time are enforced, access is denied by default, the application terminates safely when a check fails (including abnormal conditions), and ABAC policies are enforced. Owner: `qa`. Source: Authorization.

## Authorization matrix design

- **Access model not written down as Actor-Resource-Action.** Tests without an explicit model drift from the policy.
  Check: the matrix enumerates actors (roles or specific users, including anonymous), resources and actions, optionally with a data dimension for business-level filtering. Owner: `qa`. Source: Authorization Regression Testing, Authorization Testing Automation.
- **Matrix kept in a spreadsheet or scattered one-off tests.** Hand-maintained cases fall behind policy changes.
  Check: the matrix lives in a machine-readable, human-editable file (YAML, JSON, XML or structured fixtures) that is independent of implementation technology and drives generated test cases. Owner: `qa`. Source: Authorization Regression Testing, Authorization Testing Automation.
- **Matrix rows lack expected denial behavior.** A test that only checks "not 200" cannot spot an unexpected status.
  Check: each entry declares the expected allowed and denied response codes, and any other response code is reported as a failure. Owner: `qa`. Source: Authorization Regression Testing, Authorization Testing Automation.
- **Failures do not name the violated combination.** Unclear failures get ignored.
  Check: integration tests read the matrix as their only input, run one test case per point of view (logical role), and report the service, role and expected versus actual code for each violation. Owner: `qa`. Source: Authorization Testing Automation.
- **Matrix not reviewable.** Reviewers need to see the policy to spot inconsistencies.
  Check: the matrix can be rendered or read in a form suitable for audit and review discussions. Owner: `qa`. Source: Authorization Testing Automation.
- See `xml-and-deserialization.md` for parsing an XML matrix file with external entities and external DTD loading disabled.

## Contract-driven validation

- **Authorization requirements absent from the API contract.** Undeclared requirements cannot be tested or enforced automatically.
  Check: the OpenAPI document declares `securitySchemes` and global and per-operation `security` with required scopes. Owner: `backend`. Source: Authorization Regression Testing.
- **Contract security definitions not enforced by middleware.** Declared requirements mean nothing if no layer enforces them.
  Check: the gateway or framework is configured to enforce the contract's security definitions automatically. Owner: `backend`. Source: Authorization Regression Testing.
- **No test that enforcement middleware survives refactors.** A refactor can bypass or disable it.
  Check: regression tests fail if the contract-enforcing middleware is removed or bypassed for any operation. Owner: `qa`. Source: Authorization Regression Testing.
- **Only missing credentials tested, not missing scopes.** Rejecting absent credentials does not prove scope enforcement.
  Check: tests send otherwise-valid tokens that lack required scopes, plus explicit expired-token and missing-scope fixtures with expected denials, rather than assuming schema-driven generators produce such credentials. Owner: `qa`. Source: Authorization Regression Testing.

## Framework and CI integration

- **Authorization tests in a separate toolchain.** Tests outside the standard runner are skipped.
  Check: authorization suites use the project's standard test runner and run in the same CI pipeline as functional tests. Owner: `qa`. Source: Authorization Regression Testing.
- **Authorization suite not a required merge check.** A failing authorization test must block the merge.
  Check: the CI configuration marks the authorization suite as a required status check and runs it on every pull request and release. Owner: `platform`. Source: Authorization Regression Testing, Authorization Testing Automation.
- **Authorization tests not runnable on their own.** Developers skip slow suites locally.
  Check: authorization tests are tagged or grouped (a marker or dedicated script) so they run independently. Owner: `qa`. Source: Authorization Regression Testing.
- **Switching identity requires a full login per test.** Expensive identity switching discourages coverage.
  Check: fixtures issue per-role credentials and swap the `Authorization` header cheaply between cases. Owner: `qa`. Source: Authorization Regression Testing, Authorization Testing Automation.
- **Unusual 401/403 volumes in integration runs go unnoticed.** Spikes signal functional changes colliding with security controls.
  Check: CI integration environments flag unusual counts of `401` and `403` responses. Owner: `platform`. Source: Authorization Regression Testing.
