---
name: designing-frontend
description: >
  Frontend design and UI implementation guidelines. Use when building web
  components, pages, or applications, or when reviewing UI code. Covers:
  creative design direction, typography, color/theming, animation/motion,
  layout, accessibility, forms, performance, images, navigation, touch,
  hydration, i18n, and content/copy. Triggers on: building UI, designing
  components, reviewing frontend code, checking accessibility, auditing UX,
  or any web interface work.
license: MIT
metadata:
  date: 08-March-2026
  version: "1.0.0"
  sources:
    - https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design
    - https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines
---

# Frontend Design Guide

Creative design direction + technical UI rules for building and reviewing web interfaces.

## Design Direction

<!-- via: frontend-design -->

Before coding, commit to a **bold aesthetic direction**:

- **Purpose** — what problem does this solve? Who uses it?
- **Tone** — pick a clear direction: brutally minimal, maximalist, retro-futuristic, organic, luxury, playful, editorial, brutalist, art deco, soft/pastel, industrial. Execute with precision.
- **Differentiation** — what makes this unforgettable?

Bold maximalism and refined minimalism both work — the key is **intentionality**, not intensity. Match implementation complexity to the vision.

**NEVER** use generic AI aesthetics: overused fonts (Inter, Roboto, Arial, system fonts), cliched purple gradients on white, predictable layouts, cookie-cutter design. Every design must feel context-specific.

## Typography

<!-- via: frontend-design + web-design-guidelines -->

**Creative choices:**
- Choose distinctive, characterful fonts — avoid Inter, Roboto, Arial, system defaults
- Pair a display font with a refined body font
- Vary choices between generations — never converge on common picks

**Technical rules:**
- Use `…` not `...` — real ellipsis character
- Use curly quotes `""` `''`, not straight `"` `'`
- Non-breaking spaces (`&nbsp;`) in measurements (`100 kg`) and brand names
- `font-variant-numeric: tabular-nums` for number columns/tables
- `text-wrap: balance` or `text-pretty` on headings
- Loading states end with `…`

## Color & Theming

<!-- via: frontend-design + web-design-guidelines -->

**Creative choices:**
- Use CSS variables for consistency
- Dominant colors with sharp accents outperform timid, evenly-distributed palettes
- Vary between light and dark themes across designs

**Technical rules:**
- Set `color-scheme: dark` on `<html>` for dark mode
- Add `<meta name="theme-color">` matching the background
- Native `<select>` elements: set explicit `background-color` and `color`

## Animation & Motion

<!-- via: frontend-design + web-design-guidelines -->

**Creative choices:**
- Focus on high-impact moments: one well-orchestrated page load with staggered reveals (`animation-delay`) beats scattered micro-interactions
- Use scroll-triggering and hover states that surprise
- Prefer CSS-only for HTML; use Motion library for React when available

**Technical constraints:**
- Honor `prefers-reduced-motion` — always
- Animate only `transform` and `opacity` (composited properties)
- Never use `transition: all`
- Set correct `transform-origin` before animating
- SVG transforms go on a `<g>` wrapper, not the SVG element
- Animations must be interruptible

## Spatial Composition & Layout

<!-- via: frontend-design + web-design-guidelines -->

**Creative choices:**
- Unexpected layouts: asymmetry, overlap, diagonal flow, grid-breaking elements
- Generous negative space OR controlled density — commit to one

**Technical rules:**
- Full-bleed layouts need `env(safe-area-inset-*)` for notched devices
- Avoid unwanted scrollbars
- Prefer flex/grid over JS measurement
- Backgrounds & textures: gradient meshes, noise, geometric patterns, layered transparencies, dramatic shadows, grain overlays — create atmosphere, not flat color

## Accessibility

<!-- via: web-design-guidelines -->

- Icon-only buttons need `aria-label`
- Form controls need `<label>` or `aria-label`
- Interactive elements need keyboard handlers (`onKeyDown`/`onKeyUp`)
- `<button>` for actions, `<a>`/`<Link>` for navigation — never `<div onClick>`
- Images need `alt` (or `alt=""` if decorative)
- Decorative icons need `aria-hidden="true"`
- Async updates (toasts, validation) need `aria-live="polite"`
- Use semantic HTML before ARIA
- Headings hierarchical `<h1>`–`<h6>`; include skip link for main content
- `scroll-margin-top` on heading anchors

## Focus States

<!-- via: web-design-guidelines -->

- Interactive elements need visible focus: `focus-visible:ring-*` or equivalent
- Never `outline-none` without a focus replacement
- Use `:focus-visible` over `:focus`
- Group focus with `:focus-within` for compound controls

## Forms

<!-- via: web-design-guidelines -->

- Inputs need `autocomplete` and meaningful `name`
- Use correct `type` and `inputmode`
- Never block paste
- Labels clickable (`htmlFor` or wrapping the control)
- Submit button enabled until request starts; show spinner during request
- Errors inline; focus first error on submit
- Warn before navigation with unsaved changes

See `references/forms.md` for detailed form rules.

## Images

<!-- via: web-design-guidelines -->

- `<img>` needs explicit `width` and `height` (prevents layout shift)
- Below-fold images: `loading="lazy"`
- Above-fold critical images: `priority` or `fetchpriority="high"`

## Performance

<!-- via: web-design-guidelines -->

- Large lists (>50 items): virtualize
- No layout reads in render
- Batch DOM reads/writes
- Prefer uncontrolled inputs when possible
- Add `<link rel="preconnect">` for CDN domains
- Critical fonts: `<link rel="preload" as="font">` with `font-display: swap`

## Content Handling

<!-- via: web-design-guidelines -->

- Text containers handle long content: `truncate`, `line-clamp-*`, or `break-words`
- Flex children need `min-w-0` to allow truncation
- Handle empty states
- Anticipate short, average, and very long user inputs

## Navigation & State

<!-- via: web-design-guidelines -->

- URL reflects state: filters, tabs, pagination, panels in query params
- Deep-link all stateful UI
- Links use `<a>`/`<Link>`, not click handlers on divs
- Destructive actions need confirmation or undo

## Touch & Interaction

<!-- via: web-design-guidelines -->

- `touch-action: manipulation` on interactive elements
- Set `-webkit-tap-highlight-color` intentionally
- `overscroll-behavior: contain` in modals/drawers/sheets
- During drag: disable text selection, `inert` on dragged elements
- Use `autoFocus` sparingly

## Hover & Interactive States

<!-- via: web-design-guidelines -->

- Buttons and links need `hover:` state
- Interactive states increase contrast

## Dark Mode & Hydration

<!-- via: web-design-guidelines -->

- Inputs with `value` need `onChange` (controlled components)
- Guard date/time rendering against hydration mismatch
- Use `suppressHydrationWarning` sparingly and only for expected mismatches

## Locale & i18n

<!-- via: web-design-guidelines -->

- Dates/times: use `Intl.DateTimeFormat` — never hardcode formats
- Numbers/currency: use `Intl.NumberFormat`
- Detect language via `Accept-Language` header or `navigator.languages`

## Content & Copy

<!-- via: web-design-guidelines -->

- Active voice preferred
- Title Case for headings and buttons
- Use numerals for counts
- Specific button labels (not "Submit" — say what happens)
- Error messages include fix or next step
- Second person (`you`); avoid first person
- `&` over "and" when space-constrained

## Anti-patterns to Flag

<!-- via: frontend-design + web-design-guidelines -->

**Design anti-patterns:**
- Generic AI slop: Inter/Roboto, purple gradients, predictable layouts
- Converging on the same fonts/colors across designs

**Code anti-patterns:**
- `user-scalable=no` or `maximum-scale=1`
- `onPaste` with `preventDefault`
- `transition: all`
- `outline-none` without replacement
- `<div>` or `<span>` with click handlers (use `<button>`/`<a>`)
- Images without dimensions
- Large arrays without virtualization
- Form inputs without labels
- Icon buttons without `aria-label`
- Hardcoded date/number formats
- `autoFocus` without justification

## Review Workflow

To audit existing UI code against these guidelines:

1. Fetch latest rules: `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`
2. Read the target files
3. Check against all rules above
4. Output findings in `file:line` format
