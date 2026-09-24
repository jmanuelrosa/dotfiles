# Content quality and E-E-A-T

When to read: the brief or diff touches pages generated at scale, thin or duplicate content, titles and descriptions, or author and trust surfaces.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Programmatic pages below the value floor.** Templates that mint a page per keyword permutation with swapped tokens and no differentiated data are scaled content abuse under Google's spam policies, and the helpful-content signal is sitewide: the thin pages drag down the pages that earn their place.
  Check: each generated page carries substantive data unique to its subject that a user comparing two sibling pages would notice; if not, the page set shrinks or gains a noindex tier.
- **Sitewide quality classification risk ignored.** Because quality signals apply site-wide, publishing a large low-value section is a decision about every other page's ranking, not just the new section's.
  Check: any bulk publish states its size relative to the existing indexed page count and the rollback path (noindex tier, removal) in the report.
- **Duplicate titles and descriptions at scale.** Templated `<title>` and meta description that render identically across pages make the engine pick its own snippets and blur which page should rank for what.
  Check: title and description templates interpolate enough page-specific data to be unique across the page set; spot-check the two most similar siblings.
- **Doorway pages.** Near-identical location or variant pages that all funnel to the same destination exist to capture queries, not serve users; this is a named spam policy.
  Check: each variant page has distinct content and a distinct job, or the variants collapse into one page with a parameter.
- **Trust surfaces stripped by a redesign.** Author bylines, credentials, publication and modified dates, citations, and about/contact pages are the machine-readable evidence behind E-E-A-T; templates that drop them remove the evidence sitewide in one deploy.
  Check: the diff preserves or adds authorship, dates, and sourcing on content templates; dates shown are honest, not bumped to feign freshness.
- **AI-generated content shipped unreviewed.** Generated text at scale without human review and named accountability is exactly what the scaled-content policy targets, regardless of the tool.
  Check: the pipeline for generated content includes review and attribution steps, and the report says so; if the brief omits them, escalate.
- **Spam patterns a template can trigger accidentally.** Hidden text via CSS (off-screen, zero opacity, matching colors) on keyword-bearing content, user-agent-conditional content branches, and redirects that show users something other than what the crawler saw are named spam policies a styling or routing refactor can walk into.
  Check: no keyword-bearing content in the diff is hidden by CSS while remaining in the DOM for engines, and no conditional serves crawlers different primary content.
- **Cannibalizing an existing page.** A new page targeting a query the site already ranks for splits signals between two URLs and can demote both.
  Check: search the existing sitemap and content inventory for the target topic before adding a page; consolidate or differentiate instead of duplicating.
- **Removing content without a traffic decision.** Deleting or gutting pages that hold rankings and backlinks discards equity invisibly.
  Check: pages slated for removal are listed with their inbound-link and traffic significance stated, and each gets a 301 to an equivalent, a 410, or a reprieve.

## Escalation triggers (`needs-decision`)

- Publishing or generating pages at scale (new template times large N) (also an ask-first boundary in the agent).
- Removing pages or sections that currently hold rankings or backlinks (also an ask-first boundary in the agent).
- Any brief that requires shipping content below the value floor described above.

## What good looks like

- Every indexable page can answer "what does a user get here they get nowhere else on this site".
- Generated page sets have a quality gate and a noindex tier for entries that fail it.
- Authorship, dates, and sources are visible to users and mirrored in structured data.
- New content starts from a query inventory, so pages divide the topic space instead of fighting over it.
