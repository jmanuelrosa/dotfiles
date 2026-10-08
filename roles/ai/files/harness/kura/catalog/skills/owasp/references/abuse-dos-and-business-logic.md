# Abuse, Denial of Service and Business Logic

When to read: the brief, diff, or assessed surface touches prices, totals, coupons, credits, referrals, trials or other value-dispensing features; multi-step workflows (checkout, approvals, KYC, signup); check-then-act operations on balances, counters, slots or inventory; idempotency keys or retries of external side effects; rate limits, quotas, CAPTCHA, honeypots or other anti-bot controls; request size, timeout, connection or bandwidth limits; DDoS or edge filtering; abuse-case or misuse threat modeling.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Business Logic Security](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html), [Denial of Service](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html), [Bot Management and Anti-Automation](https://cheatsheetseries.owasp.org/cheatsheets/Bot_Management_and_Anti-Automation_Cheat_Sheet.html), [Abuse Case](https://cheatsheetseries.owasp.org/cheatsheets/Abuse_Case_Cheat_Sheet.html)

## Contents

- Client-supplied value and identity
- Race conditions and idempotency
- Workflow state
- Business rules, contextual authorization and semantic validation
- Value-dispensing and abuse-prone features
- Rate limiting and quotas
- Application resource exhaustion
- Connection, network and edge controls
- Bot defense, challenges and graduated response
- Flow-specific anti-automation
- Anti-bot privacy and accessibility
- Abuse logging and monitoring
- Abuse threat modeling and tests

## Client-supplied value and identity

- **Price, total or discount accepted from the client.** The server accepts product identifiers, quantities and coupon codes only, and computes price, subtotal, tax, discount, shipping cost and tax exemption from its own data; a trusted price or "discounted total" field lets a user pay any amount, and no format validation catches it because the input is syntactically valid.
  Check: request schemas for cart, checkout, order or transfer endpoints carry no price, total, discount amount, shipping cost or exemption field that reaches the charged amount; fix by looking the value up server-side. Owner: `backend`. Source: Business Logic.
- **Security-relevant derived value trusted from the request.** Any value that influences price, access, ownership or state (post visibility that should follow privacy settings, a client-calculated source balance) is recomputed from trusted data rather than read from the request.
  Check: handlers do not persist or act on request fields that the server could derive itself; fix by deriving them from stored state. Owner: `backend`. Source: Business Logic.
- **Hidden, disabled or round-tripped fields treated as trusted.** Every field in a request is attacker-controlled input, including hidden and disabled form controls, fields set by JavaScript, and values the server sent in a previous response and expects back unchanged.
  Check: fields not editable in the UI are validated or re-derived server-side like any other input. Owner: `backend`. Source: Business Logic.
- See `authorization.md` for re-checking ownership on every request and for never taking the acting user, tenant or role from the request body.

## Race conditions and idempotency

- **Check-then-act outside one atomic operation.** Read-decide-write sequences (check balance then debit, check coupon unused then record use, check fewer than N items then add, check slot free then book, check referral not applied then apply, check registration unique then insert) let concurrent requests both pass the check, draining balances or redeeming single-use items many times. A short window is not a defense: concurrent tooling lands requests within a millisecond, including as one multiplexed HTTP/2 request.
  Check: each such operation uses a `SERIALIZABLE` transaction (with explicit retry logic when consistency spans rows), an explicit row lock (`SELECT ... FOR UPDATE`) inside a transaction, or a conditional update (`UPDATE ... WHERE balance >= amount`, `SET value = value - 1 WHERE value > 0`) whose affected-row count is checked and a zero count returned as an error. Owner: `backend`. Source: Business Logic.
- **One-per-user grant enforced only in application code.** One-per-user bonuses and similar invariants are backed by a unique constraint (for example on user id and bonus type) so the database rejects the duplicate.
  Check: migrations add a unique constraint matching each one-per-user rule; fix by adding it. Owner: `database`. Source: Business Logic.
- **External side effect retried without the provider's idempotency key.** Non-idempotent external calls (charging a card) use the provider's idempotency mechanism, reuse the same key when retrying the same operation, and follow the provider's key-generation, parameter-matching and retention rules (a provider may reject changed parameters or treat an expired key as new).
  Check: payment and other external write calls send an idempotency key that is persisted before the call and reused on retry. Owner: `backend`. Source: Business Logic.
- **Own API idempotency key not bound to caller and parameters.** Stored idempotency keys are scoped to the authenticated caller and operation, bound to the original request parameters, and reuse with different parameters is rejected; the request is authorized before a cached result is returned, because possession of a key is not authorization; concurrent requests with one key are coordinated atomically so only one starts the action, with its state and result recorded durably.
  Check: the idempotency store keys on caller plus operation, stores a parameter fingerprint, runs authorization before replay, and claims the key atomically. Owner: `backend`. Source: Business Logic.
- **No defined retry window or unknown-outcome recovery.** The retry and retention window is defined, including recovery when the external result is unknown; a local transaction cannot make an external side effect atomic with saving its result, so after the retry window expires the external outcome is reconciled before resubmitting.
  Check: retry code has a bounded window and a reconciliation path for unknown outcomes instead of blind resubmission. Owner: `backend`. Source: Business Logic.

## Workflow state

- **Multi-step workflow gated only by the UI.** Signup, checkout, approval, KYC and password-reset flows have an explicit server-side state record keyed to the user or session; each step endpoint checks the current state, acts, and advances it, rejecting a request whose step does not match; terminal actions (submit order, approve, transfer funds) run only from exactly the required state. Without it, direct requests skip, repeat or reorder steps (calling the post-verification endpoint directly, completing checkout without paying).
  Check: every step handler loads and validates the persisted state before acting and writes the next state; fix with a server-side state machine. Owner: `backend`. Source: Business Logic.
- **Workflow step kept in a hidden field or client-readable cookie.** A "current step" value the client can set is not enforcement; state lives in storage the client cannot write.
  Check: no workflow decision reads the step from a form field, query parameter or client-writable cookie. Owner: `backend`. Source: Business Logic.
- **Completed one-time step can be replayed.** Signup bonus, coupon redemption, voucher claim and referral reward completions are marked in persistent storage, and re-runs are rejected as errors.
  Check: one-time operations write a completion record and refuse when it exists (ideally under a unique constraint). Owner: `backend`. Source: Business Logic.
- **Partial workflow state never expires.** Workflows that pause for user input (email verification, bank transfer confirmation, multi-step KYC) carry a deadline; past a bounded time the partial state is invalidated and the user restarts, since long-lived half-completed workflows are a frequent source of exploitable inconsistencies.
  Check: workflow records have an expiry that step handlers enforce. Owner: `backend`. Source: Business Logic.

## Business rules, contextual authorization and semantic validation

- **Contextual rule missing beside a role check.** Authorization asks whether this user may do X on this object, in this state, now: a manager cannot approve their own expense report, an author cannot approve their own pull request, an order cannot be cancelled after shipping, an email cannot change to an address in use or without verifying it. These rules live close to the operation they guard, not in auth middleware.
  Check: approval, cancellation and update handlers check self-action, object state and uniqueness rules in addition to role. Owner: `backend`. Source: Business Logic.
- **Sensitive operation reachable through a less-guarded entry point.** Every sensitive operation is mapped to every entry point that can trigger it (API versions, internal tools, webhook handlers, public endpoints), and each enforces the same business rules; a new entry point is audited for which rules it must apply.
  Check: a diff adding a route, version, tool or webhook that reaches an existing sensitive operation applies the same rule checks (ideally through one shared service function). Owner: `backend`. Source: Business Logic.
- **Business invariant enforced by the UI or by assumption.** Invariants for features handling value, ownership or state are written down in plain English (a user cannot approve their own request; a coupon is valid once per user and never more than N total; a transfer cannot leave the source below zero; approval needs both reviewers), and each is mapped to the code that enforces it; "the UI" or "the user won't try that" means it is not enforced, and the enforcement must be atomic.
  Check: the design or spec lists the invariants and the enforcing server-side code for each. Owner: `architect`. Source: Business Logic.
- **Input valid in format but outside the business range.** Values are validated against the meaningful business range: quantity at least 1 and at most available stock (no negative quantities), dates in the future, not beyond a horizon and not on blocked days, amounts positive and within account and regulatory limits, text length within what the downstream system accepts; zero-price flags and currency changes mid-transaction that keep the amount are rejected.
  Check: server-side validators encode business ranges, not only types and lengths. Owner: `backend`. Source: Business Logic.
- **Individually valid fields in an invalid combination.** Legal combinations are written as server-side rules (check-out after check-in; both transfer accounts owned by or delegated to the caller) and unit-tested with cases where each field is valid but the combination is not.
  Check: cross-field rules exist in the handler or domain layer with negative tests. Owner: `backend`. Source: Business Logic.
- **Coupons stack or apply outside their scope by default.** Promotions meant to be used alone cannot be combined to push a price below cost, and a coupon applies only to the products it was meant for; stacking allowed by default is probably a bug.
  Check: the coupon engine rejects combinations unless explicitly configured and restricts each code to eligible items. Owner: `backend`. Source: Business Logic.

## Value-dispensing and abuse-prone features

- **Value-dispensing endpoint protected only by a global edge limit.** Signup-bonus, referral and promo-redemption endpoints each have their own rate limits; a global edge limit is not enough.
  Check: per-feature limits are configured on each value-dispensing route. Owner: `backend`. Source: Business Logic.
- **Single cap on dispensed value.** Defense in depth layers a per-action cap (one bonus per account), a per-account cap (total lifetime promo value) and a per-source cap (per payment method or device).
  Check: all three caps exist for each reward or credit type. Owner: `backend`. Source: Business Logic.
- **One-per-person reward keyed on email.** Multi-accounting, self-referral and free-trial resets defeat eligibility tied to email addresses, which are cheap in bulk; eligibility uses stronger signals (device fingerprint, payment-method fingerprint, phone verification, KYC), and referral flows check that referrer and referee are distinguishable humans, not just distinguishable accounts.
  Check: trial, referral and bonus eligibility queries key on a signal stronger than email. Owner: `backend`. Source: Business Logic.
- **Claiming value costs nothing extra.** Actions that give value are made harder than actions that do not (a wait or a challenge before claiming a reward), imposing a per-request cost on automated abusers.
  Check: reward-claim flows include a friction step. Owner: `backend`. Source: Business Logic.
- **Outbound-effect feature without a rate limit.** Features that send email or messages, make outbound HTTP calls, trigger webhooks or run expensive computations on demand are DoS and spam vectors (including "refer a friend" spam that looks like it comes from the platform) unless rate-limited.
  Check: each such trigger has a per-user and per-source limit. Owner: `backend`. Source: Business Logic.
- See `authentication.md` for password-reset and recovery responses that must not reveal whether an account exists.

## Rate limiting and quotas

- **Rate limit keyed on IP only.** Limits apply on several keys: per IP (a floor, defeated by residential proxies), per session or cookie, per authenticated identity (most reliable), per endpoint (login tighter than the home page), and per ASN or geo where datacenter traffic is unexpected.
  Check: limiter configuration for sensitive routes includes identity and endpoint keys, not just client IP. Owner: `backend`. Source: Bot Management.
- **Fixed-window counter.** Limiters use a token-bucket or sliding-window algorithm; fixed windows allow bursts at window boundaries.
  Check: the limiter algorithm is token bucket or sliding window. Owner: `backend`. Source: Bot Management.
- **Login limiter keyed on the IP and username pair.** A single bucket keyed on the combination lets one IP try the threshold against unlimited usernames (the credential-stuffing pattern); login applies two independent buckets with separate windows, per username and per IP (or IP plus ASN), and both must be under threshold.
  Check: login rate limiting reads two separate counters, not one composite key. Owner: `backend`. Source: Bot Management.
- **Rate-limit response tells the attacker how to tune.** A tripped limit on abuse-sensitive routes returns a generic `429 Too Many Requests` with no `Retry-After` precise enough to schedule against and no detail on which bucket fired or attempts remaining.
  Check: 429 bodies and headers on login and similar routes are generic. Owner: `backend`. Source: Bot Management.
- **Rate limits dropped after a challenge is passed.** Passing a CAPTCHA or proof-of-work challenge does not remove the rate limit.
  Check: challenge success paths still run the limiter. Owner: `backend`. Source: Bot Management.

## Application resource exhaustion

- **Unbounded request or upload size.** Total request size, file upload size and allowed extensions are limited, protecting storage and downstream processing that consumes uploads (image resizing, PDF generation).
  Check: body-size limits exist at the server or framework and on upload handlers. Owner: `backend`. Source: Denial of Service.
- **User input drives resource allocation or iteration.** Input does not decide how much memory is allocated, how many times a function runs, how many threads are used, or how much CPU an operation consumes.
  Check: loop counts, page sizes, allocation sizes and fan-out derived from input are capped server-side. Owner: `backend`. Source: Denial of Service.
- **Expensive validation runs before cheap validation.** Cheap checks (size, type, authentication) run first so CPU-, memory- and bandwidth-expensive validation only sees requests that passed them.
  Check: handler and middleware order puts cheap rejections before expensive parsing or processing. Owner: `backend`. Source: Denial of Service.
- **CPU-heavy or blocking work on the request path.** Highly CPU-consuming operations are reviewed for performance (including language-specific pitfalls), operations do not block waiting for large tasks (use asynchronous processing), and resource-intensive pages are identified and planned for.
  Check: long-running or CPU-bound work is offloaded to jobs or async paths rather than run inline in handlers. Owner: `backend`. Source: Denial of Service.
- **Exceptions unhandled under load.** Code handles exceptions gracefully so an overwhelmed system keeps operating instead of terminating abruptly.
  Check: request handlers and workers catch and contain failures without crashing the process. Owner: `backend`. Source: Denial of Service.
- **Buffer overflow and underflow unguarded.** Code that manages buffers prevents overflow and underflow, which commonly become vulnerabilities.
  Check: native or low-level buffer code bounds every read and write. Owner: `backend`. Source: Denial of Service.
- **Session holds unbounded data or never times out.** Server-side sessions have an inactivity timeout and an absolute timeout, and the data bound to a session is kept small, since sessions are also a resource-exhaustion vector.
  Check: session config sets both timeouts and session payloads stay minimal. Owner: `backend`. Source: Denial of Service.
- **DoS-prone function reachable anonymously.** Least privilege applies: functions an attacker could abuse for DoS are exposed only to authenticated callers who need them.
  Check: expensive endpoints require authentication unless public access is a stated requirement. Owner: `backend`. Source: Denial of Service.
- **Lockout an attacker can trigger.** Failed-login lockout can itself be abused to deny service to legitimate users, so the lockout policy accounts for it.
  Check: lockout logic does not let an unauthenticated party lock arbitrary accounts at will; see `authentication.md`. Owner: `backend`. Source: Denial of Service.
- **CAPTCHA presented as a DoS control.** Puzzles defend against functionality abuse (form-triggered email floods) but not against DoS attacks.
  Check: DoS mitigation in the design does not rely on a CAPTCHA. Owner: `architect`. Source: Denial of Service.
- **Single points of failure with no graceful degradation.** A DoS inventory analyzes components by functionality, architecture and performance to find single points of failure and bottlenecks; the design uses stateless components, redundancy and bulkheads, survives external service failures, and degrades to reduced functionality rather than failing completely, weighing scale-up, scale-out and cost.
  Check: the design records the SPOF analysis and the redundancy, bulkhead and degradation strategy for each critical component. Owner: `architect`. Source: Denial of Service.

## Connection, network and edge controls

- **No minimum ingress rate or request-read timeout.** Slow HTTP attacks hold connections open with fragmented requests; a minimum ingress data rate with request-read timeouts mitigates them, tuned from a log-derived baseline of genuine traffic so it neither rejects legitimate slow clients nor is too lax.
  Check: web server, proxy or load balancer config sets request-read timeouts and a minimum data rate. Owner: `cloud`. Source: Denial of Service.
- **No absolute connection timeout or traffic ceilings.** An absolute connection timeout, a maximum ingress data rate (dropping connections above it), a total bandwidth limit and a load limit on concurrent users per resource are defined.
  Check: edge and server config define each of these limits. Owner: `cloud`. Source: Denial of Service.
- **Cacheable and static content served from the application origin.** Caching more data, and hosting static resources (images, JavaScript) on a different domain, reduces load and bandwidth exhaustion at the application.
  Check: static assets go through a CDN or separate host with caching configured. Owner: `cloud`. Source: Denial of Service.
- **Spoofed source addresses not filtered at the edge.** Edge routers filter invalid sender addresses (RFC 2267) so IP spoofing cannot bypass block lists.
  Check: network edge configuration includes ingress anti-spoofing filtering. Owner: `cloud`. Source: Denial of Service.
- **DDoS capacity of ISP and filtering provider not assessed.** ISP DDoS services are checked beforehand (multiple access points, sufficient bandwidth, traffic analysis and application-level defense hardware); for larger attacks a DDoS filtering service is considered, its mitigation capacity and coverage assessed against availability requirements without assuming a fixed attack-size ceiling, and its traffic routing checked against data protection law.
  Check: infrastructure documentation records the DDoS provider choice and the capacity and jurisdiction assessment. Owner: `cloud`. Source: Denial of Service.
- **Layer 2 spoofing unfiltered.** Packet filtering inspects and blocks offending ARP packets (static ARP tables are an alternative but hard to maintain).
  Check: network device configuration includes ARP inspection where the LAN is in scope. Owner: `cloud`. Source: Denial of Service.

## Bot defense, challenges and graduated response

- **Single anti-bot layer or single vendor.** Controls are layered at the edge (IP reputation, ASN filtering, TLS JA3/JA4 and HTTP/2 fingerprints, basic rate limits), the application (session-aware limits, identity-bound quotas, behavioral signals, honeypots, challenges) and the business layer (transaction anomaly detection, account velocity rules, fraud scoring, async review queues); relying solely on one edge vendor means a mistuned rule takes the site down or opens it up.
  Check: the design names controls at all three layers for each at-risk endpoint. Owner: `architect`. Source: Bot Management.
- **Visible CAPTCHA as the primary bot defense.** Visible CAPTCHAs are accessibility-hostile, machine-solvable and farmed out cheaply, so they are a last-resort step-up, never on every login attempt; prefer or layer attestation tokens (Privacy Pass, with trusted issuers whose policies match the use case, remembering a valid token is not proof of a human), managed challenges, invisible risk scoring with application-defined thresholds, proof of work, and WebAuthn or passkeys for high-value flows.
  Check: login and signup flows do not show a CAPTCHA unconditionally; challenges are triggered by risk. Owner: `backend`. Source: Bot Management.
- **Managed challenge token not verified server-side.** Each managed-challenge token (for example Turnstile) is validated server-side with the provider's verification endpoint, requiring `success: true` and checking the expected hostname and configured action; tokens are single-use and expire after five minutes.
  Check: the handler calls the verification API and checks success, hostname and action before proceeding. Owner: `backend`. Source: Bot Management.
- **Proof-of-work validated by hash only.** Use a maintained challenge implementation; the challenge, difficulty and expiry stay under server control, unknown, expired or spent challenges are rejected, concurrent reuse is prevented, and accepted work is bound to the intended policy; difficulty is benchmarked on supported clients because overly hard puzzles deny service to legitimate users.
  Check: PoW verification tracks issued challenges server-side with expiry and single-use state. Owner: `backend`. Source: Bot Management.
- **No honeypot or trap signals.** Hidden form fields that humans never fill (visually hidden, `aria-hidden`, out of tab order, autocomplete off) cause the server to silently drop or tarpit submissions that fill them; a bait path disallowed in `robots.txt` flags traffic to it as malicious; watermarked canary records on listing pages prove and fingerprint scraping.
  Check: sensitive forms include a hidden honeypot field and the handler rejects non-empty values. Owner: `frontend`, `backend`. Source: Bot Management.
- **Hard block on the first signal.** Responses are graduated by confidence: low (log, serve normally, flag the session), medium (step-up challenge, MFA or PoW), high (tarpit with progressively slower responses rather than `403`, or stale or randomized data), very high (soft-block specific actions such as checkout while allowing browsing), confirmed abuse (account hold and manual review, not deletion, to preserve forensics); for scrapers, plausible but slightly wrong data poisons the dataset.
  Check: bot-decision code maps scores to graduated actions instead of a single block. Owner: `backend`. Source: Bot Management.
- **Blocking non-standard user agents or hardened browsers.** Blocking all non-standard User-Agents breaks research, accessibility and integration tools, and privacy-hardened browsers often look bot-like; prefer challenge to block.
  Check: no rule blocks solely on User-Agent shape or browser hardening signals. Owner: `backend`. Source: Bot Management.

## Flow-specific anti-automation

- **Endpoints not mapped to automated threats.** Each endpoint is mapped to the applicable OWASP Automated Threat (OAT) categories with a first control: login (rate limit, breached-password check, MFA), signup (email or phone verification, velocity limits), search and catalog (per-identity rate limit, behavioral signal), checkout and cart (queue, purchase limits, 3-D Secure), public API (API keys, per-key quotas, signed requests), comments and reviews (reputation, delayed publishing).
  Check: the threat model lists OAT categories and first controls per endpoint type. Owner: `architect`. Source: Bot Management.
- **Account usable before verification.** At signup, email is verified before the account is usable (features gated, not just a confirmation sent); email domains are checked against disposable-domain lists refreshed weekly; phone verification checks carrier type to reject cheap VoIP numbers; per-IP, per-ASN and per-device signup velocity is limited (for example 3 per hour); signups whose email local part has high entropy on a recently created domain are rejected.
  Check: signup handlers gate features on verification and apply the domain, carrier and velocity checks. Owner: `backend`. Source: Bot Management.
- See `authentication.md` for breached-password checks with step-up, MFA on suspicious login patterns, and the rest of credential-stuffing prevention.
- **Scarce inventory without anti-scalping controls.** Limited drops use a waiting room with randomized admission and tokens bound to session and identity; per-account purchase limits are enforced server-side including identity proxies (same payment method, shipping address, device); cart holds expire after N seconds unpaid; address and payment are deduplicated at order time with normalized hashes.
  Check: the order path enforces purchase limits across identity proxies and releases unpaid holds. Owner: `backend`. Source: Bot Management.
- **Public API keyed by a static bearer token in client code.** Public APIs use API keys with rotating secrets, per-key quotas advertised in `X-RateLimit-*` headers so well-behaved clients self-throttle, request signing (HMAC over method, path, timestamp and body) to prevent replay, and explicit tiers (public endpoints serve cached, slightly delayed data; partner endpoints serve realtime data with an authenticated key).
  Check: API clients carry no static bearer token, requests are signed with a timestamp, and quotas are per key. Owner: `backend`. Source: Bot Management.

## Anti-bot privacy and accessibility

- **Browser fingerprinting used before passive signals.** Passive network signals come first (JA3/JA4, HTTP/2 fingerprint, Client Hints verified against the TLS fingerprint); browser-side fingerprinting (WebGL, canvas, fonts, audio) is a last resort with consent where required, behavioral telemetry is collected only on sensitive flows, and authenticated low-risk traffic is not re-fingerprinted.
  Check: client fingerprinting scripts load only on sensitive flows and behind consent where required. Owner: `frontend`. Source: Bot Management.
- **Raw fingerprints stored indefinitely.** Fingerprints are hashed or truncated before storage, raw anti-bot signals have short retention (hours to days) with aggregation for long-term analytics, and only data needed to score the request is collected.
  Check: anti-bot storage hashes fingerprints and has a short TTL. Owner: `backend`. Source: Bot Management.
- **Anti-bot processing undocumented.** Fingerprinting and anti-bot processing are disclosed in the privacy notice with a documented lawful basis and data categories; consent requirements for device storage and access are assessed (legitimate interests cannot replace consent where consent is required); a third-party anti-bot vendor is listed as a sub-processor with its DPIA reviewed.
  Check: the privacy notice and processing records cover the anti-bot controls and vendor. Owner: `architect`. Source: Bot Management.
- **Challenge with no accessible alternative.** Any user-facing challenge offers an accessible alternative (audio challenge, support contact).
  Check: challenge UI includes an accessible fallback. Owner: `frontend`. Source: Bot Management.

## Abuse logging and monitoring

- **Value or permission change without an audit trail.** Operations that dispense value, change permissions or move money log the authenticated user, target user or resource, action, outcome, request context (IP, user agent, correlation id) and business context (computed price, coupon applied, new state); these logs are tamper-evident and separate from general application logs.
  Check: value-dispensing and permission-changing handlers emit an audit event with these fields to a dedicated sink. Owner: `backend`. Source: Business Logic.
- **Anti-bot decisions not logged.** For each sensitive-endpoint request the decision is logged with its signals: timestamp, request id, route, status, client IP, ASN, country, JA3/JA4 and HTTP/2 fingerprint, raw and parsed User-Agent, authenticated identity or session id hash, decision, score and rule; credentials and PII are masked. Hidden rules with no logging cannot be tuned.
  Check: the bot-decision path emits a structured record with these fields and masks credentials. Owner: `backend`. Source: Bot Management.
- **No anomaly dashboards or alerts on abuse rates.** Dashboards cover requests per second by endpoint, 4xx/5xx and failure rate by route, signup-to-purchase funnel and login success rate, with sudden shifts beyond 3 sigma treated as bot signals; simple per-user, per-IP and per-device thresholds alert on signups sharing an IP, device or payment instrument, repeated failed password resets from one source, high promo, referral or credit rates, bursts from a single user to one endpoint, and workflows completed faster than a human could.
  Check: alert rules exist for these rates. Owner: `sre`. Source: Business Logic, Bot Management.
- **Detection without a prevention follow-up.** Each confirmed abuse incident is investigated and resolved, and the control that should have prevented it is added or tightened.
  Check: the incident runbook includes a step to add or tighten the preventive control. Owner: `sre`. Source: Business Logic.

## Abuse threat modeling and tests

- **Threat model covers only technical attacks.** Features are modeled from the business process: what a legitimate user does step by step, what the system assumes at each step and which false assumptions benefit the user, whether steps can be skipped, repeated or reordered, whether two users or two tabs can act on one object at once, what the feature produces that has value, and a "dishonest user" pass that combines legitimate actions in an unanticipated order or volume.
  Check: the design for a value-, ownership- or state-handling feature includes these business-process questions and answers. Owner: `architect`. Source: Business Logic, Abuse Case.
- **Abuse cases not turned into requirements.** Concrete abuse cases are identified per feature (marked technical or business), each with a unique identifier, a business risk rating and rationale recorded separately from any CVSS score (never adjust CVSS to express business risk), a countermeasure and a handling decision; accepted risks carry a written justification; selected cases become security requirements or user-story acceptance criteria, and where each is handled is recorded so coverage can be traced.
  Check: the feature spec or stories carry abuse-case acceptance criteria and a traceable handling decision for each. Owner: `architect`. Source: Abuse Case.
- **Business rules untested.** Each written invariant has a test that attempts the violation and asserts rejection; concurrent-request tests race sensitive operations and assert a consistent end state (balance never negative, coupon redeemed once, bonus granted once); workflow tests try to skip, repeat and reorder steps and expect rejection; adversarial tests derived from the spec cover how a motivated user would misuse the feature; these run automatically in CI so a countermeasure cannot be silently removed.
  Check: the test suite contains invariant, concurrency, ordering and abuse-case tests for each value- or state-handling feature, wired into CI. Owner: `qa`. Source: Business Logic, Abuse Case.
