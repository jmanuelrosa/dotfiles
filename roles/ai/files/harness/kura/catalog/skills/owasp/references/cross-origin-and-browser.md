# Cross-origin and browser security

When to read: the brief, diff, or assessed surface touches state-changing endpoints authenticated by cookies, CSRF tokens or middleware, `Origin` / `Referer` / `Sec-Fetch-*` checks, CORS headers, redirects or server-side forwards built from request input, framing headers (`frame-ancestors`, `X-Frame-Options`), `postMessage`, `window.open` or `target="_blank"`, iframes and `sandbox`, `localStorage` / `sessionStorage` / IndexedDB, service workers, web workers, or cross-origin isolation headers (COOP, CORP).
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Cross-Site Request Forgery Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [Clickjacking Defense](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html), [Cross-site leaks](https://cheatsheetseries.owasp.org/cheatsheets/XS_Leaks_Cheat_Sheet.html), [HTML5 Security](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html), [Unvalidated Redirects and Forwards](https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html)

## Contents

- CSRF: tokens and request shape
- CSRF: origin verification and Fetch Metadata
- CSRF: SameSite, cookie prefixes, and client integration
- CORS
- Open redirects and forwards
- Cross-document messaging
- Framing and clickjacking
- Cross-site leaks and isolation headers
- Browser storage
- Windows, frames, workers, and other HTML5 features

## CSRF: tokens and request shape

- **State-changing endpoint without a CSRF defense.** Cookie-authenticated requests are sent automatically, so the server cannot tell a forged request from a real one; use the framework's built-in CSRF protection first, otherwise add CSRF tokens to all state-changing requests and validate them on the backend, and implement at least one defense-in-depth mitigation. XSS defeats every CSRF mitigation, so the XSS defenses are a prerequisite.
  Check: list state-changing routes on cookie-authenticated surfaces and confirm each passes through the framework CSRF middleware or a server-side token check; flag routes exempted without a recorded reason. Owner: `backend`. Source: CSRF.
- **State change reachable through a safe method.** `GET` (and `HEAD`, `OPTIONS`) must not perform state-changing operations; if one does, it must be CSRF-protected, and `SameSite=Lax` does not stop it because Lax still sends cookies on top-level `GET` navigations.
  Check: read every `GET` handler for writes, deletes, sends, or toggles; move the action to `POST`/`PUT`/`PATCH`/`DELETE`. Owner: `backend`. Source: CSRF.
- **Synchronizer token weak or loosely validated.** Tokens are generated server-side, once per session or per request (per-request is stronger but can break the back button), unique per session, secret, and unpredictable from a CSPRNG. The server must verify the token exists in the request and matches the session value, rejecting the request otherwise, and should consider logging the event.
  Check: token generation uses a secure random source; validation rejects missing and mismatched tokens on every protected route. Owner: `backend`. Source: CSRF.
- **CSRF token in a URL, a cookie, or logs.** For the synchronizer pattern the token must not be sent in a cookie and must not appear in URLs or server logs (GET parameters leak through history, logs, and `Referer`); send it in a hidden form field, a custom request header, or the JSON body, preferring a custom header set by JavaScript.
  Check: grep for tokens in query strings, redirect URLs, and log statements. Owner: `backend`. Source: CSRF.
- **Double-submit cookie not bound to the session.** Stateless apps should use the Signed Double-Submit Cookie: an HMAC (the sheet uses SHA-256) with a server-side secret over a session-dependent value that changes each login (never a static email or user id, and the session id never leaves the server in plaintext) plus a cryptographic random value (the sheet's example: 64 bytes, 128 hex characters). Reject tokens that are not exactly the expected two lowercase hex components, recompute against the current session, compare in constant time, read the token from a header or form field (never the cookie), do not add timestamps, and do not log token values. The naive unsigned double-submit pattern is bypassable by anyone who can write cookies on the domain and is discouraged.
  Check: read the token builder and validator for session binding, HMAC with a stored secret, format checks, constant-time comparison, and request-side (not cookie) token source. Owner: `backend`. Source: CSRF.
- **JSON API accepts simple content types.** `application/x-www-form-urlencoded`, `multipart/form-data`, and `text/plain` requests are sent cross-origin without preflight; JSON APIs should reject them. Any `<form>` posting still needs tokens.
  Check: API body parsers accept only `application/json` (or the intended non-simple type) on state-changing routes. Owner: `backend`. Source: CSRF.
- **Custom-header defense paired with permissive CORS.** Requiring a custom request header works because it forces a CORS preflight; the backend must reject requests without the header, and CORS must only allow specific origins you control.
  Check: the header presence check is server-side on every protected route and the CORS allowlist is exact (see CORS). Owner: `backend`. Source: CSRF.
- **Login form without CSRF protection.** Login CSRF lets an attacker sign the victim into the attacker's account; protect the login form with a pre-session token or a custom AJAX header, and destroy the pre-session and issue a new session at authentication.
  Check: the login handler validates a token or custom header and rotates the session on success. Owner: `backend`. Source: CSRF.
- **Highly sensitive operation with no user-interaction check.** Password changes, money transfers, and similar operations can add re-authentication or one-time tokens; CAPTCHA must not be used as a CSRF defense.
  Check: critical operations require re-authentication or a one-time token in addition to CSRF tokens. Owner: `backend`. Source: CSRF.

## CSRF: origin verification and Fetch Metadata

- **Origin check by substring, prefix, or missing-header acceptance.** Verify that `Origin` matches the target origin, falling back to the `Referer` host when `Origin` is absent, and match the entire origin so `example.org.attacker.com` fails. Missing headers and `Origin: null` are not evidence of same-origin; never allowlist the literal `null`, and reject the state-changing request unless another configured defense such as a valid token succeeds.
  Check: read the comparison logic for exact origin equality and for the missing / `null` branch. Owner: `backend`. Source: CSRF.
- **Target origin derived from client-controllable headers.** The most secure target origin is configured server-side; `Host` changes behind proxies, and `X-Forwarded-Host` may be used only from trusted proxies that remove or overwrite client-supplied values, verified on every ingress path including direct access to the app server. Keep the central origin configuration secured.
  Check: confirm where the expected origin comes from; flag trust of forwarded headers without a trusted-proxy setting. Owner: `backend`. Source: CSRF.
- **Fetch Metadata policy that lets cross-site writes through.** When `Sec-Fetch-Site` is present, reject non-safe methods (`POST`, `PUT`, `PATCH`, `DELETE`) when it is `cross-site`, also guard sensitive endpoints reached by safe methods, allow `same-origin`, treat `same-site` as trusted only if sibling subdomains are trusted, and allow `none` for user-driven top-level navigation. Allow `GET` top-level navigations (`Sec-Fetch-Mode: navigate`, destination not `object` or `embed`) so the site stays linkable, ignore unrecognized values, and explicitly exempt intended cross-origin endpoints (CORS APIs, webhooks) secured by CORS, authentication, and logging.
  Check: read the policy function for each of these branches and an explicit exemption list. Owner: `backend`. Source: CSRF.
- **Fetch Metadata check without a fallback.** Some clients omit `Sec-*` headers and intermediaries can strip them, so a fallback to `Origin` / `Referer` verification is mandatory; fail safe (block) on sensitive endpoints, or fail open to origin checks or tokens for compatibility. Fetch Metadata is sent only to potentially trustworthy URLs, so HTTPS must be enforced site-wide (HSTS helps).
  Check: the absent-header branch performs origin verification or token validation rather than allowing the request. Owner: `backend`. Source: CSRF, XS-Leaks.
- **Responses varying on Fetch Metadata without `Vary`.** Responses that differ by `Sec-Fetch-Site` or `Origin` must send `Vary: Sec-Fetch-Site, Origin` so caches do not serve a response built for another context. Roll the policy out in log-only mode first, monitor which user agents send the headers, and document exempted endpoints.
  Check: the middleware sets `Vary`; rollout config has a log-only switch and a documented exemption list. Owner: `backend`. Source: CSRF.

## CSRF: SameSite, cookie prefixes, and client integration

- **SameSite relied on as the only CSRF defense.** `SameSite` is defense in depth: `Lax` allows top-level safe-method requests, the attribute is scoped to the registrable domain so any sibling subdomain (including a taken-over one) is same-site, window-opening tricks produce same-site requests, older browsers ignore it, and client-side CSRF is unaffected. It is sufficient alone only when the app shares no registrable domain with hosts you do not control, no safe-method endpoint changes state, the session cookie is `Strict` (or `Lax` with `__Host-` and an audited `GET` set), Origin/Referer checks exist, and unsupported browsers are an accepted risk; otherwise combine it with tokens. `SameSite=None` requires `Secure`; `Strict` suits sites whose transactional pages are never linked externally.
  Check: if a design omits tokens because of SameSite, verify each listed condition. Owner: `backend`. Source: CSRF, Clickjacking, XS-Leaks.
- **Session cookie scoped with a `Domain` attribute.** Setting a cookie specifically for a domain shares it with every subdomain, which is especially dangerous when a subdomain CNAMEs to a domain you do not control.
  Check: session and CSRF cookies omit `Domain`. Owner: `backend`. Source: CSRF.
- **CSRF cookie without the `__Host-` prefix.** `__Host-` cookies cannot be overwritten from subdomains, cannot have `Domain`, must use `Path=/`, and must be `Secure`; use `__Host-` together with `SameSite`, and the weaker `__Secure-` only when authenticated users must move across subdomains.
  Check: CSRF token cookies are named `__Host-...` with `Secure; Path=/` and no `Domain`. Owner: `backend`. Source: CSRF.
- **Client attaches the CSRF token to every destination.** Prefer the HTTP client's maintained CSRF integration, restricted to same-origin or relative URLs, and attach tokens only after checking the origin of the resolved request URL against an explicit trusted list; do not globally override request primitives or put tokens in global method defaults, since an unrelated origin that allows the request receives the token. A client-side header alone enforces nothing: the server must validate the token on every protected request. Render a DOM-stored token with the template's attribute encoder; in cookie-to-header setups the token cookie is readable while the auth cookie stays `HttpOnly`.
  Check: find interceptors or `beforeSend` hooks adding the token; they must check the destination origin, not only the method. Owner: `frontend`. Source: CSRF.
- **Client code builds requests from attacker-controllable input (client-side CSRF).** When the URL, `window.name`, `document.referrer`, or `postMessage` data chooses the endpoint, method, or parameters of an async request, the app attaches its own token and same-site cookies, bypassing tokens and SameSite. Generate requests independently of such inputs; where impossible, strictly validate format and values and limit them to non-state-changing operations (for example only `GET` to a predefined path prefix), or select from a predefined table of safe request data by a switch parameter.
  Check: trace `fetch` / XHR URL and method arguments back to `location`, `window.name`, `referrer`, or message data. Owner: `frontend`. Source: CSRF.

## CORS

- **`Access-Control-Allow-Origin` wildcard or reflected origin.** Allow only selected, trusted domains; never use `*` on URLs that return sensitive content and never echo the request `Origin` without checking it. Send CORS headers only on the URLs that need cross-domain access, not the whole domain, and with credentials allow only exact origins you control; a regex allowing all subdomains lets a taken-over subdomain bypass the same-origin policy.
  Check: read CORS config for `*`, origin reflection, and regex or suffix origin matching. Owner: `backend`. Source: HTML5, CSRF.
- **CORS treated as access control.** CORS does not stop data from going to an unauthorized location, preflights may not happen, and `Origin` can be spoofed outside a browser, so ordinary `GET` and `POST` handlers must enforce authentication, authorization, and CSRF protection themselves.
  Check: routes behind a CORS allowlist still perform authz and CSRF checks. Owner: `backend`. Source: HTML5.
- **Plain-HTTP requests carrying HTTPS origins accepted.** Requests received over plain HTTP with HTTPS origins should be discarded to prevent mixed-content bugs.
  Check: CORS or origin middleware rejects scheme mismatches. Owner: `backend`. Source: HTML5.
- **Client request URL taken from untrusted input.** URLs passed to `XMLHttpRequest.open` or the `EventSource` constructor can be cross-domain; validate them, paying extra attention to absolute URLs.
  Check: client request URLs built from input are validated against expected origins. Owner: `frontend`. Source: HTML5.

## Open redirects and forwards

- **Redirect destination taken from request input.** Accepting a URL parameter as the redirect target enables phishing from your domain and, in `Location` or `Refresh` headers, script execution through non-HTTP schemes. Avoid redirects, or do not take the destination as user input: map a short name, id, or token server-side to the full URL (without creating an enumerable list of targets). If input is unavoidable, the value must be valid, appropriate, and authorized for the user; use the framework's local-redirect helper for local return URLs.
  Check: grep redirect calls and `Location` / `Refresh` header writes whose argument derives from request data. Owner: `backend`. Source: Redirects, XSS Filter Evasion.
- **Redirect allowlist checked by string prefix or suffix.** Parse with a maintained URL parser consistent with the browser and redirect API, compare scheme, canonical host, and effective port against an explicit allowlist, constrain the path where only specific endpoints are allowed, reject userinfo and ambiguous input, and redirect to the validated URL rather than a transformed one.
  Check: flag `startsWith`, `endsWith`, `contains`, or regex checks on raw URL strings. Owner: `backend`. Source: Redirects.
- **Off-site redirect without an interstitial.** Redirects should go through a page that tells users they are leaving the site, shows the destination clearly, and requires a click to continue.
  Check: external redirects render a confirmation page rather than issuing an immediate `3xx`. Owner: `backend`. Source: Redirects.
- **Server-side forward to a target from request input.** A user-controlled forward can pass the access check and reach a privileged function; the application must check the user is authorized for the target URL and that it is an appropriate request.
  Check: internal dispatch or forward calls with a request-derived path enforce authorization on the target. Owner: `backend`. Source: Redirects.
- **Handler keeps running after issuing a redirect.** In stacks where setting a `Location` header does not end the request, code after it still executes and its output reaches a client that ignores the redirect.
  Check: redirect header writes are followed by an explicit return or exit. Owner: `backend`. Source: Redirects.

## Cross-document messaging

- **`postMessage` sent with a `*` target origin.** Always pass the exact expected origin, otherwise any window that obtained a reference, or a window that navigated away, receives the message.
  Check: grep `postMessage(` for `'*'` as the second argument. Owner: `frontend`. Source: HTML5, XS-Leaks.
- **Message handler without an exact origin check.** Receivers must always check `event.origin` against the exact expected FQDNs (substring checks such as `indexOf(".example.org")` match `www.example.org.attacker.com`), validate the format of `event.data`, and not assume control over the data since an XSS in the sender can send anything. Treat messages only as data: never `eval` them or insert them with `innerHTML`; use `textContent`. The same applies to `EventSource` messages (allowlisted `event.origin`, `event.data` never evaluated as HTML or script) and to Web Worker messages (validate, never exchange JavaScript for evaluation).
  Check: every `message` listener compares origin by equality against an allowlist before parsing, and no message data reaches an HTML or code sink. Owner: `frontend`. Source: HTML5.

## Framing and clickjacking

- **Page frameable by any origin.** Send `Content-Security-Policy: frame-ancestors 'none'` unless a specific framing need exists (`'self'` or explicit origins otherwise; quotes only around `self` and `none`; `https://*.example.com` matches subdomains but not the bare host). It must be a response header (it is ignored in `<meta>`) and does not fall back to `default-src`. Framing protection also blocks frame-based cross-site leaks.
  Check: every HTML response carries `frame-ancestors` from server or edge config. Owner: `backend`. Source: Clickjacking, CSP, XS-Leaks.
- **`X-Frame-Options` misused as the only framing control.** If used for older browsers, set it on all HTML responses as a header (meta tags do not work), prefer `DENY`, use `SAMEORIGIN` only when needed, and never rely on `ALLOW-FROM`, which is obsolete and fails open; only one value is honored, and proxies may strip it. It is superseded by `frame-ancestors`.
  Check: flag `ALLOW-FROM`, meta-tag framing directives, and pages lacking both headers. Owner: `backend`. Source: Clickjacking, HTML5.
- **JavaScript frame-busting as the defense.** Simple `top != self` frame busters are defeated by double framing, `onbeforeunload` cancellation, 204 flushing, and sandboxed frames, and are not recommended. Where legacy browsers must be covered, use the pattern that hides the body with a styled element and reveals it only when `self === top`, alongside the header defenses.
  Check: frame-busting scripts are not the only control. Owner: `frontend`. Source: Clickjacking, HTML5.
- **SameSite cookies relied on against clickjacking.** `SameSite=Strict` or `Lax` withholds cookies from cross-site frames but does not block framing, does not cover same-site sibling origins, and does nothing for unauthenticated attacks; keep `frame-ancestors`.
  Check: framing headers are present even where SameSite is set. Owner: `backend`. Source: Clickjacking.
- **High-risk action vulnerable to DoubleClickjacking.** Framing defenses do not stop attacks that use a separate top-level window; for consent screens, payment confirmations, and security settings, require users to review the action and complete transaction authorization enforced on the server.
  Check: high-risk confirmations require server-verified transaction authorization, not just a confirm button. Owner: `backend`. Source: Clickjacking.
- **Interaction gating implemented as the only DoubleClickjacking control.** Disabling sensitive controls until prior interaction is a supplementary mitigation; if used, render the controls disabled from the start and make them enable and activate with mouse, keyboard, touch, and assistive technology. `window.confirm()` in frameable content is likewise supplementary, can be suppressed (returning `false`), and the action must run only on a `true` result.
  Check: gating code does not require mouse movement specifically; `confirm()` results are checked for `true`. Owner: `frontend`. Source: Clickjacking.

## Cross-site leaks and isolation headers

- **No cross-origin isolation headers.** Use `Cross-Origin-Opener-Policy` (for example `same-origin`, which removes cross-origin window references and defeats frame counting) and `Cross-Origin-Resource-Policy` (`same-site` or `same-origin`, which stops other sites loading your resources) with appropriate values.
  Check: response header config sets COOP and CORP for authenticated pages and resources. Owner: `backend`. Source: XS-Leaks.
- **Sensitive endpoint answers cross-site subresource requests.** Load success or error events reveal state (for example which user id is logged in); build a resource isolation policy from Fetch Metadata, such as rejecting `Sec-Fetch-Site: cross-site` on sensitive APIs and `Sec-Fetch-Dest: iframe` on pages not meant to be framed, with a fallback when headers are absent. Alternatively require a long, unique token validated by the backend on sensitive endpoints.
  Check: user-specific API routes reject cross-site requests or require an unguessable token. Owner: `backend`. Source: XS-Leaks.
- **User-specific resource detectable through cache timing.** Add an unpredictable per-user token to the resource URL so attackers cannot probe the cache, or send `Cache-Control: no-store` on resources to protect where reduced performance is acceptable.
  Check: role- or user-specific static resources carry per-user tokens or `no-store`. Owner: `backend`. Source: XS-Leaks.
- See `sessions-and-cookies.md` for general cookie attribute guidance; XS-Leaks recommends setting an appropriate `SameSite` on every cookie.

## Browser storage

- **Session identifier or secret in web storage.** `localStorage`, `sessionStorage`, and IndexedDB are readable by any script, so one XSS steals everything and anyone with access to the browser profile can read it; do not store session identifiers there (cookies can be `HttpOnly`), avoid sensitive data and credentials, and use `sessionStorage` instead of `localStorage` when persistence is not needed. If sensitive data must be stored locally, design encryption and key management for the device-access threat; a non-extractable `CryptoKey` does not protect persisted keys or stop hostile scripts from using the key.
  Check: grep `localStorage.setItem`, `sessionStorage`, and IndexedDB writes for tokens, credentials, or personal data. Owner: `frontend`. Source: HTML5.
- **Client storage read back as trusted.** XSS can write malicious data into web storage and IndexedDB, so values read from them get the same validation and output encoding as network input.
  Check: storage reads flowing into sinks are validated and encoded. Owner: `frontend`. Source: HTML5.
- **Several applications hosted on one origin.** Web storage is shared across the whole origin with no path scoping; host separate applications on separate subdomains.
  Check: deployment layout does not co-host unrelated apps under one origin. Owner: `architect`. Source: HTML5.
- **Removed browser storage or cache APIs in use.** Web SQL is removed from major browsers and must not be used (prefer an embedded SQLite WebAssembly build over IndexedDB or OPFS, with IndexedDB as the standard store); the HTML5 Application Cache is removed and usage must migrate to Service Workers with the Cache API.
  Check: grep for `openDatabase(` and `manifest=` / `.appcache`. Owner: `frontend`. Source: HTML5.

## Windows, frames, workers, and other HTML5 features

- **New window keeps an `opener` back link (reverse tabnabbing).** Add `rel="noopener noreferrer"` to every link that opens a new browsing context and pass `noopener,noreferrer` in `window.open` features; send `Referrer-Policy: no-referrer` on every response.
  Check: grep `target="_blank"` and `window.open(` for the noopener / noreferrer settings. Owner: `frontend`. Source: HTML5.
- **Untrusted content in an unsandboxed iframe.** Use the `sandbox` attribute for untrusted content (unique origin, no forms, scripts, plugins, auto-triggered features, or cross-context links) and grant capabilities only as needed; treat it as an extra layer because old user agents ignore it, or show the content only when supported. Embedding user-controlled scripts is highly discouraged.
  Check: iframes rendering user or third-party content carry `sandbox` with a minimal token list. Owner: `frontend`. Source: HTML5.
- **Service worker registered loosely.** Register service workers only from your own origin, serve the script only over HTTPS with a cache-busting hashed filename, and restrict its scope with the `scope` option or `Service-Worker-Allowed`. Keep a documented recovery process that updates or unregisters the worker and removes affected caches (expiring data does not unregister a worker).
  Check: registration code sets an explicit scope; a kill-switch or unregister path exists. Owner: `frontend`. Source: HTML5.
- **Sensitive responses stored in the Cache API.** The Cache API ignores HTTP caching headers and never expires entries, so service-worker code must exclude sensitive responses and delete any already stored, while still sending `Cache-Control: no-store` for HTTP caches.
  Check: service-worker caching rules exclude authenticated or personal responses. Owner: `frontend`. Source: HTML5.
- **Web Worker created from user input.** Do not build Web Worker scripts from user-supplied input, and ensure worker code is not malevolent (workers can burn CPU or abuse CORS).
  Check: `new Worker(` arguments are static, same-origin script URLs. Owner: `frontend`. Source: HTML5.
- **Geolocation requested without a user action.** For privacy, require user input before calling `getCurrentPosition` or `watchPosition`.
  Check: geolocation calls sit behind an explicit user interaction. Owner: `frontend`. Source: HTML5.
- **`autocomplete="off"` treated as credential protection.** Input hint attributes (`autocomplete`, `spellcheck`, `autocorrect`, `autocapitalize`) do not enforce a no-storage policy, and browsers may still save login credentials; do not rely on them for shared-computer protection.
  Check: flag designs that cite `autocomplete="off"` as a security control. Owner: `frontend`. Source: HTML5.
- **Fallback to obsolete browser plugins.** Use feature detection and native HTML5 substitutes; do not fall back to Flash, Java applets, Silverlight, or ActiveX.
  Check: grep for `<object>` / `<embed>` plugin fallbacks. Owner: `frontend`. Source: HTML5.
- See `graphql-grpc-and-websockets.md` for WebSocket protections.
- See `http-headers-tls-and-caching.md` for the full set of browser security headers.
