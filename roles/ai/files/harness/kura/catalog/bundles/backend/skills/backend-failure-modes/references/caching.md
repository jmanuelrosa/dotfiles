# Caching

When to read: the brief or diff adds or touches a cache (Redis, in-process, HTTP, CDN, memoization), or changes data that something else caches.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Cache without an invalidation map.** A cache added before enumerating every write path that mutates the underlying data serves stale data on exactly the paths nobody listed.
  Check: write down each mutation path and what it must invalidate or update; if you cannot enumerate them, do not add the cache.
- **Stampede on expiry.** A hot key expiring under load sends every concurrent request to the origin at once; the cache made peak load worse, not better.
  Check: hot keys get TTL jitter plus single-flight locking or stale-while-revalidate; the origin survives a cold cache at peak (that is the sizing question, not the warm case).
- **Missing key dimension.** A cache key that omits tenant, user, locale, or version serves one caller's data to another; this is a security incident, not staleness.
  Check: the key contains every input that changes the value, tenant and identity first; review the key construction character by character.
- **Undefined staleness budget.** How stale user-visible data may be is a product decision; a silently chosen TTL becomes an invisible contract.
  Check: the acceptable staleness window is stated in the brief or confirmed via `needs-decision`, then the TTL is derived from it.
- **Miss and null conflated.** Storing nothing for "known absent" makes every request for a missing entity hammer the origin; storing null accidentally can mask real data.
  Check: negative caching is an explicit decision with its own shorter TTL, distinguishable from a miss.
- **Serialization drift across deploys.** New code deserializing cache entries written by old code (or vice versa during rollout) throws or, worse, silently misreads fields.
  Check: cached value shapes are versioned in the key or namespace, so a deploy reads its own entries and old ones age out.
- **Unbounded local cache.** An in-process map used as a cache without size bounds or TTL is a memory leak with a flattering name, and its contents differ per instance behind the load balancer.
  Check: bounded size, eviction policy, and TTL; per-instance inconsistency is acceptable for this data or the cache moves to a shared store.
- **Cache as accidental source of truth.** Data written to the cache that cannot be rebuilt from the system of record is data waiting to be lost on the next eviction or flush.
  Check: every cached value is derivable from durable storage; flushing the entire cache is always survivable.

## Escalation triggers (`needs-decision`)

- Adding a cache to a path with strict read-after-write expectations.
- Introducing a new cache store or layer (also an ask-first boundary in the agent).
- Any staleness window the brief leaves undefined for user-visible data.

## What good looks like

- The cache is a pure performance layer: correctness holds, slower, with it removed.
- The cache hides no fixable inefficiency: N+1 queries and missing indexes are fixed before anything is cached over them.
- Hit rate, latency, and origin fallback are visible in metrics from day one.
- Invalidation is triggered by the write path itself, not by hope and TTL alone.
