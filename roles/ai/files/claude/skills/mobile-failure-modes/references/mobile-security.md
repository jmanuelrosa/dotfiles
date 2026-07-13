# Mobile security

When to read: the brief or diff touches secrets and tokens, sensitive data at rest, webviews, exported entry points, or transport security.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Secrets in the bundle.** A key in code, config, or the script bundle is extractable from any shipped binary in minutes; obfuscation only changes the minutes.
  Check: nothing in the diff embeds a secret the backend should hold; any key the client must carry is treated as public and scoped server-side accordingly.
- **Sensitive data in plain storage.** Tokens and personal data in plain key-value stores or files are readable on rooted devices and in backups; the platform keystore exists for exactly this (OWASP MASVS-STORAGE).
  Check: sensitive data at rest uses the platform secure store with a deliberate protection class, and nothing sensitive lands in plain preferences "temporarily".
- **Sloppy session lifecycle.** Tokens that never rotate, refresh tokens in insecure storage, or an account switch that reuses the previous session's state.
  Check: token storage, rotation, and invalidation-on-logout follow the project's existing auth pattern, and account switch provably cannot reuse prior session state.
- **Webview as a hole.** A webview loading remote content with a script bridge exposed, arbitrary URL loading, or file access enabled is remote code inside your app (OWASP MASVS-PLATFORM).
  Check: webviews load allowlisted origins only, bridges expose the minimal API, and file or universal access stays off unless the brief justifies it.
- **Exported surfaces by accident.** Components, schemes, and handlers reachable by other apps, with input nobody validates, are a public API you never meant to publish.
  Check: new entry points are unexported by default; anything exported validates its caller and its input.
- **Transport security weakened for convenience.** A cleartext exception or a trust-all certificate hack added "for dev" ships to release and silences the platform's protections (OWASP MASVS-NETWORK).
  Check: no cleartext or trust-relaxing config reaches release builds; adding or changing certificate pinning is escalated, not decided in-flight, because a botched pin bricks the app until the next store release.
- **Leaky input surfaces.** Secret fields that allow copy, feed third-party keyboard learning, or echo into logs put credentials in places the app does not control.
  Check: secret fields use secure text entry, exclude sensitive values from logs and autocomplete-learning, and clipboard exposure of secrets is a decision, not a default.
- **Sensitive data on system surfaces.** Notifications, share sheets, widgets, and search indices render app content outside the app, including on the lock screen.
  Check: system-visible surfaces show minimal content for sensitive data, and lock-screen visibility is chosen, not inherited.
- **Client-side trust.** A security decision enforced only in the app (feature gates, price checks, entitlement checks) is enforced nowhere, because the client is the attacker's machine.
  Check: every trust decision in the diff has a server-side enforcement point; client checks are UX, not security.

## Escalation triggers (`needs-decision`)

- Adding attestation, anti-tamper, or root/jailbreak detection (an architecture and false-positive decision).
- Adding or changing certificate pinning, or relaxing any transport-security setting.
- Introducing a webview with a script bridge where none existed.

## What good looks like

- The app assumes its binary and its traffic are public and inspectable.
- Anything sensitive at rest sits behind the platform secure store; anything sensitive in transit rides the platform's TLS defaults or stricter.
- The server enforces every rule the app displays.
