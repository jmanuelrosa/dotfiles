# Color and contrast

When to read: the brief or diff touches color values, palettes, state colors, contrast, or anything rendered in more than one theme.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Contrast verified in one theme.** A pairing that passes in light mode fails in dark, or the reverse; the failing theme is exactly the one you did not develop in.
  Check: compute text contrast (WCAG 1.4.3, 4.5:1 for body text, 3:1 for large text) in every shipped theme, including hover, selected, and error variants; never eyeball it.
- **Non-text contrast ignored.** Input borders, focus indicators, icons, and chart elements that convey meaning need 3:1 (WCAG 1.4.11); a subtle gray border on white makes the field invisible to low-vision users.
  Check: component boundaries and meaningful graphics meet 3:1 against adjacent colors in every theme.
- **State conveyed by color alone.** Error, valid, selected, or disabled encoded as hue only excludes colorblind users (WCAG 1.4.1).
  Check: every state pairs color with a second channel: an icon, weight, underline, text, or shape change.
- **Disabled styled into illegibility.** WCAG exempts inactive controls, but a disabled option users cannot read is a decision, not a freebie.
  Check: disabled text remains legible; where it does not, the report records that as a deliberate choice.
- **Alpha colors composited blind.** Semi-transparent text or borders produce a different ratio on every surface they land on; the untested surface is the failing one.
  Check: contrast is computed against the actual composited backgrounds; alpha values are verified over the lightest and darkest surfaces they can sit on.
- **Universal white or black assumed.** Literal white text on a brand color works in light mode; when the theme lightens the brand for dark mode, the literal fails.
  Check: text-on-color pairs are tokens defined per theme, never literals assumed to work everywhere.
- **Focus indicator below contrast.** A focus ring at low contrast against the surface is invisible exactly when it is needed.
  Check: the focus indicator meets 3:1 against adjacent colors (WCAG 1.4.11) in every theme.
- **Text over imagery with no floor.** Text on an image or gradient has no single ratio; the worst pixel is the real ratio.
  Check: a scrim or overlay guarantees the minimum at the worst point, verified against the lightest and darkest imagery the slot accepts.
- **Forced-colors mode erased.** In forced-colors (Windows High Contrast), custom colors are overridden; boundaries drawn with box-shadow or background alone disappear.
  Check: structure, focus, and state distinctions survive forced-colors: real borders and outlines, or a deliberate `forced-color-adjust` decision.

## Escalation triggers (`needs-decision`)

- A brand-palette change or a new hue added to the palette (also an ask-first boundary in the agent).
- A mock or brief that forces a pairing below the WCAG minimum (recommend changing the design, never lowering the bar).
- Choosing the conformance target where the project has none stated.

## What good looks like

- Ratios are computed and recorded per theme and per state, not judged by eye.
- Meaning never rides on a single hue; text-on-color pairs are theme-defined tokens.
- The UI keeps its structure, focus, and states in forced-colors mode.
