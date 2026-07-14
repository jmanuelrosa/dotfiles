# Conversion APIs

When to read: the brief or diff touches server-to-server destinations (Meta Conversions API, Google Ads Enhanced Conversions, GA4 Measurement Protocol): event dedup, PII hashing, API versions, or auth.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **No shared dedup key across paths.** The same conversion is sent from the browser and the server with no shared identifier, so the destination counts it twice.
  Check: one dedup key is generated once and propagated to both paths (Meta: matching `event_id` and `event_name`; Google Ads: `order_id`/transaction id), not re-read from a GTM variable that re-resolves per call; confirm both paths emit the same value.
- **PII raw or wrongly normalized.** Sending email or phone unhashed, or hashing without the required normalization (lowercase, trim; phone to E.164), fails matching or leaks data.
  Check: personal identifiers are normalized then SHA-256 hashed per the destination's spec before transmission; nothing personal is sent in clear.
- **Wrong fields hashed.** Some fields must stay raw and some must be hashed; hashing `fbp`, `fbc`, the client IP, or the user agent breaks matching, while sending an email, phone, or name in clear leaks data and fails the match.
  Check: identifiers the destination hashes (`em`, `ph`, name, location, `external_id`) are hashed; transport and browser-context fields (`fbp`, `fbc`, client IP, user agent) are sent raw.
- **API version unpinned or stale.** Calling a destination without a pinned API version, or on a deprecated one, breaks or silently drops fields when the vendor changes it.
  Check: the API version is explicit and current, with a deprecation plan rather than a floating latest.
- **Missing fields degrade match.** Omitting fields the destination needs (event time, action source, user agent, IP, click IDs like `fbc`/`fbp` or gclid) tanks match quality or rejects the event.
  Check: required and match-improving fields are populated where consent allows; event time is within the destination's accepted window.
- **Auth token mishandled.** The access token or API key is inlined, over-scoped, or shared across environments, and rotation is unplanned.
  Check: tokens come from the server container's secret store, are environment-specific and least-scope, and rotation needs no code edit.
- **No test-event verification.** The integration ships without the destination's test tooling (Meta Test Events, Google Ads diagnostics), so match quality and dedup are unverified.
  Check: events are validated in the destination's test surface; dedup and match quality are confirmed before the data is trusted.
- **Retries duplicate.** Retrying a failed send without the dedup key, or against a destination lacking idempotency, creates duplicates on transient errors.
  Check: retries reuse the same dedup key; the send is idempotent from the destination's perspective.
- **Consent not enforced server-side.** Forwarding to an ad destination for a denied purpose because the check lived only on the client.
  Check: the consent state gates the server-to-server send per purpose (see consent-and-privacy).

## Escalation triggers (`needs-decision`)

- Adding a new advertising or measurement destination that receives personal data (a lawful-basis and data-sharing decision; also an ask-first boundary in the agent).
- Changing which personal identifiers are collected or forwarded for matching.

## What good looks like

- One shared dedup key across browser and server; the destination counts each conversion once.
- Personal identifiers normalized and hashed to spec; required match fields populated within consent.
- Pinned API version, secret-store tokens, and test-tool verification before the data is trusted.
