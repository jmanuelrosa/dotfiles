# Structured data

When to read: the brief or diff touches JSON-LD, microdata, schema.org types, or rich result eligibility.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Markup describing content not on the page.** Structured data must reflect what a user can see on that page (Google structured data general guidelines); marking up absent reviews, prices, or FAQs is a spam-policy violation that risks a manual action, not a missed rich result.
  Check: every property value in the emitted JSON-LD corresponds to visible page content; nothing is fabricated or pulled from data the page does not show.
- **Invalid or unparseable JSON-LD.** A trailing comma, an unescaped quote from user content, or a template interpolation error silently disqualifies the whole block.
  Check: the emitted JSON-LD parses as JSON with real page data flowing through it, including data containing quotes, newlines, and HTML.
- **Wrong or ineligible type for the intent.** A type Google has no rich result for, or one it has restricted (FAQ and HowTo rich results were deprecated for most sites in 2023), ships markup that can never pay off while adding maintenance surface.
  Check: the chosen type appears in Google's current rich result gallery for this content kind, verified against current docs rather than memory.
- **Missing required properties.** Each rich result type has required and recommended properties; omitting a required one makes the item ineligible without any error at build time.
  Check: the type's required properties per Google's documentation for that rich result are all present and populated.
- **Self-serving review markup.** Review or rating markup for the organization's own products or services, sourced from the organization itself, is explicitly disallowed for review snippets.
  Check: review markup only wraps genuinely third-party reviews displayed on the page.
- **Duplicated or conflicting entities.** Two blocks on one page describing the same entity with different values (a CMS plugin plus a hand-rolled component) make the engine pick one arbitrarily.
  Check: one source of truth emits each entity; audit the rendered page for pre-existing emitters before adding another.
- **Markup on non-canonical or blocked pages.** Structured data on a variant that canonicalizes elsewhere, or on a page that is robots-blocked or noindexed, is attributed to a page the engine will not index; markup injected client-side inherits every rendering failure and is invisible to AI crawlers that execute no JavaScript.
  Check: the canonical, indexable version of the page emits the markup in the server response.
- **Stale markup after content change.** Prices, availability, dates, and ratings in JSON-LD that render from a different data path than the visible content drift apart on the next content edit.
  Check: markup and visible content derive from the same source data in the same render.

## Escalation triggers (`needs-decision`)

- Adding or upgrading any dependency to emit or validate markup (also an ask-first boundary in the agent).
- Marking up a content kind whose rich result eligibility is ambiguous or recently changed: confirm current support first.

## What good looks like

- JSON-LD generated from the page's own data source, validated in CI or at build time, one emitter per entity.
- Types chosen for a rich result the site can actually earn, with required properties complete.
- Markup that a deletion of the visible content would also delete.
- Eligibility claims verified against current Google documentation, dated in the report.
