# Responsive and layout

When to read: the brief or diff touches breakpoints, container queries, grids, fluid sizing, or viewport and zoom behavior.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Between-breakpoint breakage.** A layout verified at the named breakpoints alone breaks at the widths in between, which is where real windows live.
  Check: drag the viewport continuously across the supported range; wrapping is content-driven, not snapped to the exact widths you tested.
- **Off-scale breakpoint.** An ad-hoc media query width fixes one component and forks the system grid; the next component picks a different ad-hoc width.
  Check: breakpoints come from the system scale; a component-specific threshold is a container query on the component's own size, or an escalated new scale step.
- **Viewport query where a container query belongs.** A component styled by viewport width breaks the moment it is placed in a sidebar: the viewport says wide, the container is narrow.
  Check: components respond to their container; viewport queries are reserved for page-level layout.
- **Reflow failure.** At 320 CSS px width or 400% zoom, content requires scrolling in two dimensions (WCAG 1.4.10).
  Check: the change reads with single-axis scrolling at 320px-equivalent width; no fixed-width element forces horizontal scroll.
- **Fixed dimensions on content boxes.** Heights copied from the mock and pixel widths on text or media overflow with real content, translations, and user font sizes.
  Check: content boxes size intrinsically with min and max constraints; media reserves space with aspect-ratio, not a hardcoded height.
- **Absolute positioning as layout.** Layout built from absolutely positioned boxes detaches from flow; siblings overlap at the sizes nobody tried.
  Check: layout uses flow mechanisms (grid, flex, stack primitives); absolute positioning is reserved for genuine overlays anchored to a positioned ancestor.
- **Short-viewport blindness.** Fixed headers plus footers leave no content room on a landscape phone; a modal taller than the viewport has no internal scroll.
  Check: verify at short heights (landscape mobile, small laptop); sticky chrome collapses or scrolls, and modals scroll internally.
- **Long-content collapse.** The design was only seen with short labels; a long name, URL, or unbroken token overflows its cell or pushes siblings out of line.
  Check: every text cell has a wrap, truncate, or scroll policy, exercised with adversarial lengths including unbroken strings (`overflow-wrap`).
- **Scrollbar and safe-area shifts.** A layout that assumes no scrollbar jumps when content grows; fixed chrome lands under notches and home indicators.
  Check: the layout tolerates scrollbar appearance (`scrollbar-gutter` or tolerant sizing), and fixed elements respect safe-area insets.

## Escalation triggers (`needs-decision`)

- Adding a new breakpoint to the system scale (also an ask-first boundary in the agent).
- A design that requires fixed dimensions on content-bearing boxes.
- Dropping support for a viewport range the project previously handled.

## What good looks like

- Layout is content-driven; breakpoints correct it, they do not define it.
- Components respond to their containers; pages respond to the viewport.
- The change survives 320px, 200% zoom, short viewports, and hostile content lengths.
