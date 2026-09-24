# International

When to read: the brief or diff touches hreflang, locale routing, or translated or geo-targeted pages.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Missing return links.** hreflang is only honored when every referenced page links back to every other variant, including itself; one missing return tag invalidates the cluster for that pair.
  Check: the hreflang emitter generates the full bidirectional set including the self-reference, from one data source, so a partial cluster cannot be hand-assembled.
- **hreflang pointing at non-final URLs.** Targets that redirect, 404, are noindexed, or canonicalize elsewhere break the cluster silently.
  Check: every hreflang URL is the absolute, canonical, 200, indexable version of that variant.
- **Invalid locale codes.** hreflang takes ISO 639-1 language, optional ISO 15924 script, and optional ISO 3166-1 alpha-2 region; region alone is invalid, and near-miss codes (`en-UK`, `gb`, `EU`) are ignored without error.
  Check: every code in the diff validates against the ISO lists; `en-GB` not `en-UK`, `zh-Hans` for script variants; URLs are fully qualified absolute URLs including protocol.
- **No x-default.** Without `x-default`, users and engines outside the mapped locales get whichever variant wins by accident instead of the chosen fallback or selector page.
  Check: the cluster includes an `x-default` pointing at the deliberate fallback.
- **Canonical fighting hreflang.** Cross-locale canonicals (all variants canonicalizing to one language) tell the engine the alternates are duplicates to discard, defeating the entire cluster.
  Check: each locale variant self-canonicalizes; canonicals never cross locales.
- **Forced geo-redirects.** Redirecting every visitor by IP to their regional site also redirects the crawler, which mostly crawls from one country and so never sees the other variants; it can read as cloaking.
  Check: locale suggestion is a banner or a remembered choice, never an unconditional IP redirect; all variants are directly reachable.
- **Untranslated duplicates in the cluster.** Locale URLs whose body content is identical boilerplate with a translated shell are duplicate pages wearing hreflang; they dilute rather than target.
  Check: variants differ in the content itself, or the untranslated locales are dropped from the cluster until they do.
- **Partial cluster maintenance.** Adding a locale to some templates but not others, removing a locale without pruning its references sitewide, or moving hreflang from head to sitemap while stale head tags remain decays the clusters silently: a broken pair is ignored, never warned about.
  Check: locale membership is defined once and consumed by every emitter, so adding or removing a locale is one change; the delivery methods (HTML head, HTTP header, sitemap) never disagree because only one is in use.

## Escalation triggers (`needs-decision`)

- Rolling out hreflang or locale routing sitewide, or removing a locale (also an ask-first boundary in the agent).
- Choosing URL strategy for internationalization (ccTLD vs subdirectory vs subdomain): a business decision with infrastructure consequences.

## What good looks like

- One locale registry drives routing, sitemaps, hreflang, and canonicals, so the signals cannot disagree.
- Full bidirectional clusters with self-reference and x-default, generated, never hand-edited.
- Every variant is directly reachable by any visitor and any crawler from anywhere.
- Locales exist because the content serves them, not because the router can mint them.
