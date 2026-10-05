# Typography and spacing

When to read: the brief or diff touches font sizes, the type scale, line-height, spacing values, truncation, or web fonts.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Off-scale values.** A 13px gap in a 4/8 system or a font size between scale steps ships a new de facto step nobody ratified, and the next screen copies it.
  Check: every size and space in the diff is a scale step; a value the scale lacks is an escalation, not an inline literal.
- **Size changed, metrics kept.** Changing font-size while inheriting a line-height and letter-spacing tuned for another size breaks rhythm and readability at both ends of the scale.
  Check: type changes ship as complete scale steps (size with its line-height and tracking), taken from the type scale, never size alone.
- **Web font without tuned fallback.** A font that swaps in without metric-compatible fallbacks shifts layout on every cold load; the CLS lands on real users, not your warm cache.
  Check: the fallback stack is metric-tuned (size-adjust, ascent-override, or a metric-compatible face) and the swap is verified with cache disabled.
- **Truncation without a path to the full text.** Ellipsis hides exactly the differentiating suffix; two truncated items become identical and the user cannot recover the difference.
  Check: truncated text keeps an affordance (title, tooltip, expansion, or wrapping at wider sizes) and is verified with real long content, not lorem.
- **Fixed heights on text containers.** A container sized to the mock's copy overflows with a longer translation, a two-line wrap, or a larger user font size.
  Check: text containers size from content (min-height over height) and survive a doubled string and 200% text zoom (WCAG 1.4.4).
- **Unbounded line length.** Text that spans a wide viewport reaches an unreadable measure; the design was only ever seen at laptop width.
  Check: reading text has a maximum measure from the system, verified at the widest breakpoint.
- **Proportional digits in changing numbers.** Timers, counters, and numeric columns set in proportional figures change width on every tick, jittering the layout.
  Check: changing values and numeric tables use tabular figures (`font-variant-numeric: tabular-nums`) or an equivalent fixed-width slot.
- **Spacing idiom soup.** Mixing child margins, parent padding, and ad-hoc gaps yields spacing nobody can predict; reordering siblings shifts the layout.
  Check: spacing follows the project's one idiom (gap-based, stack primitives, or a consistent margin direction); the diff introduces no second idiom.
- **User text-spacing adjustments break the layout.** Content clips or overlaps when users increase line height, paragraph spacing, or letter spacing (WCAG 1.4.12).
  Check: the layout survives line-height 1.5, paragraph spacing 2x font size, letter spacing 0.12em, and word spacing 0.16em without loss of content or function.
- **Optical nudges scattered as literals.** One-off pixel nudges for visual alignment spread through the diff; they break at other sizes and nobody dares remove them.
  Check: alignment derives from shared box metrics; a genuine optical adjustment is centralized (a token or the component's one documented offset), not sprinkled.

## Escalation triggers (`needs-decision`)

- Adding a web font, which is a dependency (also an ask-first boundary in the agent).
- Adding a new step to the type or spacing scale (also an ask-first boundary in the agent).
- A mock that can only be matched with off-scale values.

## What good looks like

- Every measurement in the diff answers to a scale.
- Type ships as complete steps; text containers grow with their content.
- Fonts load without shift; truncation always leaves a path to the full text.
