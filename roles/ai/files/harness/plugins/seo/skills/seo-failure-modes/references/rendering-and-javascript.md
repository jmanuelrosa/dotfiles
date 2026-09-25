# Rendering and JavaScript

When to read: the brief or diff touches rendering strategy, client-rendered content, lazy loading, SPA routes, or anything a bot must execute JavaScript to see.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Ranking content only in the hydrated DOM.** Googlebot renders JavaScript on a deferred budget, and most AI crawlers execute none at all; content that exists only after client-side rendering is invisible to the engines that matter most for the page.
  Check: fetch the page with a plain HTTP client (no JS execution) and confirm the title, meta tags, canonical, primary content, and internal links are present in the server response.
- **Meta tags injected client-side.** A title, canonical, robots meta, or hreflang added by a client-side head manager may be seen late, inconsistently, or never; directives especially must not depend on rendering.
  Check: index directives, canonicals, and hreflang appear in the initial server HTML, not only after hydration.
- **Content behind interaction.** Bots do not click, scroll, or hover; tabs, accordions, "load more" buttons, and infinite scroll gate content behind events that never fire.
  Check: content that must rank is present in the loaded DOM without any user event; paginated or windowed lists have crawlable URL-based access to every item.
- **Lazy loading tied to viewport events.** Images or sections loaded via scroll listeners instead of native `loading="lazy"` or IntersectionObserver render blank in the bot's tall-viewport snapshot.
  Check: lazy loading uses mechanisms that fire without scrolling, and above-the-fold content is never lazy.
- **Fragment routing.** URLs distinguished only by `#fragment` are one URL to a crawler; every route that should rank needs a path or query the server can address.
  Check: no indexable content is reachable only via hash-based routing.
- **Render-blocking on bot-hostile dependencies.** Google's renderer clears localStorage, sessionStorage, and cookies between loads, declines permission prompts, and lacks service workers and similar APIs; content gated on stored state, a granted permission, a consent wall, or a geo gate renders empty for it and for every crawler that satisfies less.
  Check: primary content renders with no stored state, no granted permissions, and no third-party scripts; consent and geo gates leave the crawlable content intact.
- **Diverging bot and user responses.** Serving crawlers different content than users is cloaking, a spam-policy violation; user-agent branching in rendering code is one refactor away from it, and shipping full content in the server response only to hide it client-side behind a paywall is indistinguishable from it.
  Check: any user-agent conditional in the diff changes delivery mechanics only, never content or directives; gated content is gated server-side.
- **Error states swallowing routes.** A JS error during hydration that blanks the page, or an error boundary that replaces content with a generic message at HTTP 200, gets indexed exactly as rendered.
  Check: the page's no-JS and error-path renders still contain the core content, or return a real error status.

## Escalation triggers (`needs-decision`)

- Changing a page's rendering strategy (CSR to SSR/SSG or back): the implementation belongs to the frontend seat; the crawlability requirement is this seat's to state.
- Introducing any user-agent-conditional serving, including "SEO-only" prerendering of a subset of pages: prerendering may change delivery only; content or directive divergence is the never tier, and no approval reaches it.

## What good looks like

- Everything that must rank (content, tags, links, directives) is in the first HTML response; JavaScript enhances, it does not constitute.
- A curl of the page and a browser render of the page tell the same story.
- Pagination, filtering, and detail views are all URL-addressable.
- The no-JS experience is degraded but truthful: same content, same status codes.
