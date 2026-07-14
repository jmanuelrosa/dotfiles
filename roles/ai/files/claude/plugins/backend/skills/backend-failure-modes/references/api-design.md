# API design and contracts

When to read: the brief or diff touches endpoint shape, request or response contracts, input validation, status codes, versioning, or generated API artifacts (OpenAPI, GraphQL schema, protobuf, generated clients).

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Silent breaking change.** Renaming, removing, or retyping a response field breaks consumers you cannot see; so does tightening validation on a field clients already send loosely.
  Check: diff the serialized shape before and after; only additive changes ship without a decision.
- **Error contract drift.** A new endpoint that returns a different error envelope, or different status-code semantics (400 vs 422 vs 409, 401 unauthenticated vs 403 unauthorized), than its neighbors forces every consumer to special-case it.
  Check: copy the error shape and status conventions of the nearest existing endpoints exactly; validation failures carry machine-readable codes and field paths, not just prose.
- **Unbounded or unstable lists.** A list endpoint without a default page size and a hard cap will eventually time out; offset pagination over mutable data skips or duplicates rows; ordering without a unique tiebreaker is nondeterministic across pages.
  Check: default and max page size enforced server-side; cursor or keyset pagination when rows mutate; sort key includes a unique column.
- **Shape-only validation.** Validating types but not semantics lets through out-of-range values, oversized arrays, and unknown enum members; accepting client-supplied fields wholesale enables mass assignment.
  Check: bounds on lengths, ranges, and array sizes; enums validated against the closed set; writable fields allowlisted, never spread from the request body.
- **Retry-unsafe mutations.** Clients, proxies, and mobile networks retry; a POST that creates a resource per attempt produces duplicates under normal operation, not edge cases.
  Check: creation and payment-like endpoints accept an idempotency key or use a natural unique constraint, and retried calls return the original result.
- **Long work in the request path.** An endpoint that does slow work inline hits gateway and client timeouts and cannot be retried safely.
  Check: work that can exceed a couple of seconds moves to a job with a 202-plus-status-endpoint pattern, matching how the project already does it.
- **Contract artifacts out of sync.** Code changed but the OpenAPI spec, GraphQL schema, or generated clients were not regenerated; the artifact now lies to every consumer and codegen user.
  Check: regenerate with the project's own command and include the regenerated artifact in the diff.

## Escalation triggers (`needs-decision`)

- Any breaking change to a contract other code consumes, even when the brief implies it.
- A new public or cross-service endpoint whose shape is not pinned down by the brief or an existing convention.
- Changing the meaning of an existing status code, error code, or field without a version bump.

## What good looks like

- Contracts evolve additively; deprecation precedes removal.
- Every endpoint answers the same way for pagination, errors, and validation as its neighbors.
- The spec artifact is generated or verified in CI, so drift fails a check instead of a consumer.
