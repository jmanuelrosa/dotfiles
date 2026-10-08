# Authentication

When to read: the brief, diff, or assessed surface touches login, registration, password storage or hashing, password policy, password reset or account recovery, email verification or email change, account lockout and anti-automation on login, security questions, OIDC sign-in or federated account linking, or where authentication is enforced (edge gateway, sidecar, service).
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [Authentication Patterns](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Patterns_Cheat_Sheet.html), [Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html), [Choosing and Using Security Questions](https://cheatsheetseries.owasp.org/cheatsheets/Choosing_and_Using_Security_Questions_Cheat_Sheet.html), [Credential Stuffing Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html), [Email Validation and Verification](https://cheatsheetseries.owasp.org/cheatsheets/Email_Validation_and_Verification_Cheat_Sheet.html), [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

## Contents

- Password storage
- Credential verification and transport
- Authentication architecture and trust boundaries
- Password reset and account recovery
- Re-authentication and sensitive account changes
- Federated sign-in and account linking
- User enumeration
- Brute force, credential stuffing and automation
- Password policy
- Email as identifier
- Security questions (legacy only)
- Logging, monitoring and notification
- Login form usability for password managers

## Password storage

- **Passwords stored reversibly or in plaintext.** Passwords must be hashed with a slow, salted password hashing algorithm (Argon2id, scrypt, bcrypt, PBKDF2), never stored in plaintext, encrypted, or hashed with a fast hash such as SHA-256, MD5 or SHA-1. Encrypt only when the plaintext is genuinely needed to log in to a legacy system with no modern delegation option, and prefer an architecture that removes that need.
  Check: the credential write path calls a password hashing function, not a general digest, cipher, or raw column write; replace fast hashes and encryption with Argon2id. Owner: `backend`. Source: Password Storage.
- **Argon2id below the published minimum.** Use Argon2id with one of the equivalent minimums: m=47104 (46 MiB) t=1 p=1, m=19456 (19 MiB) t=2 p=1, m=12288 (12 MiB) t=3 p=1, m=9216 (9 MiB) t=4 p=1, or m=7168 (7 MiB) t=5 p=1; the first two must not be used with Argon2i. Raising parallelism does not substitute for memory or passes, and parameters should be benchmarked on the target system.
  Check: the hashing config names the `id` variant and memory/iteration values at or above one of these rows; reject Argon2i/Argon2d or lower values. Owner: `backend`. Source: Password Storage.
- **scrypt used where Argon2id is available, or below minimum cost.** Use scrypt only when Argon2id is unavailable, with one of: N=2^17 (128 MiB) r=8 p=1, N=2^16 r=8 p=2, N=2^15 r=8 p=3, N=2^14 r=8 p=5, N=2^13 r=8 p=10.
  Check: scrypt N, r, p match or exceed one of these rows. Owner: `backend`. Source: Password Storage.
- **bcrypt below work factor 10 or without the 72-byte limit.** Use bcrypt only in legacy systems where Argon2 and scrypt are unavailable, with a work factor as high as the server allows and at least 10, and enforce a maximum password length of 72 bytes (or the implementation's smaller limit) so input is not silently truncated.
  Check: bcrypt cost is >= 10 and the input path rejects passwords over 72 bytes rather than truncating. Owner: `backend`. Source: Password Storage.
- **bcrypt pre-hash with a plain fast hash.** Pre-hashing with a raw fast hash (for example `bcrypt(sha512(pw))`) enables password shucking and null-byte collisions and is only as strong as the fast hash. If pre-hashing is unavoidable, base64-encode an HMAC-SHA384 of the password keyed with a pepper stored outside the database, then bcrypt that.
  Check: any digest applied before bcrypt is a keyed HMAC whose output is base64-encoded and whose key is not in the database. Owner: `backend`. Source: Password Storage.
- **PBKDF2 iteration count below the FIPS recommendation.** When FIPS-140 compliance is required, use PBKDF2 with HMAC-SHA-256 at 600,000 iterations or more (HMAC-SHA-512: 220,000; HMAC-SHA1: 1,400,000 and legacy only, never for new systems). Use an implementation that pre-hashes long passwords once rather than per iteration, or a salted manual pre-hash, to avoid long-password denial of service.
  Check: PBKDF2 PRF and iteration count meet the table; SHA1 appears only in legacy verification paths. Owner: `backend`. Source: Password Storage.
- **Salt missing, shared, or hand-rolled.** Each password must get a unique random salt; use the library's built-in salt generation rather than managing salts by hand.
  Check: no constant or per-application salt is passed to the hash call; the stored hash string carries its own salt. Owner: `backend`. Source: Password Storage.
- **Pepper stored with the hashes.** A pepper (optional defense in depth) is a secret shared across all passwords, must be generated securely, and must be stored in a secrets vault or HSM, never alongside the hashes. Pre-hash peppers are random values; post-hash peppers act as the HMAC key over the stored hash. Rotating a compromised pepper requires forcing affected users to reset passwords.
  Check: the pepper is loaded from a secret store, not a DB column or source file, and a rotation procedure exists. Owner: `backend`. Source: Password Storage.
- **Work factor untuned or unbounded.** Tune the work factor so hashing stays under one second on production hardware; too high a factor lets login floods exhaust CPU. Increase it over time by re-hashing at next successful login, and consider expiring hashes that never upgrade.
  Check: cost parameters are configurable (not hardcoded), a rehash-on-login path compares stored parameters to current ones. Owner: `backend`. Source: Password Storage.
- **Legacy hash algorithm with no upgrade path.** Re-hash legacy MD5/SHA-1 hashes with the modern algorithm at next login and expire them; for inactive users either expire and delete the hash and force a reset, or wrap the old hash (for example `bcrypt(md5(pw))`) and replace it with a direct hash on next login. Store algorithm and parameters with the hash in a standard format such as the PHC string format so mixed algorithms can coexist.
  Check: stored hashes are self-describing (algorithm and cost prefix) and a migration path exists for any legacy algorithm still present. Owner: `backend`. Source: Password Storage.
- **Password input altered before hashing.** The hashing library must accept the full Unicode range and NULL bytes, and the input must not be reduced in entropy (truncated, case-folded, stripped) before hashing.
  Check: no normalization, truncation or character filtering occurs between the request body and the hash call. Owner: `backend`. Source: Password Storage, Authentication.

## Credential verification and transport

- **Password hash compared with a non-constant-time or loosely typed comparison.** Verify passwords with the language or framework's password verification function. Where unavailable, the comparison must bound input length, set explicit types on both operands (to stop type juggling such as PHP magic hashes), and run in constant time.
  Check: login code calls a library verify function, not `==` on hash strings. Owner: `backend`. Source: Authentication.
- **Login or authenticated pages reachable without TLS.** The login page and every authenticated page must be served exclusively over TLS so the form action cannot be rewritten and the session id is never sent in clear.
  Check: routes, ingress and redirects force HTTPS for login and all post-login routes. Owner: `backend`. Source: Authentication.
- **Internal or service accounts able to log in through the public UI.** Accounts used internally (backend, middleware, database) must not be able to log in to any front-end user interface.
  Check: the login handler rejects service and technical account types. Owner: `backend`. Source: Authentication.
- **Internal identity provider reused for public access.** Do not use the authentication solution used internally (IdP, AD) for unsecured public or DMZ access.
  Check: public-facing apps point to a different IdP or tenant than internal staff systems. Owner: `architect`. Source: Authentication.
- **Third-party apps holding user passwords.** Third-party, mobile or desktop clients must not store the user's password; use a delegated token protocol (OAuth 2.0/2.1 for API authorization, OIDC for authentication) instead.
  Check: no integration asks users for their password to store or replay it. Owner: `architect`. Source: Authentication.
- **TLS client certificates used as the sole login for a public consumer site.** Client-certificate authentication fits intranets and single-device use, breaks behind TLS-intercepting proxies, and is generally unsuitable for public consumer sites; where used, consider combining it with a password.
  Check: client-cert auth is limited to managed or internal audiences in the design. Owner: `architect`. Source: Authentication.

## Authentication architecture and trust boundaries

- **Sidecar identity headers spoofable by the caller.** When a sidecar proxy injects identity headers, the sidecar must strip or overwrite every inbound identity header, the application must accept traffic only from its sidecar (bind to loopback or enforce a network policy), or, where isolation cannot be guaranteed, the sidecar must sign injected headers with HTTP Message Signatures that bind identity to the intended service and request components, with the application verifying signer, freshness and replay.
  Check: proxy config sanitizes identity headers; the app listens on loopback or a NetworkPolicy restricts its port to the sidecar. Owner: `platform`. Source: Authentication Patterns.
- **Edge-propagated identity accepted unsigned.** When authentication happens at a gateway, propagate identity in a protected format (a newly issued JWT, HTTP Message Signatures, or another signed structure), and internal services must verify it and reject requests whose identity context is missing or unsigned.
  Check: downstream services verify a signature on the identity context instead of trusting a plain header. Owner: `backend`. Source: Authentication Patterns.
- **External access token forwarded to internal services.** Authenticate external actors at the edge and normalize them into a signed internal assertion; forward an external access token only to its intended recipients with validation at each, otherwise exchange it or issue an internal assertion.
  Check: services behind the gateway do not receive the raw external bearer token unless they are its audience. Owner: `architect`. Source: Authentication Patterns. See `tokens-and-federation.md` for identity propagation patterns.
- **Service-to-service calls unauthenticated behind the gateway.** Edge authentication does not cover internal calls; give every workload its own cryptographic identity (for example an X.509 SVID via SPIFFE) and enforce mutual TLS on every service-to-service connection so nothing can reach a service directly and anonymously.
  Check: mesh or service config requires mTLS between workloads (strict mode, no plaintext fallback). Owner: `platform`. Source: Authentication Patterns.
- **New service embeds its own credential store.** Do not build service-level embedded authentication in new systems; delegate to an IdP and verify issued proofs. Reserve embedded authentication for legacy code that cannot change, and then apply this file's rules.
  Check: a new service does not add its own user/password tables or login handler. Owner: `architect`. Source: Authentication Patterns.
- **Service verifying IdP proofs with incomplete checks.** Services that verify authentication proofs themselves must check expiration and use cryptography correctly; missing checks are a severe flaw of the code-mediated pattern.
  Check: token verification code checks signature, issuer, audience and expiry via a maintained library. Owner: `backend`. Source: Authentication Patterns.
- **Inconsistent auth proxy configuration across services.** All authentication proxies across the service landscape must be configured uniformly.
  Check: sidecar or proxy auth config comes from one shared template or policy, not per-service copies. Owner: `platform`. Source: Authentication Patterns.
- **Network-layer node authentication used as the only control.** IPsec or WireGuard node identity authenticates hosts, not users or workloads; treat it as a transport complement combined with edge-level or proxy-mediated authentication. For sensitive applications, use layer 3 segmentation to stop callers bypassing the sidecar.
  Check: the design does not grant access based on network location or node identity alone. Owner: `architect`. Source: Authentication Patterns.

## Password reset and account recovery

- **Reset token weak, reusable, or long-lived.** Reset and verification tokens and codes must come from a CSPRNG, be long enough to resist brute force, be linked to one user, be single-use and invalidated after use or expiry, expire after an appropriate period, and be stored securely (hashed, as for passwords). JWTs can replace random tokens but add their own risks.
  Check: token generation uses a CSPRNG, the record has an expiry and a used flag or is deleted on use, and only a hash is persisted. Owner: `backend`. Source: Forgot Password, Email Validation.
- **Reset URL built from the Host header.** Build reset links from a hard-coded base URL or one validated against an allowlist of trusted domains, never from the request `Host` header, and always over HTTPS.
  Check: the email template's link origin comes from config, not request headers. Owner: `backend`. Source: Forgot Password.
- **Reset page leaks the token via Referer.** The reset page must send `Referrer-Policy: no-referrer`, and token submission must be rate limited against brute force.
  Check: the reset route sets the header and sits behind a rate limiter. Owner: `backend`. Source: Forgot Password.
- **Reset request changes account state before a valid token.** Do not change the account (for example lock it) until a valid token is presented, and do not lock accounts in response to forgotten-password requests.
  Check: the request handler only issues a token and sends a message; no status field is written. Owner: `backend`. Source: Forgot Password.
- **Reset requests not throttled per account.** Rate limit reset requests per account and/or require CAPTCHA so an attacker cannot flood a user's inbox or SMS.
  Check: a per-account limiter wraps the reset-request endpoint. Owner: `backend`. Source: Forgot Password, Email Validation.
- **Reset delivered without a side channel.** Communicate the reset method through a side channel (email URL token, SMS PIN of 6 to 12 digits, or an offline method). A PIN or token may create a restricted session that only permits the password reset.
  Check: the session created from a reset PIN or token cannot access any route except setting a new password. Owner: `backend`. Source: Forgot Password.
- **Auto-login after password reset.** After reset, require the user to log in through the normal mechanism rather than logging them in automatically, require the new password twice, apply the same password policy as elsewhere, store it per Password Storage rules, and email a notification that never contains the password.
  Check: the reset-complete handler does not create an authenticated session and triggers a notification. Owner: `backend`. Source: Forgot Password.
- **Existing sessions survive a password reset.** Ask the user whether to invalidate all existing sessions, or invalidate them automatically.
  Check: reset completion calls a revoke-all-sessions path or offers it. Owner: `backend`. Source: Forgot Password.
- **Compromised-account recovery trusts recently changed recovery data.** When recovering a possibly compromised account, do not rely solely on recently added or changed recovery information, do not automatically restore superseded recovery addresses or numbers, promptly suspend compromised authenticators, review recovery addresses, phone numbers and MFA methods with the verified owner, invalidate existing sessions and outstanding reset or recovery links and codes, and notify all registered addresses with instructions to report unauthorized recovery.
  Check: the recovery flow reads recovery evidence with an age requirement and ends by revoking sessions and pending tokens. Owner: `backend`. Source: Forgot Password.
- **No recovery path exists.** Users must always have a way to recover their account, even if that means contacting support and proving identity to staff.
  Check: a documented support recovery procedure exists alongside self-service. Owner: `security`. Source: Forgot Password.

## Re-authentication and sensitive account changes

- **Sensitive change accepted on session alone.** Require current credentials (password, passkey or another already-bound authenticator, or MFA) before changing password, email address, payment details, shipping to a new address, adding trusted devices, or other sensitive account data, and after risk events such as account recovery, password reset, unusual login patterns, IP change, or device enrollment. Never substitute security questions. After re-authentication, invalidate the session and rotate tokens, and explain to the user why re-authentication is needed.
  Check: handlers for these operations require a fresh authentication timestamp or a credential in the request, then rotate the session. Owner: `backend`. Source: Authentication, Session Management.
- **Change-password without current password.** The change-password feature must require an authenticated active session and verification of the current password.
  Check: the change-password request includes and verifies the current password. Owner: `backend`. Source: Authentication.
- **Email change applied immediately.** Treat email change as an identity change: confirm the session, require re-authentication (MFA if enrolled, otherwise current password), store the new address as pending, create time-limited nonces, send a confirmation-required message to the new address and a message to the current address (notification-only with MFA; confirmation-required without MFA, and confirmation from both for high-risk systems), and apply the change only after confirmation.
  Check: the email column is not updated in the request handler; a pending-change record and two outbound messages exist. Owner: `backend`. Source: Authentication, Email Validation.
- **Help desk can be socially engineered into account changes.** Train administrators and help desk staff to follow the prescribed process and recognize social engineering.
  Check: support runbooks for email or credential changes require identity verification steps. Owner: `security`. Source: Authentication.
- **Risk signals used as authentication.** Use device fingerprints, IP addresses and remembered-device cookies only as risk signals, never as substitutes for authentication; require authentication or a valid authenticated session before exposing private account data, and stronger or fresher authentication for high-risk operations. Map each risk tier to an action (allow, CAPTCHA, step-up MFA, block, revoke session), apply decisions consistently across web, mobile and API clients, and define how tokens or cookies are revoked when a mid-session check escalates.
  Check: no route grants access because a remembered-device cookie or IP matched without a session; the risk policy is documented per tier. Owner: `architect`. Source: Authentication.
- See `mfa-passkeys-and-transaction-signing.md` for transaction authorization of sensitive operations.

## Federated sign-in and account linking

- **ID token accepted without full validation.** The relying party must validate the ID token issuer (`iss`), audience (`aud`), signature against the provider's JWKs, and expiry (`exp`), using a well-maintained library with provider discovery and JWKS endpoints; use the UserInfo endpoint for claims beyond the ID token. Use OIDC for authentication and OAuth only for API authorization.
  Check: the OIDC callback uses a maintained client library with issuer and audience configured; no manual JWT decode without verification. Owner: `backend`. Source: Authentication. See `tokens-and-federation.md` for OAuth, JWT and SAML specifics.
- **OpenID 2.0 implemented.** OpenID 2.0 is obsolete and must not be implemented in new systems; use OpenID Connect.
  Check: no OpenID 2.0 library or endpoint in dependencies or routes. Owner: `backend`. Source: Authentication.
- **Federated identity keyed on `sub` alone or auto-linked by email.** Identify a federated identity by the `iss` plus `sub` pair, and never auto-link accounts because `email`, `preferred_username` or other profile claims match.
  Check: the identity link table has a unique key on (issuer, subject); no lookup joins on email to link. Owner: `backend`. Source: Authentication.
- **Account link added without an authenticated, re-verified session.** Require an authenticated session with re-authentication before adding or removing linked identities, authenticate the identity being added, validate its ID token, and bind the response to the user's linking session (state/nonce) before saving.
  Check: the link endpoint requires a fresh session and verifies state and nonce from the same session. Owner: `backend`. Source: Authentication.
- **Unlinked identity still logs in.** After unlinking, disallow access through the removed identity, and notify the user when an identity is added or removed without terminating the account.
  Check: unlink deletes the mapping used by the login lookup and triggers a notification. Owner: `backend`. Source: Authentication.

## User enumeration

- **Login, reset, or registration reveals whether an account exists.** Login, password reset and recovery must return the same generic message whether the user id or password is wrong, the account does not exist, or it is locked or disabled; registration should use a generic message too (for example "a link to activate your account has been emailed"). HTTP status codes and error pages must not differ either. Where a generic message cannot be used for UX reasons, apply CAPTCHA and brute-force protection.
  Check: every failure branch of these handlers returns the same body and status. Owner: `backend`. Source: Authentication, Forgot Password, Email Validation.
- **Quick-exit login leaks account existence through timing.** Do not return early when the user does not exist; run the same hashing and lookup work on every path (or respond asynchronously) so response times are uniform.
  Check: the login and reset handlers perform a hash or dummy verify when the user is missing. Owner: `backend`. Source: Authentication, Forgot Password, Email Validation.
- **Multi-step or account-first login enables enumeration.** Multi-step login (username first, then password) must not disclose which usernames exist.
  Check: step one returns the same response for unknown and known users. Owner: `backend`. Source: Credential Stuffing.

## Brute force, credential stuffing and automation

- See `mfa-passkeys-and-transaction-signing.md` for MFA coverage, the strongest defense against brute force, credential stuffing and password spraying.
- **Failed-login counter keyed on IP.** Account lockout counters must be tied to the account, not the source IP. Define the lockout threshold, observation window and duration (or an exponentially increasing duration), and prevent lockout being used for denial of service, for example by letting the forgot-password flow work while the account is locked.
  Check: the failure counter is stored per account with a window and duration in config. Owner: `backend`. Source: Authentication.
- **CAPTCHA treated as preventive.** Use CAPTCHA as defense in depth, preferably only after a few failed attempts or when a request looks suspicious, and monitor solve rates to spot impact on users and automated solving.
  Check: CAPTCHA is one layer among others, not the only login throttle. Owner: `backend`. Source: Authentication, Credential Stuffing.
- **IP blocking as the only defense.** Do not rely on IP blocking alone; use graduated responses that consider burst and long windows, low-and-slow distributed traffic, IP classification (residential vs hosting) and geolocation, correlate with proxy and hosting-provider intelligence (for example CAPTCHA for all hosting-provider IPs), and make mitigations temporary with a removal process.
  Check: mitigation rules use more than a single fixed per-IP threshold and blocks expire. Owner: `backend`. Source: Credential Stuffing.
- **Login defenses emit no metrics.** Each defense should produce volume metrics (detected and mitigated) filterable by fields such as IP, and layers must assume client-side defenses (fingerprinting, JS challenges) can be bypassed. Coordinate changes when different teams own different defenses.
  Check: each anti-automation layer increments a metric or emits a structured event. Owner: `sre`. Source: Credential Stuffing.
- **Account IP history not kept.** Store each account's authentication IP history; when a recent IP lands on a block list, consider locking the account and notifying the user.
  Check: successful logins persist source IP per account. Owner: `backend`. Source: Credential Stuffing.
- **Device fingerprint mismatch blocks instead of stepping up.** Use device and connection fingerprints (User-Agent, client attributes, JA3, HTTP/2 or header order) to prompt for additional authentication on mismatch, not to block, remembering they can be spoofed; let users view and manage remembered devices.
  Check: a fingerprint mismatch triggers step-up, and a device management view exists. Owner: `backend`. Source: Credential Stuffing.
- **Predictable or email-only usernames.** Consider requiring users to choose a username rather than using their email; generated usernames must not be predictable (not derived from full name or sequential ids). Internal user ids should ideally be random, not sequential. Users may use a verified email as username but should be able to choose another.
  Check: user id generation uses random values; username generation does not derive from personal data. Owner: `backend`. Source: Credential Stuffing, Authentication.
- **JavaScript challenge excludes assistive technology.** Requiring JavaScript or blocking headless browsers raises attacker cost but reduces accessibility, especially for screen readers, and may breach equality law; weigh it explicitly. Degradation (proof-of-work, delays, growing JS complexity) needs a context-specific risk assessment.
  Check: any JS-required login gate has a documented accessibility decision. Owner: `frontend`. Source: Credential Stuffing.

## Password policy

- **Minimum password length too short.** Enforce a minimum length: passwords under 8 characters are weak when MFA is enabled, and under 15 characters are weak without MFA.
  Check: the password validator's minimum is >= 15 for accounts without MFA and >= 8 with MFA. Owner: `backend`. Source: Authentication.
- **Maximum length below 64 or silent truncation.** Allow at least 64 characters for passphrases (bounded only by the hashing algorithm's limits) and never silently truncate.
  Check: max length >= 64 (or exactly the bcrypt 72-byte bound) and over-length input is rejected, not cut. Owner: `backend`. Source: Authentication, Password Storage.
- **Composition rules or character restrictions.** Allow all characters, including Unicode and whitespace, with no composition rules (no required upper case, digits or symbols).
  Check: the validator has no character-class requirement or charset allowlist. Owner: `backend`. Source: Authentication.
- **Common and breached passwords accepted.** Block common and previously breached passwords on set and change, for example against Pwned Passwords (API or self-hosted copy).
  Check: password set/change paths call a breached-password check. Owner: `backend`. Source: Authentication, Credential Stuffing.
- **Periodic password expiry enforced.** Do not require periodic password changes; rotate credentials only on leak, identified compromise, or authenticator technology change.
  Check: no password max-age setting forces routine resets. Owner: `backend`. Source: Authentication.
- **No strength feedback.** Include a password strength meter (for example zxcvbn-ts) to help users choose stronger passwords.
  Check: registration and change-password forms render a strength estimate. Owner: `frontend`. Source: Authentication.
- **Partial-character secret verification.** When verifying a password, PIN or memorable word, request and verify the full secret, never selected characters.
  Check: no "enter characters 2, 5 and 7" style prompt. Owner: `backend`. Source: Authentication, Credential Stuffing.

## Email as identifier

- **Inconsistent email normalization across flows.** Define one canonicalization policy (lowercase the domain, no provider-specific transforms such as Gmail dot removal unless fully controlled), store both the original and canonical forms, document the comparison policy, and apply it identically in registration, login, reset, recovery and account linking. Fold the local part only when the system fully owns that behavior and it cannot cause account collisions.
  Check: one shared normalization function is used by every lookup; the schema has original and canonical columns. Owner: `backend`. Source: Email Validation.
- **Unicode and IDN emails compared raw.** Normalize Unicode input, convert internationalized domains to punycode for comparison, account for homoglyphs, and be cautious with internationalized local parts.
  Check: the normalization function applies Unicode normalization and IDNA conversion. Owner: `backend`. Source: Email Validation.
- **Custom email regex.** Validate format with a well-tested library, accept the broad range of valid formats, and reject only clearly malformed input.
  Check: no handwritten email regex in validators. Owner: `backend`. Source: Email Validation.
- **Account usable before email ownership is verified.** Verify ownership with a CSPRNG, single-use, time-limited token before activating the account.
  Check: the account status stays inactive until the verification token is consumed. Owner: `backend`. Source: Email Validation.
- **Email treated as a strong factor.** Email is a weak factor; do not rely on email alone for account security, and require MFA for sensitive operations.
  Check: no sensitive operation is authorized by an emailed link alone. Owner: `backend`. Source: Email Validation.
- **Disposable email hard-blocked without risk logic.** Prefer risk-based controls over strict blocking for disposable domains, maintain a disposable-domain list where appropriate, and monitor account-creation patterns.
  Check: disposable-domain handling feeds a risk decision. Owner: `backend`. Source: Email Validation.

## Security questions (legacy only)

- **Security questions used as an authentication or recovery factor.** Security questions are not an acceptable authentication factor and must not be used for authentication, re-authentication, or as an additional login challenge, or as the sole reset mechanism; a password plus questions is not MFA. Keep them only in legacy systems, and prefer an independent factor.
  Check: no new code path asks a knowledge-based question; legacy uses are documented for removal. Owner: `backend`. Source: Security Questions, Authentication, Credential Stuffing, Forgot Password.
- **Legacy security answers stored in plaintext.** Where legacy questions remain, store answers hashed like passwords, lowercase answers before hashing and comparing, give format hints, check answers against a denylist (username, email, current password, common strings), do not let users write their own questions, and pick questions that are memorable, consistent, applicable, confidential and specific.
  Check: the answer column holds password hashes and the set-answer path applies the denylist. Owner: `backend`. Source: Security Questions.
- **Legacy security questions bypass lockout or rotate on failure.** Count wrong answers as failed logins against the lockout counter, keep presenting the same question from a bank until answered correctly, show questions in reset flows only after email ownership is proven via a single-use link, and require re-authentication (ideally MFA) to update answers.
  Check: the question selection is persisted per user and failures increment the account counter. Owner: `backend`. Source: Security Questions.

## Logging, monitoring and notification

- **Authentication failures not logged.** Log and review all authentication failures, password failures and account lockouts, and monitor authentication functions in real time; log email verification attempts and failures and monitor reset activity for abnormal patterns such as high-frequency requests.
  Check: login, lockout, reset and verification handlers emit security events. Owner: `backend`. Source: Authentication, Email Validation.
- **Tokens or full emails written to logs.** Never log verification, reset or authentication tokens or full verification/reset URLs; mask or pseudonymize email addresses and restrict access to logs containing them as personal data.
  Check: log statements in these flows exclude token values and URLs and mask the email. Owner: `backend`. Source: Email Validation.
- **Users not told about suspicious account activity.** Notify users of meaningful security events (not every wrong password, which causes notification fatigue), consider that the user's email may also be compromised, hold access pending verification when multiple resets come from different devices or IPs, and show the date, time and location of the previous login.
  Check: a notification hook exists for suspicious events and the last-login details are rendered. Owner: `backend`. Source: Credential Stuffing.

## Login form usability for password managers

- **Login form blocks password managers.** Use standard HTML forms with correct input `type` attributes, no plugin-based login, allow paste into username, password and MFA fields, allow any printable characters, and let users Tab once from username to password.
  Check: login fields are native inputs with `type="password"`, no paste-blocking handlers, adjacent in tab order. Owner: `frontend`. Source: Authentication.
