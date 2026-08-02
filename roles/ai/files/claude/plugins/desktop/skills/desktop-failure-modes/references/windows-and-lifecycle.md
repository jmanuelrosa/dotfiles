# Windows and lifecycle

When to read: the brief or diff touches window creation or geometry, multi-window behavior, quit and close paths, tray, menu-bar or dock presence, multiple displays, or sleep and wake.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Bounds restored onto a display that no longer exists.** Saved window coordinates point at a monitor that was disconnected or a resolution that changed, so the window opens offscreen and the user has no way to reach it.
  Check: the restore path intersects the saved rectangle against the enumerated display set and falls back to a centered default when no display holds a usable portion of it; coordinate-clamping alone silently relocates a window the user placed deliberately.
- **The window manager assumed to obey.** Some platforms deliberately refuse to tell an app where its window sits globally, so positioning and cursor-location calls are unavailable rather than inaccurate; compositors that draw their own decorations make frame geometry differ from content geometry; and a tiling manager or a full-screen or split layout simply ignores the size you asked for.
  Check: code reading or writing global screen coordinates has a branch for the platforms that refuse them, nothing assumes the requested size was granted, and the change is exercised at full screen and at the smallest size the window permits.
- **Close conflated with quit.** Closing the last window quits an app that platform convention says should stay resident, or hides an app the user believes they exited, leaving a process running.
  Check: close, hide, and quit are three distinct paths, and each follows the convention of the platform it runs on rather than one platform's behavior shipped everywhere.
- **Quit races unsaved work.** A termination handler tears down state before pending writes finish, so the last edit is lost exactly when the user is not watching. Frameworks usually offer both a graceful quit that runs teardown hooks and an immediate exit that runs none, named as similarly as `quit` and `exit`.
  Check: the quit path awaits or explicitly cancels in-flight writes, no forced-exit call sits on a path that can carry unsaved work, and the platform's veto point is honored before teardown begins.
- **Quit vetoed with no way back.** Cancelling termination to run an async save, and then never re-issuing the quit (or never re-issuing it on the error branch), produces an application the user cannot close.
  Check: every veto of a quit or close has a terminating branch on both the success and the failure path.
- **Second launch dropped or duplicated.** Relaunching either starts a second process contending for the same app-data, or discards the arguments that launched it (the file the user double-clicked, the URL they opened).
  Check: the single-instance decision is explicit, and a second launch's arguments and file-open events are forwarded to the running instance.
- **Scale factor captured once.** Sizes and fonts computed at initialization go stale when the window is dragged to a display with a different scale, and a process that never declares per-monitor DPI awareness in its manifest gets bitmap-stretched into blurriness on every display but one.
  Check: per-monitor awareness is declared, dimensions and asset choices derive from the current scale factor at layout time, and the DPI-change handler adopts the suggested rectangle the OS passes it rather than computing its own, which is what causes cursor drift and recursive resize loops.
- **Sleep and wake assumed continuous.** Timers, sockets, and elapsed-time math behave differently across a system sleep; connections are dead and credentials expired while the code believes nothing happened.
  Check: timers and long-lived connections in the diff have a wake path that revalidates rather than resuming, and durations use a clock whose behavior across sleep you have confirmed.
- **Hidden with no way back.** An app that minimizes to a tray or menu-bar item without a discoverable path to reopen, or that leaves its item behind after quitting; the sibling defect is a reactivation handler that builds a second window instead of focusing the one already open.
  Check: every hidden state has a visible way to restore the window, reactivation focuses an existing window before creating one, and the item is torn down on quit.
- **Geometry persisted on every event.** Writing bounds on each move or resize writes continuously during a drag and corrupts the file if the process dies mid-write.
  Check: window-state persistence is debounced and written atomically.

## Escalation triggers (`needs-decision`)

- Changing whether the app is single-instance, or changing what the close button does on any platform (also an ask-first boundary in the agent).
- Adding a tray, menu-bar, or dock presence the app did not previously have.

## What good looks like

- Geometry is restored defensively: validated against the current display set, clamped, then shown.
- Quit is a sequence with a veto point, not an event that fires and hopes.
- Where platform conventions differ, each platform gets its own behavior rather than the developer's own platform winning by default.
