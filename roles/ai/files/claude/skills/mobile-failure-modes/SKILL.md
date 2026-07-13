---
name: mobile-failure-modes
description: >-
  Failure-mode checklists for mobile implementation work, split by domain.
  Use when implementing or reviewing changes that touch store releases and OTA updates,
  offline and network behavior, local data and migrations, permissions and privacy,
  deep links and navigation, performance and battery, lifecycle and background work,
  adaptive and accessible UI, or mobile security.
  Read only the reference files whose triggers match the change.
---

# Mobile failure modes

Checklists of the ways mobile changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Store releases, build variants and flavors, signing, OTA updates, version gates, crash reporting wiring | [references/release-and-updates.md](references/release-and-updates.md) |
| Network calls, sync, request retries, caching, anything that must work offline or on a bad connection | [references/offline-and-network.md](references/offline-and-network.md) |
| Local persistence: databases, key-value stores, changes to persisted state shape, logout, account switch | [references/local-data-and-migrations.md](references/local-data-and-migrations.md) |
| OS permissions, tracking and consent, data collection, store privacy declarations, SDKs that collect data | [references/permissions-and-privacy.md](references/permissions-and-privacy.md) |
| Deep links, universal or app links, navigation flows, auth-gated screens, back behavior, push-opened screens | [references/navigation-and-deep-links.md](references/navigation-and-deep-links.md) |
| Lists and scrolling, images, animation, the startup path, main-thread work, location or sensors, polling | [references/performance-and-battery.md](references/performance-and-battery.md) |
| App lifecycle, backgrounding, process death, push notification handling, background tasks and schedulers | [references/lifecycle-and-background.md](references/lifecycle-and-background.md) |
| New or changed screens, text and layout, localization, inputs and keyboards, custom controls | [references/ui-adaptivity-and-accessibility.md](references/ui-adaptivity-and-accessibility.md) |
| Secrets and tokens, sensitive data at rest, webviews, exported entry points, transport security | [references/mobile-security.md](references/mobile-security.md) |

Most real changes fire two or three rows (a typical feature-screen brief fires at least offline-and-network, lifecycle-and-background, and ui-adaptivity-and-accessibility).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: platform- and framework-specific guidance belongs to the stack skills the caller has installed, not here.
