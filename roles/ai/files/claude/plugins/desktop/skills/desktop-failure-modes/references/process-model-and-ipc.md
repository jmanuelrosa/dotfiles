# Process model and IPC

When to read: the brief or diff touches the main, renderer or preload split, a preload bridge, a Tauri command or capability, an XPC or helper process, or any message crossing a process boundary.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Isolation and sandboxing treated as one switch.** Context isolation separates the preload's JavaScript world from the page; the sandbox is the OS-level restriction on the process itself. Disabling the sandbox, or enabling Node integration, removes the second while the first still reads as correctly configured in the diff.
  Check: no renderer setting in the diff disables the sandbox, enables Node integration, disables web security, or turns on experimental features; each is a separate boundary, and one that is off is an escalation rather than a comment in the diff.
- **The bridge exposes a mechanism instead of an API.** Three shapes of the same defect: handing the renderer the messaging object itself, exposing a send function whose channel the caller chooses, and forwarding the raw event object into a renderer callback, which leaks the sender and with it the whole messaging surface.
  Check: the exposed surface is a fixed set of named verbs on fixed channels; no exposed function takes a channel, path, command, or method name from the caller, and no callback receives the raw event.
- **Privileged handler trusts its arguments.** The main process treats a message from a renderer as trusted because it came from its own app, so a compromised or injected renderer reaches the filesystem, the shell, or the network through it.
  Check: every privileged handler validates the shape, type and range of its arguments, and resolves paths and identifiers against an allowlist rather than using them as given.
- **Sender identity never checked.** A handler serves any frame that can reach it, including a nested iframe, a webview, or a window showing remote content.
  Check: handlers that matter assert which window or frame they will answer, rather than answering whatever arrives.
- **A path crosses the boundary as a string.** The renderer names a file and the main process opens it, so directory traversal and symlink tricks turn a UI action into arbitrary read or write.
  Check: file selection produces a handle, token, or bookmark on the privileged side; where a path must cross, it is canonicalized and confirmed to sit inside an allowed root.
- **Synchronous IPC on an interaction path.** A blocking cross-process call inside render, scroll, or input handling stalls the exact thread that must stay free, and the freeze is attributed to the whole app.
  Check: cross-boundary calls on hot paths are asynchronous or batched; anything synchronous is justified and bounded.
- **Handlers accumulate per window.** Registering listeners when a window opens without removing them when it closes leaks memory and leaves handlers answering for windows that are gone.
  Check: every registration in the diff has a teardown tied to the lifetime of what registered it.
- **Helper process failure is invisible.** A crashed or unresponsive helper, worker, or XPC service leaves the UI waiting forever with no error and no restart.
  Check: the diff handles the helper dying: a timeout, a user-visible failure state, and a restart or degraded path.
- **A capability attached to the wrong windows.** Capability files (Tauri) key off window labels, so a wildcard, a stale label, or a capability carrying remote origins grants its whole permission set to contexts never meant to hold it, and a window named by two capabilities receives the union of both.
  Check: a new capability names specific window labels rather than a wildcard, states its platforms where the permission is platform-specific, and adds remote origins only with a justification.
- **A privileged command shipped without a scope.** In Tauri's model permissions decide which commands the frontend may call and scopes decide what those commands may reach, so a filesystem or network command with a permission and no scope is the primitive itself handed to the webview.
  Check: every new command exposed to the frontend carries a scope bounding the paths, URLs, or resources it may touch, and validation lives in the command rather than only in an interception layer, which cannot make an unsafe command safe.

## Escalation triggers (`needs-decision`)

- Widening a capability allowlist or a scoped permission the feature genuinely requires (also an ask-first boundary in the agent, so the caller may approve it).
- Disabling context isolation, Node-integration or sandbox settings, whatever the dependency requires: this escalates and stays refused, because it is in the agent's never tier rather than its ask-first tier.
- Adding a new privileged operation to the bridge or command surface, or a new helper or background process.

## What good looks like

- The privileged side treats every message as attacker-controlled, because one day it will be.
- The exposed surface is small, named, and shaped: an audit can read it in one sitting and enumerate everything the renderer can cause.
- Process boundaries are also failure boundaries: each side handles the other dying.
