---
name: desktop-failure-modes
description: >-
  Failure-mode checklists for desktop application work, split by domain.
  Use when implementing or reviewing changes that touch window and lifecycle behavior, the process
  and IPC model, code signing and sandboxing, packaging and auto-update, resource use, local data
  and migrations, OS integration and permissions, native UI and accessibility, error resilience,
  or crash visibility. Read only the reference files whose triggers match the change.
---

# Desktop failure modes

Checklists of the ways desktop application changes go wrong on a user's machine, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

Two asymmetries generate most of what follows, and neither has an equivalent on the web or on mobile.
**The app is its own store.** It self-distributes and self-updates, so there is no review before release and no store-side rollback, and the signing key is a single point of total failure: lose it and the installed fleet can never be updated again.
**Sessions last weeks.** A per-window or per-session leak that a page navigation or an app suspension would have swept away is, here, the normal failure.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Window creation or geometry, multi-window behavior, quit and close paths, tray or menu-bar or dock presence, multiple displays, sleep and wake | [references/windows-and-lifecycle.md](references/windows-and-lifecycle.md) |
| The main, renderer or preload split, a preload bridge, a Tauri command or capability, an XPC or helper process, any message crossing a process boundary | [references/process-model-and-ipc.md](references/process-model-and-ipc.md) |
| Remote content or navigation, custom protocol and URL handlers, entitlements, sandbox or hardened-runtime settings, a local listening port, bundled credentials, signing and notarization | [references/desktop-security.md](references/desktop-security.md) |
| Installer or bundle configuration, the auto-update path, release channels, version numbers, signing key handling, first-run and uninstall behavior | [references/packaging-and-distribution.md](references/packaging-and-distribution.md) |
| The launch path, work on the UI thread, long-lived caches or subscriptions, recurring or background work, rendering and GPU use, anything called slow or heavy | [references/performance-and-resources.md](references/performance-and-resources.md) |
| Where the app stores data, a persisted format or schema, a local database or preference store, cache handling, anything read at launch | [references/local-data-and-migrations.md](references/local-data-and-migrations.md) |
| An OS permission prompt, file access outside the app's own directories, notifications, login items or background helpers, the clipboard, drag and drop, global shortcuts, file-type or URL-scheme associations | [references/os-integration-and-permissions.md](references/os-integration-and-permissions.md) |
| New or changed UI, menus and keyboard shortcuts, custom-drawn controls, colors and system appearance, user-visible text, window sizing behavior | [references/native-ui-and-accessibility.md](references/native-ui-and-accessibility.md) |
| Any new user flow; error handling, unsaved work, quit or restart paths, retries, anything that depends on the network | [references/errors-and-resilience.md](references/errors-and-resilience.md) |
| Any new window, flow, helper process, or background task; crash reporting, logging, symbol upload, telemetry and consent | [references/failure-visibility.md](references/failure-visibility.md) |

Most real changes fire two or three rows (a typical feature-window brief fires at least windows-and-lifecycle, native-ui-and-accessibility, and errors-and-resilience).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks on a user's machine, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: framework- and toolchain-specific guidance belongs to the stack skills the caller has installed, not here.
