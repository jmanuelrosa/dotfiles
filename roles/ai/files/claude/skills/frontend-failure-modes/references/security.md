# Browser-side security

When to read: the brief or diff touches rendering of user- or API-supplied content, authentication state or tokens, redirects, embeds and third-party scripts, or cross-window messaging.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Injected HTML.** `dangerouslySetInnerHTML`, `v-html`, or `innerHTML` with anything not statically authored is XSS; sanitizer bypasses are rediscovered every year.
  Check: user- and API-supplied content renders as text through the framework's escaping; any raw-HTML path goes through the project's sanctioned sanitizer with an allowlist and a stated reason.
- **Tokens where scripts can read them.** Long-lived tokens in localStorage are exfiltrated by any XSS on any page; auth material in URLs leaks through history, referrers, and logs.
  Check: follow the project's existing auth storage pattern exactly; never move tokens into storage, query strings, or client-readable state for convenience.
- **Client-side authorization theater.** Hiding a button while leaving the route and API callable, or trusting a client-held role flag, protects nothing.
  Check: UI hiding is UX, not security; every privileged action is enforced server-side, and the UI handles the 403 as a designed state.
- **Open redirect.** Navigating to a URL taken from a query parameter or API response without validation turns your login flow into a phishing vector.
  Check: redirect targets validate against an allowlist or same-origin relative paths only, and dangerous protocols like `javascript:` are rejected.
- **Tabnabbing through new tabs.** A link to user-supplied or third-party destinations opened in a new tab without `rel` protection hands the target window a handle on yours.
  Check: `target="_blank"` carries `rel="noopener noreferrer"` whenever the destination is not fully trusted.
- **Input interpolated into requests.** User input concatenated into request URLs or query documents breaks or gets weaponized on the first special character.
  Check: parameters go through URL and search-params APIs; GraphQL uses variables, never string interpolation.
- **Secrets in the bundle.** Anything in client code or client-exposed env vars is public the moment it ships; public-prefix env conventions make this easy to do by accident.
  Check: nothing secret enters client code or env; keys the client genuinely needs are scoped as public by design; everything else proxies through the backend.
- **Third-party code with full authority.** A new script tag or embed runs with the page's whole authority: reading storage, watching input.
  Check: third-party additions are ask-first; iframes carry `sandbox` and minimal `allow`; static third-party scripts get integrity attributes where feasible.
- **postMessage without origin checks.** A message listener that accepts any origin lets any page that can reach yours drive it.
  Check: every listener validates `event.origin` against an allowlist and validates the payload shape before acting.
- **PII in client persistence and telemetry.** Personal data in localStorage, analytics payloads, or session replay outlives the session and violates policy silently.
  Check: nothing sensitive persists client-side without an explicit decision; analytics carry IDs, not personal data; replay masking survives your change.

## Escalation triggers (`needs-decision`)

- Any change to authentication or token handling (also an ask-first boundary in the agent).
- A feature that must render user-supplied rich content (HTML, markdown that allows HTML, uploaded SVG).
- Adding a third-party script, embed, or origin, or loosening CSP or sandbox restrictions (also dependency ask-first in the agent).

## What good looks like

- User content is data, never markup; the sanitizer allowlist is short and owned.
- The client holds no secret whose exposure would matter; privileged decisions live server-side.
- Third-party code is a deliberate, least-privilege decision with the smallest reachable surface.
