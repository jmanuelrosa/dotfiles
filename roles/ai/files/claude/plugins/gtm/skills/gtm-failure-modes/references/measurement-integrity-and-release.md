# Measurement integrity and release

When to read: the brief or diff touches publishing a container version, cross-path double-counting, attribution and identity continuity, QA before publish, or tag monitoring.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Publishing straight to live.** A container version is published with no Preview or QA pass, so a broken tag or trigger reaches every visitor at once.
  Check: changes are validated in Preview and Tag Assistant (and GA4 DebugView for GA4 events) before any publish; publishing is a human action, not part of the change.
- **Client and server double-count.** The same conversion or pageview is counted on both paths (a native GA4-to-Ads integration firing alongside a GTM conversion tag, or a browser pixel alongside CAPI) because dedup was not verified end to end.
  Check: for every event that has both paths, exactly one path owns it or a shared dedup key is confirmed present and effective in the destination (see conversion-apis, ga4-integration).
- **Attribution discontinuity.** A change resets or fragments the identifier chain (GA4 `client_id`, ad click IDs, first-party cookie), breaking attribution with no error.
  Check: identity continuity is confirmed across the change; click IDs and `client_id` survive the client-to-server hop.
- **No version discipline.** Container versions are unnamed and undescribed, so there is no clean point to roll back to when a release regresses measurement.
  Check: each published version has a description of what changed; the previous good version is a known rollback target.
- **No tag-health signal.** A tag that stops firing (a renamed dataLayer key, a broken template, a consent change) fails silently, and the gap surfaces in a report weeks later.
  Check: critical tags have a health signal (volume monitoring, a canary, or a scheduled check); a silent drop to zero is detectable.
- **QA only the happy path.** Testing only the consented, logged-in, single-domain case misses denied-consent, cross-domain, and empty-state paths where tags misfire.
  Check: QA covers consent-denied, cross-domain, and edge states, not just the golden path.
- **Data loss invisible until reporting.** A collection change is called done at publish, with no before-and-after volume check and no reconciliation across systems, so a regression or a double-count surfaces weeks later in a report.
  Check: post-change event volumes are compared against the baseline, and counts are reconciled across systems (for example CRM leads against GA4 events against Ads conversions); an unexpected drop, spike, or mismatch is investigated before the change is trusted.
- **Test artifacts in production.** A test measurement or pixel ID, `debug_mode: true`, or a debug validation endpoint ships in the published container, polluting production data or exposing debug traffic.
  Check: no test IDs, debug flags, or validation endpoints remain in the published version.

## Escalation triggers (`needs-decision`)

- Anything that would change what reaches production measurement: the agent configures and Previews but never publishes; leave the container version for a human.
- A change that would reset or reshape the identity or attribution chain across historical data.

## What good looks like

- Nothing reaches live without a Preview and DebugView pass; publishing is a deliberate, described, reversible human step.
- Dedup and identity continuity are verified in the destination, not assumed.
- Critical tags are monitored; before-and-after volumes confirm the change did what it claimed.
