# SEO staff-engineer seat

## Context

The staff-engineer fleet has no owner for search visibility.
Meta tags, canonicals, structured data, sitemaps, robots, redirects and hreflang are unclaimed by any seat, and frontend explicitly escalates URL-structure changes naming SEO as the reason with nobody to receive them.
The user wants an SEO specialist that stays current with search engine and AI-search trends (AI Overviews, LLM crawlers, GEO/AEO), which is exactly what the agent-writer research protocol provides at authoring time and WebSearch provides at run time.

Decisions locked with the user: **implementer seat** (edits SEO surfaces directly, like backend/frontend), **9 reference domains** (the 8 proposed plus authority & internal linking).

## What ships

A seat plugin at `roles/ai/files/claude/plugins/seo/`:

- `agents/seo-staff-engineer.md` - implementer seat, ~205-215 lines, canonical 13-section skeleton (no `tools:` key, `model: opus`, `effort: xhigh`, `thinking: xhigh`, `memory: project`)
- `skills/seo-failure-modes/SKILL.md` + `references/` (9 files, ~35-40 lines each)
- `.claude-plugin/plugin.json` matching the gtm shape exactly (`$schema`, name `seo`, description, version `0.1.0`, author, `groups`). Never use the key `dependencies` (reserved, silently ships nothing, `test_catalog.py:87`). Groups: exactly one discipline; propose `["marketing", "marketer", "seo", "web"]` since `marketing` and `seo` are already in the controlled vocabulary

One edit outside the plugin: add `seo` to the specialist list in `roles/ai/files/claude/agents/architect.md:30`, or the architect never routes a slice to it (known shipped bug class, `docs/internals/seat-plugins.md:8`).

## The 9 reference domains

1. `crawlability-and-indexation.md` - robots, sitemaps, canonicals, redirects, index directives, crawl budget
2. `rendering-and-javascript.md` - SSR/CSR/hydration as crawlability, what bots execute, lazy-loaded content
3. `structured-data.md` - schema.org, rich-result eligibility, validation, deprecations
4. `ai-search-visibility.md` - AI Overviews, LLM crawlers (GPTBot, ClaudeBot, etc.), GEO/AEO, citation optimization
5. `content-quality-and-eeat.md` - helpful content, thin/duplicate content, programmatic SEO risks
6. `page-experience.md` - CWV **as ranking inputs only**; the metrics work itself belongs to frontend
7. `migrations-and-url-changes.md` - redirect maps, traffic-loss failure modes, receiving frontend's URL-change escalations
8. `international.md` - hreflang, geo-targeting, multilingual duplication
9. `authority-and-internal-linking.md` - anchor strategy, orphan pages, link equity, nav structure

## Demarcation (the audit's sharpest risks)

| Surface | Owner | SEO seat's stance |
|---|---|---|
| Core Web Vitals implementation, budgets, RUM | frontend (`performance.md` owns LCP/INP/CLS) | Reads CWV as ranking signals; routes fixes to frontend |
| URL structure changes | frontend escalates (`routing-and-navigation.md:29`), SEO decides | SEO seat is the receiver: owns redirect strategy |
| Heading semantics, alt text, contrast | frontend accessibility + design | Route, never re-check |
| Tagging, pixels, consent | gtm | Excluded |
| GA4/Search Console reporting and modeling | analytics | Excluded |
| Landing-page visual design | design | Excluded |
| Meta/OG/canonical/JSON-LD/robots/sitemaps/hreflang | nobody today | The seat's core claim |

Step 2 routing must name the four upstream `seo`-group skills already in `skill-registry.json` (`seo-audit`, `ai-seo`, `copywriting`, `cro` from coreyhaines31/marketingskills) as installable skills to route to, not duplicate.
Sibling pair for the fresh-eyes audit: **frontend** (sharpest demarcation risk).

## Trend-following requirement

Two mechanisms, both standard for the family:

- Authoring time: the two background researchers (`seo-ladder-researcher`, `seo-pack-researcher`) bring current-state facts into the references; volatile claims get verified against 2025-2026 sources
- Run time: operating loop step instructing the seat to verify volatile claims (ranking signals, AI-crawler behavior, rich-result eligibility) via WebSearch before asserting them, since this domain moves faster than training data

## Execution steps (agent-writer pipeline, Steps 2-7)

1. **Ground**: read the canon exemplars in full - `plugins/backend/agents/backend-staff-engineer.md` + `backend-failure-modes/`, `plugins/platform/agents/platform-staff-engineer.md` + `platform-failure-modes/`. Never re-derive from memory
2. **Research**: read `references/research-protocol.md`; launch `seo-ladder-researcher` and `seo-pack-researcher` in background before authoring. If one dies on a connection error, message it to resend; do not relaunch
3. **Author the skill**: `seo-failure-modes` per `references/failure-modes-skill.md` (router SKILL.md with trigger table + 9 references, checks against a diff, stack-agnostic)
4. **Author the agent**: per `references/seat-agent-anatomy.md`, applying `references/coherence-rules.md` while writing. Boundaries tier notes: never fabricate structured data for content that does not exist on the page (spam policy), never cloak; ask-first on robots/sitemap changes that can deindex, sitewide redirect maps, hreflang rollouts
5. **Package**: plugin.json per `references/packaging.md`; add `seo` to architect.md's specialist list
6. **Fresh-eyes audit**: synchronous no-context subagent over the new pair + plugin.json + the frontend pair; apply must-fix and should-fix
7. **Verify**: every check in `references/verification-sweep.md`, plus `make test` (catalog tests assert manifest shape and namespace uniqueness; the advisor-set assertion at `test_catalog.py:415` is untouched since this is an implementer)

Fold researcher deltas in when they report.
Commit nothing; the user drives `/commit`. No research doc is committed.

## Verification

- `make test` passes (catalog and registry suites)
- All `verification-sweep.md` checks pass
- No em or en dashes anywhere under `plugins/seo/` (the em-dash-gate hook enforces this on write); semantic line breaks throughout
- Name `seo` unique across `skill-registry.json`, `agent-registry.json`, `plugins/`
- Trigger table in the agent's Step 3 matches the actual reference filenames one-to-one
- architect.md lists `seo`

## Final report contract

What shipped with paths and line counts, research adopted vs rejected, audit findings and fixes, verification results, git status.
