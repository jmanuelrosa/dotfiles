# Errors and resilience

When to read: always for new user flows; and whenever the brief or diff touches error handling, telemetry, offline or flaky-network behavior, or anything that renders remote data.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **No error boundary on a new surface.** A render error in one widget white-screens the entire route.
  Check: new surfaces render inside an error boundary with a recovery UI; one widget failing degrades that widget, not the page.
- **Silently dropped telemetry.** Removing or renaming analytics events, error-tracker context, or feature-flag checks in a touched flow blinds product and on-call without failing any test.
  Check: every analytics event, flag check, and error-tracking call in the flow you touch survives the change; new failure paths reach the error tracker with enough context to act on.
- **Failure states unmodeled.** Only the happy path has UI: failures render blank sections, infinite spinners, or raw exception text.
  Check: loading, empty, error, and success each have explicit UI; error UI says what happened and what the user can do next.
- **Retry without design.** A retry button that re-fires a non-idempotent mutation duplicates data; automatic retries from thousands of clients hammer an API that is already down.
  Check: the retry affordance matches the operation's semantics; automatic retries are bounded with backoff; non-idempotent retries go through the same guard as double submit.
- **Slow network treated as no network.** Code that only distinguishes success from failure leaves slow-connection users with spinners and timeouts nobody chose.
  Check: user-facing operations have explicit timeout behavior; long operations show progress and stay cancelable.
- **Connection loss corrupts state.** A mutation in flight when the connection drops leaves the client convinced of a write the server never saw, or vice versa.
  Check: failed mutations roll back optimistic state and tell the user; reconnection reconciles by refetching rather than trusting the stale cache.
- **Swallowed promise rejections.** Fire-and-forget async in handlers fails invisibly: the user's click did nothing, and nobody finds out.
  Check: every async path surfaces failure in the UI, reports it to the tracker, or both; an unhandled-rejection warning is a bug, not ambience.
- **Error text leaks internals.** Raw API errors, stack traces, or debug identifiers shown to users confuse them and expose the system.
  Check: user-facing messages are written for users; raw detail goes to the tracker; show a correlation or request ID when support workflows need one.

## Escalation triggers (`needs-decision`)

- A failure mode whose user experience the brief does not define.
- Adding a new alert or telemetry signal others will consume or be paged on.
- Offline or degraded-mode behavior beyond what the brief scopes.

## What good looks like

- Any single widget or request can fail and the page stays useful and honest about it.
- Every user-visible failure is also visible in the error tracker, correlated by request or trace ID.
- The flow behaves predictably on a slow connection and across a connection drop.
