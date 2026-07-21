# Errors and observability

When to read: any new screen, flow, network call, or background task; and whenever the brief or diff touches crash reporting, error handling, logging, or the analytics and crash SDKs.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The silent crash path.** A new flow that throws in release mode without reaching the crash tracker is invisible until the store rating drops.
  Check: every new failure path reports to the existing crash tracker (Sentry, Crashlytics) with enough context to act on, wired through the app's existing SDK setup, not a parallel one.
- **Context-free reports.** A crash with no breadcrumbs, screen, or user action is unactionable.
  Check: reports answer what happened, why, when, and to whom: app version and build, OS and device, the screen or action, and a correlation or trace id that ties to the backend request where one exists.
- **Swallowed errors.** A `catch` that shows a toast and moves on where the caller needed the failure hides real defects.
  Check: every catch either handles meaningfully or reports; a user-visible failure is also a tracked one, never a spinner that never resolves.
- **Broken symbolication.** An obfuscated stack trace is a crash you cannot read.
  Check: dSYMs or mapping files upload for every binary the change produces; a test crash resolves to real symbols.
- **Secrets and PII in reports.** Tokens, emails, and personal data in breadcrumbs, tags, or context are a breach with long retention on a third-party backend.
  Check: scrubbing covers every new breadcrumb and context field; dump whole objects nowhere.
- **Events lost offline.** A device with no connection drops the very errors that explain the bug.
  Check: the tracker's offline queue is intact; errors captured offline send on reconnect, matching how the app already buffers events.

## Escalation triggers (`needs-decision`)

- Adding a new crash or analytics SDK, or changing sampling and release-tracking config.
- Alert thresholds or release-health gates someone else is paged on.
- Instrumentation the brief needs that the app has no pattern for yet.

## What good looks like

- Every question the next crash triage asks ("which build, which OS, which screen, which user action") is answerable from the report.
- One user-visible failure is one tracked event, correlated to the backend trace by a shared id.
- Release health is visible per version, so a bad rollout is caught in hours.
- Report volume stays boring: breadcrumbs bounded, PII scrubbed, noise filtered.
