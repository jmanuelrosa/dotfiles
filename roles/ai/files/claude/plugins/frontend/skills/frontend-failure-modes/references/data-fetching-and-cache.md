# Data fetching and client caches

When to read: the brief or diff touches data fetching, route loaders, mutations, client-side caches, revalidation, or the API contract the UI consumes.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Request waterfall.** Child components each fetching after their parent renders serializes round trips; a view needing three resources pays three sequential network hops.
  Check: fetches for one view run in parallel, hoisted to the route loader or prefetched; a new fetch nested under an existing one needs a stated reason.
- **Server state in a client store.** Fetched data jammed into a global UI store with a hand-rolled staleness scheme rots; caching, refetching, invalidation, and dedup are a solved lifecycle.
  Check: server data lives in the project's server-state layer (query cache, loader) with explicit staleness; the store holds client-only UI state.
- **Mutation without an invalidation map.** A mutation that does not invalidate or update every query showing the affected data leaves the UI lying until a reload.
  Check: enumerate the queries and views that display the mutated entity and update or invalidate each; list views and detail views both.
- **Optimistic update without rollback.** Applying the optimistic result but not restoring state on failure leaves phantom data on screen; a refetch racing the optimistic write corrupts it from the other side.
  Check: conflicting in-flight refetches are cancelled before the optimistic write; the failure path restores the exact prior state and surfaces the error; concurrent updates to the same entity reconcile or queue.
- **Unaborted in-flight requests.** Fetches that survive unmount or a parameter change resolve into dead components or overwrite newer data; rapid navigation multiplies them.
  Check: requests are aborted on unmount and supersession (AbortController or the data layer's cancellation).
- **Duplicate fetches of shared data.** Components independently fetching the same resource multiply load and desynchronize copies of the same entity.
  Check: shared resources dedupe through the cache key or loader; identical concurrent requests collapse into one.
- **Non-2xx treated as success.** Fetch wrappers that parse the body without checking status feed error payloads into success paths as if they were data.
  Check: every response path checks status before parsing; non-2xx throws into the designed error path, never into rendering.
- **Contract drift consumed silently.** Passively consuming the API means a renamed or retyped field fails at runtime in production instead of in CI; papering over a mismatch with `any` or a cast ships the same failure with extra steps.
  Check: response types are generated from the contract, or validated at the boundary with the project's schema tool; a backend shape change fails a typecheck or contract test, not a user.
- **Read-after-write staleness.** Create-then-navigate flows that show a stale list convince users the write failed, so they submit again.
  Check: the write updates or invalidates the cache before navigation completes, or the destination refetches on entry.

## Escalation triggers (`needs-decision`)

- The UI needs a change to the shape or semantics of what the API returns: that is a backend contract change to coordinate, not absorb.
- Introducing a new data-fetching library or cache layer (also an ask-first boundary in the agent).
- Any staleness window the brief leaves undefined for user-visible data.

## What good looks like

- Each route knows its data needs up front; fetches parallelize and dedupe by construction.
- The cache is the single client copy of server truth, invalidated by the mutations that change it.
- A silent backend field rename fails CI, never a user session.
