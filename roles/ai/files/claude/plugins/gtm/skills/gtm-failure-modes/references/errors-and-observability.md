# Errors and observability

When to read: any new or changed tag, trigger, variable, template, or server client; and whenever the brief or diff touches error handling, failed sends, or tag health monitoring.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **The silently dropped event.** A server tag whose outbound send is not awaited, or whose failure is swallowed, drops events with no trace.
  Check: every send is awaited and its failure is handled; server-side errors reach the error tracker (Sentry) with enough context to act on.
- **Context-free failures.** A failed send with no identity cannot be diagnosed.
  Check: error context answers what, why, when, and to whom: the event name, the destination, the response status, and a correlation id that ties the browser and server paths.
- **The tag that drops to zero.** A tag that silently stops firing is worse than one that errors, because nobody notices.
  Check: a health signal exists so a regression in fire volume is caught in hours; before-and-after volumes were compared.
- **PII in error context.** Emails, user ids, or raw payloads in tracker context or logs are a breach, and often a consent violation.
  Check: redaction covers every new log and error field; personal data is hashed where the destination requires it and never logged raw.
- **Client errors invisible.** A custom template that throws in the browser fails the tag with no report.
  Check: template failures surface rather than failing silently; `runTemplateTests` covers the malformed-input path.

## Escalation triggers (`needs-decision`)

- Adding or changing the error tracker or a tag-monitoring integration.
- New volume or failure alerts someone else is paged on.
- Instrumentation the brief needs that the container has no pattern for yet.

## What good looks like

- Every question triage asks ("which event, which destination, which status") is answerable from the report.
- A browser event and its server counterpart correlate by a shared id.
- A drop in fire volume pages someone in hours, not at the monthly report.
- No personal data reaches a log, a tracker, or an unhashed destination field.
