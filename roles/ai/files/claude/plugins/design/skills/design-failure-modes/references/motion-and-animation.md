# Motion and animation

When to read: the brief or diff touches transitions, animations, easing, durations, loading indicators, or view transitions.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Layout properties animated.** Animating width, height, top, or margin runs layout and paint every frame; it is smooth on your machine and janks on the mid-range devices your users hold.
  Check: animations run on transform and opacity; anything else is justified in the report and tested with CPU throttling.
- **No reduced-motion path.** Users with vestibular disorders get the full parallax, zoom, or spin regardless of their OS setting (WCAG 2.3.3, AAA, held here as a hard bar).
  Check: every new animation has a `prefers-reduced-motion` treatment, and the reduced path is designed (crossfade or instant), not merely broken.
- **Duration and easing off-system.** Ad-hoc durations and bezier curves per component make the product feel inconsistent in a way nobody can name.
  Check: durations and easings come from the motion tokens or system; a needed new value is a system addition to escalate, not an inline literal.
- **Non-interruptible animation.** Motion that must finish before the next input applies makes fast users wait; triggering it twice mid-flight lands in a wrong end state.
  Check: animations are interruptible and re-targetable; mash the trigger and the end state is still correct.
- **Entrance animation gating content.** Content that is unreadable or inert until a stagger completes taxes every visit; delight on the first view is delay on the hundredth.
  Check: content is readable and interactive during entrance motion, never after it.
- **Animation on a high-frequency action.** Motion on an action users repeat all day (keyboard-invoked commands, list operations) reads as latency by the tenth repetition.
  Check: frequency drives the treatment; keyboard-initiated and high-repetition actions get instant or near-instant transitions, and delight is reserved for rare moments.
- **Unstoppable looping motion.** Auto-playing motion that loops beyond five seconds with no pause or stop violates WCAG 2.2.2 and burns battery in background tabs.
  Check: loops stop on their own, pause on interaction or `prefers-reduced-motion`, or are user-initiated.
- **Transition on `all`.** `transition: all` catches properties added later, including layout ones and theme swaps; a dark-mode toggle animates every color on screen.
  Check: transitions enumerate their properties; theme switches are exempted from transition.
- **Hover motion that moves the target.** A control that shifts or grows under the cursor moves its own hit area, causing flicker loops at the boundary.
  Check: hover and focus effects keep the hit area stable; hover the element's edge and confirm no flicker.
- **Scripted motion for declarative work.** A JS animation loop or library for a simple transition adds main-thread work and bundle weight the platform primitive avoids.
  Check: motion is declarative (CSS transitions and animations, or the platform's primitive) unless the interaction genuinely needs physics or gesture tracking.

## Escalation triggers (`needs-decision`)

- Adding an animation library (also an ask-first boundary in the agent).
- A brief that requires animating a layout property on a hot path.
- Motion that must auto-play on every page load or route change.

## What good looks like

- Motion explains a state change: where something came from, where it went.
- Transform and opacity only, system durations and easings, interruptible everywhere.
- The interface is fully usable with motion reduced or absent.
