# Authentication and authorization

When to read: the brief or diff touches endpoints (all of them carry auth), permission checks, tokens or sessions, tenant scoping, or user-supplied identifiers.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The unguarded new endpoint.** A new route added without the guard chain its neighbors carry ships unauthenticated by accident; frameworks rarely fail closed.
  Check: the new endpoint declares the same authn and authz middleware or decorators as the nearest comparable route, verified by reading that route, not by assumption.
- **Authenticated is not authorized (IDOR).** Checking that a caller is logged in but not that the requested object belongs to them lets any user read any ID they can guess.
  Check: every ID from the path, query, or body is validated against the caller's ownership or tenant before use, on reads as well as writes, including batch and nested lookups.
- **Missing tenant scope.** In a multi-tenant system, one query without the tenant filter is a cross-tenant data breach, not a bug.
  Check: every new query is tenant-scoped; prefer the project's enforced mechanism (row-level security, default scopes, repository filters) over remembering a `WHERE` clause.
- **Mass assignment to privilege.** Binding the request body wholesale to a model lets a caller set `role`, `is_admin`, or `tenant_id` on themselves.
  Check: writable fields are explicitly allowlisted; privilege- and ownership-bearing fields are never client-writable.
- **Sloppy token validation.** Accepting a JWT without verifying signature, expiry, issuer, and audience (or trusting the token's own `alg` header) makes tokens forgeable.
  Check: validation uses the project's established verifier with all claims checked; no hand-rolled parsing.
- **Fail-open authorization.** An authz check that returns "allow" when the permission service errors or the lookup throws converts every outage into an escalation of privilege.
  Check: every error path in an auth decision denies; prove it by reading the catch branches.
- **Secrets in telemetry.** Authorization headers, tokens, and credentials logged once are compromised forever, and log pipelines replicate them widely; anything in a URL or query string is logged by every proxy on the path.
  Check: redaction covers headers and token-bearing fields in every log statement the change touches; no secret reaches an error tracker's context; tokens and PII never travel in URLs.
- **"Internal, so it's safe."** Endpoints protected only by network position get exposed by a gateway change or SSRF; internal services still authenticate callers.
  Check: service-to-service calls carry credentials the callee verifies; "not reachable from outside" is not an authz model.
- **Hand-rolled crypto.** Custom password hashing, token generation, or comparison logic loses to timing attacks and weak randomness.
  Check: passwords use the project's established KDF (argon2, bcrypt); comparisons of secrets are constant-time; randomness comes from the CSPRNG.

## Escalation triggers (`needs-decision`)

- Any change to authentication or authorization behavior beyond the brief (also an ask-first boundary in the agent).
- A new endpoint intended to be public or unauthenticated: that intent must be explicit, never inferred.
- Changes to the permission model, roles, or token lifetime and rotation.

## What good looks like

- Authorization decisions live in one enforced layer, not scattered per-handler judgment calls.
- New routes inherit guards by construction (router-level middleware), so forgetting is impossible.
- Access failures are observable: denied attempts are logged with actor and resource, without leaking secrets.
