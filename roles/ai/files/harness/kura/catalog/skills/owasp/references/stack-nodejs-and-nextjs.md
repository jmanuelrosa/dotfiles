# Node.js and Next.js

When to read: the brief, diff, or assessed surface touches Node.js server code (Express middleware, body parsers, `child_process`, `fs`, `vm`, `eval`, EventEmitters, `process.on('uncaughtException')`, `express-session`, `helmet`), the `node` start command or `--permission` flags, or Next.js server entry points (`proxy.ts`/`middleware.ts`, Server Actions, `route.ts`, `pages/api`, Server Components, `getServerSideProps`/`getStaticProps`/`getInitialProps`, Draft Mode), `use cache` and revalidation calls, `NEXT_PUBLIC_` variables, or `next.config.*` (rewrites, redirects, `images`, `serverActions`, `productionBrowserSourceMaps`, CSP).
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [NodeJS Security](https://cheatsheetseries.owasp.org/cheatsheets/Nodejs_Security_Cheat_Sheet.html), [Next.js Security](https://cheatsheetseries.owasp.org/cheatsheets/Nextjs_Security_Cheat_Sheet.html)

## Contents

- Next.js server entry points and authorization
- Data crossing into the browser
- Cache audience and invalidation
- Next.js configuration as security code
- Node.js code execution and input handling
- Event loop, request size and brute force
- Error and exception handling
- Cookies, headers and CSRF in Express
- Node.js runtime permissions
- Dependencies, linting and patching
- Verifying the boundaries

## Next.js server entry points and authorization

- **Authorization not enforced at a boundary every path traverses.** Next.js has several independently callable server entry points, and a check in one does not protect another.
  Check: protected data is reached only through a server-only Data Access Layer (or an equivalent service-layer policy point or database control) that authorizes and returns minimal DTOs, and every Server Action, Route Handler, Pages API Route and data loader goes through it. Owner: `backend`. Source: Next.js.
- **Proxy or middleware as the only authorization layer.** A `matcher` can omit a route, routing changes move operations out of coverage, and framework bugs such as CVE-2025-29927 bypassed middleware-only authorization.
  Check: `proxy.ts` (or legacy `middleware.ts`) does only optimistic redirects and filtering; each protected handler or the data source authorizes again. Owner: `backend`. Source: Next.js.
- **Layout or Client Component check treated as protection.** A layout enforces render-time access but not for independently callable descendants, and Client Component checks only change what the UI shows.
  Check: no protected operation relies solely on a layout, page or Client Component guard. Owner: `backend`, `frontend`. Source: Next.js.
- **Server Action assumed protected by its page.** Any reachable Server Action accepts a client-originated POST independently of the page that renders its form; page-level authentication does not extend to it.
  Check: each action is classified public or protected; every argument is validated as untrusted input; protected actions derive the authentication context on the server rather than from arguments. Owner: `backend`. Source: Next.js.
- **Client-submitted ids treated as authorization proof.** A user or tenant id passed to an action or handler is only a selector.
  Check: actions and handlers check permission on the exact object read or changed, and high-impact or expensive actions apply rate limits or step-up re-authentication. Owner: `backend`. Source: Next.js.
- **Route Handlers or Pages API Routes left open because the page is protected.** Next.js treats Route Handlers as public-facing endpoints.
  Check: each `route.ts` and `pages/api` handler has an explicit audience (public with validation and abuse controls, webhook with signature verification, or protected API with authentication plus object-level or tenant-level authorization). Owner: `backend`. Source: Next.js.
- **Internal-only HTTP handler kept as an entry point.** A handler is not private just because only a Server Component calls it.
  Check: when no browser, service, webhook or external client needs the HTTP API, the Server Component calls the DAL directly and the handler is removed. Owner: `backend`. Source: Next.js.
- **Draft Mode enabled without caller authentication.** Calling `enable()` on `await draftMode()` sets the `__prerender_bypass` cookie without authenticating anyone.
  Check: the Draft Mode handler authenticates the CMS or caller (a high-entropy shared secret where appropriate), validates the requested content id against the trusted content source, and redirects to a server-established path, never to an untrusted query parameter. Owner: `backend`. Source: Next.js.
- **Server Action origin allowance too broad or host spoofable.** Next.js compares the request `Origin` with the host, which only helps when the host value is trustworthy.
  Check: `serverActions.allowedOrigins` lists only trusted application and proxy origins; on self-hosted deployments only trusted infrastructure can set `Host` or `X-Forwarded-Host`; the Origin check is not treated as a substitute for authentication, authorization or CSRF controls. Owner: `backend`. Source: Next.js.
- **Roles granted beyond need in Node services.** Authorization should follow least privilege, each role reaching only the resources it must use.
  Check: role and permission definitions (for example with an ACL module) grant each role only the resources it needs. Owner: `backend`. Source: Node.js.
- See `authorization.md` for object-level and tenant-level authorization patterns.

## Data crossing into the browser

- **Server data passed to the client unshaped.** App Router serializes values passed to Client Components, Server Action return values reach the client, and Pages Router props appear in the initial HTML.
  Check: values crossing to the client are explicit DTOs with only authorized, needed fields (selecting only required columns as extra defense); ORM records, session objects and configuration are never passed just because they are available; Express responses likewise return only the needed fields of user and other objects. Owner: `backend`. Source: Next.js, Node.js.
- **Secrets in page props or client components.** Values returned in `props` from `getStaticProps`, `getServerSideProps` and `getInitialProps` are visible to the browser.
  Check: no secret is sent to Client Components or returned in page props; any token intentionally sent to the browser is narrowly scoped and treated as exposed; configuration sent to the client is explicitly classified public. Owner: `backend`. Source: Next.js.
- **Non-public value behind a `NEXT_PUBLIC_` prefix.** Prefixed variables are inlined into client JavaScript.
  Check: only intentionally public values use the `NEXT_PUBLIC_` prefix. Owner: `frontend`. Source: Next.js.
- **Sensitive server module importable from client code.** `server-only` blocks client imports at build time, but neither it nor React taint APIs stop server code from returning sensitive data.
  Check: sensitive modules import `server-only`; taint APIs, where used, are defense in depth on top of DTO shaping. Owner: `backend`. Source: Next.js.
- See `xss-and-csp.md` for browser rendering sinks and React client concerns.

## Cache audience and invalidation

- **Cache entry reusable by a broader audience.** `use cache` keys include serializable arguments and captured closure values, so a missing audience dimension leaks one user's data to another.
  Check: each cached function or response has a classified audience; the key includes every verified dimension that changes the value or a cached authorization decision (user id, tenant id, permission version, locale), never a raw cookie or bearer token; identical content for all authorized callers is not duplicated per identity when authorization runs before return. Owner: `backend`. Source: Next.js.
- **User-specific data in a cache with no user input.** A `use cache` function without a user-specific argument serves the same result to everyone.
  Check: no `use cache` function returns user-specific data unless the user dimension is part of its inputs. Owner: `backend`. Source: Next.js.
- **Protected data in pre-authorization caches.** ISR, `getStaticProps` and shared CDN caching can serve a response before per-request authorization.
  Check: these hold only data the full cache audience may read; server-side data or `fetch` caches holding protected content authorize on every return path and key every content variant. Owner: `backend`. Source: Next.js.
- **Shared caching on personalized responses.** Shared `Cache-Control` directives on personalized `getServerSideProps` responses let intermediaries serve them to others.
  Check: personalized `getServerSideProps` responses carry no shared `Cache-Control` directives, and Express pages with sensitive data disable caching (for example with `nocache`), while non-sensitive pages stay cacheable. Owner: `backend`. Source: Next.js, Node.js.
- **Cached data outlives a permission change.** After role or tenancy changes, stale entries keep granting old access.
  Check: authorization or tenancy changes invalidate affected keys or tags, advance a permission version in the key, or rely on a bounded expiry. Owner: `backend`. Source: Next.js.
- **Revalidation callable by anyone.** `revalidatePath` and `revalidateTag` can be called from any server entry point (`updateTag` only from Server Actions) and amount to a mutation capability.
  Check: invalidation callers are authenticated and authorized, targets are derived from an authorized object or validated against constrained application-owned path and tag patterns, externally reachable invalidation handlers have abuse controls, and a global purge requires a correspondingly privileged operation. Owner: `backend`. Source: Next.js.
- **`use cache: private` treated as safe for over-broad data.** Its results are cached in browser memory and still delivered to that browser.
  Check: functions under `use cache: private` return only data the browser may receive. Owner: `backend`. Source: Next.js.
- See `http-headers-tls-and-caching.md` for HTTP and CDN cache controls.

## Next.js configuration as security code

- **Rewrite upstream selectable by the request.** Rewrites act as a URL proxy and matcher captures can flow into destinations.
  Check: external rewrite hosts come from a fixed allowlist or server-controlled registry; no header, host, cookie or query capture selects an upstream scheme, authority or port. Owner: `backend`. Source: Next.js.
- **Rewrite treated as an authorization boundary.** A rewrite masks the destination URL but direct requests to the destination still work.
  Check: each protected rewrite destination enforces equivalent authentication and authorization itself, or sits behind a trusted gateway whose network policy blocks direct access. Owner: `backend`. Source: Next.js.
- **Redirect target built from untrusted captures.** Captures selecting the scheme or authority of an external redirect create open redirects.
  Check: no untrusted capture selects an external redirect's scheme or authority, and interpolated path or query parts are validated (see `cross-origin-and-browser.md`). Owner: `backend`. Source: Next.js.
- **`images.remotePatterns` with omitted fields.** Omitted fields imply broad wildcards.
  Check: each `remotePatterns` entry specifies every restriction the app can enforce, allowing port, pathname or query variation only where required and accounted for. Owner: `backend`. Source: Next.js.
- **Image optimizer allowed to fetch private addresses.** `images.dangerouslyAllowLocalIP` can let users reach internal network content.
  Check: `images.dangerouslyAllowLocalIP` stays disabled unless a reviewed private-network use case requires it; see `ssrf.md` for any server-side fetch destination. Owner: `backend`. Source: Next.js.
- **Production browser source maps served.** `productionBrowserSourceMaps` makes Next.js emit and publicly serve original browser source.
  Check: `productionBrowserSourceMaps` is off unless an operational need is documented. Owner: `frontend`. Source: Next.js.
- **`next dev` serving production.** Development mode enables hot reloading and detailed error reporting.
  Check: production runs an optimized build with a production server or adapter, never `next dev`. Owner: `platform`. Source: Next.js.
- **Security config from environment not validated.** Hosts and origins assembled from environment variables are code.
  Check: at startup, hosts and origins are validated against an allowlist and other security settings against a schema, type or range, failing closed when a required value is missing or invalid. Owner: `backend`. Source: Next.js.
- **CSP nonce reused or weakened.** A nonce must be unpredictable and unique per response.
  Check: nonces are generated fresh in Proxy and applied during rendering; HTML carrying a nonce is not cached for reuse; nonce-based pages accept dynamic rendering (no static optimization, ISR or PPR), while statically rendered apps use a nonce-free CSP their resources permit; production policies carry no development-only directives such as `'unsafe-eval'`. Owner: `backend`. Source: Next.js.
- See `xss-and-csp.md` for CSP policy design.

## Node.js code execution and input handling

- **Input reaching `eval`, `child_process.exec` or `fs`.** `eval` with user input is remote code execution, `child_process.exec` passes its argument to `/bin/sh`, and unsanitized paths in `fs` cause file inclusion and traversal.
  Check: no request data reaches `eval()` or `child_process.exec`; `fs` calls receive only validated paths; such calls are used only where unavoidable. Owner: `backend`. Source: Node.js.
- See `injection.md` for OS command and argument injection defenses.
- **`node:vm` used as a sandbox.** `vm` is not a security mechanism.
  Check: no untrusted code is executed through `node:vm`. Owner: `backend`. Source: Node.js.
- **Query and body values assumed to be strings.** Express query parsing turns `?foo[]=`, `?foo[bar]=` and repeated keys into arrays, objects or nested trees.
  Check: input is validated against an allowlist of accepted values or an expected schema including type (for example with `validator`, and `express-mongo-sanitize` for MongoDB queries) before use. Owner: `backend`. Source: Node.js.
- See `injection.md` for input validation strategy.
- **Duplicate parameters interpreted unpredictably.** HTTP parameter pollution gives arrays where code expects one value.
  Check: `hpp` middleware (or equivalent handling) is applied to `req.query` and `req.body`. Owner: `backend`. Source: Node.js.
- **Output encoded for the wrong context.** `escape-html` covers HTML text and quoted ordinary attributes only, not JavaScript, CSS or URL contexts.
  Check: output encoding matches its destination context; user-supplied HTML that must be rendered goes through a maintained sanitizer such as DOMPurify (with `jsdom` server-side) or `sanitize-html`; `node-esapi` is not used. Owner: `backend`. Source: Node.js.
- **Auto-generated REST routes left enabled.** Frameworks such as Sails and Feathers generate endpoints that answer unmatched URLs.
  Check: every automatically generated route the app does not use is removed or disabled. Owner: `backend`. Source: Node.js.
- **Strict mode not enabled.** Sloppy mode keeps unsafe legacy features and silent errors.
  Check: CommonJS sources start with `"use strict";` (ES modules are strict by default). Owner: `backend`. Source: Node.js.
- **Objects that must not change left mutable.** Assigned properties default to writable, enumerable and configurable.
  Check: objects that must not be altered use `Object.defineProperty` with restrictive descriptors or `Object.preventExtensions()`. Owner: `backend`. Source: Node.js.

## Event loop, request size and brute force

- **No request body size limit.** Unbounded bodies exhaust memory or disk, and JSON parsing blocks the event loop.
  Check: body parsers set limits per content type (for example `express.json({ limit })` and `express.urlencoded({ limit })`), and request data is validated against the declared `Content-Type` so a changed header cannot bypass the limit. Owner: `backend`. Source: Node.js.
- **Blocking or racing operations on the event loop.** CPU-heavy work stalls all requests, and sync calls placed after an async call (for example `unlinkSync` after `readFile`) can run first, including authenticated actions running before an async authentication check completes.
  Check: blocking work runs asynchronously, and operations that depend on each other run in one ordered async flow. Owner: `backend`. Source: Node.js.
- **Event loop overload not shed.** A saturated server stops serving everyone.
  Check: the app monitors event loop lag (for example with `toobusy-js`) and returns `503` when over threshold. Owner: `backend`. Source: Node.js.
- **Regex with catastrophic backtracking.** Nested repetition and overlapping alternation make a regex hang on crafted input, blocking the single thread.
  Check: regexes applied to user input avoid grouping with repetition and overlapping alternation, or are checked with a ReDoS detector. Owner: `backend`. Source: Node.js.
- **Login without brute-force controls.** Login endpoints need throttling, delay or lockout.
  Check: login routes use a limiter such as `express-bouncer`, `express-brute` or `rate-limiter` with a shared store (never `ExpressBrute.MemoryStore` in production), plus CAPTCHA or account lockout where appropriate. Owner: `backend`. Source: Node.js.
- See `authentication.md` for lockout and credential stuffing defenses and `abuse-dos-and-business-logic.md` for DoS layering.

## Error and exception handling

- **Process resumes after `uncaughtException`.** The application is in an unknown state after an uncaught exception.
  Check: the `uncaughtException` handler releases resources, logs, and exits; error responses never include stack traces. Owner: `backend`. Source: Node.js.
- **EventEmitter without an `error` listener.** An unhandled `error` event is thrown and crashes the process.
  Check: every EventEmitter the app creates or consumes has an `error` listener. Owner: `backend`. Source: Node.js.
- **Errors lost in async callbacks.** Express does not handle errors raised in async calls inside routes unless they are passed on, and nested callbacks drop errors.
  Check: callbacks receive an `Error` as first argument and propagate it; async code uses flat promise chains ending in `.catch` or `async`/`await` with `try`/`catch`. Owner: `backend`. Source: Node.js.
- **No application activity logging.** Logs support incident response and detection.
  Check: a logger such as Winston, Bunyan or Pino records application activity, with errors routed to a separate transport. Owner: `backend`. Source: Node.js.
- See `logging-and-error-handling.md` for what to log and how.

## Cookies, headers and CSRF in Express

- **Session cookie flags missing.** `httpOnly`, `secure` and `sameSite` are the important session cookie flags.
  Check: `express-session` (and other session cookies) set `cookie: { secure: true, httpOnly: true, sameSite: ... }`, with domain, path and expiry scoped appropriately. Owner: `backend`. Source: Node.js.
- See `sessions-and-cookies.md` for session lifecycle.
- **Security headers not set.** `helmet` sets a baseline of headers.
  Check: the app uses `helmet()` or its parts: `hsts`, `frameguard`, `xssFilter` (sets `X-XSS-Protection: 0`), `noSniff`, `ieNoOpen`, `hidePoweredBy` (removing `X-Powered-By`), and a `contentSecurityPolicy` whose directives are verified with a CSP checker because helmet barely validates them. Owner: `backend`. Source: Node.js.
- See `http-headers-tls-and-caching.md` for header values.
- **Deprecated `csurf` used for CSRF.** `csurf` has an unfixed vulnerability and is deprecated.
  Check: `csurf` is absent and CSRF protection comes from a maintained mechanism (see `cross-origin-and-browser.md`). Owner: `backend`. Source: Node.js.

## Node.js runtime permissions

- **Node process runs with unrestricted permissions.** The Permission Model (stable from Node.js v23.5.0, `--experimental-permission` before that) limits what a compromised process can touch.
  Check: the start command uses `--permission` with `--allow-fs-read` and `--allow-fs-write` scoped to required paths, and `--allow-child-process`, `--allow-worker`, `--allow-addons` and `--allow-wasi` only when needed. Owner: `platform`. Source: Node.js.
- **Allowed paths contain relative symlinks.** Symlinks are followed even when they point outside allowed paths.
  Check: no path granted by `--allow-fs-*` contains relative symbolic links. Owner: `platform`. Source: Node.js.

## Dependencies, linting and patching

- **Known-vulnerable npm packages.** Application security depends on its dependencies.
  Check: `npm audit` (or OWASP Dependency-Check or Retire.js) runs regularly and findings are fixed; see `supply-chain-and-dependencies.md` for the wider process. Owner: `dx`. Source: Node.js.
- **No security lint rules.** ESLint and JSHint include no security checks by default.
  Check: lint config enables a security ruleset such as `eslint-plugin-security` or `eslint-plugin-node-security`, rules are reviewed periodically, findings audited, and a SAST tool complements them. Owner: `dx`. Source: Node.js.
- **Unpatched Next.js release.** Advisories such as CVE-2025-29927, the Server Action SSRF fixed in 14.1.1, and CVE-2024-46982 affect older versions.
  Check: `next` is pinned to a supported, patched release. Owner: `dx`. Source: Next.js.

## Verifying the boundaries

- **No inventory of Next.js entry points and caches.** Unclassified surfaces are where controls get omitted.
  Check: tests derive an inventory from the route and source tree (Server Actions, Route Handlers, Pages API Routes, Draft Mode entry points, data loaders, Proxy matchers, cached functions, invalidation call sites, rewrites, redirects, CSP config, source map settings, remote image patterns) and fail when a new entry point or cache lacks a classification. Owner: `qa`. Source: Next.js.
- **Handlers only tested through the UI.** Direct calls are how attackers reach actions and handlers.
  Check: tests call actions and handlers directly without loading the page and assert that unauthenticated, unauthorized, wrong-owner and wrong-tenant requests fail, and that public operations keep their abuse controls. Owner: `qa`. Source: Next.js.
- **Proxy-protected routes not tested without Proxy.** An unmatched path must still be denied.
  Check: tests exercise an unmatched or bypassed-Proxy path for protected route families and prove the handler or data boundary denies access. Owner: `qa`. Source: Next.js.
- **Serialized payloads not inspected.** Server-only fields can leak through HTML, RSC payloads, Pages Router data and Server Action responses.
  Check: tests assert that these responses contain no server-only fields. Owner: `qa`. Source: Next.js.
- **Scoped caches not tested across identities.** Positive-path cache tests miss missing audience keys.
  Check: tests fill the cache as identity A, request the same route and object ids as identity B, and repeat after role or tenant changes and revalidation. Owner: `qa`. Source: Next.js.
- **Draft Mode and invalidation handlers untested.** These are privileged state changes.
  Check: tests call them directly and prove unauthorized callers cannot obtain `__prerender_bypass`, expose unpublished content, or invalidate content. Owner: `qa`. Source: Next.js.
