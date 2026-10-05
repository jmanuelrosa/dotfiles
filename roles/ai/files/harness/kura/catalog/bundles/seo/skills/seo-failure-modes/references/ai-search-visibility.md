# AI search visibility

When to read: the brief or diff touches AI crawlers, AI Overviews, LLM citation, answer extraction, or GEO/AEO work.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Conflating crawler purposes when blocking.** Training controls (GPTBot, the Google-Extended robots token), answer-engine fetchers (OAI-SearchBot, PerplexityBot), and user-triggered fetchers (ChatGPT-User, Claude-User) serve different products; one Disallow written for "AI bots" silently removes the site from AI search answers, not just from training sets.
  Check: each robots.txt rule targeting an AI user agent names which product it affects and matches the stated intent; verify current crawler names and purposes against the vendors' docs, not memory.
- **Blocking Google-Extended to escape AI Overviews.** Google-Extended controls Gemini training, not Search; AI Overviews are part of Google Search and are governed by normal indexing and snippet controls (`nosnippet`, `max-snippet`, `noindex`).
  Check: any attempt to control AI Overview appearance uses snippet controls, and the trade-off (snippets shrink everywhere in Search) is stated.
- **JS-only content invisible to answer engines.** The measured answer-engine and training fetchers execute no JavaScript (Vercel's 2024-2025 measurement of 500M+ GPTBot fetches found zero JS execution; ClaudeBot downloads scripts but never runs them); Gemini, riding Google's rendering infrastructure, is the exception. Client-rendered content cannot be cited by the rest regardless of how well it ranks on Google.
  Check: the content meant to earn citations is present in the raw server HTML (see rendering-and-javascript).
- **Answer buried below the fold of the document.** Extraction favors self-contained passages: a direct answer near a descriptive heading, definitions and steps in list or table form; pages that wind up to the point get paraphrased from a competitor instead.
  Check: each target question maps to a heading plus an answer-first passage that stands alone when extracted, with supporting detail after it, not before.
- **Unverifiable GEO tactics shipped as fact.** The field is young and full of snake oil; llms.txt in particular is not read by Google (stated on the record in 2025) and server-log studies show near-zero bot fetches. An installed skill that mandates llms.txt is overridden by this check per skill precedence; name the override in the report.
  Check: every AI-visibility tactic in the diff cites a vendor doc or reproducible evidence; adopting a speculative standard is the escalation trigger below, never a labeling exercise or a satisfied requirement.
- **No citation entity for the engine to name.** Answer engines attribute to named sources; pages without a clear publisher, author, and dateModified give the engine nothing to cite and no reason to trust recency.
  Check: publisher and author identity and an honest modified date are machine-readable on the page (visible content plus structured data).
- **Rate limits and WAF rules silently 403ing fetchers.** Bot-mitigation defaults often block answer-engine fetchers wholesale, which reads as an outage from the engine's side; conversely, robots.txt is a policy statement, not enforcement, and non-compliant crawlers have been documented evading it, so blocking is a WAF job.
  Check: WAF, CDN bot rules, and rate limits in the diff distinguish the crawlers the business wants from the ones it blocks, and enforcement intent never rests on robots.txt alone.
- **Optimizing for AI answers by degrading the page.** Stuffing Q&A blocks onto every page or duplicating content in "AI-friendly" endpoints creates thin duplicates that hurt classic ranking, which AI answers still draw from.
  Check: extraction-friendly structure is applied to the canonical page itself, not bolted on as parallel content.

## Escalation triggers (`needs-decision`)

- Allowing or blocking any AI crawler in robots.txt: a business decision about training, traffic, and citation trade-offs (also an ask-first boundary in the agent).
- Adopting a speculative AI-visibility standard (llms.txt or similar) on the production site.

## What good looks like

- A deliberate, documented per-crawler policy: who may train, who may answer, who may fetch on demand.
- Content that answers first and elaborates after, on the canonical URL, in server HTML.
- Attribution surfaces (author, publisher, dates) consistent between visible content and structured data.
- Volatile claims about engine behavior verified against current vendor docs and dated in the report.
