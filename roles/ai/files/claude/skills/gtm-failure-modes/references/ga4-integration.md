# GA4 integration

When to read: the brief or diff touches GA4 tags, events, or parameters, client and session identity, cross-domain, Measurement Protocol, or GA4 consent wiring.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Double-counted hits.** GA4 receives the same event from both gtag/GTM and the Measurement Protocol, or from two GA4 config tags, inflating pageviews, users, and sessions; GA4 has no cross-source dedup.
  Check: each GA4 event has one sending path; the Measurement Protocol is used only for events the client cannot send, never to mirror them.
- **Broken client or session identity.** Server-side or Measurement Protocol events send a wrong or missing `client_id`, or a `session_id` that does not match the client's, creating ghost users and fragmented sessions.
  Check: `client_id` is read from the GA4 cookie or event and preserved through the server; `session_id` matches the client session where continuity matters.
- **Personal data in GA4.** Email, phone, or a personal `user_id` lands in event parameters or user properties, violating GA4 policy and risking data deletion.
  Check: no personal data in parameters, `user_id`, or user properties; `user_id` is a non-identifying key.
- **Consent not wired to GA4.** A denied `analytics_storage` is not reflected, so GA4 stores cookies without basis, or advanced consent behavior is assumed but not configured.
  Check: GA4 honors `analytics_storage`; the intended basic or advanced consent behavior is actually configured and verified in both states.
- **Cross-domain and referral gaps.** Navigation across owned domains starts new sessions and self-referrals because cross-domain linking or referral exclusions are unset.
  Check: cross-domain linking covers all owned hosts; the collection domain is excluded as a referrer.
- **Naming drift.** Custom events and parameters use names that collide with reserved GA4 names or diverge from the taxonomy, so they are dropped or unqueryable.
  Check: names avoid reserved prefixes and names and match the documented taxonomy; parameters are registered as custom dimensions where they must be reportable.
- **Measurement Protocol misuse.** Calls omit `api_secret` or `measurement_id`, drop `session_id` or `engagement_time_msec` (so the event never joins a session or shows in Realtime), send `timestamp_micros` in milliseconds, or post outside the accepted recency window.
  Check: MP requests carry stream-matched `api_secret` and `measurement_id`, include `session_id` and `engagement_time_msec`, use microsecond timestamps within the accepted window, and expectations about which reporting dimensions populate are realistic.

## Escalation triggers (`needs-decision`)

- Changing the GA4 identity model (`client_id` or `user_id` source) or the session definition in a way that reshapes historical continuity (also an ask-first boundary in the agent).
- Sending a new event class via Measurement Protocol alongside existing client collection.

## What good looks like

- One sending path per GA4 event; the Measurement Protocol fills gaps rather than mirroring the client.
- Stable client and session identity through the server; no personal data in GA4; consent honored and verified in both states.
- Cross-domain and referral exclusions cover every owned host.
