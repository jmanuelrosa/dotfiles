# Offline and network

When to read: the brief or diff touches network calls, sync, request retries, caching, or anything that must work offline or on a bad connection.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Happy-path-only networking.** Mobile networks drop mid-request as normal operation, not as an edge case; a call with no failure handling leaves a dead screen or an infinite spinner.
  Check: every new call has an explicit timeout, a rendered failure state, and bounded retries with backoff and jitter.
- **No offline read path.** A screen that rendered data yesterday shows blank or an error today in a tunnel, even though the data is on the device.
  Check: previously fetched data renders from the local cache when offline, with staleness signaled, and refreshes on reconnect.
- **Lost writes.** A user action taken offline is silently dropped instead of queued or refused.
  Check: mutations either persist to a queue with visible pending state and sync later, or fail loudly at the moment of action; silence is never an option.
- **Duplicate submission on retry.** A retried or replayed mutation without idempotency double-posts the order, the message, or the payment.
  Check: retried writes carry an idempotency key or a server-side dedupe, and the UI guards against double-tap re-submission.
- **Check-then-act connectivity races.** Code that asks "am I online?" before acting is wrong by the time it acts; reachability flips mid-flow.
  Check: act and handle the failure, rather than gating on a connectivity check; in-flight requests tolerate the transition.
- **Sync conflicts resolved by accident.** Two devices or an offline session edit the same data; last-write-wins silently discards someone's work.
  Check: the conflict strategy is explicit and named (merge, last-write-wins with a stated rationale, or surface to the user), not an accident of write order.
- **Cache without identity or expiry.** A cache keyed without the user or account dimension leaks data across account switches; a cache with no invalidation path serves stale data forever.
  Check: cache keys carry the identity dimension, entries have an expiry or invalidation path, and logout clears them.
- **Unbounded transfers on metered connections.** A full-quality media upload or a whole-collection download runs on cellular and burns the user's plan or dies at 90%.
  Check: large transfers are chunked or resumable, and deferred or degraded on constrained connections where the platform exposes that state.

## Escalation triggers (`needs-decision`)

- Changing sync or conflict-resolution semantics that shipped clients already rely on.
- Introducing a new offline store or queue others must maintain.

## What good looks like

- Every screen has deliberate loading, offline, error, and empty states.
- Writes are idempotent end to end; a retry storm changes state exactly once.
- The app degrades by feature, not by screen: what is cached works, what needs the network says so.
