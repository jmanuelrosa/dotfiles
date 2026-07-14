# Navigation and deep links

When to read: the brief or diff touches deep links, universal or app links, navigation flows, auth-gated screens, back behavior, or screens opened from a push notification.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Unvalidated link parameters.** IDs, URLs, and flags arriving in a deep link are attacker-supplied input; used raw they navigate to other users' content or inject into whatever consumes them.
  Check: every link parameter is validated and authorized like server input, and unrecognized links route to a safe fallback screen, never a crash or a blank.
- **Auth bypass via link.** A link or push opens an auth-gated screen before session state resolves, or relies on the tab root having checked auth earlier.
  Check: gated destinations re-check auth on entry, and unauthenticated link opens park the destination until after login.
- **Cold-start link loss.** The link works while the app is running but is dropped or mishandled when it also has to boot the app.
  Check: warm and cold entry paths both handle the link, and the cold-start path is exercised explicitly.
- **Back-stack corruption.** A deep-link destination lands with an empty or foreign back stack; back exits the app, repeats the screen, or reveals another flow's state.
  Check: link destinations construct a deliberate parent stack, and back from them goes where a user would expect.
- **Double navigation.** A double-tap or a push racing a link pushes the same screen twice or interleaves two flows.
  Check: navigation actions are idempotent or debounced; a second identical request is a no-op.
- **Restoration-unsafe routes.** A route whose parameters cannot be serialized breaks state restoration after process death, crashing on resume.
  Check: every route's parameters are serializable and restoring any screen with saved parameters yields a working screen.
- **Shipped link formats broken.** URL formats already printed in emails, QR codes, and push payloads are immutable; a format change orphans them all.
  Check: existing link formats keep resolving; new formats are additive, never replacements.
- **Scheme-only trust.** Custom URL schemes can be claimed by other apps; a sensitive flow (auth callback, payment result) trusting a scheme-only link can be hijacked.
  Check: sensitive callbacks use verified app or universal links backed by the domain association file, and the association config matches every link the code claims and stays in sync when app identifiers or signing certificates change (a mismatch silently falls back to the browser).

## Escalation triggers (`needs-decision`)

- Changing a deep-link URL format or push payload contract already shipped in old binaries (also an ask-first boundary in the agent).
- Adding a new externally invokable entry point (new scheme, new exported handler).

## What good looks like

- Links are treated as untrusted input that happens to arrive via the OS.
- Every destination guards itself; no screen's safety depends on how it was reached.
- Back behavior after any entry path looks designed, not accidental.
