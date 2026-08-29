# Authority and internal linking

When to read: the brief or diff touches navigation, internal links, anchor text, orphan pages, faceted navigation, or pagination.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Orphans fed only by the sitemap.** Pages reachable via sitemap but linked from nowhere get crawled reluctantly and ranked as the dead ends they are; the sitemap is a feed, not a substitute for links.
  Check: every page the change adds is linked from at least one indexable page a user could plausibly navigate from; page sets get hub or category pages, not just sitemap entries.
- **Nav rework severing link paths.** Removing a nav section, footer block, or category page silently cuts the only crawl path to everything beneath it, without touching those pages' files.
  Check: for each removed or reworked link block, list what was reachable through it and confirm each destination retains another internal path.
- **Anchor text that describes nothing.** "Click here" and "learn more" spend the link without passing the topical signal; the anchor is how engines learn what the target is about.
  Check: internal anchors in the diff describe the destination; templates interpolate the target's title or topic, not a generic verb.
- **Links invisible to crawlers.** Anchors rendered only after interaction, buttons with onclick navigation, or `<a>` tags without `href` do not exist as links to a crawler.
  Check: every navigational element that should pass signal is an `<a href>` present in the loaded DOM (see rendering-and-javascript).
- **nofollow on internal links.** Internal nofollow discards the equity rather than sculpting it, and as crawl control it only works with 100% coverage of every anchor to the URL (Google's faceted-navigation guidance); partial application achieves nothing except the signal loss.
  Check: no internal link in the diff carries `rel="nofollow"`; crawl control belongs to robots directives, not link attributes.
- **Faceted navigation minting crawl space.** Every crawlable filter combination is a URL; unbounded facets generate millions of near-duplicates that exhaust crawl budget on large sites.
  Check: each facet dimension is deliberately indexable (a real landing page, and an escalation trigger below), canonicalized to its base, or kept out of crawl paths; the decision per dimension is stated.
- **Pagination hiding the long tail.** Item pages reachable only from page 47 of a paginated list are effectively unreachable; rel-prev/next no longer changes this.
  Check: important items are reachable within a few hops via category, hub, or related-item links, not only through deep pagination; paginated pages themselves stay crawlable, self-canonicalized per page, not canonicalized to page one.
- **Deep-burying the pages that matter.** Link depth is a statement of importance; a strategic page five clicks from the home page is marked unimportant regardless of its content.
  Check: pages the brief says matter are within three hops of a major hub, or the report says why not.
- **Sitewide link blocks as ranking hacks.** Stuffing keyword-anchored links to target pages into every footer reads as manipulation and dilutes the pages it means to boost.
  Check: sitewide link blocks contain navigation users actually use; boosted pages earn contextual links from relevant content instead.

## Escalation triggers (`needs-decision`)

- Restructuring primary navigation or removing category and hub pages: an information-architecture decision with sitewide crawl consequences.
- Making a new facet dimension indexable, or flipping an existing one.
- Anything involving acquiring external links: paid, exchanged, or automated link schemes are spam policies; this seat does not participate.

## What good looks like

- Every important page is few hops from a hub, linked with anchors that say what it is.
- Link structure mirrors the site's actual topic hierarchy, so equity flows where the strategy points.
- Facets and pagination are bounded, deliberate, and stated per dimension.
- The sitemap confirms the link graph instead of compensating for it.
