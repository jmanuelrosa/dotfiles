# Accessibility

When to read: the brief or diff adds or changes any interactive element, form, dynamic content, or visual presentation.
There is no "not applicable" for UI work.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Clickable non-element.** A `div` or `span` with a click handler but no role, tab stop, or key handling excludes keyboard and assistive-technology users entirely.
  Check: interactive means `button`, `a`, or `input` first; a custom control carries the right role, `tabindex`, Enter and Space activation, and an accessible name.
- **Focus lost across dialog lifecycles.** A modal that opens without moving focus in, does not contain it while open, or drops it to `body` on close strands keyboard users.
  Check: on open, focus moves into the dialog; Tab cycles within it; on close, focus returns to the trigger element.
- **Missing accessible name.** Icon-only buttons, unlabeled inputs, and meaningful images without alt text announce as "button" or nothing at all; a placeholder is not a label.
  Check: every input has an associated label; icon-only controls carry an explicit name (decorative icons inside get hidden); images get meaningful alt text, or empty alt when decorative.
- **ARIA that lies.** A role or state without the matching behavior (`role="button"` that Space cannot press, `aria-expanded` that never updates) is worse than no ARIA.
  Check: every ARIA attribute is backed by working behavior and synced to state; prefer native semantics that make the ARIA unnecessary.
- **Dynamic content unannounced.** Async results, toasts, and validation errors that appear visually but say nothing to screen readers make the flow uncompletable.
  Check: status changes surface through a live region or the project's announcer; errors are tied to their inputs with `aria-describedby`.
- **Invisible focus.** Removing focus outlines without an equivalent replacement makes keyboard navigation a blindfold; sticky headers and footers that cover the focused element blind it just as well.
  Check: every focusable element shows a visible focus indicator with sufficient contrast, and fixed UI never obscures the element that has focus.
- **Contrast below AA.** New text or UI colors below WCAG AA thresholds are unreadable for a measurable share of users; gray-on-gray disabled states are the usual offender.
  Check: verify new color pairs against AA with a tool, not by eye; prefer tokens that are already vetted; color is never the only signal for state, error, or meaning.
- **Motion that ignores preferences.** Animations and transitions that play regardless of `prefers-reduced-motion` are a physical accessibility failure, not a style choice.
  Check: any animation the change adds is disabled or reduced under the preference, and motion is purposeful and interruptible.
- **Keyboard traps and broken order.** Widgets that swallow Tab with no escape, or CSS repositioning that makes DOM order diverge from visual order, scramble navigation.
  Check: tab through the changed flow end to end; order matches reading order; every trap has a keyboard exit.

## Escalation triggers (`needs-decision`)

- The mandated design conflicts with AA (contrast, target size): flag it, do not silently comply.
- Replacing a native control with a custom one.
- A flow that cannot be made keyboard-operable without UX changes beyond the brief.

## What good looks like

- The whole flow works with a keyboard alone, with visible focus, in a sensible order.
- Semantic HTML does most of the work; ARIA is rare and always backed by behavior.
- A screen reader narrates the flow's states as clearly as the pixels show them.
