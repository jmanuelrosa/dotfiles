# GraphQL, gRPC and WebSockets

When to read: the brief, diff, or assessed surface touches a GraphQL schema, resolvers, introspection or GraphiQL, query depth, cost or batching limits; gRPC services, protobuf messages, interceptors, reflection, streaming RPCs or service discovery; or WebSocket handshakes, origin checks, message handlers, connection limits or long-lived socket sessions.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [GraphQL](https://cheatsheetseries.owasp.org/cheatsheets/GraphQL_Cheat_Sheet.html), [gRPC Security](https://cheatsheetseries.owasp.org/cheatsheets/gRPC_Security_Cheat_Sheet.html), [WebSocket Security](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html)

## Contents

- Authentication and connection hijacking
- Authorization per operation, field and message
- Injection and input validation
- Resource exhaustion and batching
- Schema and service exposure
- Transport and protocol configuration
- Errors, logging and monitoring
- Security testing and maintenance

## Authentication and connection hijacking

- **WebSocket handshake without `Origin` allowlist (CSWSH).** Browsers send cookies on the WebSocket handshake, so a malicious site can open an authenticated socket; validate `Origin` on every handshake against an explicit allowlist (no wildcards, substring matching or denylists), performing the check before the upgrade is completed. An origin callback that simply returns true is the classic failure.
  Check: the upgrade path compares `Origin` to an exact allowlist and rejects otherwise. Owner: `backend`. Source: WebSocket Security.
- **No CSRF token or SameSite on socket authentication.** Applications already using CSRF protection should include CSRF tokens in the handshake, and session cookies should use `SameSite=Lax` or `Strict` to strengthen CSWSH defenses.
  Check: handshake requires the CSRF token where the app uses them; session cookie sets `SameSite`. Owner: `backend`. Source: WebSocket Security.
- **WebSocket token in the URL query string.** Tokens in URLs leak into access logs; browser clients should send the token in the first message over WSS. Until validation succeeds accept only the authentication message, send no protected data, close on failure or timeout, limit unauthenticated connections, and keep tokens out of message logs.
  Check: socket URLs carry no tokens; the handler gates all other message types behind successful authentication with a timeout. Owner: `backend`, `frontend`. Source: WebSocket Security.
- **Long-lived socket outlives the session.** Close connections when sessions expire, re-validate sessions periodically (every 30 minutes is common), close all of a user's sockets immediately on logout using a session-to-connection map, and rotate tokens on long-lived connections.
  Check: a session-to-socket registry exists and logout and expiry close sockets; periodic revalidation is scheduled. Owner: `backend`. Source: WebSocket Security.
- **gRPC method without authentication.** Every protected method needs an authentication check; a unary interceptor does not protect streaming RPCs, so register an equivalent stream interceptor. Carry credentials in metadata, never in method parameters.
  Check: both unary and stream server interceptors enforce authentication; no proto request message has credential fields. Owner: `backend`. Source: gRPC Security.
- **Long-lived gRPC tokens.** Use short-lived tokens (15 to 60 minutes) with expiration and refresh mechanisms.
  Check: token issuance sets a lifetime within that range and the client refreshes. Owner: `backend`. Source: gRPC Security.
- **Service-to-service gRPC without mTLS.** Use mutual TLS between services, with short-lived certificates (90 days or less) and automated rotation; a service mesh can provide automatic mTLS and central policy.
  Check: service clients and servers configure client certificates and a CA pool, or mesh mTLS is enforced; certificate lifetime is 90 days or less. Owner: `cloud`. Source: gRPC Security.
- **Service discovery open to tampering.** Protect discovery so attackers cannot inject endpoints or read service information: TLS with client certificates to the registry, and least-privilege RBAC (read-only on services and endpoints) for discovery clients.
  Check: registry clients use HTTPS with client certs; Kubernetes roles for discovery grant only `get`, `list`, `watch`. Owner: `cloud`. Source: gRPC Security.

## Authorization per operation, field and message

- **Resolver trusts object ID possession (BOLA/IDOR).** Every query and mutation must verify the requester may view or modify the specific object; generic `node`/`nodes` fields allow fetching any object by ID and must be removed or authorized.
  Check: resolvers taking IDs perform an ownership or policy check; `node` fields enforce the same checks or are absent. Owner: `backend`. Source: GraphQL. See `authorization.md` for object-level authorization.
- **Authorization only on edges, not nodes.** Enforce checks on both edges and nodes, so an object reachable by another path is not exposed.
  Check: type-level resolvers enforce authorization independent of the parent field. Owner: `backend`. Source: GraphQL.
- **All fields readable by every consumer.** When fields need different access levels, check per field that the requester may read it; interfaces and unions can return more or fewer properties per permission.
  Check: sensitive fields have field-level authorization directives or checks. Owner: `backend`. Source: GraphQL.
- **Mutations without access control.** Where only some parties may modify data (or the API is meant read-only), restrict mutations per consumer and field.
  Check: every mutation resolver has an authorization check. Owner: `backend`. Source: GraphQL.
- **gRPC method authorization missing or allow-by-default.** Enforce least-privilege, method-level authorization, denying methods with no declared permission, and log all authorization failures.
  Check: the method-permission map denies unknown methods and failures are logged. Owner: `backend`. Source: gRPC Security.
- **Open WebSocket treated as unlimited access.** Check authorization for every action carried in a message, not only at connection.
  Check: the message dispatcher checks the user's permission per action type. Owner: `backend`. Source: WebSocket Security.
- **WebSocket tunneling internal TCP services.** Tunneling VNC, FTP, SSH or similar through WebSockets exposes them to any XSS; if necessary, add authentication and access control beyond the WebSocket layer.
  Check: tunnel endpoints require their own authentication. Owner: `backend`. Source: WebSocket Security.

## Injection and input validation

- **Loosely typed GraphQL inputs.** Allowlist-validate all incoming data using specific scalars, enums, custom scalars or validators and input types for mutations; prefer the strictest allowed character set; use a single internal character encoding for Unicode; reject invalid input without revealing how validation works.
  Check: schema arguments use enums or constrained custom scalars instead of free `String` where possible. Owner: `backend`. Source: GraphQL.
- **Protobuf types treated as validation.** Protobuf gives type safety, not business validation; validate every message server-side (length, range, format) with allowlists for strings, for example via declarative validation rules on the proto.
  Check: handlers or proto validation rules bound every string and numeric field. Owner: `backend`. Source: gRPC Security.
- **WebSocket messages trusted.** Validate message structure and content with JSON schemas and allowlists; parse with `JSON.parse`, never `eval`; for binary data verify type by magic numbers, scan uploads when appropriate, and use safe deserialization for protobuf or MessagePack.
  Check: the message handler validates against a schema before dispatch; binary handlers check magic bytes. Owner: `backend`. Source: WebSocket Security.
- **Resolver or handler builds interpreter queries from input.** Input reaching SQL, NoSQL, ORM, OS, LDAP or XML interpreters must use safe APIs such as parameterized statements (ORMs used correctly), or a maintained escaping library for the target interpreter when none exists.
  Check: data fetchers and RPC handlers use parameterized queries. Owner: `backend`. Source: GraphQL, gRPC Security, WebSocket Security. See `injection.md` for per-interpreter rules.
- **User input controls outbound requests.** Do not make HTTP or resource requests to a host the user supplies unless there is an absolute business need.
  Check: resolvers do not take URLs or hosts from arguments for outbound calls. Owner: `backend`. Source: GraphQL. See `ssrf.md` for outbound request controls.
- **WebSocket messages replayable.** Include timestamps or nonces in messages and reject duplicates.
  Check: state-changing message types carry a nonce or timestamp checked against a replay store. Owner: `backend`. Source: WebSocket Security.

## Resource exhaustion and batching

- **Unbounded GraphQL query depth and amount.** Depth and requested amounts are unlimited by default; enforce a maximum depth, cap list sizes and require pagination.
  Check: server config registers depth and amount limits; list fields require bounded pagination arguments. Owner: `backend`. Source: GraphQL.
- **No GraphQL cost limit.** Consider query cost analysis with a maximum cost per query, the most thorough DoS control, after confirming the schema needs it.
  Check: a cost or complexity limit is configured, or the decision not to is recorded. Owner: `backend`. Source: GraphQL.
- **GraphQL batching enables brute force and enumeration.** Batched operations or aliased fields bypass request-count rate limits and security tooling; enforce code-level limits per request: object-request rate limits, no batching for sensitive objects (usernames, emails, passwords, OTPs, session tokens), and a cap on operations run at once.
  Check: batch size and alias counts are capped; login, OTP and lookup-by-identifier operations reject batching. Owner: `backend`. Source: GraphQL.
- **GraphQL rate limits counted only per HTTP request.** Request counts miss expensive queries and multi-operation requests; apply rate limits per IP and/or user in the business logic layer together with cost and batching limits. A response bandwidth limiter does not limit request counts.
  Check: rate limiting accounts for operation count or cost, not just requests. Owner: `backend`. Source: GraphQL.
- **No resolver timeouts.** Add application-level query and resolver timeouts (more effective than infrastructure timeouts, which are less accurate and easier to bypass), with infrastructure timeouts as an additional layer; use server-side batching and caching to avoid duplicate fetches.
  Check: resolver execution has a deadline; data fetchers use batched loading. Owner: `backend`. Source: GraphQL.
- **gRPC message size unbounded per stream.** Set receive and send message size limits appropriate to the application (grpc-go defaults receive to 4 MiB); per-message limits do not bound a stream, so enforce maximum messages per stream and maximum session duration.
  Check: server options set explicit send and receive limits; stream handlers cap message count and duration. Owner: `backend`. Source: gRPC Security.
- **gRPC rate limiting misses streams or grows without bound.** Rate-limit unary calls and apply stream admission limits plus per-message limits inside streams; cap the number of limiter keys, schedule cleanup of stale keys, derive keys from a trusted connection or authenticated identity (not forwarded headers), and use a shared rate-limiting service when limits must hold across replicas.
  Check: both unary and stream interceptors rate-limit; the limiter store has a size cap and running cleanup. Owner: `backend`. Source: gRPC Security.
- **gRPC calls without deadlines.** Configure client- and server-side timeouts; the server sets a defensive deadline when the client did not set a shorter one.
  Check: server handlers apply a default deadline; clients set deadlines on calls. Owner: `backend`. Source: gRPC Security.
- **WebSocket connections and messages unbounded.** Cap total connections and per-user (preferred) or per-IP connections; limit message size (typically 64 KB or less); rate-limit messages (100 per minute is a common starting point); close idle connections; use ping/pong heartbeats to reap dead ones; and apply backpressure so fast producers cannot exhaust memory.
  Check: server config sets max payload, connection caps, idle timeout and heartbeat; handlers enforce per-connection message rate. Owner: `backend`. Source: WebSocket Security.
- **No OS or container resource limits.** Limit CPU and memory for the API process (cgroups, ulimits, container limits).
  Check: deployment manifests set CPU and memory limits. Owner: `platform`. Source: GraphQL. See `containers-and-kubernetes.md` for container resource limits.

## Schema and service exposure

- **GraphQL introspection enabled in production.** Disable introspection system-wide for internal APIs and production or public environments, or restrict it to authenticated, authorized consumers when the API is public.
  Check: production config disables introspection or gates it by role. Owner: `backend`. Source: GraphQL.
- **GraphiQL or schema explorers exposed.** Disable GraphiQL and similar tools in production or publicly accessible environments.
  Check: the explorer is enabled only behind a development environment flag. Owner: `backend`. Source: GraphQL.
- **Field suggestions leak schema with introspection off.** "Did you mean" hints allow schema guessing; disable them where the implementation allows when introspection is disabled.
  Check: field suggestion is turned off alongside introspection. Owner: `backend`. Source: GraphQL.
- **gRPC reflection registered in production.** Reflection reveals the full method and message surface; register it only outside production.
  Check: reflection registration is behind a non-production environment check. Owner: `backend`. Source: gRPC Security.

## Transport and protocol configuration

- **gRPC without TLS.** Production gRPC must use TLS 1.2 or higher with strong cipher suites and weak protocols and ciphers disabled; TLS must be configured explicitly where the stack requires it (and HTTP/2 ALPN supported).
  Check: servers are created with TLS credentials, not insecure/plaintext options. Owner: `backend`. Source: gRPC Security. See `http-headers-tls-and-caching.md` for TLS settings.
- **WebSocket over `ws://`.** Never use unencrypted `ws://` in production; use `wss://`.
  Check: client socket URLs use `wss://`; server does not listen for plain WebSocket in production. Owner: `backend`, `frontend`. Source: WebSocket Security.
- **Legacy WebSocket protocol versions accepted.** Support only RFC 6455; drop Hixie-76 and hybi-00.
  Check: the WebSocket library or server does not enable legacy draft support. Owner: `backend`. Source: WebSocket Security.
- **`permessage-deflate` enabled without need.** Compression combined with secrets can leak data (CRIME/BREACH class); disable it unless specifically needed.
  Check: server config disables per-message deflate. Owner: `backend`. Source: WebSocket Security.
- **Proxy or WAF not handling WebSockets.** Reverse proxies, load balancers and CDNs must support the HTTP/1.1 upgrade, pass `Upgrade` and `Connection: upgrade`, and set read timeouts for long-lived connections; if the WAF cannot inspect messages beyond the handshake, rely on server-side validation and application logging.
  Check: proxy config handles the upgrade headers with explicit timeouts. Owner: `cloud`. Source: WebSocket Security.

## Errors, logging and monitoring

- **Verbose errors returned to clients.** Do not return stack traces or run in debug mode in production; return generic messages, log details server-side, and mask errors through middleware. gRPC uses `UNAUTHENTICATED`, `PERMISSION_DENIED` and `INVALID_ARGUMENT` appropriately.
  Check: production disables stack traces in GraphQL responses and error masking is configured; gRPC handlers return generic status messages. Owner: `backend`. Source: GraphQL, gRPC Security.
- **WebSocket traffic invisible in logs.** HTTP logs capture only the upgrade; log connection open and close (identity, IP, origin), authentication and authorization events, rate-limit and validation violations, and abnormal disconnections, never full message contents, tokens, session IDs or personal data.
  Check: socket handlers emit these events and redact payloads. Owner: `backend`. Source: WebSocket Security. See `logging-and-error-handling.md` for logging practice.
- **gRPC security events unlogged or uncorrelated.** Log authentication attempts, authorization failures and suspicious activity as structured events with correlation IDs and without passwords or tokens; enable distributed tracing with method and client context.
  Check: interceptors emit structured security events with a correlation id; tracing is enabled. Owner: `backend`. Source: gRPC Security.
- **No alerting on RPC abuse.** Monitor request rates per method and client, authentication and authorization failure rates, error rates and unusual traffic; alert on high authentication failure rates, calls to non-existent methods and resource exhaustion patterns.
  Check: dashboards and alerts exist for these signals. Owner: `sre`. Source: gRPC Security.

## Security testing and maintenance

- **No protocol-specific security tests.** The pipeline should test authentication bypass, authorization boundaries, input validation and injection, rate limiting, message size limits, TLS configuration and error disclosure for every gRPC method; and for WebSockets, connections from unauthorized origins, unauthenticated connections, injection payloads, connection and message flooding, oversized messages, and session expiry and logout handling.
  Check: test suites contain these negative cases for each RPC service and socket endpoint. Owner: `qa`. Source: gRPC Security, WebSocket Security.
- **Malformed messages crash the server.** Use async exception handling so malformed WebSocket messages cannot crash the application.
  Check: message handlers catch parse and validation errors per message. Owner: `backend`. Source: WebSocket Security.
- **Outdated WebSocket libraries.** WebSocket libraries have had critical DoS and RCE flaws; update them regularly and monitor advisories.
  Check: the WebSocket library is covered by automated dependency updates. Owner: `dx`. Source: WebSocket Security. See `supply-chain-and-dependencies.md` for dependency management.
