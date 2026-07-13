# Lifecycle and background

When to read: the brief or diff touches app lifecycle, backgrounding, process death, push notification handling, or background tasks and schedulers.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Process-death amnesia.** The OS kills the backgrounded app as routine memory management; a naive resume loses the half-written form, the scroll position, and the navigation stack.
  Check: state a user would expect to survive is saved via the platform's restoration mechanism, and the kill-and-restore path is exercised with the platform's own tooling.
- **Sensitive snapshot exposure.** The app switcher screenshots whatever was on screen at backgrounding; balances and messages sit in the carousel for anyone holding the phone.
  Check: screens showing sensitive content obscure themselves on backgrounding.
- **Fire-and-forget background work.** An upload or sync started in the foreground gets seconds after backgrounding, then dies silently.
  Check: work that must outlive the foreground uses the platform's background-task mechanism with an expiration handler, and abandoned work resumes on next foreground.
- **Push token lifecycle ignored.** Device tokens rotate on reinstall, restore, and OS refresh; a server holding a dead token notifies nobody and nobody notices.
  Check: the token refresh callback updates the server, and logout unregisters the token.
- **Trusted or brittle push payloads.** A notification payload is remote input; parsing it naively crashes, and old app versions receive whatever the server sends forever.
  Check: payloads parse defensively with unknown fields tolerated, and a screen opened from a push goes through the same validation and auth as a deep link.
- **Foreground-only time math.** Timers and accumulated ticks assume continuous execution; time jumps at resume, across time zones, and when the user changes the clock.
  Check: elapsed time derives from timestamps, and the resume path recomputes any time-dependent state.
- **Exact-time background assumptions.** Background schedulers batch, defer, and skip to save battery; work scheduled for 3:00 runs at 3:40, twice, or tomorrow.
  Check: scheduled work is idempotent, tolerates deferral and duplication, and nothing user-facing promises exact background timing.
- **Lifecycle-blind resource handles.** Camera sessions, audio, sockets, and file handles held across a background transition get revoked by the OS mid-use.
  Check: exclusive resources are acquired on foreground, released on background, and reacquired on resume.

## Escalation triggers (`needs-decision`)

- Adding a new background execution mode or capability (a declaration and store-policy decision).
- Changing a deep-link URL format or push payload contract already shipped in old binaries (also an ask-first boundary in the agent).

## What good looks like

- Death at any moment is safe, and resume looks intentional rather than lucky.
- Background work is a scheduled, idempotent citizen of the OS's budget.
- Nothing sensitive is visible in the app switcher, and nobody keeps a dead push token.
