# REST APIs, Web Services and Webhooks

When to read: the brief, diff, or assessed surface touches REST or SOAP endpoints, API keys, bearer-token validation on an API, HTTP method routing, content negotiation, API error responses or status codes, CORS on an API, management or admin endpoints, multi-step API workflows, OpenAPI specs, webhook receivers (signature verification, replay, idempotency) or webhook senders (callback URL registration, delivery workers, retries).
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [REST Security](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html), [REST Assessment](https://cheatsheetseries.owasp.org/cheatsheets/REST_Assessment_Cheat_Sheet.html), [Web Service Security](https://cheatsheetseries.owasp.org/cheatsheets/Web_Service_Security_Cheat_Sheet.html), [Webhook Security](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html)

## Contents

- Webhook delivery authentication
- Webhook replay, duplicates and ordering
- Webhook sender: SSRF and delivery behavior
- API authentication and access control
- Workflow state enforcement
- Transport and message protection
- Input, content type and schema validation
- Resource limits and rate limiting
- Responses, errors and headers
- Logging and monitoring
- Security testing

## Webhook delivery authentication

- **Webhook receiver without signature verification.** A webhook endpoint is a public unauthenticated `POST` handler, so forged events can trigger fulfillment, account access or record changes; every delivery must be verified with HMAC-SHA256 (or the publisher's documented scheme) before any processing. Use the publisher's maintained verification library when one exists and follow its exact signing format.
  Check: the webhook handler verifies the signature before parsing or acting on the event. Owner: `backend`. Source: Webhook Security.
- **Signature computed over a re-serialized body.** Verification must use the raw request bytes captured before framework parsing; re-serializing JSON, reordering fields, or changing whitespace, line endings or encoding breaks verification.
  Check: the route reads the raw body (raw-body middleware or equivalent) for HMAC input. Owner: `backend`. Source: Webhook Security.
- **Signature compared with `==`.** Comparison must be constant-time (`hmac.compare_digest`, `crypto.timingSafeEqual`, `MessageDigest.isEqual`); ordinary equality leaks timing and can make the endpoint a signing oracle.
  Check: the HMAC comparison calls a constant-time function. Owner: `backend`. Source: Webhook Security.
- **Signature scheme downgrade or rotation failure.** Accept only the expected scheme (for example Stripe `v1`) and ignore others in the header; when several signatures are present, accept if any one matches so planned rotation works in either order.
  Check: the verifier filters by scheme version and iterates all supplied signatures. Owner: `backend`. Source: Webhook Security.
- **Signature failure reveals the reason.** Missing or mismatched signatures return `401` with no explanation.
  Check: verification failures return a bare `401`. Owner: `backend`. Source: Webhook Security.
- **Weak or shared signing secrets (publisher).** Generate a cryptographically random secret per registered webhook (32 bytes is a sound default; Standard Webhooks specifies 24 to 64 bytes), and for a new protocol sign the event ID, delivery timestamp and raw body together with a documented scheme. During planned rotation sign with every active secret and send one signature per secret.
  Check: secret generation uses a CSPRNG with at least 24 bytes per webhook; signed material includes id, timestamp and body. Owner: `backend`. Source: Webhook Security.
- **Webhook secret hardcoded or logged.** Store signing secrets in a secrets manager (never in source, config files or images), use one secret per webhook, and redact secrets and signature header values from logs and error responses.
  Check: secrets are read from the secret store; logging excludes signature and `Authorization` headers. Owner: `backend`. Source: Webhook Security. See `secrets-management.md` for secret storage.
- **Compromised webhook secret kept in an overlap window.** On suspected compromise revoke and replace immediately; overlap windows (Stripe allows up to 24 hours) are only for planned rotation, after which deliveries signed only with the revoked secret get `401`.
  Check: the rotation runbook distinguishes compromise (immediate revoke) from planned rotation (overlap). Owner: `sre`. Source: Webhook Security.
- **Signing secret is the only barrier.** HMAC authenticates the payload, not the connection; where a leaked secret must not suffice, add mTLS, a rotated bearer token or API key, or OAuth 2.0 client credentials with full token validation (including token type for RFC 9068 JWTs). IP allowlisting is an extra layer only, never proof of identity.
  Check: high-value webhook routes require a second authentication factor beyond the HMAC. Owner: `backend`. Source: Webhook Security.
- **CSRF exemption broader than the webhook route.** Exempt only the webhook route from CSRF token checks, and only once signature verification is in place as the replacement control.
  Check: CSRF exemption lists exactly the webhook path, which verifies signatures. Owner: `backend`. Source: Webhook Security.
- **Webhook endpoint over plain HTTP.** Require HTTPS with TLS 1.2 or higher and a trusted-CA certificate; signatures do not encrypt the payload. Publishers must verify the subscriber's certificate on every delivery.
  Check: receiver listens on HTTPS only; sender HTTP client keeps certificate verification enabled. Owner: `backend`. Source: Webhook Security.

## Webhook replay, duplicates and ordering

- **No freshness check on deliveries.** A captured delivery remains validly signed; where the protocol authenticates a timestamp, reject deliveries outside a small tolerance (five minutes is Stripe's default) with NTP-synced clocks, and publishers generate a fresh timestamp and signature for every retry.
  Check: the verifier compares the signed timestamp to now with a bounded tolerance. Owner: `backend`. Source: Webhook Security.
- **No replay cache for authenticated event IDs.** After signature and freshness checks, cache event IDs for at least twice the tolerance (10 minutes for a 5-minute window). Body-only signatures (for example GitHub's) do not authenticate a timestamp or delivery id, so rely on idempotent downstream effects there.
  Check: accepted event IDs are cached with TTL of at least twice the tolerance. Owner: `backend`. Source: Webhook Security.
- **Non-idempotent webhook processing.** Publishers retry (Stripe for up to three days), so persist processed event IDs across the retry period, skip repeats, return `200` for authenticated duplicates already durably queued or processed, and make side effects (writes, emails, payments) idempotent.
  Check: a durable processed-event table keyed on event ID guards side effects. Owner: `backend`. Source: Webhook Security.
- **In-order delivery assumed.** Fetch current object state from the publisher API when an event may be stale; use sequence or version fields only when the publisher documents ordering, since timestamps alone may not establish order.
  Check: handlers do not apply state transitions purely in arrival order. Owner: `backend`. Source: Webhook Security.

## Webhook sender: SSRF and delivery behavior

- **Subscriber callback URL not restricted (SSRF).** Accept only `https://`, resolve the host and reject every non-globally-reachable address (the SSRF deny-list including IPv6 equivalents) plus internal names such as `metadata.google.internal`.
  Check: registration and delivery code enforce a scheme allowlist and a non-public address deny-list. Owner: `backend`. Source: Webhook Security. See `ssrf.md` for the full deny-list.
- **Callback IP validated before the client re-resolves (DNS rebinding).** Validate the address actually connected to: resolve once and connect to that IP while sending the original `Host` and SNI, or validate inside the client's connect hook using the same lookup.
  Check: validation happens at connect time on the resolved IP, not on a separate pre-lookup. Owner: `backend`. Source: Webhook Security.
- **Delivery client follows redirects.** Disable redirects or apply the same destination checks to every redirect target (treating redirects as failed deliveries is acceptable).
  Check: the delivery HTTP client has redirects disabled or re-validated. Owner: `backend`. Source: Webhook Security.
- **Delivery workers on a network that reaches internals.** Isolate delivery workers or their egress proxy in a segment that cannot reach internal services; an egress proxy can enforce destination checks.
  Check: IaC places webhook workers behind a restricted egress path. Owner: `cloud`. Source: Webhook Security.
- **Unbounded delivery retries.** Publishers apply per-subscriber delivery limits, exponential backoff with jitter, a maximum retry count, and disable endpoints that keep failing for days; keep payloads small (Standard Webhooks recommends under 20 KB).
  Check: retry policy is capped with backoff and jitter; payload size is bounded. Owner: `backend`. Source: Webhook Security.

## API authentication and access control

- **Endpoint without its own access control decision.** Every non-public REST endpoint must perform access control, authorizing the caller for the method and the specific resource on every request; decisions are taken locally at the endpoint while user authentication is centralized in an identity provider that issues access tokens.
  Check: each new route has an authorization check covering both the operation and the object. Owner: `backend`. Source: REST Security, Web Service Security. See `authorization.md` for object-level authorization design.
- **Sensitive operations without step-up.** Password changes, primary contact details such as email, physical address, and payment or delivery instructions should require a challenge-response authorization on top of the session.
  Check: these handlers require re-authentication or a challenge. Owner: `backend`. Source: Web Service Security.
- **JWT accepted without full validation.** Require signed or MACed tokens (reject `alg: none`), prefer signatures over MACs (a shared MAC key lets every verifier mint tokens), select the algorithm from relying-party configuration never the token header, require and validate `iss`, `aud` and `exp` (and `nbf` when the profile requires it), and denylist the `jti` on explicit session termination until expiry.
  Check: the verifier pins algorithms and issuer/audience in config and rejects tokens missing `exp`. Owner: `backend`. Source: REST Security, REST Assessment. See `tokens-and-federation.md` for full JWT handling.
- **API key treated as sufficient protection.** Require the key on every request to protected endpoints, return `429` when requests arrive too quickly, revoke keys whose clients violate the agreement, and never rely on API keys alone for sensitive, critical or high-value resources.
  Check: high-value endpoints require user or client authentication beyond a static key. Owner: `backend`. Source: REST Security.
- **HTTP method not allowlisted (verb tampering).** Allowlist permitted methods per route, reject others with `405`, and authorize the caller for the incoming method on the collection, action and record. Webhook routes accept `POST` only.
  Check: routes declare explicit methods; authorization rules are not method-scoped in a way that lets an unlisted verb bypass them. Owner: `backend`. Source: REST Security, Webhook Security.
- **Management endpoints reachable from the internet.** Avoid exposing them publicly; otherwise require strong authentication such as MFA, expose them on different ports or hosts (ideally a separate NIC and restricted subnet), and restrict with firewall rules or ACLs. Admin functions should be limited to service administrators, ideally in a separate application.
  Check: actuator, admin and metrics endpoints are bound to an internal listener or network-restricted. Owner: `cloud`. Source: REST Security, Web Service Security.
- **Basic Authentication on a web service.** Basic Authentication is not recommended because it sends secrets in base64 headers; if used it must run over TLS. Mutual TLS client certificates are recommended where appropriate, and should be considered for highly privileged services.
  Check: no Basic Auth over HTTP; privileged service-to-service APIs evaluate mTLS. Owner: `backend`. Source: Web Service Security, REST Security.
- **Credentials in URLs.** Passwords, tokens and API keys must not appear in URLs, where logs capture them; send them in the body for `POST`/`PUT` or in headers for `GET`.
  Check: no route or client puts keys or tokens in query strings. Owner: `backend`. Source: REST Security.
- **State passed through the client to keep the API stateless.** Passing state from client to backend to appear stateless is prone to replay and impersonation and should be avoided.
  Check: no security-relevant state round-trips through client-held fields without server-side binding. Owner: `backend`. Source: REST Security.

## Workflow state enforcement

- **Multi-step workflow callable out of order.** Each step (for example create, pay, confirm) must validate the current workflow state on the server for every request, using an explicit state machine; bind tokens or identifiers to specific stages, never rely on the frontend for sequencing, and reject invalid transitions.
  Check: later-stage handlers load and verify the persisted state before acting. Owner: `backend`. Source: REST Security. See `abuse-dos-and-business-logic.md` for broader business logic abuse.

## Transport and message protection

- **API reachable over plain HTTP.** REST services must only expose HTTPS endpoints; all communication with and between services carrying sensitive features, authenticated sessions or sensitive data must use well-configured TLS, even when messages are separately encrypted.
  Check: service listeners and internal service clients use HTTPS only. Owner: `backend`. Source: REST Security, Web Service Security. See `http-headers-tls-and-caching.md` for TLS configuration.
- **Service consumer skips server authentication.** Consumers must verify the server certificate is from a trusted issuer, unexpired, unrevoked and matches the service domain.
  Check: HTTP clients do not disable certificate or hostname verification. Owner: `backend`. Source: Web Service Security.
- **Sensitive data at rest left with only transport encryption.** Messages with sensitive data must be encrypted with a strong cipher; data that must stay encrypted after receipt needs message-level or data encryption, not just TLS. For XML, use XML digital signatures with the sender's private key for message integrity.
  Check: persisted sensitive message content is encrypted at rest; XML messages needing integrity are signed. Owner: `backend`. Source: Web Service Security.
- **Client and server SOAP encoding differ.** Enforce the same encoding style on client and server.
  Check: SOAP bindings declare matching encoding styles. Owner: `backend`. Source: Web Service Security.
- **WS-I Basic Profile treated as a security baseline.** It is an interoperability profile that permits services with no countermeasures; enforce transport security, authentication, authorization and resource limits independently.
  Check: services claiming WS-I conformance still implement the controls above. Owner: `architect`. Source: Web Service Security.

## Input, content type and schema validation

- **Unvalidated API input.** Validate length, range, format and type; use strong types (numbers, booleans, dates, enums); constrain strings with regexes; reject unexpected content; use the language's validation libraries; and use a secure parser (XML parsers must be hardened against XXE).
  Check: request DTOs or schemas declare types and bounds; unknown fields are rejected. Owner: `backend`. Source: REST Security, Web Service Security. See `injection.md` for input validation depth.
- **Webhook payload trusted because it is signed.** A valid signature proves the sender, not that content is safe; enforce a body size limit, reject unexpected `Content-Type`, validate against a strict schema, then use parameterized queries and context output encoding downstream.
  Check: webhook handlers validate a schema after verification. Owner: `backend`. Source: Webhook Security.
- **Request content type not enforced.** For requests with a body, require a supported `Content-Type` per contract and reject others with `415`; do not require it for bodiless requests; explicitly declare consumed and produced types so unintended parsers (for example XML) are not exposed. Document all supported content types.
  Check: routes declare accepted media types and return `415` otherwise. Owner: `backend`. Source: REST Security.
- **Response `Content-Type` copied from `Accept`.** Select a supported type matching the client's `Accept` (including ranges and quality values), return `406` when none fits and no default applies, and send a type matching the body (for example `application/json`, not `application/javascript`).
  Check: no code echoes `Accept` into `Content-Type`. Owner: `backend`. Source: REST Security.
- **SOAP payloads not schema-validated.** Validate SOAP payloads against their XSD, which should define maximum length and character set for every parameter and strict allowlist patterns for fixed-format fields.
  Check: XSDs carry `maxLength` and pattern facets; the service validates against them. Owner: `backend`. Source: Web Service Security.
- **XML input not protected against malformed entities, bombs and XXE.** XML content validation must cover malformed entities, entity expansion and recursive or oversized payloads, external entities, overlong element names, and strong allowlists, ideally in the parser or schema validator, with test cases proving it.
  Check: parser config disables DTDs and external entities and sets size/depth limits; tests cover these payload classes. Owner: `backend`. Source: Web Service Security. See `xml-and-deserialization.md` for parser hardening.
- **Attachments stored without malware scanning.** Scan files and attachments inline before they reach disk, with regularly updated definitions.
  Check: the attachment path invokes a scanner before persistence. Owner: `backend`. Source: Web Service Security. See `file-upload.md` for upload handling.
- **API output not encoded for consumers that render HTML.** Output must be encoded so clients consume it as data, not script, following XSS prevention rules.
  Check: API fields rendered by clients are encoded or treated as text. Owner: `backend`. Source: Web Service Security.

## Resource limits and rate limiting

- **No request size limit.** Define a request size limit and reject larger requests with `413`; SOAP messages must be size-limited.
  Check: server or gateway config sets a max body size per route. Owner: `backend`. Source: REST Security, Web Service Security, Webhook Security.
- **No rate or execution-time limits.** Enforce request-rate and execution-time limits based on tested capacity and per-operation cost, stricter for expensive operations; answer excess with `429` and `Retry-After`.
  Check: gateway or middleware rate limits exist, with tighter limits on expensive routes. Owner: `backend`. Source: REST Security, Web Service Security, Webhook Security. See `abuse-dos-and-business-logic.md` for DoS controls.
- **Unbounded CPU, memory, files or connections.** Limit CPU and memory per service and cap simultaneous open files, network connections and processes.
  Check: deployment manifests set CPU and memory limits and connection caps. Owner: `platform`. Source: Web Service Security.
- **Webhook processed synchronously.** Acknowledge quickly (GitHub expects a `2xx` within 10 seconds) and process through an asynchronous queue; subscribe only to the event types actually handled.
  Check: the handler enqueues and returns; subscriptions list specific event types. Owner: `backend`. Source: Webhook Security.

## Responses, errors and headers

- **Error responses leak internals.** Return generic messages without stack traces or internal hints; use semantically correct status codes (`401` authentication, `403` authorization, `405`, `406`, `413`, `415`, `429`, generic `500`).
  Check: global error handler strips stack traces and maps exceptions to generic bodies. Owner: `backend`. Source: REST Security, Webhook Security.
- **Webhook acknowledged before durable handling.** Return `200` only after the event is durably queued or processed, `400` for malformed payloads, `401` for signature failures; route repeatedly failing events to a dead-letter queue with alerting.
  Check: acknowledgement follows the durable enqueue; a DLQ exists. Owner: `backend`. Source: Webhook Security.
- **Browser-consumable API missing security headers.** Send `Cache-Control: no-store`, `Content-Security-Policy: frame-ancestors 'none'`, a correct `Content-Type`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`; where the API might ever return HTML, add `Content-Security-Policy: default-src 'none'`, a restrictive `Permissions-Policy` and `Referrer-Policy: no-referrer`. Keep sensitive responses out of application-managed caches.
  Check: API middleware sets these headers on all responses. Owner: `backend`. Source: REST Security. See `http-headers-tls-and-caching.md` for header values.
- **CORS enabled without need or with broad origins.** Disable CORS headers when cross-domain calls are not expected; otherwise be as specific as possible about allowed origins.
  Check: CORS config is absent or lists explicit origins. Owner: `backend`. Source: REST Security.

## Logging and monitoring

- **No audit trail for security events.** Write audit logs before and after security-related events, consider logging token validation and input validation failures (hundreds per second indicates attack), and sanitize log data against log injection.
  Check: auth and authorization handlers emit audit events with sanitized fields. Owner: `backend`. Source: REST Security. See `logging-and-error-handling.md` for logging practice.
- **Webhook logs missing fields or leaking data.** Log timestamp, source IP, method, status, event ID, event type and latency; never full bodies, secrets, or `Authorization`/signature headers. Alert on signature-failure spikes, sustained `4xx`/`5xx`, and deliveries from unexpected addresses.
  Check: webhook log schema includes those fields and excludes bodies and secrets; alerts exist. Owner: `sre`. Source: Webhook Security.

## Security testing

- **Webhook handling untested.** Before production and after changes, test: missing or invalid signature returns `401`; stale and duplicate deliveries do not repeat side effects; oversized payloads get `400` or `413`; publisher rejects `http://`, metadata, loopback, internal and private-resolving callback URLs; rotation accepts both secrets during overlap and rejects revoked ones. Use the publisher's test tooling for genuine signed deliveries.
  Check: the webhook test suite contains these cases. Owner: `qa`. Source: Webhook Security.
- **Token handling untested.** Tests should send tampered, re-signed, unsigned (`alg: none`), algorithm-confused, expired, not-yet-valid, wrong-issuer, wrong-audience and malformed tokens, expecting authentication failure rather than a server error; and call each operation with a token lacking the required scope or role, expecting the documented denial status.
  Check: API test suites include negative token and scope cases. Owner: `qa`. Source: REST Assessment.
- **No BOLA swap tests.** Create objects under two accounts or tenants and replay each request with the other's identifiers across `GET`, `PUT`, `PATCH`, `DELETE` and nested routes; also test low-privilege tokens against admin-only operations (function-level authorization), for every object type.
  Check: an authorization test matrix covers cross-account access per object type and verb. Owner: `qa`. Source: REST Assessment. See `authorization-testing.md` for authorization test automation.
- **No mass-assignment tests.** Add out-of-contract fields (role, verification flag, internal id) to create, update and partial-update requests, including nested objects, and verify by reading back that they did not persist.
  Check: tests assert unadvertised fields are ignored or rejected. Owner: `qa`. Source: REST Assessment. See `authorization.md` for mass assignment prevention.
- **OpenAPI description not reconciled with behavior.** Use the published description (`/openapi.json`, `/swagger.json`, `/docs`) to build a per-operation security matrix from effective `security` requirements (operation-level replaces root-level), fuzz from the schema one constraint at a time, and investigate undocumented endpoints or accepted undefined fields.
  Check: contract tests compare implemented routes and accepted fields with the spec and test each operation's security requirement. Owner: `qa`. Source: REST Assessment.
- **Rate limits untested or keyed only on IP.** Verify throttling on authentication, token and recovery endpoints and on expensive operations (search, export, bulk), that per-account or per-key limits hold beyond per-IP limits, that authenticated sessions do not disable them, and that a single request's cost is bounded.
  Check: tests exercise limits on these endpoints and limits are keyed on account or key. Owner: `qa`. Source: REST Assessment.
- **Workflow sequencing untested.** Tests should invoke later workflow endpoints out of sequence and reuse tokens across steps, expecting rejection.
  Check: workflow tests include out-of-order calls. Owner: `qa`. Source: REST Security.
