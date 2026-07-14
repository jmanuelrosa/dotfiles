# Service-to-service resilience

When to read: the brief or diff touches outbound HTTP/gRPC calls, service clients, load balancer or gateway config, health checks, connection pools, or shutdown behavior.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The infinite default timeout.** Most HTTP clients default to no read timeout; one slow dependency then pins threads or sockets until the service starves.
  Check: every outbound call has an explicit connect and read timeout, chosen from the caller's latency budget, not a round number.
- **Retry amplification.** Retries at multiple layers multiply: three retries at the client times three at the gateway is nine times the load, aimed at a dependency that is already down.
  Check: retries are bounded, use exponential backoff with jitter, apply only to idempotent operations, and never fire on 4xx; know which other layers already retry this path.
- **Failure cascades instead of degrading.** A dead downstream taking the whole feature (or service) with it turns one incident into two.
  Check: the call site fails fast when the dependency is unhealthy (circuit breaker or equivalent) and the feature degrades to a defined fallback; if the brief does not define the degraded behavior, that is a `needs-decision`.
- **Pool exhaustion as the real outage.** A slow dependency plus an unbounded or oversized wait queue exhausts the connection pool, and unrelated endpoints sharing the pool start failing.
  Check: pool sizes and acquisition timeouts are explicit; isolate critical paths from bulk work rather than sharing one pool.
- **Deepened sync chains.** Adding a synchronous call to a hot path adds its latency to the p99 and multiplies unavailability: five sequential 99.9% dependencies are already under 99.5%.
  Check: a new synchronous cross-service dependency in a request path is an escalation, not a default; prefer async or cached data when the brief allows.
- **Timeout hierarchy inverted.** If the server keeps working after the client and gateway gave up, capacity burns on abandoned requests; if the LB idle timeout exceeds the server's keep-alive, connections die mid-request.
  Check: client timeout > gateway timeout > server handler timeout, and server keep-alive exceeds the LB idle timeout.
- **Health check lies.** A liveness probe that checks dependencies causes restart storms when a dependency blips; a readiness probe that checks nothing routes traffic to an instance that cannot serve it.
  Check: liveness tests only the process itself; readiness tests what serving actually requires; neither change is casual.
- **Ungraceful shutdown.** A deploy that kills in-flight requests, drops uncommitted queue messages, or abandons running jobs turns every release into a micro-incident.
  Check: the service drains on SIGTERM within the platform's grace period: stop accepting, finish in-flight work, commit or release, then exit.
- **Synchronized recovery stampede.** When a dependency recovers, every waiting client reconnecting at once knocks it back down.
  Check: reconnects and cache refills are jittered, not synchronized.

## Escalation triggers (`needs-decision`)

- Adding a new synchronous dependency to a request-serving path.
- Changing timeout, retry, or health-check config that platform or SRE owns.
- A fallback behavior the brief leaves undefined.

## What good looks like

- Any single dependency can be down and the blast radius is one degraded feature, not the service.
- Every remote call has a timeout, a bounded retry policy, and a metric.
- Deploys and dependency blips are invisible to users.
