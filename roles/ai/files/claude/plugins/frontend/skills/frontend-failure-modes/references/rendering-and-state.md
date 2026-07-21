# Rendering and state

When to read: the brief or diff touches component state, effects, derived data, context, SSR or hydration, or list rendering.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Re-render storm.** State lifted too high, context values recreated every render, or unstable props passed to memoized children make one keystroke re-render an entire subtree.
  Check: state is colocated at its lowest owner; context values and callbacks are referentially stable; confirm the hot path with a profiler pass or render count, not intuition.
- **Effect race on stale responses.** Two in-flight async effects resolving out of order paint stale data over fresh data; fast typing in a search box is the classic reproduction.
  Check: every async effect cancels or ignores superseded results (AbortController or a staleness flag in cleanup); the latest user action always wins.
- **Derived state stored, not computed.** Copying props or fetched data into local state creates two sources of truth that drift after the first update.
  Check: derive during render (memoized if measured to matter); a local copy exists only for genuine initial-value semantics and is named to say so.
- **Hydration mismatch.** Server markup differing from the first client render (dates, locale, random IDs, browser-only branches) causes flicker, lost event handlers, or a full client re-render.
  Check: nothing nondeterministic in render; browser-only reads live in effects or explicitly client-only components; nothing non-serializable crosses a server-client component boundary; hydration warnings are failures, not noise.
- **Stale closure.** A callback, timer, or subscription capturing an old state value acts on data that no longer exists.
  Check: hook dependency lists are complete; long-lived callbacks read current state through refs or updater functions.
- **Index keys on mutable lists.** Array index as key on lists that reorder, insert, or delete pins component state to positions instead of items; the wrong row ends up checked or edited.
  Check: keys are stable item identities; index keys only on static lists that never reorder.
- **Uncleaned subscriptions.** Listeners, observers, timers, and sockets set up on mount without teardown leak memory and fire against unmounted components.
  Check: every subscribing effect returns a cleanup; the flow survives a strict-mode double mount cleanly.
- **Global store as dumping ground.** Reaching for a global store for data one subtree needs fragments state ownership and makes changes untraceable.
  Check: state lives at the lowest common owner; global stores hold genuinely app-wide client state only (server data belongs to the data-fetching layer, see that reference).

## Escalation triggers (`needs-decision`)

- Changing a route's rendering strategy (CSR, SSR, SSG, streaming) or moving components across the server-client boundary.
- Introducing a new state-management library or pattern the project does not already use (also an ask-first boundary in the agent).
- Changing the shape of state that other components, persisted storage, or URLs already consume.

## What good looks like

- Each piece of state has one owner and one write path; everything else derives from it.
- Re-render cost is proportional to what actually changed.
- Async effects are cancel-safe: unmounting mid-flight leaves no trace.
- Server and client agree on the first paint.
