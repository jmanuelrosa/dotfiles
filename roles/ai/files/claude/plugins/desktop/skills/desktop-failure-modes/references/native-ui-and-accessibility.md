# Native UI and accessibility

When to read: the brief or diff touches new or changed UI, menus and keyboard shortcuts, custom-drawn controls, colors and system appearance, user-visible text, or window sizing behavior.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Pointer-only interaction.** A control reachable only by mouse excludes keyboard users, assistive-technology users, and the power users who are most of a desktop app's daily audience.
  Check: every interactive element in the diff is reachable and operable from the keyboard, in a sensible tab order, with a focus indicator that is actually visible.
- **Commands missing from the menu structure.** Desktop users find and script functionality through the menu bar, so a feature reachable only from a toolbar or a context menu is effectively undiscoverable.
  Check: new commands appear in the menu structure using the platform's naming and placement, with correct enabled and disabled states.
- **Shortcuts that collide or ignore the platform.** Hard-coding one platform's modifier key, or claiming a combination the OS, a screen reader, or the app already uses, breaks muscle memory with no error anywhere. A system-wide shortcut is worse: it takes the combination from every other application silently, and it simply fails to register if something claimed it first.
  Check: shortcuts follow each platform's modifier conventions and collide with neither system nor existing app bindings; a global registration is user-configurable and its return value is checked rather than discarded.
- **Custom controls invisible to assistive technology.** A control drawn from primitives has no role, name, value, or state unless it is given them, so a screen reader reports nothing however good it looks. EN 301 549 clause 11 is the standard that applies these requirements to non-web software, which is what makes desktop accessibility checkable rather than analogized from the web.
  Check: custom controls expose role, name, value and state, and the change is exercised with the platform's own screen reader rather than inspected in markup.
- **Accessibility exposed through only one tree.** Each platform has its own accessibility API, and in a web-shell app the document feeds that tree automatically while anything built outside the document does not: a native menu, a tray item, or custom window chrome exposes nothing just because the rest of the UI does.
  Check: UI built outside the rendered document is given its accessibility properties explicitly, and the diff states which side of that split each new affordance sits on.
- **Appearance handled only at launch.** Light and dark, increased contrast, reduced motion, reduced transparency and accent color all change while the app is running, and the native surfaces (tray icon, window chrome) are not reached by the document's own styling.
  Check: appearance changes are observed at runtime rather than read once at startup, native surfaces update with them, and contrast meets WCAG 2.2 AA (4.5:1 for body text, 3:1 for large text and for UI component boundaries) in each setting.
- **Text that cannot grow.** Fixed heights and single-line assumptions clip at the user's chosen text size and in any language wordier than the one it was written in.
  Check: layouts survive the largest text size the platform supports and a pseudo-localized string substantially longer than the original.
- **Strings and formats built by hand.** Concatenated sentences, and dates, numbers and currency assembled manually, are correct in exactly one locale.
  Check: user-visible text goes through the project's localization path, and all formatting uses locale-aware APIs.
- **Only one window size exercised.** A layout developed at the default size clips, overlaps, or stretches uselessly at the extremes the user can actually reach.
  Check: the change works at the smallest size the window permits and at full screen on a large display.
- **Standard behavior reimplemented.** Rebuilding selection, scrolling, right-click, or text editing discards the platform behaviors, accessibility, and input-method support that came free.
  Check: standard interactions use the platform's own controls unless the caller has approved a custom implementation.

## Escalation triggers (`needs-decision`)

- Replacing a platform-standard control or interaction with a custom implementation.
- Changing an existing keyboard shortcut, or moving an existing command within the menu structure.

## What good looks like

- Everything the app can do is reachable from the keyboard, and the menu bar is a complete index of it.
- The app looks and behaves like it belongs on each platform it ships to, rather than on the author's.
- Accessibility is confirmed with the actual assistive technology, never inferred from the code.
