---
name: frontend-failure-modes
description: Failure-mode checklists for frontend implementation work, split by domain. Use when implementing or reviewing frontend changes that touch component state and rendering, data fetching and client caches, accessibility, performance, forms, error handling and resilience, browser-side security, or routing and navigation. Read only the reference files whose triggers match the change.
---

# Frontend failure modes

Checklists of the ways frontend changes go wrong for real users, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Component state, effects, derived data, context, SSR or hydration, list rendering | [references/rendering-and-state.md](references/rendering-and-state.md) |
| Data fetching, loaders, mutations, client caches, revalidation, the API contract the UI consumes | [references/data-fetching-and-cache.md](references/data-fetching-and-cache.md) |
| Any interactive element, form, dynamic content, or visual presentation change | [references/accessibility.md](references/accessibility.md) |
| Lists, images and media, bundles and dependencies, fonts, rendering hot paths, anything labeled "slow" | [references/performance.md](references/performance.md) |
| Forms, inputs, validation, submission flows, file uploads | [references/forms-and-input.md](references/forms-and-input.md) |
| Any new user flow; error handling, telemetry, offline or flaky-network behavior | [references/errors-and-resilience.md](references/errors-and-resilience.md) |
| Rendering user- or API-supplied content, auth state and tokens, redirects, embeds, third-party scripts | [references/security.md](references/security.md) |
| Routes, links, URL parameters, navigation flows, view state that should survive reload or sharing | [references/routing-and-navigation.md](references/routing-and-navigation.md) |

Most real changes fire two or three rows (a new form fires at least forms-and-input, accessibility, and errors-and-resilience).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks for users, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: framework- and library-specific guidance belongs to the stack skills the caller has installed, not here.
