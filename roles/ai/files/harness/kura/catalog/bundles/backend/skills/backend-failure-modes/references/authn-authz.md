# Authentication and authorization

When to read: the brief or diff touches endpoints (all of them carry auth), permission checks, tokens or sessions, tenant scoping, or user-supplied identifiers.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The unguarded new endpoint.** A new route added without the guard chain its neighbors carry ships unauthenticated by accident; frameworks rarely fail closed.
  Check: the new endpoint declares the same authn and authz middleware or decorators as the nearest comparable route, verified by reading that route, not by assumption.
- **Authenticated is not authorized (IDOR).** Checking that a caller is logged in but not that the requested object belongs to them lets any user read any ID they can guess.
  Check: every ID from the path, query, or body is validated against the caller's ownership or tenant before use, on reads as well as writes, including batch and nested lookups and tool calls a model makes on the user's behalf; no authorization rule exists only in client code or a prompt.
- **Missing tenant scope.** In a multi-tenant system, one query without the tenant filter is a cross-tenant data breach, not a bug.
  Check: every new query is tenant-scoped, counts, exports, and search included; the tenant comes from the verified identity, never a client-supplied id, and its predicate is AND-ed with every other filter; a tenant setting on a pooled connection is scoped to the transaction; prefer the project's enforced mechanism (row-level security, default scopes, repository filters) over remembering a `WHERE` clause.
- **Mass assignment to privilege.** Binding the request body wholesale to a model lets a caller set `role`, `is_admin`, or `tenant_id` on themselves.
  Check: writable fields are explicitly allowlisted; privilege- and ownership-bearing fields are never client-writable.
- **Sloppy token and session handling.** Accepting a JWT without verifying signature, expiry, issuer, and audience (or trusting the token's own `alg` or key headers) makes tokens forgeable; a session id that survives login, logout, or idleness can be fixed or replayed.
  Check: validation uses the project's established verifier with a fixed algorithm allowlist, keys resolved from the configured issuer (never `jwk`, `jku`, `x5u`, or `x5c` from the token), and `exp`, `iss`, and `aud` required, with no hand-rolled parsing; external identities key on issuer plus subject, never auto-linked by email; session ids rotate on login and privilege change, are destroyed server-side on logout, and expire on server-enforced idle and absolute timeouts.
- **Fail-open authorization.** An authz check that returns "allow" when the permission service errors or the lookup throws converts every outage into an escalation of privilege.
  Check: every error path in an auth decision denies, and so does every other gate (fraud or sanctions screening, approval services) when it errors or times out; prove it by reading the catch branches.
- **Secrets in telemetry.** Authorization headers, tokens, and credentials logged once are compromised forever, and log pipelines replicate them widely; anything in a URL or query string is logged by every proxy on the path.
  Check: redaction covers headers and token-bearing fields in every log statement the change touches; no secret reaches an error tracker's context; tokens and PII never travel in URLs.
- **"Internal, so it's safe."** Endpoints protected only by network position get exposed by a gateway change or SSRF; internal services still authenticate callers.
  Check: service-to-service calls carry credentials the callee verifies, and every protected handler makes its own authorization decision even behind a gateway that authenticated the user; inbound webhooks and payment callbacks verify the sender's signature over the raw body, compared in constant time, before acting; "not reachable from outside" is not an authz model.
- **Hand-rolled crypto and guessable tokens.** Custom password hashing, token generation, or comparison logic loses to timing attacks and weak randomness, and a reset link that is reusable, long-lived, or built from the request's `Host` header hands out account takeover.
  Check: passwords use the project's established KDF (argon2, bcrypt); comparisons of secrets are constant-time; randomness comes from the CSPRNG; encryption uses an authenticated mode, never ECB, DES, 3DES, or RC4; reset and verification tokens are stored hashed, single-use, and short-lived, in links built from the configured origin, never the request `Host` header.
- **Cross-site requests riding the user's cookies.** Browsers attach cookies to requests other sites trigger, so a cookie-authenticated route without CSRF defense, a GET that changes state, a CORS policy that echoes any origin with credentials, or a WebSocket upgrade that ignores `Origin` lets any page act as the user.
  Check: cookie-authenticated state-changing routes pass the project's CSRF defense; no GET or HEAD handler writes state; session cookies carry `Secure`, `HttpOnly`, and `SameSite`; credentialed CORS allows an exact origin list, never `*`, an echoed `Origin`, or a suffix match; WebSocket upgrades check `Origin` against an exact allowlist.

## Escalation triggers (`needs-decision`)

- Any change to authentication or authorization behavior beyond the brief (also an ask-first boundary in the agent).
- A new endpoint intended to be public or unauthenticated: that intent must be explicit, never inferred.
- Changes to the permission model, roles, or token lifetime and rotation.

## What good looks like

- Authorization decisions live in one enforced layer, not scattered per-handler judgment calls.
- New routes inherit guards by construction (router-level middleware), so forgetting is impossible.
- Access failures are observable: denied attempts are logged with actor and resource, without leaking secrets.
