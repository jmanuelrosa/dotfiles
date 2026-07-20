# Errors and observability

When to read: any new or changed component, especially one that fetches data, renders user content, or owns an interactive flow; and whenever the diff touches error boundaries or the error-tracking wiring.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The unmodeled error state.** A component with loading and success states but no error state renders a blank or a broken tree when data fails.
  Check: loading, empty, error, and success each have explicit UI; the error state says what happened and what the user can do next.
- **The uncaught render error.** A throw inside a component with no boundary takes down the surrounding tree.
  Check: an error boundary contains the failure at the right level with a usable fallback; the boundary reports to the error tracker (Sentry) with enough context to act on.
- **Torn-out tracking.** A refactor that drops the existing error-tracking or analytics wiring blinds production.
  Check: existing error-tracking, analytics, and feature-flag wiring in any component you touch is preserved; new failure paths reach the tracker.
- **Context-free reports.** An error with no component identity is unactionable.
  Check: reported context answers what, why, and when: the component and the action, and a correlation or request id where a support workflow needs one, never secrets or PII.
- **Internals leaked to users.** A raw error string or stack shown in the UI is both confusing and a disclosure.
  Check: user-facing messages are written for users; raw detail goes to the tracker.

## Escalation triggers (`needs-decision`)

- Changing the error-tracking SDK or where boundaries live in the app shell.
- Instrumentation the brief needs that the design system has no pattern for yet.

## What good looks like

- Every user-visible failure is also visible in the error tracker, correlated by request or trace id.
- Every interactive component degrades to a usable state when its data or children fail.
- Error messages help the user; the detail that helps the engineer is in the tracker, not on screen.
