# OS integration and permissions

When to read: the brief or diff touches an OS permission prompt, file access outside the app's own directories, notifications, login items or background helpers, the clipboard, drag and drop, global shortcuts, or a file-type or URL-scheme association.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Permission requested before it means anything.** A prompt at first launch, with no action behind it, is denied by reflex, and on several platforms the app cannot ask a second time from inside itself. The surface is also wider than it looks: reaching the local network for discovery, multicast, or a direct address now prompts on current macOS, which catches sync and LAN features that never thought of themselves as permissioned.
  Check: each permission is requested at the moment a user action needs it, with the reason visible in the app's own words first, and the diff accounts for any new local-network or discovery traffic as a prompt.
- **A prompt that cannot appear.** A protected capability needs its usage description, its entitlement, and an intact signature on the bundle; missing any one of them produces a silent denial rather than an error, and editing the bundle after signing is enough to cause it.
  Check: a diff adding a protected capability adds the usage string and the entitlement together, and nothing modifies the bundle after it is signed.
- **Denial treated as impossible.** The permission-granted path is written and the denied path is a crash, a hang, or a feature that silently does nothing.
  Check: every permission-gated path has a working denied branch that says what is unavailable and how to grant it in system settings.
- **File access assumed to survive relaunch.** A path the user chose in an open panel is not accessible on the next launch under a sandbox, so recent documents quietly stop opening. Two further failures follow: a bookmark goes stale when the file moves or its volume reconnects and cannot be refreshed from a path alone, and starting scoped access without a paired stop leaks a kernel resource until the app can add no new location at all.
  Check: access outside the app's own directories is persisted as a scoped bookmark, every start of scoped access has a matching stop on every exit path, and the stale case re-prompts the user rather than failing silently.
- **The app answering a permission prompt on the user's behalf.** Content rendered in the app can request camera, microphone, location, or notifications, and without an explicit handler the framework may grant them without the user ever being asked.
  Check: a permission-request handler is installed and denies by default, allowing only the specific permissions the app's own UI asked for.
- **Reaching beyond what the user selected.** Enumerating a directory the user did not pick, or writing beside their document, exceeds the access granted and trips the platform's privacy machinery at the worst moment.
  Check: the diff touches only what the user chose; derived and temporary files go to the app's own directories unless the user named the destination.
- **A helper installed on the machine without consent.** Registering to launch at login, or installing a background agent or daemon, changes the user's machine in a way that outlives closing the app, and modern registration is a request the user can decline or revoke from system settings rather than a state you set.
  Check: launch-at-login and background helpers are opt-in, the code reads the service status back instead of assuming registration succeeded and degrades when it is not enabled, and everything installed is removed on uninstall, including agents that would otherwise keep running a binary the update moved.
- **Notifications used as a channel.** Repeated, uncoalesced, or non-actionable notifications train the user to turn them off, taking the important ones with them.
  Check: each notification corresponds to something the user asked to be told, is coalesced rather than repeated, and respects focus and do-not-disturb state.
- **Data from another application treated as your own.** A path, URL, or serialized object arriving by drop or paste was produced by something outside your process and reaches a privileged handler unvalidated; on the write side, the general clipboard is readable by every app on the machine and may sync to the user's other devices.
  Check: dropped and pasted payloads are validated by type and content, a dropped path is treated exactly as a path from an untrusted source, reads happen only in response to an explicit user action rather than on focus or a timer, and nothing sensitive is written to the general clipboard.
- **Global input capture left registered.** A system-wide hotkey or input monitor requires elevated permission, collides with other applications, and keeps working after the window is gone.
  Check: global shortcuts are user-configurable, registered only while needed, released on quit, and a failed registration is surfaced rather than swallowed.

## Escalation triggers (`needs-decision`)

- Adding an OS permission, a login item, a background agent or daemon, or any global input capture (also an ask-first boundary in the agent).
- Registering a file-type or URL-scheme association the app did not previously claim (also an ask-first boundary in the agent).

## What good looks like

- Permissions are asked for at the point of use, explained in the app's own words first, and denial is an ordinary state with a route forward.
- Nothing the app installs on the machine outlives the user's intent to have it there.
- Anything arriving from another application, by drop, paste, or association, is untrusted input.
