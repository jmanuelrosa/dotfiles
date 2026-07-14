# Routing and navigation

When to read: the brief or diff touches routes, links, URL parameters, navigation flows, or view state that should survive reload or sharing.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **View state not in the URL.** Filters, tabs, pagination, and selection held only in memory make reload, share, and back lose the user's place.
  Check: state a shared link should reproduce lives in the URL; transient UI state stays out of it; the split is deliberate, not accidental.
- **Back button betrayal.** Modals, wizards, and feeds that ignore history make back either exit the app or replay something destructive.
  Check: walk the changed flow with back and forward; each step lands where a user expects; push versus replace is chosen per step (replace for redirects and normalization, push for user-visible steps).
- **Broken deep links.** A route that only renders after in-app navigation, because it depends on state set by the previous page, blanks or crashes on direct entry.
  Check: cold-load every new or changed route by URL; it fetches its own data, enforces authorization on the destination itself (a hidden link is not access control), and renders a designed state for missing or invalid parameters.
- **Scroll position mishandled.** Back that jumps to top loses a feed position; a new page that keeps old scroll lands users mid-nowhere.
  Check: back and forward restore scroll; new navigations start at the top or the anchor; match the router's convention rather than fighting it.
- **Focus and title ignore navigation.** An SPA route change that moves nothing for keyboard and screen-reader users leaves focus on a removed element and announces nothing.
  Check: navigation moves focus to the new content root or heading per the project's pattern; the document title updates per route.
- **Pending navigation limbo.** Loader-based navigation with slow data shows a frozen old page with no feedback, so users click again.
  Check: navigations show pending feedback beyond a frame's delay (indicator, skeleton, or optimistic UI in the router's idiom).
- **Unvalidated route params.** Route and query parameters consumed as trusted, correctly-typed values break on the first hand-edited URL.
  Check: parameters are parsed and validated at the route boundary; invalid values render the designed invalid state (redirect targets have their own check in the security reference).
- **Guards that lose work or loop.** Auth redirects that drop the intended destination, or guard chains that bounce between rules, strand users.
  Check: guarded entry preserves the destination for after login; redirect chains provably terminate; unauthorized renders a designed state, not a blank.

## Escalation triggers (`needs-decision`)

- Changing the URL structure of existing routes: URLs are a public contract (bookmarks, external links, SEO).
- Adding route guards or auth-gated areas beyond the brief.
- Changing a route's rendering strategy as part of navigation work.

## What good looks like

- Any state worth sharing survives copy-pasting the URL; any step worth revisiting survives the back button.
- Every route stands alone: direct entry, invalid parameters, and unauthorized access all render designed states.
- Navigation is perceivable: pending feedback, focus movement, and a title change on every route.
