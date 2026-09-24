# Performance and resources

When to read: the brief or diff touches the launch path, work on the UI thread, long-lived caches or subscriptions, recurring or background work, rendering and GPU use, or anything described as slow or heavy.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Work on the UI thread.** Parsing, decoding, filesystem access, or cryptography on the thread that owns the window freezes it, the OS puts up the wait cursor, and the user force-quits before the operation finishes.
  Check: nothing heavier than the next frame runs on the UI thread; heavy work is asynchronous, off-thread, or in a helper process.
- **Cold start grows by accretion.** Each release adds one more synchronous initialization to the launch path, and launch is the interaction a desktop user performs every single morning. Module cost is paid at import time, so a dependency added to the entry file of the process that owns the UI is startup cost and resident memory even when nothing ever calls it.
  Check: additions to the startup path are deferred behind first use and required at their call site rather than at the top of the entry module; where measurement tooling exists, launch is timed before and after.
- **Memory grows across a long session.** Desktop apps run for days, so a leak invisible in a five-minute test is a multi-gigabyte process by the end of the week.
  Check: every listener, timer, observer, cache entry and window reference added in the diff has a teardown, and every cache has an explicit bound and eviction policy.
- **Work continues while nobody is looking.** A timer, animation, poll, or subscription that keeps running when the window is hidden, minimized, or unfocused spins the fan and drains the battery for output no one can see.
  Check: recurring work is suspended on window-hidden, system sleep, screen lock, and loss of network or external power, and CPU use at rest is actually observed rather than assumed.
- **Energy cost that the OS attributes by name.** Frequent wakeups, continuous compositing, and power assertions preventing display or system sleep all appear in the platform's energy accounting next to the app's name. The OS will throttle a backgrounded, obscured app on its own, but an app that keeps drawing, disables background throttling, or holds a power assertion has opted itself out of that protection.
  Check: the change does not raise the wakeup rate at idle, timers are coalesced rather than multiplied, recursive filesystem watchers are bounded, and any disabled throttling or held assertion names the user-visible behavior requiring it and releases it after.
- **Unbounded rendering.** Drawing an entire collection is comfortable with the ten items in dev and stalls at the hundred thousand in production.
  Check: long or unbounded lists virtualize, with stable keys and a bounded per-item cost.
- **Full-resolution assets in small views.** Decoding a large image into a thumbnail-sized view multiplies memory by orders of magnitude, and a multi-window app pays it per window.
  Check: images are downsampled to display size at the current scale factor and cached within an explicit budget.
- **Crash-prone work inside the UI process.** Putting parsing, plugin execution, or native library calls in the process that owns the window means one fault takes the whole app down with everything unsaved in it.
  Check: work that can hang or crash independently runs where the UI can survive it failing.
- **Speed asserted rather than measured.** A change described as faster with no number is a guess that is now permanent.
  Check: every performance claim in the report carries evidence: a profile, a timing, or a memory sample from before and after.

## Escalation triggers (`needs-decision`)

- Adding work to the launch path that cannot be deferred, or a recurring cadence the feature genuinely requires while the app is hidden or the machine is asleep.
- Adding a heavy runtime or a large framework to the shipped bundle (also an ask-first boundary in the agent, which covers every added dependency).
- Adding an additional embedded browser instance, which multiplies baseline memory per window rather than adding to it once.

## What good looks like

- The UI thread carries the next frame and nothing else.
- An app nobody is currently using is close to invisible in the system activity monitor.
- Every claim about speed or memory is backed by a measurement someone else could repeat.
