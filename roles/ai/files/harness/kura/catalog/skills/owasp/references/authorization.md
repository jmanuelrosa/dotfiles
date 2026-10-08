# Authorization

When to read: the brief, diff, or assessed surface touches access-control checks, endpoints or queries that load an object by an identifier from the request, request-to-object binding (DTOs, model binding, ORM fill), role, attribute or relationship policies, a policy engine (PDP/PEP, OPA, Cerbos, OpenFGA, AuthZEN), gateway or proxy authorization, list/search/export filtering by permission, or the distribution of policies and authorization data.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [Authorization Decisions and Output Handling](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Decisions_And_Output_Handling_Cheat_Sheet.html), [Authorization Patterns](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Patterns_Cheat_Sheet.html), [Authorization Policy and Data Distribution](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Policy_And_Data_Distribution_Cheat_Sheet.html), [Insecure Direct Object Reference Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html), [Mass Assignment](https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html)

## Contents

- Object-level authorization (IDOR)
- Enforcement placement and coverage
- Mass assignment
- Deny by default and failing closed
- Collections, filters and batch decisions
- Policy and authorization data inputs
- Access model design and least privilege
- Static resources
- Logging and testing pointers

## Object-level authorization (IDOR)

- **Object fetched by a request-supplied reference without an ownership check.** Access to an object type does not imply access to every object of that type; changing `123` to `124` must not return another user's record.
  Check: every handler that resolves an identifier from the path, query, body, hidden field or header (numeric ID, UUID, account number, filename, token, slug) checks the caller's permission for that specific object on that request, for read, create, update, delete, export and admin actions. Owner: `backend`. Source: Authorization, IDOR.
- **Unscoped lookup by primary key.** A global `find(id)` searches every owner's data.
  Check: lookups go through a dataset the caller can access (a query constrained by owner or relationship), or the handler verifies ownership explicitly after the fetch; prefer the scoped lookup. Owner: `backend`. Source: IDOR.
- **Identifier exposed where the server already knows it.** Identifiers in URLs and bodies invite tampering.
  Check: objects derivable from the authenticated identity (own account, own profile) are resolved from the session or validated token, multi-step flows keep identifiers in the session, and per-user or per-session indirect references are used where an identifier must be exposed. Owner: `backend`. Source: Authorization, IDOR.
- **Random identifiers treated as the access control.** GUIDs and random IDs only slow enumeration; leaked URLs still work without a check.
  Check: random IDs or UUIDs replace enumerable keys only as defense in depth on top of the object check, and identifiers are not encrypted as a substitute (hard to do securely). Owner: `backend`. Source: Authorization, IDOR.
- **Existence revealed by distinct "forbidden" and "not found".** A post-fetch check can tell a caller that an object exists.
  Check: where existence is sensitive, use the scoped lookup and return the same public response (for example 404) for missing and unauthorized objects. Owner: `backend`. Source: IDOR.
- **Declarative method-level authorization never enabled.** Method-security annotations are inert until the framework's method security is switched on, and some frameworks leave it off by default.
  Check: when authorization is expressed as method annotations, the configuration that activates them is present and the annotated bean is framework-managed. Owner: `backend`. Source: IDOR.

## Enforcement placement and coverage

- **Authorization decided in the client.** Client-side checks are easy to bypass and may only shape the UI.
  Check: every protected operation is enforced server-side, at the gateway, or in a serverless function; UI visibility checks are never the decisive control. Owner: `backend`. Source: Authorization, Authorization Decisions.
- **Permission check missing on some requests.** An attacker needs only one unchecked path; validating most requests is insufficient.
  Check: permissions are validated on every request whatever its origin (AJAX, server-side, other), via a global application-wide mechanism (filter, middleware, interceptor) rather than per-method opt-in. Owner: `backend`. Source: Authorization, Authorization Patterns.
- **Enforcement far from the protected resource.** The PEP must see the requested action, object and tenant, and delegating evaluation to a PDP does not transfer the PEP's duty to enforce.
  Check: the service owning the resource enforces the decision before accessing it; object-level and business checks stay in the service when a gateway lacks the context. Owner: `backend`. Source: Authorization Patterns.
- **In-code policies scattered across handlers.** Scattered conditionals make omissions and inconsistencies hard to detect.
  Check: checks are centralized in the application's authorization layer and every protected entry point is covered by a test. Owner: `backend`. Source: Authorization Patterns.
- **PDP decision not enforced or fed untrusted inputs.** A separately managed policy is only as good as the subject and resource attributes supplied and the enforcement of its result.
  Check: the PEP sends authenticated subject context and authoritative resource attributes, enforces the decision before accessing the resource, and denies when no valid decision is available. Owner: `backend`. Source: Authorization Patterns.
- **Gateway assumed to see all traffic.** Complete coverage is a deployment requirement, not a property of a gateway.
  Check: services reject direct access that bypasses the gateway, permitted callers are authenticated, and internal calls and alternate endpoints are covered. Owner: `cloud`. Source: Authorization Patterns.
- **Authorization not re-evaluated after the target changes.** Routing or rewriting after a check can invalidate it.
  Check: if the effective resource or action changes after the authorization check (rewrite, reroute), authorization is evaluated again. Owner: `backend`. Source: Authorization Patterns.
- **Propagated authorization context trusted blindly.** A signed gateway context neither prevents bypass nor authorizes a different resource, tenant or action.
  Check: downstream services validate issuer, integrity, audience, expiry and applicability to the actual request, reject direct calls lacking the context, strip client-supplied copies of trusted headers before populating them, and keep service-level enforcement. Owner: `backend`. Source: Authorization Patterns.
- **Single control trusted to enforce access.** Any framework or library can have an authorization flaw.
  Check: access control does not rest on one framework, library or component alone (for example a gateway rule with no service check). Owner: `backend`. Source: Authorization.
- **Framework authorization logic assumed sufficient and correctly configured.** Prebuilt logic is general purpose, defaults evolve, and documentation can be wrong.
  Check: explicit authorization configuration is preferred over framework defaults, custom logic covers requirements the component cannot express, and configuration is verified by tests rather than assumed. Owner: `backend`. Source: Authorization.
- See `supply-chain-and-dependencies.md` for detecting and responding to vulnerable authorization components.

## Mass assignment

- **Request bound directly to a domain or persistence object.** Automatic binding lets an attacker set fields such as `isAdmin`, a role, or an owner by adding parameters; field names can be guessed.
  Check: handlers bind input to dedicated input objects (DTOs) that contain only caller-editable fields, not to entity or model classes. Owner: `backend`. Source: Mass Assignment.
- **Binding without an allowlist.** When binding to an object with extra properties, unlisted fields remain writable.
  Check: an explicit allowlist of bindable fields is configured (binder allowed fields, fillable fields, strong parameters, picked keys). Owner: `backend`. Source: Mass Assignment.
- **Blocklist as the only protection.** A new or overlooked sensitive field stays bindable.
  Check: denylist mechanisms (disallowed fields, guarded attributes, protected flags) are not the sole control; replace with an allowlist or DTO. Owner: `backend`. Source: Mass Assignment.
- **Nested or constructor-bound fields overlooked.** Binding is not limited to setters on the top-level object.
  Check: review which inputs the binder exposes, including nested objects and constructor binding, when adding or changing a bound type. Owner: `backend`. Source: Mass Assignment.
- **Writable-field control mistaken for authorization.** DTOs and allowlists restrict which properties are written, not which object or operation the caller may touch.
  Check: the object and operation are still authorized separately. Owner: `backend`. Source: Mass Assignment.

## Deny by default and failing closed

- **Access permitted when no rule matches.** The application must always decide, and logic errors are likely in complex rules.
  Check: the default outcome is deny for existing and newly exposed functionality, and each grant can be justified explicitly. Owner: `backend`. Source: Authorization.
- **PDP error, timeout or unusable output treated as permit.** Allowing requests when authorization fails bypasses the control.
  Check: PDP errors, timeouts, undefined results and an absent filter deny protected operations; gateway or proxy authorization failure modes are configured to deny, not allow. Owner: `backend`. Source: Authorization Decisions, Authorization Patterns, Authorization Policy.
- **Protected operations served before policy loads.** A PDP without valid policy and data cannot decide.
  Check: at startup protected operations are not served until the required policy and data are available and valid. Owner: `backend`. Source: Authorization Policy.
- **Stale policy or data still used after its freshness bound.** A retained bundle preserves availability but not freshness; a local PDP with stale revocation data permits incorrectly.
  Check: a previously verified policy is evaluated only while policy, data and decision-cache freshness requirements hold; inputs that are missing, invalid or older than the allowed bound cause denial. Owner: `backend`. Source: Authorization Policy, Authorization Patterns.
- **Authorization failure leaves the application in an unstable state.** Mishandled failures can lead to bypass.
  Check: every exception and failed check is handled, failure handling is centralized, and failures (however unlikely) are verified not to leave partial state that grants access. Owner: `backend`. Source: Authorization.
- See `logging-and-error-handling.md` for keeping sensitive information out of authorization error messages.

## Collections, filters and batch decisions

- **Decision not bound to the full request context.** A decision evaluated without the tenant or resource can be reused where it does not apply.
  Check: each decision request carries the authenticated subject, action, resource, tenant and relevant context; verified role or relationship attributes are fine, a client's assertion of its own privileges is not. Owner: `backend`. Source: Authorization Decisions.
- **One permit applied to a whole batch.** Batch checks are separate decisions.
  Check: each response is matched to its request by the API's ordering or identifiers, and items with missing, invalid or error results are denied. Owner: `backend`. Source: Authorization Decisions.
- **Restriction enforced on reads but not on other outputs.** Counts, exports, aggregates and search reveal protected data too.
  Check: the authorization restriction is applied to list, search, export, count, aggregate and direct-object reads; an authorized list does not authorize a later update or delete. Owner: `backend`. Source: Authorization Decisions.
- **Per-item filtering leaks candidates.** With check-each-candidate, data must not leave the trusted service before checks finish.
  Check: the candidate set is bounded, held inside the service until checked, and denied or unresolved items are excluded. Owner: `backend`. Source: Authorization Decisions.
- **Empty or truncated authorized-ID list removes the restriction.** List APIs may cap results or time out.
  Check: the authorized-ID list is treated as complete only when the API guarantees it, an empty or incomplete list never disables the restriction, and authorization is rechecked for subsequent operations or state changes. Owner: `backend`. Source: Authorization Decisions.
- **Authorization filter OR-ed with or replacing application predicates.** An always-allowed result does not lift tenant or business restrictions.
  Check: authorization predicates are combined with application and tenant predicates by logical AND, and an always-denied plan returns no protected data. Owner: `backend`. Source: Authorization Decisions.
- **Policy predicate translated lossily into a query.** Silently dropped expressions or different null, join or membership semantics widen access.
  Check: a maintained adapter for the exact PDP and data store is used, unsupported operators or incomplete translations are rejected, and null, missing-attribute, join and collection-membership behavior is checked against the policy. Owner: `backend`. Source: Authorization Decisions.
- **Filter values concatenated into query syntax.** A returned predicate is untrusted input to the data layer.
  Check: filter values are bound as parameters, field names and operators are allowlisted, and no returned debug string is executed as a query. Owner: `backend`. Source: Authorization Decisions.
- **Cached decision reused outside its scope.** A cached permit can outlive a required revocation.
  Check: cache keys include subject, action, resource scope, tenant and relevant policy/input state, entries respect the approved freshness limit, and no cached permit outlives a revocation deadline. Owner: `backend`. Source: Authorization Decisions.
- **Enforcement or freshness traded for latency.** Batching and filtering must not weaken enforcement.
  Check: large queryable collections use a documented query-filter integration, otherwise bounded per-item checks, with no shortcut that skips enforcement or freshness. Owner: `backend`. Source: Authorization Decisions.
- **PDP integration tested only on the happy path.** Successful communication with a PDP is not evidence of correct enforcement.
  Check: tests cover permitted and denied resources, tenant boundaries, each filter result kind, incomplete batches or lists and PDP failure, and compare filter selections with individual decisions for representative policies. Owner: `qa`. Source: Authorization Decisions.

## Policy and authorization data inputs

- **Request-time attributes copied from the end-user request.** An authenticated PEP still must derive identity, roles, ownership and tenant membership from trusted sources.
  Check: values sent to the PDP come from the verified session, token or authoritative store, resource identifiers are validated against the actual target, and user-supplied context is kept distinct from verified attributes. Owner: `backend`. Source: Authorization Policy.
- **Required attribute lookup fails open.** A lookup source, replica or cache can be stale or unavailable.
  Check: when a required attribute cannot be obtained reliably, affected operations are denied. Owner: `backend`. Source: Authorization Policy.
- **Replicated authorization data applied unsafely.** Replication creates a revocation delay and can deliver updates out of order.
  Check: the consumer handles missed, repeated and reordered updates and does not treat local availability as freshness. Owner: `backend`. Source: Authorization Policy.
- **Replication lag invisible.** Without monitoring, the revocation delay is unknown.
  Check: synchronization progress of replicated policy data is monitored against the propagation bound. Owner: `sre`. Source: Authorization Policy.
- **No ownership or freshness budget for policies and attributes.** Acceptable delay depends on the input, not on who owns it.
  Check: a record names who may change each policy and attribute, its authoritative source, and its maximum propagation delay, distinguishing policy changes from data changes. Owner: `architect`. Source: Authorization Policy.
- **Delivery mechanism cannot meet the revocation deadline.** Bundle distribution is eventually consistent and publication is not activation.
  Check: emergency restrictions and revocations use dynamic updates or authoritative lookup with a measured propagation bound (deny when unmet); policies ship independently of app releases when a deploy is too slow; mutable account status or revocation data is not embedded in releases that cannot update promptly. Owner: `architect`. Source: Authorization Policy.
- **Decision and policy administration APIs unprotected.** Network-exposed decision APIs and the APIs that read or modify policy and data are high-value targets.
  Check: PEPs and administrators authenticate, each is restricted to the tenants and operations it needs, service teams cannot replace organization-wide restrictions, and a local sidecar PDP has a restricted API and handled process failure. Owner: `backend`. Source: Authorization Policy, Authorization Patterns.
- **Policy artifacts activated without signature verification.** A valid signature proves origin and integrity, not correctness or currency.
  Check: bundles require a signature from a configured trusted publisher covering all files before activation, and transport and signing keys are protected. Owner: `platform`. Source: Authorization Policy.
- **Unpinned or unrecorded policy revisions.** Unexpected or obsolete revisions silently change access.
  Check: deployments pin reviewed policy and schema versions, record which revision each PDP activated, reject unexpected or obsolete revisions, allow rollback only through the reviewed release process, and test that service-owned rules cannot override mandatory restrictions. Owner: `platform`. Source: Authorization Policy.
- **Revocation and outage behavior never exercised.** Delivery to the PDP is not the effective decision.
  Check: tests exercise revocation, delayed updates, invalid artifacts, unavailable sources and recovery, asserting the decision observed at the PEP. Owner: `qa`. Source: Authorization Policy.
- **Decisions not logged with policy version.** Discrepancies cannot be investigated without it.
  Check: the decision and its enforcement are logged with policy and version context, without sensitive attributes. Owner: `backend`. Source: Authorization Patterns.

## Access model design and least privilege

- **Permissions not mapped at design time.** Least privilege applies horizontally and vertically and is harder to retrofit than to grant.
  Check: the design defines trust boundaries and, for every user type and resource, the permitted operations (with all ABAC attribute categories, such as network and time, considered). Owner: `architect`. Source: Authorization.
- **RBAC chosen where object-level or multi-factor rules are needed.** Role checks handle horizontal access, multi-tenancy and contextual rules poorly and lead to missed checks and role explosion.
  Check: ABAC or ReBAC is preferred for application authorization, the model is chosen early, and authorization requirements are decided before selecting components rather than shaped by a library's capabilities. Owner: `architect`. Source: Authorization.
- **Policy-engine deployment chosen without its required controls.** Each deployment mode has its own obligations, and locality does not establish trust.
  Check: embedded PDPs keep policy and data current with enforcement on every entry point; remote PDPs authenticate and authorize PEPs, protect responses and deny without a valid decision; growing systems prefer service-level enforcement with shared reviewed policies, adding gateway checks only for early rejection. Owner: `architect`. Source: Authorization Patterns.
- **Privilege creep after deployment.** Users accumulate permissions beyond the design.
  Check: a periodic review compares actual permissions to the designed mapping plus approved changes. Owner: `security`. Source: Authorization.

## Static resources

- **Static files outside the access-control policy.** Static resources often bypass application checks.
  Check: static resources are classified and covered by the same access-control logic and mechanisms as other application resources where possible. Owner: `backend`. Source: Authorization.
- **Cloud storage for static assets left at defaults.** Misconfigured buckets expose data.
  Check: cloud storage holding static resources is secured with the provider's access configuration and tooling. Owner: `cloud`. Source: Authorization.

## Logging and testing pointers

- See `logging-and-error-handling.md` for log format, volume, clock synchronization and centralized collection of access-control events.
- See `authorization-testing.md` for authorization test matrices, multi-user IDOR replay tests, and unit and integration tests that verify deny-by-default, safe failure and enforced permissions.
