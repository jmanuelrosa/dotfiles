# Client Code and Third-Party Scripts

When to read: the brief, diff, or assessed surface touches browser JavaScript or TypeScript, DOM rendering, eval-like APIs, postMessage, third-party or vendor scripts, tag managers and data layers, Subresource Integrity, micro-frontend composition (Module Federation, remotes, iframes, Web Components), browser extensions (manifest, content scripts, background service workers), or client-side storage of tokens.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Third Party JavaScript Management](https://cheatsheetseries.owasp.org/cheatsheets/Third_Party_Javascript_Management_Cheat_Sheet.html), [Web Frontend Security](https://cheatsheetseries.owasp.org/cheatsheets/Web_Frontend_Security_Cheat_Sheet.html), [Micro-Frontend Security](https://cheatsheetseries.owasp.org/cheatsheets/Micro_Frontend_Security_Cheat_Sheet.html), [Browser Extension Vulnerabilities](https://cheatsheetseries.owasp.org/cheatsheets/Browser_Extension_Vulnerabilities_Cheat_Sheet.html), [JavaScript and TypeScript Security](https://cheatsheetseries.owasp.org/cheatsheets/JavaScript_and_TypeScript_Security_Cheat_Sheet.html)

## Contents

- Client-side trust and server-side enforcement
- Third-party scripts and tag managers
- Micro-frontend boundaries and remote code
- Cross-window and cross-application messaging
- DOM sinks and dynamic code execution
- Object safety and prototype pollution
- Browser extensions
- Server endpoints called by browser code
- Language hygiene, TypeScript and tooling

## Client-side trust and server-side enforcement

- **Security decision made only in client code.** The user controls client logic (breakpoints, skipped code, changed values), so authorization, security checks and important business rules must be enforced on the server; route guards, hidden controls and client role checks only affect presentation. When a security decision is ambiguous, perform it on the server.
  Check: every client-side permission or business-rule check has a matching server-side check on the endpoint it gates. Owner: `backend`. Source: Web Frontend Security, Micro-Frontend Security.
- **Role, tenant or permission flag trusted from the frontend.** Every backend request must authorize the operation, resource and tenant itself, regardless of which shell or remote initiated it; a role, tenant id or permission flag supplied by the client is not trusted. A shared server-side policy keeps independently developed features consistent.
  Check: handlers derive role and tenant from the authenticated session, not request fields set by the client. Owner: `backend`. Source: Micro-Frontend Security. See `authorization.md` for per-request authorization design.
- **Secrets shipped to the client.** Anything sent to the browser can be read or modified, so API keys, credentials and other secrets stay on the server; never hardcode them in client or extension bundles.
  Check: bundled code, public env variables and extension sources contain no keys or credentials. Owner: `frontend`. Source: Web Frontend Security, Browser Extension Vulnerabilities.
- **All data treated as trusted by default.** Client input, API responses, third-party integrations, internal services, cached responses, browser storage and hidden form fields are untrusted until explicitly validated and safely handled.
  Check: data read from APIs, storage or hidden fields is validated before use in sinks or logic. Owner: `frontend`. Source: Web Frontend Security.
- **Session identifiers or upstream tokens in web storage.** Keep session identifiers out of `localStorage` and `sessionStorage`; with a backend-for-frontend, keep upstream access tokens on the server and use a properly configured session cookie, with CSRF protection on cookie-authenticated operations. `HttpOnly` stops token reading, not authenticated requests made by compromised in-page code.
  Check: no token or session id is written to web storage; BFF holds upstream tokens server-side. Owner: `frontend`. Source: Micro-Frontend Security. See `sessions-and-cookies.md` for cookie attributes.
- **Homemade client-side cryptography.** Use TLS for transport; client-side encryption is appropriate only for end-to-end or encrypt-before-upload cases, using reviewed protocols and implementations, and it does not protect plaintext or keys from malicious code in the page.
  Check: client crypto uses a reviewed library or Web Crypto with a documented threat model and key management. Owner: `frontend`. Source: Web Frontend Security.

## Third-party scripts and tag managers

- **Third-party script without integrity pinning.** Vendor JavaScript can change or be compromised at any time and runs with the user's privileges; mirror scripts in-house where practical, load over HTTPS, and pin Subresource Integrity (`integrity` plus `crossorigin`; the vendor must enable CORS) so only reviewed code executes. Monitor vendor scripts for changes, since an update can break a pinned integration.
  Check: every external `<script>` from a CDN or vendor carries an `integrity` hash and `crossorigin`, or is self-hosted. Owner: `frontend`. Source: Third Party JavaScript Management, JavaScript and TypeScript Security.
- **Vendor code pasted into the page unreviewed.** Vendor JavaScript placed on the host page must be reviewed for XSS and for exfiltrating DOM data to other sites, which is hard when obfuscated.
  Check: vendored inline scripts are reviewed and their source recorded. Owner: `frontend`. Source: Third Party JavaScript Management.
- **Tag manager allowed custom HTML or JavaScript tags.** Tag manager containers execute remotely managed code inside the page's trust boundary; restrict tag types (disable custom HTML and JavaScript tags), limit tags to data-layer values, restrict publishing access (with two-factor authentication) and review changes as application code.
  Check: tag manager configuration disables custom HTML/JS tags and publishing is limited to named reviewers. Owner: `gtm`. Source: Third Party JavaScript Management.
- **Tags reading unvalidated DOM or URL values.** Tag logic that reads URL parameters or input fields and writes them into a scriptable location causes XSS; tags should read only a host-defined data layer, never URL parameters, and the data layer must validate values taken from user-exposed DOM sources. A data layer limits collected data but is not a sandbox.
  Check: tag variables reference data-layer keys only; data-layer population validates URL- and input-derived values. Owner: `gtm`. Source: Third Party JavaScript Management.
- **Analytics executed in the browser when it need not be.** For analytics that do not need browser execution, send a fixed event schema to a collector you control and run vendor integrations server-side, which filters what vendors receive; audit the scripts actually loaded before claiming only first-party code runs.
  Check: new analytics integrations use the server-side collector unless browser execution is required; script inventory matches what the page loads. Owner: `gtm`. Source: Third Party JavaScript Management.
- **Untrusted vendor script running in the host page.** Where integrity pinning is impractical, run vendor code in an iframe on a separate domain with the `sandbox` attribute, communicating via origin-checked `postMessage`; for high-risk applications add CSP on top of the sandbox. Virtual iframe containment is another option.
  Check: high-risk vendor scripts load inside a sandboxed cross-domain iframe rather than the main document. Owner: `frontend`. Source: Third Party JavaScript Management.
- **Untrusted HTML from vendors or users inserted unsanitized.** Sanitize DOM data with a maintained sanitizer (or a JavaScript sandbox) before it reaches the page.
  Check: vendor- or user-supplied HTML passes through a sanitizer before insertion. Owner: `frontend`. Source: Third Party JavaScript Management.
- **Outdated client-side libraries.** JavaScript libraries must be kept up to date because old versions carry known XSS and other vulnerabilities.
  Check: frontend dependency manifests have automated update and known-vulnerability scanning. Owner: `dx`. Source: Third Party JavaScript Management, Browser Extension Vulnerabilities. See `supply-chain-and-dependencies.md` for dependency management.
- **No contractual control over vendor script integrity.** Contracts with marketing technology vendors should require evidence of secure coding, server access security and monitoring of their source code for malicious changes, and may carry penalties for serving malicious JavaScript; penetration testing requirements should include client-side malicious script behavior.
  Check: vendor onboarding records include code-integrity evidence. Owner: `security`. Source: Third Party JavaScript Management.

## Micro-frontend boundaries and remote code

- **Remote assumed sandboxed because it loads from another origin.** Remote JavaScript (including Module Federation), Web Components and server- or edge-assembled fragments all run with the host page's privileges; Shadow DOM, separate repos and download origins are not isolation. Document each micro-frontend's origin, deployment owner and data access before choosing composition, and isolate a less-trusted feature in a cross-origin iframe on a dedicated origin.
  Check: each remote is listed with owner and trust level; less-trusted features load in a cross-origin iframe, not as in-page modules. Owner: `architect`. Source: Micro-Frontend Security.
- **Iframe sandbox over-granted.** Grant only the sandbox capabilities the feature needs, leave top-navigation and popups off unless necessary, and never combine `allow-scripts` with `allow-same-origin` for content on the host's own origin, since the frame can then remove its sandbox.
  Check: `sandbox` attributes list minimal tokens and do not pair `allow-scripts` with `allow-same-origin` for same-origin content. Owner: `frontend`. Source: Micro-Frontend Security.
- **Remote URL chosen by untrusted input.** Load only approved HTTPS remote URLs from host-controlled configuration; query parameters or other untrusted input must never select executable code.
  Check: remote entry URLs come from build-time or server config, not from location or request data. Owner: `frontend`. Source: Micro-Frontend Security.
- **Mutable or unreviewed remote releases.** Hosts should select immutable, reviewed releases covering the entry script and all dependent chunks, keep a known-good release for rollback, apply SRI where the loader supports it (verifying coverage of dynamically loaded chunks) and apply the host CSP to remote loading. Integrity and CSP verify bytes and sources, not behavior.
  Check: remote manifest pins versioned immutable URLs with integrity for entry and chunks; rollback target is defined. Owner: `frontend`. Source: Micro-Frontend Security.
- **Shared deployment credentials across shell and remotes.** Use separate deployment credentials for the shell and each remote, since permission to publish a remote is permission to change the host application.
  Check: CI pipelines for each remote use distinct, scoped deploy credentials. Owner: `platform`. Source: Micro-Frontend Security. See `ci-cd.md` for pipeline credential scoping.
- **Sensitive state shared across in-page features.** Storage key prefixes, separate stores and component boundaries do not isolate scripts in one page; treat page data and origin storage as visible to every remote, return only data the user is authorized for, and clear shared state and cached responses on logout or tenant change.
  Check: logout and tenant-switch flows clear shared stores and caches; no credentials sit in shared state. Owner: `frontend`. Source: Micro-Frontend Security.

## Cross-window and cross-application messaging

- **`postMessage` receiver without origin and source checks.** Receivers must match `event.origin` exactly against an allowlist, check `event.source` against the expected frame's `contentWindow` or parent (several frames can share an origin), and validate `event.data` against the expected schema; an opaque `"null"` origin must never be trusted as a sender identity.
  Check: every `message` listener compares `event.origin` to a fixed allowlist, checks `event.source`, and validates the payload. Owner: `frontend`. Source: Micro-Frontend Security, JavaScript and TypeScript Security, Third Party JavaScript Management.
- **`postMessage` sent with `targetOrigin` `"*"`.** Senders must pass an exact `targetOrigin`, never `"*"` for sensitive data; prefer narrow `MessageChannel` ports over broadcast messaging.
  Check: no `postMessage` call with sensitive data uses `"*"`. Owner: `frontend`. Source: JavaScript and TypeScript Security, Micro-Frontend Security.
- **Broad message contract between features.** Define a small per-pair contract accepting only needed message types and fields, pass the minimum data, avoid broadcasting credentials or sensitive state, and route privileged operations to server-side authorization; an in-page event bus has no identity boundary, so event names or app ids are not proof of authority.
  Check: message handlers allowlist types; no handler performs privileged actions based on message claims alone. Owner: `frontend`. Source: Micro-Frontend Security. See `cross-origin-and-browser.md` for general web messaging rules.

## DOM sinks and dynamic code execution

- **Untrusted data assigned to `innerHTML`.** Never use `innerHTML` or `insertAdjacentHTML` with untrusted data; use `textContent` (or `innerText` only when rendered formatting matters) and `createElement`. `innerHTML` is acceptable only for static hardcoded markup or HTML sanitized with a maintained allowlist sanitizer, ideally enforced with Trusted Types without a permissive default policy. Text APIs do not protect attribute, event-handler or URL contexts.
  Check: `innerHTML`/`insertAdjacentHTML` assignments take only constants or sanitizer output. Owner: `frontend`. Source: Web Frontend Security, JavaScript and TypeScript Security, Browser Extension Vulnerabilities.
- **Framework escaping bypass fed untrusted input.** React `dangerouslySetInnerHTML`, Vue `v-html` and Angular `bypassSecurityTrustHtml` and siblings must never receive untrusted input; prefer framework text bindings or auto-escaping templates, and give URL and style bindings context-appropriate controls.
  Check: every raw-HTML binding receives sanitized or constant content. Owner: `frontend`. Source: Web Frontend Security, JavaScript and TypeScript Security. See `xss-and-csp.md` for per-context encoding and DOM XSS.
- **String compiled as code.** Never use `eval`, `new Function`, string arguments to `setTimeout`/`setInterval`, or `with`; parse data with `JSON.parse` and replace dynamic dispatch with static function maps. Enforce with `no-eval`, `no-implied-eval` and `no-new-func` lint rules everywhere, and in browsers with an enforced CSP whose `script-src` (or `default-src`) omits `'unsafe-eval'` and `'trusted-types-eval'` (report-only does not block).
  Check: lint config enables the three rules; enforced CSP lacks `unsafe-eval`; no string-to-code calls in the diff. Owner: `frontend`. Source: Web Frontend Security, JavaScript and TypeScript Security, Browser Extension Vulnerabilities.
- **Output built without context encoding.** Data used to build HTML, script, CSS, XML or JSON must be encoded for that output context; do not build XML or JSON by hand, use a safe serialization library.
  Check: no string concatenation builds markup or JSON from untrusted values. Owner: `frontend`. Source: Web Frontend Security.

## Object safety and prototype pollution

- **Untrusted keys reaching a recursive merge or path setter.** Never pass untrusted input to recursive merge or set-by-path helpers, and reject `__proto__`, `constructor` and `prototype` key segments before writing.
  Check: merge and set-by-path utilities filter those keys or are not fed request or message data. Owner: `backend`, `frontend`. Source: JavaScript and TypeScript Security. See `xss-and-csp.md` for full prototype pollution prevention.
- **Plain objects used as untrusted dictionaries.** Use `Map` for untrusted keys, or `Object.create(null)` when an object is required; validate parsed untrusted data against a schema and drop `__proto__` keys first, since `Object.assign` mutates the target prototype through them.
  Check: dictionaries keyed by user input are `Map` or null-prototype objects; schema validation precedes `Object.assign` or spread. Owner: `backend`, `frontend`. Source: JavaScript and TypeScript Security.

## Browser extensions

- **Extension requests broad permissions.** Request only necessary permissions, prefer optional permissions, declare URL access in `host_permissions` or `optional_host_permissions` rather than all-URL patterns, and periodically remove unused permissions.
  Check: `manifest.json` has no `http://*/*`/`https://*/*` host access or unused permissions without justification. Owner: `frontend`. Source: Browser Extension Vulnerabilities.
- **Background service worker trusts message senders.** Treat every incoming message as untrusted: validate `sender.id` equals the extension's own id, validate `sender.url` or `sender.origin`, allowlist `request.action` and all parameters, and do not let webpages steer privileged logic via content scripts, which are less trusted than extension pages.
  Check: every `onMessage` listener checks `sender.id` and `sender.url` and allowlists actions. Owner: `frontend`. Source: Browser Extension Vulnerabilities.
- **Remote code loaded or self-updated by the extension.** Do not inject remote scripts or fetch-and-eval updates; rely on marketplace updates, sign updates, run integrity checks before executing any fetched code, restrict script sources with CSP, and prefer extension messaging APIs over injecting scripts into pages.
  Check: no `fetch` of script text, remote `<script src>` injection or `eval` in extension code. Owner: `frontend`. Source: Browser Extension Vulnerabilities.
- **Extension CSP weakened.** Configure `content_security_policy.extension_pages` with scripts loaded from the package only, keep inline script blocked, restrict other resource types to need, and do not apply web-page nonce or hash patterns to Manifest V3 extension pages.
  Check: manifest CSP is `script-src 'self'`-style with `object-src 'none'` and no inline or remote script sources. Owner: `frontend`. Source: Browser Extension Vulnerabilities.
- **Sensitive data rendered into the web page DOM.** Page scripts can read anything an extension writes into the page DOM, including open (and, against other extensions, closed) Shadow DOM; show sensitive data only in extension-controlled UI such as the popup, options page or side panel.
  Check: content scripts do not insert PII, financial data or tokens into page DOM. Owner: `frontend`. Source: Browser Extension Vulnerabilities.
- **Sensitive data handled in the page's main world.** Page scripts can override globals and prototypes (including `postMessage`), so scripts injected into the main world must handle only non-sensitive, essential data (for example a validation result, not a token); do not rely on tricks to recover native prototypes or on `document_start` timing.
  Check: main-world injected scripts and web-accessible resources never receive secrets or PII. Owner: `frontend`. Source: Browser Extension Vulnerabilities.
- **Extension persists sensitive data.** Extension storage is unencrypted; avoid persisting sensitive data, use `chrome.storage.session` (in memory, not exposed to content scripts by default) for runtime-only secrets, keep that restriction, and clear data when no longer needed. Never store tokens in `localStorage`.
  Check: tokens are not written to `localStorage` or persistent `chrome.storage`; session storage access level is unchanged. Owner: `frontend`. Source: Browser Extension Vulnerabilities.
- **Extension sends data over HTTP or without consent.** Use HTTPS for all external communication, validate server responses before processing, minimize collection, obtain user consent before sending personal data, allow opt-out, and publish a privacy policy disclosing collection and sharing.
  Check: no `http://` endpoints in extension code; data collection is gated on a consent flag. Owner: `frontend`. Source: Browser Extension Vulnerabilities.

## Server endpoints called by browser code

- **Browser-only endpoint assumed unreachable directly.** Services called by AJAX code can be called directly by attackers; validate all inputs as user-controlled, use JSON or XML schema validation for web service inputs, and apply CSRF protection.
  Check: endpoints used by the SPA validate input with a schema and enforce CSRF defenses for cookie auth. Owner: `backend`. Source: Web Frontend Security. See `cross-origin-and-browser.md` for CSRF.
- **JSON response with a top-level array.** Always return JSON with an object as the outermost value to defeat JSON hijacking in older browsers.
  Check: API responses wrap arrays in an object. Owner: `backend`. Source: Web Frontend Security.
- **Handwritten serialization.** Avoid writing serialization code or building XML/JSON by hand on client or server; use a reviewed framework serializer.
  Check: payloads are produced by a serializer, not string building. Owner: `backend`. Source: Web Frontend Security.

## Language hygiene, TypeScript and tooling

- **Regular expression with catastrophic backtracking (ReDoS).** Avoid nested quantifiers and ambiguous alternation, prefer well-tested validators for emails and URLs, cap untrusted input length before matching, and reject rather than sanitize non-matching input.
  Check: new regexes applied to untrusted input are linear and preceded by a length cap. Owner: `backend`. Source: JavaScript and TypeScript Security.
- **TypeScript types treated as runtime validation.** Types are erased; validate at every trust boundary (network responses, `postMessage` payloads, storage reads) with a runtime schema validator whose inferred type is the source of truth, use `unknown` instead of `any`, and never apply `as` or `!` to untrusted data.
  Check: boundary data passes a runtime schema before typed use; no `as`/`!` on unvalidated input. Owner: `backend`, `frontend`. Source: JavaScript and TypeScript Security.
- **Strict compiler and language modes off.** Ship ES modules or `'use strict'`, and enable `strict` in `tsconfig.json` (plus `noUncheckedIndexedAccess` where affordable) as code-quality hygiene, not a security boundary.
  Check: shared tsconfig enables `strict`. Owner: `dx`. Source: JavaScript and TypeScript Security.
- **Security lint rules and lockfile missing.** Lint with `typescript-eslint` recommended sets plus the eval rules, keep dependencies updated, pin with a lockfile, review dependency changes and monitor advisories.
  Check: shared lint config includes the rules; a lockfile is committed. Owner: `dx`. Source: JavaScript and TypeScript Security, Browser Extension Vulnerabilities.
- **Unhandled or silenced promise rejections.** Handle expected failures where the caller decides, keep promise chains flat with a terminal handler, and never swallow rejections with an empty `catch`.
  Check: no empty `catch` blocks; promise chains end with error handling. Owner: `backend`, `frontend`. Source: JavaScript and TypeScript Security.
