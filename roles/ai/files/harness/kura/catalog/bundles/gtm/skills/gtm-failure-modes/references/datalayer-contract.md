# dataLayer contract

When to read: the brief or diff touches dataLayer keys, event or parameter names, push timing and ordering, value types, or schema evolution.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Push races the container.** A `dataLayer.push` that runs before the array is declared, or before the tag that reads it is triggered, is lost; SPA route-change and ecommerce events are the usual victims.
  Check: the `dataLayer` array is declared before the container snippet; data-dependent tags fire on the event's own trigger, not a page-load trigger that races the push.
- **Renamed or retyped keys.** Changing a key name, its nesting, or its type (string `"19.99"` vs number `19.99`, cents vs units) silently breaks every variable, tag, and sibling container that reads the old shape; a monetary `value` sent as a string, or missing its ISO-4217 `currency`, is dropped from GA4 revenue reports.
  Check: diff the serialized dataLayer shape before and after; changes are additive; monetary `value` is numeric with a sibling ISO-4217 `currency`.
- **Conversion id not stamped at push.** A purchase or lead push without a stable `transaction_id`/`order_id` carried on the event leaves GA4 and every destination unable to dedupe, so a thank-you-page refresh double-counts.
  Check: conversion pushes carry a dedup id generated once and stored on the event, not re-read from a GTM variable that re-resolves per call (see conversion-apis).
- **Free-form values.** Values that vary in case, currency, or unit across pushes (`USD` vs `usd`, `Purchase` vs `purchase`) fork every downstream mapping and lookup.
  Check: event and parameter names come from one documented taxonomy with fixed casing and units; normalization happens once at the edge, not guessed per tag.
- **Stale state bleed.** In an SPA the `dataLayer` is not reset between virtual pageviews, so a later event inherits an earlier `ecommerce` or user object.
  Check: ecommerce and per-event objects are cleared (`dataLayer.push({ ecommerce: null })`) before the next push, or each event carries a self-contained payload.
- **Personal data on the page.** Email, phone, name, or precise location pushed in clear text is readable by every script and extension on the page.
  Check: personal data is hashed or omitted at the source; a destination that needs it is fed through a gated server-side path, never broadcast on the page (see consent-and-privacy, conversion-apis).
- **Silent default swallows a break.** A variable's "default value" masks a missing push, so a broken event still fires a tag with blank or placeholder data instead of not firing.
  Check: required parameters have no silent default; absence blocks the tag via trigger condition or exception rather than sending an empty conversion.
- **Undocumented app-side contract.** The push lives in application source the frontend seat owns, but its shape is the tagging contract; a change on either side without the other breaks collection with no error.
  Check: the schema is written down and versioned; app-side emit changes are coordinated with the container, not discovered in reporting.

## Escalation triggers (`needs-decision`)

- Any breaking change to a key name, type, or event name that tags, other containers, or downstream reports already consume (also an ask-first boundary in the agent).
- Introducing a new event taxonomy or renaming events across the site.

## What good looks like

- One documented dataLayer schema with stable names, types, and units, evolved additively: a live event is versioned (`add_to_cart_v2`) rather than mutated.
- Event-driven tags fire on their own event; state is reset between SPA views.
- No personal data on the page-level dataLayer; normalization happens once, at the edge.
