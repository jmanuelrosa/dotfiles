# Custom templates

When to read: the brief or diff touches custom tag, client, or variable templates: their permissions, sandboxed APIs, injected script, or template tests.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Over-broad permissions.** A template requests permissions wider than it uses (inject any script, read all cookies, access globals, send to any URL), so a careless or compromised template reaches far beyond its job.
  Check: every declared permission is scoped to the minimum (specific inject URLs, named cookies, specific request domains); unused permissions are removed.
- **Unvalidated template input.** Template fields become URLs, script sources, or request targets without validation, letting a misconfiguration point at an arbitrary endpoint or script.
  Check: inputs that become URLs or script sources are validated against an allowlist or fixed format; `injectScript` URLs are not free-form from a field.
- **No template tests.** A custom template ships with no `runTemplateTests` cases, so permission regressions and logic breaks surface only in production.
  Check: `runTemplateTests` covers the main path, the consent-denied path, and malformed input, asserting the security-relevant calls (for example that a pixel is not sent before consent), and runs green in the template editor.
- **Sandbox API misuse.** Reaching for `injectScript` or `accessGlobals` when a sandboxed API exists (`sendPixel`, `setCookie`, `sendHttpRequest`) enlarges the trust surface for no reason.
  Check: the narrowest sandboxed API that does the job is used; direct DOM or global access is a last resort with a stated reason.
- **Standard JS in the sandbox.** GTM templates run in sandboxed JavaScript, not the browser: `fetch`, `localStorage`, `document`, and Node `require` do not exist and fail as silent no-ops with no useful error.
  Check: only the template's own `require`'d APIs are used (`sendPixel`, `injectScript`, `setCookie`, `sendHttpRequest`, `getEventData`, `templateDataStorage`); banned browser and Node identifiers are absent.
- **Gallery template trusted blindly.** A community gallery template is added without reading its permissions or code, importing its data access into the container.
  Check: gallery templates are reviewed for requested permissions and destinations before use, like any third-party dependency.
- **Consent ignored inside the template.** A template fires its pixel or request without checking the consent state available to templates, bypassing container-level gating.
  Check: templates that transmit data honor the consent state (consent APIs or a gating input), not just the tag's trigger.
- **Personal data handled in clear.** A template logs its inputs or forwards raw personal data because hashing or redaction was left for later.
  Check: templates hash or omit personal data as the destination requires; template inputs carrying personal data are not logged.
- **Tag status never reported.** `gtmOnSuccess` and `gtmOnFailure` are not both reachable on every path (an `injectScript` failure, an HTTP non-2xx), so the tag hangs pending and sequencing stalls.
  Check: every code path ends by calling exactly one of `gtmOnSuccess` or `gtmOnFailure`.

## Escalation triggers (`needs-decision`)

- Adding a gallery or third-party template that requests broad data-access permissions (also an ask-first boundary in the agent).

## What good looks like

- Least-permission templates using the narrowest sandboxed APIs, inputs validated before they become URLs or scripts.
- `runTemplateTests` covering happy, consent-denied, and malformed-input paths, green before ship.
- Gallery templates vetted like dependencies; consent honored inside the template.
