# Performance and battery

When to read: the brief or diff touches lists and scrolling, images, animation, the startup path, main-thread work, location or sensors, or polling.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Main-thread work.** Parsing, decoding, database access, or crypto on the main, UI, or JS thread drops frames, freezes gestures, and at scale trips the platform's ANR accounting (Android vitals flags apps above published ANR and crash thresholds).
  Check: nothing heavier than the next frame runs on an interaction path; heavy work is async, deferred, or moved off-thread.
- **Unvirtualized lists.** Rendering a whole collection works with the ten dev items and exhausts memory at the production ten thousand.
  Check: long or unbounded lists virtualize, with stable keys and bounded per-item cost.
- **Image memory blowups.** Full-resolution images decoded into thumbnail-sized views multiply memory by orders of magnitude.
  Check: images are downsampled to display size and cached with explicit bounds.
- **Startup regression.** Synchronous SDK init, IO, or network on the cold-start path delays first frame for every launch forever after.
  Check: additions to the launch path are lazy or deferred; when startup tooling exists, cold start is measured before and after.
- **Re-render storms.** A state change cascades re-renders or layout passes across the tree; scrolling and typing stutter.
  Check: render work is bounded with the framework's idiom (memoization, diffing, granular state), and animations run off the interaction thread where the framework offers it.
- **Leaked subscriptions.** Listeners, timers, observers, and sensor subscriptions that outlive their screen keep the radio and CPU awake and leak memory.
  Check: every subscription in the diff has a teardown tied to its owner's lifecycle.
- **Polling where events exist.** Interval polling wakes the radio on a schedule; it drains battery in a way users attribute to the app, correctly.
  Check: polling is justified against a push or event alternative, and any interval respects app state (background vs active).
- **Battery-hostile sensor use.** Continuous high-accuracy location where coarse or significant-change accuracy would serve the feature.
  Check: accuracy and frequency match the feature's actual need, and sensing stops when the feature is not in use.
- **Chatty interop in hot paths.** Synchronous calls across the bridge, FFI, or channel boundary inside render or scroll paths serialize the exact threads that must stay free.
  Check: cross-boundary calls in hot paths are batched or async.

## Escalation triggers (`needs-decision`)

- Adding a new background execution cadence that runs while the app is not foregrounded (a background refresh, sync, or wake schedule).
- Adding a heavy SDK or framework to the startup path.

## What good looks like

- Interaction paths fit in a frame budget; everything else happens elsewhere.
- Leaks are impossible by construction: effects and subscriptions are lifecycle-scoped.
- Battery cost is proportional to user-visible value, and sensing is off by default.
