---
name: seo-failure-modes
description: >-
  Failure-mode checklists for SEO and search-visibility implementation work, split by domain.
  Use when implementing or reviewing changes that touch crawlability and indexation, JavaScript rendering for bots, structured data, AI search visibility, content quality and E-E-A-T, page experience as a ranking input, migrations and URL changes, international targeting, or internal linking.
  Read only the reference files whose triggers match the change.
---

# SEO failure modes

Checklists of the ways SEO changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| robots.txt, meta robots, canonicals, redirects, sitemaps, index directives, URL parameters | [references/crawlability-and-indexation.md](references/crawlability-and-indexation.md) |
| Rendering strategy, client-rendered content, lazy loading, SPA routes, anything a bot must execute to see | [references/rendering-and-javascript.md](references/rendering-and-javascript.md) |
| JSON-LD, microdata, schema.org types, rich result eligibility | [references/structured-data.md](references/structured-data.md) |
| AI crawlers, AI Overviews, LLM citation, answer extraction, GEO/AEO | [references/ai-search-visibility.md](references/ai-search-visibility.md) |
| Pages generated at scale, thin or duplicate content, titles and descriptions, author and trust surfaces | [references/content-quality-and-eeat.md](references/content-quality-and-eeat.md) |
| Core Web Vitals as a ranking input, interstitials, HTTPS, page experience signals | [references/page-experience.md](references/page-experience.md) |
| URL renames, domain moves, replatforming, redirect maps, route restructures | [references/migrations-and-url-changes.md](references/migrations-and-url-changes.md) |
| hreflang, locale routing, translated or geo-targeted pages | [references/international.md](references/international.md) |
| Navigation, internal links, anchor text, orphan pages, faceted navigation, pagination | [references/authority-and-internal-linking.md](references/authority-and-internal-linking.md) |

Most real changes fire two or three rows (a typical page-template brief fires at least crawlability-and-indexation, rendering-and-javascript, and structured-data).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: framework- and CMS-specific guidance belongs to the stack skills the caller has installed, not here.
