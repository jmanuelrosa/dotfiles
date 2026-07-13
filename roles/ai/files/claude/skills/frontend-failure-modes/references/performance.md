# Performance

When to read: the brief or diff touches lists, images and media, bundles and dependencies, fonts, rendering hot paths, or anything labeled "slow"; and for any new route or significant surface.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Vitals budget busted.** New UI that regresses LCP past 2.5s, INP past 200ms, or CLS past 0.1 at the p75 of real users fails even when a lab run passes; lab is not field.
  Check: respect the project's budgets where they exist, otherwise hold to the Core Web Vitals thresholds; trust field data (RUM, p75) over a single Lighthouse run.
- **Unvirtualized unbounded list.** Rendering thousands of live DOM nodes tanks INP and memory; feeds and tables grow in production, dev fixtures do not.
  Check: lists that can exceed a few hundred items paginate or virtualize; the bound is enforced by code, not assumed from sample data.
- **Layout thrash.** Interleaved DOM reads and writes force synchronous reflows; animating layout properties janks every frame.
  Check: batch reads before writes; animate `transform` and `opacity`, not geometry; scroll and resize work goes through observers or is throttled.
- **Unsized media shifting layout.** Images, embeds, and ads without reserved dimensions push content around as they load.
  Check: every image and embed has dimensions or `aspect-ratio`; fonts load with a strategy that avoids invisible or shifting text.
- **Uncontrolled bundle growth.** A heavyweight dependency for a trivial need, or a new surface bundled into the main chunk, taxes every page load in the app.
  Check: weigh any new dependency before proposing it (adding one is ask-first anyway); new routes and heavy optional UI are code-split; compare bundle output before and after when tooling exists.
- **Main thread blocked.** Long synchronous work in handlers or render (parsing, sorting large data) freezes input and blows the interaction budget; heavy client hydration is the same cost in disguise: server rendering can buy LCP while the hydration it requires regresses INP.
  Check: expensive work is memoized, deferred, or moved off the interaction path; new client-side interactivity is weighed against its hydration cost; the interaction paints feedback immediately even when the result takes longer.
- **Eager loading of the invisible.** Below-fold images, heavy modals, and rarely used panels loaded up front delay the content users came for.
  Check: below-fold images lazy-load, the LCP image never does and is prioritized; optional heavy UI loads behind interaction.
- **Optimizing on vibes.** Memoizing everything, virtualizing ten items, or micro-tuning without a measurement spends complexity where there is no problem.
  Check: every performance change cites the signal that motivated it (profile, trace, field metric) and the after measurement that confirms it.

## Escalation triggers (`needs-decision`)

- A budget (bundle or vitals) the change cannot meet without scope beyond the brief.
- Adding a dependency for performance work (also an ask-first boundary in the agent).
- Changing a route's rendering strategy to buy performance.

## What good looks like

- Interactions paint feedback within a frame; the main thread stays free of long tasks.
- Layout is stable from first paint; nothing shifts as media and fonts arrive.
- Bundle cost is proportional to what the route actually shows.
- Every optimization ships with its before-and-after measurement.
