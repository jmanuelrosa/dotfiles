# Errors and resilience

When to read: always for new user flows; and whenever the brief or diff touches error handling, unsaved work, quit or restart paths, retries, or anything that depends on the network.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **No boundary around a new surface.** A failure while drawing one panel takes down the window, and in an app the user has had open since Monday that costs a session rather than a page load.
  Check: new surfaces fail in isolation with a recovery affordance; one panel failing degrades that panel and leaves the rest of the window usable.
- **Unsaved work lives only in memory.** A crash, a force quit, a power loss, or the restart an update performs discards whatever was not written, and a desktop user expects the document to be there when they come back.
  Check: in-progress work is checkpointed to disk and recovered on the next launch; the diff introduces no path where the only copy of user input is in memory.
- **Termination without a save opportunity.** Quit, sign-out, and update-install paths that tear down immediately take unsaved work with them, silently.
  Check: every path that terminates or restarts the app first gives unsaved work a chance to be saved or explicitly discarded.
- **Failure states unmodeled.** Only the happy path has UI, so failures render as blank panes, spinners that never resolve, or raw exception text.
  Check: loading, empty, error and success each have explicit UI, and the error state says what happened and what the user can do next.
- **Retry without design.** A retry that re-fires a non-idempotent operation duplicates the user's data; an automatic retry with no bound hammers a service that is already down.
  Check: the retry affordance matches the operation's semantics, automatic retries are bounded with backoff and jitter, and non-idempotent retries pass the same guard as a double submit.
- **The network assumed present.** Desktop apps run on laptops that sleep, switch networks, and go offline, so code that only distinguishes success from failure strands the user in a spinner.
  Check: network-dependent features have an offline state, an explicit timeout, and a reconnect path that reconciles rather than trusting stale local state.
- **Swallowed async failures.** Fire-and-forget work started from a handler fails invisibly: the user's action did nothing, and nobody finds out until they complain.
  Check: every async path surfaces its failure in the UI, reports it, or both.
- **A crash of the owning process treated like a crash of a window.** A rendered view dying loses one window and can be reloaded; the process that owns the application dying takes every window with it, and the diff usually only handles one of the two.
  Check: the two are handled separately, the recoverable case actually recovers the affected window, and an unhandled rejection in the owning process is caught there, since it has no boundary above it to catch it.
- **Update failure with no way to stay put.** A download, a signature check, or an installer can fail, and an app that treats the update as mandatory either blocks use or retries in a loop.
  Check: any failure in the update path leaves the app running usably on its current version, with a bounded retry and a visible state rather than a loop.
- **Recovery that discards the reason.** Silently restarting a crashed helper or reloading a failed window turns a reproducible defect into folklore, and an unbounded restart loop burns the machine.
  Check: automatic recovery is bounded, and every recovery records what failed before retrying.

## Escalation triggers (`needs-decision`)

- A failure mode whose user experience the brief does not define.
- Changing what happens to unsaved work on quit, sign-out, or update install (also an ask-first boundary in the agent).

## What good looks like

- Any single panel, helper, or request can fail while the window stays useful and honest about it.
- The user's work survives a crash, a forced quit, and the restart an update performs.
- Offline is a state the app renders, not an error it throws.
