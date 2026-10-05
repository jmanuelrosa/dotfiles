# Migrations and URL changes

When to read: the brief or diff touches URL renames, domain moves, replatforming, redirect maps, or route restructures.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Rename without a redirect map.** Every changed URL abandons its rankings, backlinks, bookmarks, and ad destinations the moment the old path 404s; the map is part of the rename, not a follow-up.
  Check: the diff contains a one-to-one map from every old URL to its new equivalent, shipped in the same change as the rename.
- **Mass redirect to the homepage.** Redirecting removed or moved pages to the homepage instead of their equivalents is treated as a soft 404 and transfers nothing.
  Check: each redirect targets the closest equivalent page; where none exists, the URL gets an honest 410 and the loss is stated.
- **Redirect chains compounding across migrations.** This migration's redirects stacked on the last one's produce multi-hop chains that leak signal and slow crawling; Googlebot abandons a chain after 10 hops, and Google's own guidance is to stay well under that.
  Check: new redirects point at final destinations, and existing redirects whose targets moved are updated to the new final URL in the same change.
- **Temporary status for a permanent move.** 302/307 on a migration tells the engine the old URLs are coming back, delaying canonical transfer.
  Check: migration redirects are 301/308.
- **Trailing artifacts voting for the old URLs.** Sitemaps, canonicals, hreflang, internal links, and structured data URLs that still reference pre-migration paths contradict the redirects for as long as they persist; so does a development-phase `noindex` or robots block that survives cutover, which Google's site-move guidance names as a common failure.
  Check: grep the codebase and generated artifacts for old URL patterns and staging directives; internal references are updated to final URLs rather than left to bounce through redirects.
- **New sitemap only, old URLs forgotten.** Dropping the old sitemap at cutover removes the fastest path for the engine to recrawl the old URLs and discover their redirects.
  Check: the old sitemap stays submitted until the move is processed, alongside the new one; then it is retired.
- **Fragmenting one move into many.** Changing domain, protocol, URL structure, and platform in separate overlapping waves makes traffic loss undiagnosable; changing them all at once maximizes the blast radius.
  Check: the migration states what changes in this step and what is deliberately held stable, and the report says how the next step will be attributed.
- **Redirects with an expiry date.** Redirect rules parked in a config that gets pruned, or on infrastructure being decommissioned, quietly expire while external links still point at the old URLs; Google's site-move guidance is to keep them for at least a year, and inbound links live longer.
  Check: the redirect map lives in version-controlled config on infrastructure that survives the migration, with no scheduled removal.
- **No rollback or measurement plan.** A migration with no pre-change URL inventory and traffic baseline cannot prove loss, locate it, or roll it back.
  Check: the report names the baseline artifact (URL inventory with traffic and inbound-link significance) and the rollback path before the switch.

## Escalation triggers (`needs-decision`)

- Any sitewide URL structure change, domain move, or replatforming (also an ask-first boundary in the agent).
- A migration the brief wants shipped without a redirect map, baseline, or rollback path.
- Receiving a URL-change escalation from the frontend seat: the decision and redirect strategy land here.

## What good looks like

- URLs are treated as irreversible contracts: renames are rare, deliberate, and shipped with their map.
- One hop from any old URL to its final destination, kept alive for years, in version control.
- Every internal signal points at the new URLs from day one; only external links need the redirects.
- A baseline inventory exists, so post-migration traffic movement is attributable page by page.
