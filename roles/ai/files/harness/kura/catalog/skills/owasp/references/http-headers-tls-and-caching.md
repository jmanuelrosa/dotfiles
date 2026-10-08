# HTTP Headers, TLS and Caching

When to read: the brief, diff, or assessed surface touches HTTP response headers, Cache-Control or CDN/reverse-proxy cache rules, cache keys (HTTP or application-level), TLS termination, protocol or cipher configuration, certificates, HSTS, or HTTP-to-HTTPS redirects.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [HTTP Security Response Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html), [HTTP Strict Transport Security](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html), [Transport Layer Security](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html), [Transport Layer Protection](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html), [TLS Cipher String](https://cheatsheetseries.owasp.org/cheatsheets/TLS_Cipher_String_Cheat_Sheet.html), [Web Cache Security](https://cheatsheetseries.owasp.org/cheatsheets/Web_Cache_Security_Cheat_Sheet.html)

## Contents

- Shared caches and sensitive responses
- Cache keys, poisoning and deception
- Application-level caches
- TLS protocols, ciphers and key exchange
- HTTPS everywhere and HSTS
- Certificates
- Browser security headers
- Information-leaking and obsolete headers
- Cache operations, testing and monitoring

## Shared caches and sensitive responses

- **Sensitive response missing `Cache-Control: no-store`.** Authenticated, personalized, tenant-specific or otherwise sensitive responses must not be stored by browsers, proxies or CDNs; without `no-store` one stored response is replayed to other users or survives on the client after logout. `no-store` alone is sufficient on a modern stack; the legacy `no-cache, no-store, must-revalidate` plus `Pragma`/`Expires` set adds nothing unless pre-HTTP/1.1 caches must be supported.
  Check: every route returning user or tenant data sets `Cache-Control: no-store` (or at most `private`) explicitly; fix by adding it at the handler or middleware, not by relying on defaults. Owner: `backend`. Source: HTTP Headers, Transport Layer Security, Web Cache Security.
- **`no-cache` mistaken for "do not store".** `no-cache` permits storage and only requires revalidation before reuse, so sensitive data still lands in caches.
  Check: sensitive routes using `no-cache` without `no-store` are flagged; replace with `no-store`. Owner: `backend`. Source: HTTP Headers, Web Cache Security.
- **Explicit cache policy per route, not defaults.** Every route needs a defined cache policy, defaulting to no shared caching for sensitive content; relying on heuristic or framework default caching exposes protected content. Error pages, redirects and authentication responses also need explicit policies, and a sensitive route with a missing, malformed or conflicting policy must fail closed.
  Check: a route-level cache policy exists (middleware, CDN rules, or per-handler headers) covering error, redirect and auth responses; sensitive routes default to `no-store`. Owner: `backend`. Source: HTTP Headers, Web Cache Security.
- **Cookies or `Set-Cookie` assumed to make a response private.** Authentication, cookies, TLS and `Set-Cookie` do not prevent caching; a response influenced by `Authorization` or session cookies must not be `public` or carry `s-maxage` unless shared caching was deliberately designed and reviewed.
  Check: grep for `public` and `s-maxage` on routes that read `Authorization` or session cookies; remove or document the reviewed design. Owner: `backend`. Source: Web Cache Security.
- **`private` used where shared caching must be prevented.** `private` allows only non-shared caches to store the response but those may still persist it; use it only when browser storage is acceptable, combined with `no-cache` when revalidation is required.
  Check: `private` responses carry no data that must not persist on the client; otherwise use `no-store`. Owner: `backend`. Source: HTTP Headers, Web Cache Security.
- **CDN rule overriding origin `Cache-Control`.** CDN or reverse-proxy rules that cache by status code, path pattern or file extension, or override origin headers, silently weaken a secure origin policy; browser and shared-cache lifetimes must be set independently with the appropriate directives.
  Check: CDN/proxy config contains no override or extension-based caching rule that covers authenticated routes. Owner: `cloud`. Source: Web Cache Security.
- **Old entries left after switching a route to `no-store`.** The directive does not delete what is already stored.
  Check: a change that tightens a route's cache policy is accompanied by a purge step or runbook entry. Owner: `cloud`. Source: Web Cache Security.
- **Client-managed caches ignore HTTP cache headers.** The browser Cache API does not honor `Cache-Control`, so sensitive responses must be explicitly excluded from application-managed caches (service workers) and existing sensitive entries removed.
  Check: service-worker or Cache API code filters out authenticated/sensitive responses and clears them on logout. Owner: `frontend`. Source: HTTP Headers.
- **No client-side cleanup at sign-out.** When cached client data must be cleared on logout, send `Clear-Site-Data` (for example `"cache", "cookies", "storage"`); `Cache-Control` does not govern the cookie jar, which is controlled by cookie attributes.
  Check: the logout response sets `Clear-Site-Data` where client data must be removed. Owner: `backend`. Source: Transport Layer Security.

## Cache keys, poisoning and deception

- **Unkeyed input influences a cacheable response (cache poisoning).** Every request input that can change a cacheable response must be in the cache key or rejected for that route; unkeyed headers, or a body on a `GET`, must not alter a cacheable response, otherwise one poisoned response is served to every visitor.
  Check: cacheable handlers read no headers, cookies or body fields absent from the cache key; key includes method, scheme, host, normalized path and all relevant query parameters. Owner: `backend`. Source: Web Cache Security.
- **Forwarded headers trusted from any client.** `Forwarded` and `X-Forwarded-*` may be trusted only when added or replaced by a trusted proxy; host and scheme must be canonicalized before generating links, redirects or security-sensitive headers, and unvalidated request metadata must not be reflected into cached HTML, JSON, redirects or headers.
  Check: proxy-trust configuration names specific proxies; link and redirect generation uses a canonical configured host, not the raw `Host`/`X-Forwarded-Host`. Owner: `backend`. Source: Web Cache Security.
- **Dynamic route accepts static-looking suffixes (cache deception).** If `/account/profile/image.css` resolves to the same personalized handler as `/account/profile`, an extension-based cache stores private content. Dynamic routes must reject unexpected path segments and suffixes, and cache eligibility must come from an allowlisted route and response policy, not file extension alone.
  Check: router uses strict matching for authenticated routes (no catch-all trailing segments); CDN caches only allowlisted static paths. Owner: `backend`. Source: Web Cache Security.
- **Extension and `Content-Type` not cross-checked before caching.** A static asset should be cached only when the URL extension agrees with the response `Content-Type`.
  Check: edge config enables an extension/Content-Type consistency check or caches only a dedicated static namespace. Owner: `cloud`. Source: Web Cache Security.
- **Static and dynamic content share a namespace.** Separate static assets from dynamic application routes by hostname or an unambiguous path namespace where practical.
  Check: static assets are served from a distinct host or prefix that the cache rules target exclusively. Owner: `architect`. Source: Web Cache Security.
- **`Vary: Cookie` used as an authorization boundary.** `Vary` is for representation-selecting headers such as `Accept-Encoding` or `Accept-Language`; personalized responses should disable shared caching instead.
  Check: no route relies on `Vary: Cookie` to separate users; such routes use `no-store` or `private`. Owner: `backend`. Source: Web Cache Security.
- **Cache and origin disagree on normalization.** CDN, reverse proxy and origin must apply the same URL normalization and parameter handling; when the CDN normalizes its key, it must forward the normalized form. Ambiguous requests (conflicting host info, duplicate parameters with inconsistent meaning, malformed path encodings) must be rejected.
  Check: edge normalization settings match origin routing; origin rejects duplicate or malformed parameters on cacheable routes. Owner: `cloud`. Source: Web Cache Security.
- **Query parameters dropped from the key without proof.** Ignore or strip query parameters from a cache key only after proving they cannot change routing, authorization or content.
  Check: every ignored parameter in CDN key config has a documented justification. Owner: `cloud`. Source: Web Cache Security.
- **Tenant or user identity taken from untrusted input in cache keys.** Tenant and user identifiers in keys must come from authenticated server-side context, not a header or query parameter.
  Check: key-building code reads tenant/user from the verified session or token. Owner: `backend`. Source: Web Cache Security.
- **Secrets in cache keys or purge URLs.** Keys appear in logs and admin interfaces, so session tokens, API keys, credentials and session identifiers must not be part of keys, logs or purge URLs.
  Check: cache-key builders and purge calls contain no token or credential values. Owner: `backend`. Source: Web Cache Security.

## Application-level caches

- **Cache hit bypasses authorization.** In-memory, database and distributed caches leak data even with HTTP caching disabled; the current request must be authorized before cached data is returned, and a hit must not skip object-level or tenant-level checks.
  Check: the authorization check runs before the cache lookup or on the cached value, never only on the miss path. Owner: `backend`. Source: Web Cache Security.
- **Application cache key omits tenant or authorization dimension.** Keys must be namespaced by environment and application and include tenant identity plus every authorization-relevant resource dimension, using a structured, versioned format (environment, resource version, tenant id, resource type, resource id).
  Check: key templates include environment, tenant and a format version. Owner: `backend`. Source: Web Cache Security.
- **Cached authorization decisions.** Avoid caching final authorization decisions unless the key holds the complete subject, object, action and policy version and the lifetime is tightly bounded; version key formats so permission-model changes cannot reuse incompatible entries.
  Check: any cached allow/deny result is keyed on subject, object, action and policy version with a short TTL. Owner: `backend`. Source: Web Cache Security.
- **Unrestricted access to cache administration.** Access to cache contents, configuration, statistics and purge operations must be restricted.
  Check: cache admin endpoints and console access require privileged roles; IaC restricts network access to cache servers. Owner: `cloud`. Source: Web Cache Security.

## TLS protocols, ciphers and key exchange

- **TLS 1.0/1.1 or SSLv2/v3 enabled.** Endpoints must default to TLS 1.3 and may support TLS 1.2 for compatibility; TLS 1.0 and 1.1 (deprecated by RFC 8996) and SSLv2/SSLv3 must be disabled. End-of-life clients that must be served go on a dedicated endpoint with no access to sensitive data, never by weakening the primary one.
  Check: TLS policy in load balancer, ingress or server config sets a minimum of TLS 1.2 with 1.3 enabled. Owner: `cloud`. Source: Transport Layer Security.
- **No downgrade protection.** The `TLS_FALLBACK_SCSV` extension should be enabled to prevent protocol downgrade attacks.
  Check: server or TLS library config does not disable fallback SCSV. Owner: `cloud`. Source: Transport Layer Security.
- **Weak or non-forward-secret cipher suites.** TLS 1.3 uses the standard AEAD suites (AES-GCM, ChaCha20-Poly1305); TLS 1.2 should prefer ECDHE with AEAD and avoid CBC. Null, anonymous (`TLS_*_anon_*`), EXPORT, RSA key transport (`TLS_RSA_*`) and static DH (`TLS_DH_*`, `TLS_ECDH_*`) suites must be disabled; finite-field `TLS_DHE_*` is discouraged in TLS 1.2.
  Check: the cipher string or managed TLS policy excludes these families. Owner: `cloud`. Source: Transport Layer Security.
- **Key-exchange groups not set explicitly.** Configure `supported_groups` to named groups (for example `X25519MLKEM768`, `x25519`, `prime256v1`, `secp384r1`, `x448`, and RFC 7919 `ffdhe*` groups); for TLS 1.2 or earlier do not set custom Diffie-Hellman parameters, since server-generated parameters caused DoS and weakness issues.
  Check: server config lists named groups/curves and contains no custom DH parameter file. Owner: `cloud`. Source: Transport Layer Security.
- **TLS compression enabled.** TLS compression must be disabled to prevent CRIME-style recovery of session cookies.
  Check: no TLS compression option is enabled in server or library config. Owner: `cloud`. Source: Transport Layer Security.
- **Unpatched TLS libraries.** TLS libraries have a long history of critical bugs and must be kept up to date with security patches.
  Check: base images and dependency manifests pin a currently supported OpenSSL/TLS library and receive automated updates. Owner: `platform`. Source: Transport Layer Security.
- **TLS configuration never tested.** Hardened TLS configuration should be verified after each change.
  Check: CI or a release checklist includes a TLS configuration test step against the deployed endpoint config. Owner: `qa`. Source: Transport Layer Security.

## HTTPS everywhere and HSTS

- **Page or endpoint served over plain HTTP.** TLS must be used for all pages, not only sensitive ones. Public sites may listen on port 80 only to issue an immediate 301 to HTTPS backed by HSTS; API-only endpoints should disable HTTP entirely, or fail unencrypted requests rather than redirect them.
  Check: listener config exposes port 80 only as a permanent redirect for browser sites; API listeners accept HTTPS only. Owner: `cloud`. Source: Transport Layer Security.
- **Mixed content on HTTPS pages.** A TLS page must not load scripts, CSS or other resources over HTTP.
  Check: templates and asset URLs contain no `http://` resource references. Owner: `frontend`. Source: Transport Layer Security.
- **Cookie without `Secure`.** All cookies should carry `Secure`, even when the site does not listen on port 80, because an active MITM can spoof an HTTP endpoint.
  Check: every cookie set in code or config has `Secure`. Owner: `backend`. Source: Transport Layer Security. See `sessions-and-cookies.md` for the remaining cookie attributes.
- **HSTS missing or too narrow.** Send `Strict-Transport-Security: max-age=63072000; includeSubDomains` (two years); omitting `includeSubDomains` leaves subdomain-based cookie attacks open. A short `max-age` (for example 86400) is appropriate during initial rollout.
  Check: HTTPS responses set HSTS with `includeSubDomains` and a long `max-age` once rollout is verified. Owner: `backend`. Source: HTTP Headers, HTTP Strict Transport Security, Transport Layer Security.
- **HSTS `preload` sent without readiness.** `preload` can have permanent consequences: every present and future subdomain must serve HTTPS, the domain still has to be submitted to the list, and a long `max-age` with an expired or revoked certificate locks users out. Review the preload requirements and removal process first.
  Check: `preload` is only added with a recorded decision that all subdomains are HTTPS-only and certificate renewal is automated. Owner: `architect`. Source: HTTP Headers, HTTP Strict Transport Security.

## Certificates

- **RSA key under 2048 bits or unprotected private key.** Keys must be strong enough for the certificate lifetime (RSA at least 2048 bits) and protected with filesystem permissions and other access controls.
  Check: certificate requests and IaC specify RSA 2048+ (or an equivalent EC key); private keys are stored in a secret store or restricted files. Owner: `cloud`. Source: Transport Layer Security.
- **Certificate signed with MD5 or SHA-1.** Certificates should use SHA-256.
  Check: certificate signing configuration uses SHA-256. Owner: `cloud`. Source: Transport Layer Security.
- **Wrong names in the certificate.** The FQDN must be in the SAN (and the primary FQDN in CN); do not include non-qualified hostnames, IP addresses, or internal domain names on externally facing certificates (use separate certificates for internal and external FQDNs).
  Check: certificate SAN lists in IaC contain only public FQDNs for public endpoints. Owner: `cloud`. Source: Transport Layer Security.
- **Wildcard certificate shared across trust levels.** Use wildcards only for genuine need (prefer ACME per-system certificates), never across systems at different trust levels (for example a VPN gateway and a public web server), scope them to a subdomain where possible, terminate TLS on one reverse proxy so the key lives on one system, and keep an inventory of systems sharing a certificate.
  Check: wildcard certificates in IaC are attached only to same-trust-level resources and are inventoried. Owner: `cloud`. Source: Transport Layer Security.
- **Untrusted or inappropriate CA.** Internet-facing certificates must come from a publicly trusted CA; internal applications may use an internal CA. OV and EV give no additional browser-enforced protection and their issuance overhead should be weighed as an availability risk.
  Check: public endpoints use a public CA; certificate type choice is justified. Owner: `cloud`. Source: Transport Layer Security.
- **No CAA records.** CAA DNS records should restrict which CAs may issue for the domain and its subdomains.
  Check: DNS IaC includes CAA records for each production domain. Owner: `cloud`. Source: Transport Layer Security, HTTP Headers.
- **mTLS assumed to protect against a bad server certificate.** Mutual TLS authenticates the client but does not protect data if the client accepts an attacker's server certificate; server identity validation must be enforced independently. mTLS should be considered for high-value applications and APIs, especially with technically sophisticated or same-organization users.
  Check: mTLS clients keep server certificate and hostname verification enabled. Owner: `backend`. Source: Transport Layer Security. See `mobile.md` for public key pinning in apps and thick clients.

## Browser security headers

- **Framing allowed.** Pages with interactive content should forbid framing, preferably via CSP `frame-ancestors`, otherwise `X-Frame-Options: DENY`; the header gives no protection on redirects or JSON APIs.
  Check: HTML responses set `frame-ancestors` or `X-Frame-Options: DENY`. Owner: `backend`. Source: HTTP Headers. See `cross-origin-and-browser.md` for clickjacking defense in depth.
- **MIME sniffing not disabled.** Set `X-Content-Type-Options: nosniff` and a correct `Content-Type` on every response; HTML responses need `charset` (for example `text/html; charset=UTF-8`) to prevent XSS via charset confusion.
  Check: global middleware sets `nosniff`; HTML responses declare `charset=UTF-8`. Owner: `backend`. Source: HTTP Headers.
- **User-provided files rendered inline.** Serve user files with `Content-Disposition: attachment`, `Content-Type: application/octet-stream` for unknown or binary types, and `X-Content-Type-Options: nosniff`.
  Check: download handlers for user content set all three headers. Owner: `backend`. Source: HTTP Headers. See `file-upload.md` for upload handling.
- **`X-XSS-Protection` enabled.** The legacy auditor can create XSS in otherwise safe sites; do not set it or set `X-XSS-Protection: 0`, and rely on a CSP that disables inline script.
  Check: no config sets `X-XSS-Protection: 1`. Owner: `backend`. Source: HTTP Headers. See `xss-and-csp.md` for CSP configuration.
- **Referrer policy left to browser defaults.** Set `Referrer-Policy: strict-origin-when-cross-origin` explicitly.
  Check: responses set an explicit `Referrer-Policy`. Owner: `backend`. Source: HTTP Headers.
- **CORS `Access-Control-Allow-Origin: *` on non-public resources.** When CORS is used, name specific origins; `*` is acceptable only for genuinely public APIs.
  Check: CORS config lists explicit origins unless the API is documented as public. Owner: `backend`. Source: HTTP Headers.
- **No cross-origin isolation headers.** For browser-rendered documents set `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Embedder-Policy: require-corp` (cross-origin resources then need CORP or CORS permission from their server) and `Cross-Origin-Resource-Policy: same-site`.
  Check: HTML and resource responses set COOP, COEP and CORP, with third-party resources verified to grant permission. Owner: `backend`. Source: HTTP Headers.
- **Unused browser features not disabled.** Set `Permissions-Policy` disabling every feature the site does not need (for example `geolocation=(), camera=(), microphone=()`) or allowing them only to authorized origins, so an injection cannot enable them.
  Check: a `Permissions-Policy` header exists and lists unused features as `()`. Owner: `backend`. Source: HTTP Headers.
- **Private content indexable.** Use `X-Robots-Tag: noindex, nofollow` on private or sensitive non-HTML resources (it binds only compliant crawlers).
  Check: private file routes set `X-Robots-Tag: noindex, nofollow`. Owner: `backend`. Source: HTTP Headers.
- **DNS prefetch leaking to uncontrolled link targets.** If the site does not control its links, `X-DNS-Prefetch-Control: off` reduces leakage, but it is non-standard and must not be relied on for anything production-sensitive.
  Check: user-generated-link pages set the header where needed, without depending on it. Owner: `backend`. Source: HTTP Headers.
- **Security headers missing on some responses or duplicated.** Proxies may only add headers for certain status codes (nginx without `always`) or emit duplicates from separate header tables (Apache `Header set` versus `Header always set`); unset then set with the always variant so headers reach every response once.
  Check: proxy config uses the always-variant directives and unsets before setting. Owner: `cloud`. Source: HTTP Headers.

## Information-leaking and obsolete headers

- **Stack fingerprinting headers.** Remove `X-Powered-By`, `X-AspNet-Version` and `X-AspNetMvc-Version`, and remove `Server` or set it to a non-informative value.
  Check: framework and server config disables version headers. Owner: `backend`. Source: HTTP Headers.
- **`Expect-CT` still sent.** It is obsolete; remove it from existing code.
  Check: no config emits `Expect-CT`. Owner: `backend`. Source: HTTP Headers.
- **`Public-Key-Pins` still sent.** HPKP is unsupported; remove `Public-Key-Pins` and `Public-Key-Pins-Report-Only` and rely on Certificate Transparency and CAA records.
  Check: no config emits HPKP headers. Owner: `backend`. Source: HTTP Headers, Transport Layer Security.

## Cache operations, testing and monitoring

- **No targeted purge mechanism.** Maintain and test a purge for individual keys, tags or narrow route groups before an incident; after poisoning, purge every affected layer and fix the key or origin behavior before re-enabling caching, since purging alone does not fix the vulnerability.
  Check: IaC or runbooks define scoped purge operations and a poisoning response procedure. Owner: `sre`. Source: Web Cache Security.
- **Cache behavior untested through the real path.** Tests should run through the production CDN/proxy path: two users and tenants on the same URL, one varied input at a time, static suffixes appended to authenticated routes, and authorization changes, logout, updates and purges against stored entries.
  Check: an integration or pre-release test suite covers cross-user, cross-tenant and suffix-append cases. Owner: `qa`. Source: Web Cache Security.
- **No cache anomaly monitoring.** Monitor for cache hits on authenticated routes, abrupt hit-ratio changes, unusual forwarded headers and repeated purges; log cache-status and routing metadata without secrets or full sensitive bodies.
  Check: edge logs capture cache status and alerting covers authenticated-route hits. Owner: `sre`. Source: Web Cache Security.
