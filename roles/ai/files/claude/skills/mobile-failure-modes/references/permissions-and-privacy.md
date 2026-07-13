# Permissions and privacy

When to read: the brief or diff touches OS permissions, tracking and consent, data collection, store privacy declarations, or third-party SDKs that collect data.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Protected API without its declaration.** Accessing a guarded capability (camera, location, contacts, photos, notifications...) without the platform declaration, runtime request, or usage string crashes at runtime on one platform and fails review on the other; notifications are a runtime permission too on current OS versions.
  Check: every protected API in the diff has its manifest entry or usage description, written as a real purpose, not a placeholder.
- **Denial treated as an error.** Permission denied leaves the feature blank or broken, or the app re-prompts into a dead end because the platform only asks once.
  Check: denied and permanently-denied paths degrade the feature usefully and route to system settings only as a deliberate step.
- **Prompt before context.** Asking for a permission at first launch, before the user knows why, burns the one meaningful chance to ask.
  Check: requests fire at the moment of use, preceded by rationale UI where the platform idiom expects it.
- **Declaration and collection drift.** The code (or a bundled SDK acting on its own) collects data the store privacy declaration does not cover; the mismatch is a rejection or a listing takedown.
  Check: new data collection, and every new SDK's own collection, is reflected in the privacy manifest and data-safety declarations, including required-reason API declarations where the platform demands them.
- **Tracking before consent.** Identifiers, analytics, or ad SDKs fire at cold start, before the consent state is known or against a recorded "no".
  Check: every collection path gates on the app's consent state at the moment of send; denial suppresses collection, it does not just get stored.
- **Purpose creep on a granted permission.** An already-granted permission gets reused for a new purpose the original rationale never covered.
  Check: the new use matches the declared purpose, or it goes through a new consent and declaration pass.
- **Background access surprise.** Location, microphone, or camera use continues in the background, lighting the OS indicator and triggering policy scrutiny the feature never needed.
  Check: background access is intentional, separately declared, and minimal; foreground-only is the default.
- **PII in telemetry.** Names, emails, tokens, or location leak into logs, crash context, or analytics payloads and outlive every retention promise.
  Check: telemetry paths in the diff carry no direct identifiers; crash and analytics context is scrubbed by construction.

## Escalation triggers (`needs-decision`)

- Adding a permission, a tracking or analytics SDK, or a new data-collection category (also an ask-first boundary in the agent).
- Changing consent-flow semantics or the meaning of an existing consent state.
- Any collection that would change the store privacy declarations.

## What good looks like

- Every declared datum maps to code that needs it, and nothing collected is undeclared.
- Consent state is a single source of truth that collection paths consult at send time.
- The app is fully usable in its degraded form by a user who denies everything.
