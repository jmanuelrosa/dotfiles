---
name: design-failure-modes
description: >-
  Failure-mode checklists for design-engineering work, split by domain.
  Use when implementing or reviewing changes that touch design tokens and theming,
  component APIs and variants, typography and spacing, color and contrast,
  motion and animation, interaction states and focus, responsive layout, or CSS architecture.
  Read only the reference files whose triggers match the change.
---

# Design failure modes

Checklists of the ways design-engineering changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Design tokens, semantic aliases, theme definitions, dark mode, brand values | [references/design-tokens-and-theming.md](references/design-tokens-and-theming.md) |
| Component props, variants, slots, composition, shared or published component APIs | [references/component-api-and-variants.md](references/component-api-and-variants.md) |
| Font sizes, type scale, line-height, spacing values, truncation, web fonts | [references/typography-and-spacing.md](references/typography-and-spacing.md) |
| Color values, palettes, state colors, contrast, anything rendered in more than one theme | [references/color-and-contrast.md](references/color-and-contrast.md) |
| Transitions, animations, easing, durations, loading indicators, view transitions | [references/motion-and-animation.md](references/motion-and-animation.md) |
| Any interactive element; hover, focus, active, disabled, loading states; hit areas | [references/interaction-states-and-focus.md](references/interaction-states-and-focus.md) |
| Breakpoints, container queries, grids, fluid sizing, viewport or zoom behavior | [references/responsive-and-layout.md](references/responsive-and-layout.md) |
| Stylesheet structure, specificity, cascade layers, custom properties, z-index | [references/css-architecture.md](references/css-architecture.md) |

Most real changes fire two or three rows (a new component brief fires at least component-api-and-variants, interaction-states-and-focus, and color-and-contrast).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: framework- and styling-library-specific guidance belongs to the stack skills the caller has installed, not here.
