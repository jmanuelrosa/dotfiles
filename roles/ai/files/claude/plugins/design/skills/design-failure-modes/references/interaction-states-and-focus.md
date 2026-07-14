# Interaction states and focus

When to read: the brief or diff touches any interactive element; hover, focus, active, disabled, or loading states; or hit areas.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Missing state in the matrix.** An element shipped with rest and hover only inherits wrong or absent focus, active, and disabled styles from whatever cascade is nearby.
  Check: enumerate hover, focus-visible, active, and disabled (plus loading and selected where they exist) for every new interactive element, in every shipped theme.
- **Focus indicator removed.** `outline: none` for aesthetics leaves keyboard users with no idea where they are (WCAG 2.4.7).
  Check: every focusable element shows a visible indicator on keyboard focus; `:focus-visible` styling replaces the default, never removes it.
- **Focus indicator clipped or obscured.** `overflow: hidden` and tight containers clip the ring, and sticky chrome can hide the focused control entirely (WCAG 2.4.11 for the obscured control).
  Check: tab through the change and look: the ring renders fully at container edges, and `scroll-padding` keeps the focused control visible under sticky chrome.
- **Hover as the only affordance.** Actions revealed on hover do not exist for touch or keyboard users.
  Check: hover-revealed actions are reachable by focus and present on touch, visibly or through an alternate path.
- **Stuck hover on touch.** Touch devices apply hover styles on tap and leave them applied; the control still looks active after the finger lifts.
  Check: hover-only styles are gated to hover-capable input (`@media (hover: hover)`), verified by tapping in a touch emulator.
- **Hit area trimmed for density.** Visual compactness that shrinks targets below the 24x24 CSS px minimum of WCAG 2.5.8, absent its spacing and inline exceptions, makes controls miss-prone, worst on touch.
  Check: the hit area, not the glyph, meets the minimum via padding or an expanded target; adjacent targets do not overlap.
- **Decorative layer hijacking input.** A glow, gradient, or overlay positioned above a control intercepts the clicks aimed at it.
  Check: decorative layers are non-interactive (`pointer-events: none`); click every control near or under one.
- **State change that shifts layout.** A hover border or weight change that alters geometry jitters the row on every pass.
  Check: state styles change paint, not geometry: pre-reserved borders, outline or shadow, fixed weights or reserved space.
- **No pressed or in-progress feedback.** Without an active state and an in-progress state, users double-fire actions during the gap where nothing visibly happened.
  Check: activation gives immediate visual feedback, and async actions show an in-progress state on the control itself.
- **Native control replaced, contract dropped.** Restyling by replacing a native control with styled elements silently drops focus, keyboard, and announced semantics.
  Check: styling reuses the native element (accent-color, appearance, pseudo-elements) before replacing it; a replacement reproduces the full interaction contract.

## Escalation triggers (`needs-decision`)

- A density requirement that pushes hit areas below the published minimum.
- Replacing a native control with a custom implementation.
- An interaction that is hover-only by design on a product that supports touch.

## What good looks like

- The state matrix is enumerated and verified per theme before the component ships.
- Keyboard focus is always visible and never clipped.
- Hit areas meet the minimum; state changes never move the layout.
