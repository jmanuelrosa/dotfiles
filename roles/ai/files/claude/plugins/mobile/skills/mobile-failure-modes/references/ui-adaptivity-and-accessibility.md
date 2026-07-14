# UI adaptivity and accessibility

When to read: the brief or diff touches new or changed screens, text and layout, localization, inputs and keyboards, or custom controls.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Fixed-size assumptions.** A layout tuned to one device breaks on small phones, tablets, split screen, and foldables.
  Check: touched screens are verified at the smallest and largest supported bounds, not just the simulator default.
- **Safe-area violations.** Content slides under notches, cameras, home indicators, and status bars, or the keyboard covers the input the user is typing into.
  Check: insets come from the platform mechanism, and every input remains visible with the keyboard up.
- **Font-scaling breakage.** At the largest accessibility text sizes, labels truncate, buttons overflow, and fixed-height containers clip their content.
  Check: text respects the system scale, containers grow with their content, and the screen is exercised at the maximum setting.
- **Silent controls.** New interactive elements without accessible name, role, and state; a screen reader announces noise or nothing.
  Check: every interactive element carries name, role, and state; decorative elements are hidden from the accessibility tree; custom controls expose what the platform control would have given for free.
- **Sub-minimum touch targets.** Hit areas below the platform minimums (44pt on iOS per the HIG, 48dp on Android per Material) fail real fingers even when the visual design is smaller.
  Check: hit areas meet the platform minimum independent of visual size.
- **Contrast and color-only meaning.** Text below WCAG AA contrast, and states distinguished by color alone, are invisible to a meaningful share of users.
  Check: text meets WCAG AA against its actual background, and every color-coded state has a second channel (icon, label, position).
- **RTL and localization breakage.** Hardcoded strings, concatenated sentence fragments, and left/right-frozen layouts break the moment a second language or an RTL locale arrives.
  Check: user-facing strings are externalized and parameterized, layout uses start/end semantics, and pseudo-localization runs where tooling exists.
- **Input-method assumptions.** Fields without content types get the wrong keyboard, no autofill, and broken password managers.
  Check: inputs declare their content type and purpose so the platform can offer the right keyboard and autofill.
- **Motion without mercy.** Animations that ignore the OS reduce-motion setting make the app unusable for vestibular-sensitive users.
  Check: animations honor the system reduce-motion preference with a reduced or crossfade variant.

## Escalation triggers (`needs-decision`)

- Dropping support for a size class, orientation, or platform text-size range.
- Replacing a platform control with a custom one (the accessibility surface becomes yours to rebuild).

## What good looks like

- The screen works at the extremes: smallest device, largest font, screen reader on, RTL locale.
- Platform controls are the default; custom ones justify their accessibility cost.
- Localization is a data change, not a layout project.
