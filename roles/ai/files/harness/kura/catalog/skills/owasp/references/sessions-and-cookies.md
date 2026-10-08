# Sessions and Cookies

When to read: the brief, diff, or assessed surface touches session creation or storage, login or logout handlers, `Set-Cookie` attributes, session timeouts, browser storage of tokens, cache headers on authenticated pages, concurrent session handling, or detection of stolen sessions.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [Cookie Theft Mitigation](https://cheatsheetseries.owasp.org/cheatsheets/Cookie_Theft_Mitigation_Cheat_Sheet.html), [Credential Stuffing Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html)

## Contents

- Session fixation and rotation
- Session id generation and content
- Cookie attributes and scope
- Token storage in the browser
- Server-side session store
- Transport
- Expiration and logout
- Hijack detection and stolen cookies
- Session visibility and logging

## Session fixation and rotation

- **Session id not rotated on login or privilege change.** Regenerate the session id after any privilege level change: authentication, password change, permission change, switching to an administrator role, passkey authentication, and re-authentication. Ignore and destroy the previous id so only the current one is accepted for protected resources.
  Check: the login and role-change handlers call the framework's regenerate or invalidate-and-create function, not just write the user id into the existing session. Owner: `backend`. Source: Session Management.
- **Permissive session mode accepts attacker-chosen ids.** Only accept session ids the application generated; on receiving an unknown id, issue a new valid id and raise an alert as suspicious activity. Some frameworks default to permissive mode (for example PHP), so enable strict mode explicitly.
  Check: strict session mode is configured and unknown ids are not used to create a session under that id. Owner: `backend`. Source: Session Management.
- **Session id accepted from the URL or other mechanisms.** Use cookies as the session exchange mechanism and reject session ids from URL parameters, GET/POST arguments, hidden fields or custom headers, and disable automatic URL rewriting; ids in URLs leak through logs, history, bookmarks and the Referer header.
  Check: session middleware reads only the cookie and URL-based session tracking is disabled. Owner: `backend`. Source: Session Management.
- **Pre-authentication cookie grants access to the authenticated session.** When multiple cookies make up a session, verify all of them and enforce their relationship before granting access; consider different session cookie names pre and post authentication. Avoid reusing the same cookie name for different paths or domains within one application.
  Check: authenticated routes validate the post-login cookie, not only an anonymous tracking cookie. Owner: `backend`. Source: Session Management.

## Session id generation and content

- **Session id with less than 64 bits of entropy.** Session ids must have at least 64 bits of entropy from a CSPRNG (at least 16 hex characters, more if any part is fixed or predictable); when generating your own id, use a CSPRNG with at least 128 bits and ensure uniqueness.
  Check: the id generator uses a CSPRNG of >= 128 bits for custom ids; no timestamps, counters or user data in the id. Owner: `backend`. Source: Session Management.
- **Meaningful data inside the session id.** The session id must be a meaningless identifier with no PII or sensitive data; keep user, role and state on the server in the session store.
  Check: the cookie value is not decodable into user attributes. Owner: `backend`. Source: Session Management.
- **Home-made session management.** Prefer the framework's built-in session management, keep it on the latest version, and review and harden its default configuration.
  Check: sessions use the framework mechanism and its config sets the attributes in this file. Owner: `backend`. Source: Session Management.
- **Framework default session cookie name.** Rename framework session cookies (`PHPSESSID`, `JSESSIONID`, `ASP.NET_SessionId`) to a generic name such as `id` to avoid fingerprinting.
  Check: the session cookie name is set explicitly to a generic value. Owner: `backend`. Source: Session Management.
- **Session id processed as trusted input.** Validate and filter session ids like any user input before use, so they cannot carry SQL injection or stored XSS into the session store or responses.
  Check: lookups use parameterized queries and malformed ids are rejected before storage access. Owner: `backend`. Source: Session Management.

## Cookie attributes and scope

- **Session cookie missing `Secure`.** The session cookie must set `Secure`; HTTPS-only hosting does not prevent a browser from being tricked into sending it over HTTP.
  Check: `Set-Cookie` for the session includes `Secure` in every environment above local dev. Owner: `backend`. Source: Session Management.
- **Session cookie missing `HttpOnly`.** The session cookie must set `HttpOnly` so script cannot read it through `document.cookie`.
  Check: the session cookie config sets `HttpOnly`. Owner: `backend`. Source: Session Management.
- **`SameSite` unset or `None` without `Secure`.** Session cookies must explicitly set `SameSite=Strict` (preferred) or `SameSite=Lax`, never rely on the browser default, and never use `SameSite=None` without `Secure`. SameSite is CSRF defense in depth, not a replacement for CSRF tokens.
  Check: the cookie config names a SameSite value explicitly. Owner: `backend`. Source: Session Management. See `cross-origin-and-browser.md` for CSRF tokens.
- **Session cookie without the `__Host-` prefix.** Name session cookies with the `__Host-` prefix (requires `Secure`, no `Domain`, `Path=/`) to block subdomain forgery and downgrade; use `__Secure-` only when subdomain sharing is required.
  Check: the session cookie name starts with `__Host-`. Owner: `backend`. Source: Session Management.
- **Cookie `Domain` set to a parent domain.** Do not set `Domain` (keep the cookie host-only) and keep `Path` as narrow as possible; a broad domain exposes the session to every subdomain and enables cross-subdomain fixation.
  Check: no `Domain` attribute on the session cookie. Owner: `backend`. Source: Session Management.
- **Applications of different trust levels share a domain or host.** Do not host web applications of different security levels on the same domain, and avoid running different applications on the same host, since path isolation is weak and any app can set cookies for any path.
  Check: admin or sensitive apps run on their own host, not a path of a public app. Owner: `architect`. Source: Session Management.
- **Persistent session cookie or sensitive data persisted in cookies.** Use non-persistent cookies when authentication need not survive the browser session, but never rely on browser closure to end a session (session restore keeps cookies). Do not persist sensitive information in cookies, encrypt the entire cookie if sensitive data must be persisted, ensure cookie manipulation cannot enable unauthorized activity, verify all state transitions check and enforce the cookies, and keep an inventory of every cookie the application sets with its purpose.
  Check: session cookie has no `Max-Age`/`Expires` unless justified, and cookie contents are opaque or encrypted. Owner: `backend`. Source: Session Management.

## Token storage in the browser

- **Credentials in `localStorage` or `sessionStorage`.** Do not store session ids, JWTs, access or refresh tokens, or any credential in Web Storage, where any script on the origin (one XSS) can read them; use `HttpOnly; Secure; SameSite=Strict` cookies or a Backend-for-Frontend that holds tokens.
  Check: no `localStorage.setItem` or `sessionStorage.setItem` of token-like values in the client. Owner: `frontend`. Source: Session Management.
- **Web Worker treated as XSS protection for tokens.** A worker may hold a secret in memory only when browser code genuinely needs secret-dependent operations; obtain it inside the worker, never return it to the main window, expose a narrow message interface, and enforce authorization on the server. It does not replace XSS prevention or server-side session controls.
  Check: the worker message API never posts the token back, and the design still prefers HttpOnly cookies or a BFF. Owner: `frontend`. Source: Session Management.

## Server-side session store

- **Raw session tokens readable in the store.** If read-only disclosure of the session store or backups is in the threat model, store a one-way verifier: split the cookie into a lookup identifier and a secret verifier, store the SHA-256 of the verifier, compare in constant time on every request, and never accept the identifier alone. Generate the verifier independently from a CSPRNG with at least 128 bits (prefer 160 or more), and never persist the raw verifier beside its hash.
  Check: the session table stores a hash column, and the lookup path hashes and constant-time compares the presented verifier. Owner: `backend`. Source: Session Management.
- **Session store and backups unprotected.** Restrict access to the session store, encrypt backups and replicas at rest, and encrypt sensitive data held in session objects (for example card numbers).
  Check: the session store has scoped credentials and encrypted snapshots. Owner: `cloud`. Source: Session Management.

## Transport

- **Session carried over HTTP for part of its life.** Use TLS for the entire session, not only the login; do not switch a session between HTTP and HTTPS, set or regenerate the session cookie only after the redirect to HTTPS, do not mix encrypted and unencrypted content on a page or domain, serve any required insecure public content from a separate domain, and enable HSTS.
  Check: no HTTP route sets or reads the session cookie, and HSTS is configured. Owner: `backend`. Source: Session Management. See `http-headers-tls-and-caching.md` for HSTS and TLS configuration.

## Expiration and logout

- **No server-side idle timeout.** Every session needs an idle timeout enforced on the server; client-side timers or client-held timestamps can be manipulated. Common idle ranges are 2 to 5 minutes for high-value applications and 15 to 30 minutes for low-risk ones.
  Check: session config defines an idle timeout and the server checks last activity on each request. Owner: `backend`. Source: Session Management.
- **No absolute session lifetime.** Every session needs an absolute timeout regardless of activity (for example 4 to 8 hours for a full-day office application), after which the user must re-authenticate. Where sessions must be long-lived, add a renewal timeout that rotates the session id periodically and invalidates the previous id once the client switches.
  Check: the session record stores creation time and the server enforces a maximum age. Owner: `backend`. Source: Session Management.
- **Logout or expiry only clears the client cookie.** On expiry or logout, invalidate the session on the server (mandatory) and clear the client cookie with an empty value and past expiry; deleting the cookie alone leaves stolen copies valid. Do not rely on browser-close or `beforeunload` events to log users out.
  Check: the logout handler destroys the server-side session record before responding. Owner: `backend`. Source: Session Management.
- **No logout control on every page.** Provide a visible logout button reachable from every page of the application. Client-side auto-logout and expiry warnings may complement, never replace, server-side timeouts.
  Check: the shared layout renders a logout action wired to the server logout. Owner: `frontend`. Source: Session Management.
- **Sensitive responses cacheable after logout.** Send `Cache-Control: no-store` in HTTP response headers on responses containing session ids or sensitive session data (not `no-cache`, not `no-cache="Set-Cookie"`, and not `<meta http-equiv>` tags), and return `Clear-Site-Data` (for example `"cache", "cookies", "storage"`) on logout or session termination, mindful that `"cache"` clears the whole site cache in that browser.
  Check: authenticated responses carry `no-store` and the logout response sets `Clear-Site-Data`. Owner: `backend`. Source: Session Management.
- See `authentication.md` for re-authentication after risk events (password change, new device or IP, account recovery) followed by session rotation.
- **Simultaneous session policy undefined.** Decide whether simultaneous logons are allowed; if not, on each new authentication terminate the previous session or ask the user which to keep.
  Check: the login handler applies the documented concurrency policy. Owner: `backend`. Source: Session Management.

## Hijack detection and stolen cookies

- **Session guessing and brute force undetected.** Detect many requests presenting different session ids from one IP or set of IPs, and alert or block the source.
  Check: invalid-session lookups are counted per source and trigger a limit. Owner: `backend`. Source: Session Management.
- **Session context not recorded at creation.** Store client context when the session is established (IP address, User-Agent, Accept-Language, server timestamp; optionally Accept, Accept-Encoding, and `Sec-CH-UA*` client hints as optional signals) and compare it on each request, judging whether the meaning changed significantly (region, device class) rather than exact equality, and tolerating missing headers and legitimate change.
  Check: the session record holds these fields and middleware evaluates drift on requests. Owner: `backend`. Source: Cookie Theft Mitigation, Session Management.
- **Suspected stolen session accepted after a CAPTCHA.** When drift suggests hijacking, restrict or invalidate the session and require re-authentication with an account-bound authenticator, then issue a new session cookie; a solved CAPTCHA does not validate the session. Balance against false positives, and if cost is high, focus checks on endpoints that view or modify important information.
  Check: the drift branch ends the session or forces step-up with a bound factor, not a CAPTCHA. Owner: `backend`. Source: Cookie Theft Mitigation.
- **Session anomalies not detected in-app.** Detect anomalies such as modified or deleted cookies, new cookies, reuse of another user's session id, and mid-session location or User-Agent changes; binding the session to IP, User-Agent or client certificate is a detection aid, not a reliable defense.
  Check: the session middleware emits events on these anomalies. Owner: `backend`. Source: Session Management.
- **DBSC assumed to make stolen cookies useless.** Device Bound Session Credentials only bind cookie refresh to a device key; a stolen short-lived cookie is still a bearer credential until expiry, and an attacker on the compromised device can still use it. Account for this when choosing cookie lifetimes and incident response.
  Check: the design does not shorten other controls on the assumption DBSC prevents replay. Owner: `architect`. Source: Cookie Theft Mitigation.
- **No compensating control for unmodifiable apps.** Where code cannot be changed, use a WAF to enforce `Secure` and `HttpOnly`, renew session ids on privilege change, enforce sticky sessions, and manage expiry.
  Check: WAF rules rewrite `Set-Cookie` attributes for legacy apps in scope. Owner: `cloud`. Source: Session Management.

## Session visibility and logging

- **Users cannot see or end their sessions.** Let users view active session details (IP, User-Agent, login time, idle time), alert them to concurrent logons, terminate other sessions remotely, and review account activity history.
  Check: an active-sessions view exists with a revoke action backed by server-side invalidation. Owner: `backend`. Source: Session Management, Credential Stuffing.
- **Raw session ids in logs.** Never log raw session ids; log a salted hash for correlation, and log only selected header and parameter fields after excluding credentials.
  Check: log statements reference a hashed session id. Owner: `backend`. Source: Session Management.
- **Session lifecycle not logged.** Log session creation, renewal and destruction, login and logout, privilege changes, timeouts, invalid session activity, critical business operations, and any automatic defensive action, with timestamp, source IP, resource, event type, result and user id where needed.
  Check: session middleware emits structured events for each lifecycle transition. Owner: `backend`. Source: Session Management.
- **Session administration interface weakly protected.** Thoroughly protect administrative interfaces that list or manage active sessions or allow impersonation.
  Check: the session admin routes require admin authorization and are audited. Owner: `backend`. Source: Session Management.
