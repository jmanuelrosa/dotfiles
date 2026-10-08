# Multi-Tenancy

When to read: the brief, diff, or assessed surface touches tenant identifiers or tenant context in requests, tokens, headers or messages, tenant-scoped queries or ORM filters, PostgreSQL row-level security or per-tenant schemas and databases, cache keys, object storage paths or signed URLs, shared queues and workers, per-tenant rate limits or quotas, tenant API credentials, tenant provisioning, offboarding, deletion or backup restore, or tenant-aware audit logging.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Multi-Tenant Application Security](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html)

## Contents

- Tenant context
- Cross-tenant object access
- Database isolation
- Cache isolation
- Asynchronous work
- File storage and blobs
- Tenant credentials and request signing
- Shared resource limits
- Provisioning, offboarding and restore
- Logging, monitoring and audit
- Isolation testing

## Tenant context

- **Client-supplied tenant ID used as authorization.** A tenant ID from a header or parameter is a selector; parameterizing the query stops injection, not cross-tenant access.
  Check: wherever a tenant ID comes from the client, the code verifies the authenticated principal is authorized to act in that tenant before use. Owner: `backend`. Source: Multi-Tenant.
- **Tenant context not bound to verified identity and current membership.** A token claim may select the tenant, but authorization depends on the issuer's guarantees or a current membership check.
  Check: tenant context is built from a server-verified identity plus active membership (or service authorization), and requests lacking it are rejected. Owner: `backend`. Source: Multi-Tenant.
- **Tenant context established late or inconsistently.** Handlers that resolve tenant on their own miss some paths.
  Check: for tenant-scoped operations, middleware or an interceptor establishes and validates tenant context early on every tenant-scoped request and handlers that need it fail when it is absent; public or global endpoints need no artificial tenant. Owner: `backend`. Source: Multi-Tenant.
- **Downstream components replace verified tenant context.** Propagated context loses its value if a later layer reads tenant from unverified input.
  Check: verified tenant context is propagated to components making tenant-sensitive decisions or logs, and no downstream component overrides it with request data. Owner: `backend`. Source: Multi-Tenant.
- **Authorization skipped because a service is internal.** Internal callers can carry wrong or forged tenant context.
  Check: internal services still authorize tenant-scoped operations. Owner: `backend`. Source: Multi-Tenant.

## Cross-tenant object access

- **Tenant-scoped resource fetched by ID alone.** A lookup on `resource_id` only can return another tenant's record.
  Check: every tenant-scoped resource access verifies the principal can act in the resource's tenant, typically by including tenant scope in the lookup or policy (a composite tenant plus resource key is one option), and a miss returns a response that does not reveal existence in another tenant. Owner: `backend`. Source: Multi-Tenant.
- **Tenant enforcement not on a boundary every path crosses.** Checks in some handlers leave others open.
  Check: tenant ownership is enforced at a boundary traversed by every tenant-owned access path (repository, policy layer, database policy), with data-layer checks as defense in depth where supported. Owner: `backend`. Source: Multi-Tenant.
- **Unscoped query on an ordinary tenant request path.** One unscoped query exposes every tenant.
  Check: tenant request paths never run unscoped queries; any cross-tenant administrative path is explicit, separately authorized and audited. Owner: `backend`. Source: Multi-Tenant.
- **Tenant ID on writes taken from input.** A create or update can plant a record in another tenant.
  Check: new tenant-owned records get their tenant from the verified context, and a supplied tenant that differs is rejected. Owner: `backend`. Source: Multi-Tenant.
- **Opaque tenant or resource IDs treated as protection.** Random identifiers reduce enumeration but are not authorization.
  Check: identifier complexity is never the only control against cross-tenant access. Owner: `backend`. Source: Multi-Tenant.
- **Tenant-owned data without an enforceable tenant association.** Without one, no layer can enforce isolation (a literal `tenant_id` column is not required by every architecture).
  Check: every tenant-owned table or store has an enforceable tenant association or isolation boundary. Owner: `database`. Source: Multi-Tenant.

## Database isolation

- **Isolation strategy chosen without its required conditions.** Each strategy is only a boundary when its conditions hold.
  Check: the chosen model is documented per data class: separate databases with isolated credentials, network, admin paths and backups; separate schemas with disciplined grants, role separation, `search_path` handling and migrations; shared tables with enforceable ownership, policy coverage, constrained request roles and negative tests; hybrids document and test each boundary. Owner: `architect`. Source: Multi-Tenant.
- **RLS not enabled and forced on tenant tables.** Without `FORCE ROW LEVEL SECURITY` the table owner bypasses policies.
  Check: each tenant-scoped table has RLS enabled and forced and a tenant isolation policy; policies read the tenant setting without `missing_ok`, so a missing setting errors instead of yielding `NULL`. Owner: `database`. Source: Multi-Tenant.
- **Request path connects as a superuser or `BYPASSRLS` role.** Both always bypass row security, even with `FORCE`.
  Check: the application request role is least-privileged, neither superuser nor `BYPASSRLS`; privileged connections are reserved for migrations and explicitly authorized admin jobs, which themselves authorize and constrain their tenant set because RLS will not. Owner: `database`. Source: Multi-Tenant.
- **Session-scoped tenant setting on pooled connections.** A plain `SET` outlives the transaction, so a reused connection inherits the previous request's tenant.
  Check: each transaction begins, sets tenant with `SET LOCAL` or `set_config(..., true)`, runs dependent queries in that transaction, and commits or rolls back before returning the connection; context is re-established per transaction, and session-scoped settings are used only with reliable reset-on-checkout plus connection-reuse tests. Owner: `backend`. Source: Multi-Tenant.
- **Missing tenant context falls back to an unscoped query.** Fail-open defaults leak all tenants.
  Check: missing or invalid tenant context raises an error; no code path retries without the tenant scope. Owner: `backend`. Source: Multi-Tenant.
- **ORM tenant filter misses relationship and attribute loads.** Query-compile hooks do not cover lazy or eager relationship loads.
  Check: ORM-level tenant criteria are attached at statement execution in a way that propagates to eager and lazy relationship loads; raw SQL, core connections, bulk operations and other session types have separate controls, and database policies or constrained roles remain the final boundary. Owner: `backend`. Source: Multi-Tenant.

## Cache isolation

- **Tenant-varying data under a shared or global key.** User IDs are not unique across tenants, and a global key serves one tenant's data to another.
  Check: every cached value is classified global, tenant or user scoped; keys for tenant-varying values or authorization include the tenant plus every other result-changing attribute (user, locale, feature set, permission version); intentionally shared entries use an explicit, documented global namespace. Owner: `backend`. Source: Multi-Tenant.
- **Cache read before authorization.** Key separation does not replace authorization.
  Check: requests are authorized before reading a protected cached value. Owner: `backend`. Source: Multi-Tenant.
- **Cache TTL ignores authorization risk.** Long-lived entries can outlast permission changes.
  Check: TTL and invalidation are chosen from freshness and authorization risk; only immutable, versioned global entries go without expiry. Owner: `backend`. Source: Multi-Tenant.
- **Stronger-isolation tenants share a cache instance.** Some tenants require physical isolation.
  Check: tenants with stronger isolation requirements get separate cache instances. Owner: `cloud`. Source: Multi-Tenant.

## Asynchronous work

- **Shared queue treated as an isolation boundary.** Shared messaging needs application-enforced isolation.
  Check: each job or topic is classified global, tenant-scoped or explicitly cross-tenant. Owner: `backend`. Source: Multi-Tenant.
- **Tenant taken from an unverified message field.** A message field must not replace the producer's authorized scope.
  Check: producers derive tenant from their authenticated context and bind it via trusted broker routing, authenticated metadata or an integrity-protected payload. Owner: `backend`. Source: Multi-Tenant.
- **Consumer acts on the message's tenant without re-authorizing.** A tenant ID in a queued message is not authorization proof.
  Check: consumers authenticate the producer or broker path, re-establish tenant context, authorize the operation and target, and re-check membership or permission when delay could make the original decision stale. Owner: `backend`. Source: Multi-Tenant.
- **Job bookkeeping shared across tenants.** Idempotency keys, retries and dead letters can cross tenants.
  Check: idempotency and deduplication keys, retry state, dead-letter access and ordering are tenant-scoped where data or effects vary by tenant; global and authorized cross-tenant jobs use explicit identities and scopes rather than a fabricated tenant. Owner: `backend`. Source: Multi-Tenant.

## File storage and blobs

- **Object served or URL signed before authorization.** A signed URL is a bearer grant.
  Check: access to the exact object and operation is authorized before serving it or generating a signed URL, and stored tenant ownership metadata is checked where present. Owner: `backend`. Source: Multi-Tenant.
- **Tenant objects not partitioned.** Without a tenant-aware boundary, one tenant's key can address another's object.
  Check: tenant-scoped objects live under a tenant-aware key, bucket, account or enforceable storage policy, and shared assets sit in an explicit global namespace. Owner: `backend`. Source: Multi-Tenant.
- **Object key built from unvalidated tenant ID or path.** A crafted tenant ID or `..` segment alters the key structure.
  Check: the tenant ID must match the canonical format before use in a key, and paths that are absolute, contain `..` or backslashes are rejected. Owner: `backend`. Source: Multi-Tenant.
- **Tenant prefix operations match neighbor tenants.** Prefix `acme` also matches `acme-west`.
  Check: listing and deletion by tenant prefix include the trailing delimiter. Owner: `backend`. Source: Multi-Tenant.
- **Signed URLs broader or longer-lived than needed.** Overbroad URLs extend access past authorization.
  Check: signed URLs cover only the required object and method with a lifetime suited to the operation and revocation model. Owner: `backend`. Source: Multi-Tenant.
- **Cryptographic isolation missing where required.** Some risk or compliance models require per-tenant keys.
  Check: tenant-specific encryption keys are used where required; otherwise a shared managed key with enforced access context is acceptable. Owner: `cloud`. Source: Multi-Tenant.

## Tenant credentials and request signing

- **API credential not bound to a tenant scope.** A tenant-scoped credential must not reach other tenants.
  Check: API credentials are bound to explicit tenant sets, environments and permission scopes; intentionally cross-tenant service identities are separately authorized and least privileged. Owner: `backend`. Source: Multi-Tenant.
- **B2B request signature omits tenant and request context.** A signature that does not cover the tenant selection can be replayed against another tenant.
  Check: required request signatures cover tenant selection, target audience, method, path, body digest and expiration as applicable. Owner: `backend`. Source: Multi-Tenant.
- **Tenant API keys weakly generated or stored.** A fast digest is only safe for high-entropy random secrets.
  Check: tenant API keys are high-entropy random values shown once and stored only as a hash; user passwords use a password-hashing function instead (see `authentication.md`). Owner: `backend`. Source: Multi-Tenant.

## Shared resource limits

- **No tenant dimension in rate limits.** One tenant can exhaust shared capacity or quotas.
  Check: when tenants share capacity or have tenant-level entitlements, tenant identity is a rate-limit and quota dimension alongside global, endpoint, user and IP limits, with values derived from capacity, abuse risk and contractual quotas, and tenant-aware middleware mounted only on routes that require tenant context. Owner: `backend`. Source: Multi-Tenant.
- **Bottlenecks behind the HTTP edge unbounded per tenant.** HTTP rate limits do not constrain queued work, concurrency, connections, fan-out, CPU or memory.
  Check: tenant-aware limits or scheduling apply to those bottlenecks (queue depth, concurrency, throughput on shared workers and brokers), service-wide limits remain, and dedicated pools are used when risk or service commitments justify them. Owner: `backend`. Source: Multi-Tenant.

## Provisioning, offboarding and restore

- **Provisioning leaves shared or partial resources.** Incomplete provisioning causes residual access.
  Check: provisioning creates isolated resources, generates per-tenant keys where required, cleans up on failure, and writes an audit trail for provisioning and deprovisioning. Owner: `backend`. Source: Multi-Tenant.
- **Offboarded tenant retains access.** Sessions and keys outlive the contract.
  Check: offboarding blocks new operations and revokes all sessions and API keys before export and deletion scheduling. Owner: `backend`. Source: Multi-Tenant.
- **Deletion misses stores or exceeds retention.** Data kept past policy without a contractual or legal basis is a liability.
  Check: the documented retention and deletion policy covers active stores, caches, files, keys, object versions, replicas, exports and backups; legally retained records are access-restricted; tenant data export is provided when contract, regulation or product policy requires it. Owner: `backend`. Source: Multi-Tenant.
- **Single-tenant restore over a shared snapshot.** Restoring a shared backup over live data overwrites or exposes other tenants.
  Check: the runbook restores into a separate resource and selectively recovers the target tenant, authorizes the operator for that tenant, records source, target, reason and outcome, checks ownership before copying, gives tenant operators no access to shared backups, and reapplies current access and retention rules. Owner: `sre`. Source: Multi-Tenant.
- **Tenant restore never tested.** An untested restore can copy foreign data.
  Check: a test restores one tenant from a two-tenant backup, asserts the other tenant's records and objects are absent, and asserts an unauthorized restore request is rejected. Owner: `qa`. Source: Multi-Tenant.

## Logging, monitoring and audit

- **Security events lack verified tenant context.** Tenant-specific investigation and compliance need it.
  Check: tenant-scoped security and audit events include the server-verified tenant (global infrastructure events may have none), and sensitive tenant data is not logged in plain text. Owner: `backend`. Source: Multi-Tenant.
- **Central audit store readable across tenants.** A tenant admin is not implicitly a platform auditor.
  Check: audit reads enforce tenant scope, cross-tenant reads or writes require an explicit platform permission, and immutability is enforced by database permissions, tamper-evident storage or WORM rather than the API alone. Owner: `backend`. Source: Multi-Tenant.
- **Cross-tenant attempts not monitored.** Denied attempts and isolation failures are early signals of attack or regression.
  Check: monitoring records denied or unexpected cross-tenant access (excluding authorized platform operations) and alerts on isolation control failures and repeated or suspicious denial patterns. Owner: `sre`. Source: Multi-Tenant.
- **Audit data retention undefined.** Each audit-data class needs its own access and retention policy.
  Check: the documented access and retention policy is applied per audit-data class. Owner: `sre`. Source: Multi-Tenant.

## Isolation testing

- **Isolation tested through a privileged connection.** A privileged test role can hide a bypass or make a correct policy look broken.
  Check: isolation tests use the same role, connection path and pooling mode as the application. Owner: `qa`. Source: Multi-Tenant.
- **No per-table cross-tenant matrix.** Each RLS table needs proof of both denial and permitted access.
  Check: for each RLS-protected table, tests prove cross-tenant operations are denied and same-tenant operations succeed, and intentional sharing or platform-admin paths are tested to grant nothing broader. Owner: `qa`. Source: Multi-Tenant.
- **RLS coverage checked against a hand-kept list.** The omission that skips RLS on a new table also skips its test.
  Check: a test derives tenant-scoped tables from the schema or an explicit classification and compares them with `pg_class.relrowsecurity`, `relforcerowsecurity` and `pg_policies`, failing on unclassified tables, disabled RLS or missing policies; or schema changes are gated on classifying each new table. Owner: `qa`. Source: Multi-Tenant.
- **Deployed request role never asserted.** Source-controlled configuration may not match the deployed role.
  Check: a configuration test in the deployed environment fails if the request-path role has `rolsuper` or `rolbypassrls` in `pg_roles`. Owner: `qa`. Source: Multi-Tenant.
- **Connection reuse never exercised.** Pooled sessions can carry the previous tenant.
  Check: a test runs requests for two tenants over reused connections and proves the second cannot observe the first's tenant context. Owner: `qa`. Source: Multi-Tenant.
- See `authorization-testing.md` for the API-level cross-tenant boundary regression test.
