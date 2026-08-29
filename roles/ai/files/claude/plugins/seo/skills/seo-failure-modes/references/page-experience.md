# Page experience

When to read: the brief or diff touches Core Web Vitals as a ranking input, interstitials, HTTPS, or other page experience signals.

Boundary first: measuring, budgeting, and fixing Core Web Vitals is the frontend seat's surface, with its own performance checklists.
This seat's job is narrower: know when a change threatens the page experience signals search engines consume, say so, and route the fix.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **SEO change that degrades the vitals it depends on.** SEO work adds weight in exactly the wrong places: structured data bloat, meta-management scripts, tag wrappers, and prerender proxies land in the head and the critical path.
  Check: anything this seat adds to the document head or critical path is measured for size and blocking behavior, and the delta is stated in the report.
- **Field and lab data conflated.** Ranking consumes real-user field data at p75 (CrUX), not lab runs; a green Lighthouse score on a dev machine says nothing about the signal the engine sees.
  Check: claims about vitals status name their data source; "passes locally" is never reported as "passes".
- **Intrusive interstitial reintroduced.** Popups and app-install banners that cover the main content on entry from search are a documented negative signal; legally required interstitials (cookie consent, age gates) are exempt from that signal but can still block the content from rendering for crawlers entirely.
  Check: any overlay in the diff leaves the main content visible and dismissible on first paint for search-originated visits, and legally required gates leave the crawlable content intact.
- **HTTPS holes from migration or embeds.** Mixed content, http-only redirects, or a canonical pointing at the http version undermine the HTTPS signal page by page.
  Check: canonical URLs, sitemap entries, redirects, and embedded resources are all https.
- **Vitals regressions attributed to algorithm updates.** When rankings and vitals move together after a deploy, the deploy is the first suspect; blaming an update skips the fix.
  Check: SEO-relevant template changes note the deploy date in the report so ranking movement can be correlated.
- **Ranking weight overstated to justify work.** Page experience is a set of mostly tie-breaker signals, not a dominant factor; a vitals project sold as a rankings project sets an expectation the results will miss.
  Check: recommendations that route vitals work to the frontend seat state the expected benefit honestly: user experience first, marginal ranking effect second.

## Escalation triggers (`needs-decision`)

- The brief asks this seat to implement performance optimizations: route to the frontend seat instead, with the search-signal requirement attached.
- A required third-party addition (consent platform, ad script) that will predictably damage field vitals on search landing pages.

## What good looks like

- SEO surfaces (head tags, structured data, redirects) are weight-audited like any other code.
- Vitals claims cite field data; lab data is used for diagnosis, not status.
- Landing pages from search show their content immediately, on https, with nothing covering it.
- Fixes live with the frontend seat; this seat contributes the ranking context and the routing.
