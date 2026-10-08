# Tokens and Federation

When to read: the brief, diff, or assessed surface touches JWT issuance or validation, JWKS or key lookup, OAuth 2.0 or OpenID Connect clients, authorization servers or resource servers, refresh tokens, DPoP or mTLS-bound tokens, SAML SSO (IdP or SP), service-to-service identity propagation, token exchange, or CI/CD OIDC federation into a cloud account.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [JSON Web Token](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet.html), [OAuth 2.0 Protocol](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html), [SAML Security](https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html), [Identity Propagation Patterns](https://cheatsheetseries.owasp.org/cheatsheets/Identity_Propagation_Patterns_Cheat_Sheet.html), [Workload Identity Federation](https://cheatsheetseries.owasp.org/cheatsheets/Workload_Identity_Federation_Cheat_Sheet.html)

## Contents

- JWT signature and verification key
- Issuer, audience and token type binding
- SAML signature and response validation
- OAuth 2.0 flows, redirects and grants
- Access token scope, sender constraint and refresh
- Token lifetime, replay and revocation
- Identity propagation between services
- Workload identity federation for CI/CD
- Token confidentiality and JWE
- JWT signing algorithms and secrets
- SAML deployment, keys and certificates

## JWT signature and verification key

- **Unsecured `alg: none` JWT accepted.** A parser that accepts `"alg":"none"` lets anyone forge tokens and impersonate any user or claim any authorization.
  Check: the verifier passes an explicit allowlist of algorithms that excludes `none`, and no code path decodes a token without verifying the signature; add the allowlist where it is missing. Owner: `backend`. Source: JWT.
- **Public key usable as a MAC secret (algorithm confusion).** A verifier that lets the token's `alg` pick between public-key and MAC algorithms can be fed an HMAC token signed with the issuer's public key as the secret.
  Check: accepted algorithms are hardcoded and do not mix public-key signature algorithms with MAC algorithms; the key is chosen by (or checked for consistency with) the expected algorithm, or the library strongly types keys; fix by pinning e.g. only `ES256`. Owner: `backend`. Source: JWT.
- **Verification key taken from the token header.** `jwk`, `jku`, `x5u` and `x5c` are unauthenticated attacker input; trusting a key they embed or point to accepts any self-signed forgery, including smuggled symmetric keys.
  Check: the verifier never uses a header-supplied key unless it chains to a trust anchor already associated with the issuer; keys come from out-of-band trust material (a pinned key or the issuer metadata `jwks_uri`), and `kid`, `x5t`, `x5t#S256` only select within that configured set. Owner: `backend`. Source: JWT.
- **Unsanitized `kid` reaches a lookup.** `kid` flows into databases and directories and is an injection vector.
  Check: `kid` is validated against an expected format or matched against a configured key map before any query or file lookup. Owner: `backend`. Source: JWT.
- See `ssrf.md` for fetching JWKS, `jku`/`x5u` URLs, issuer metadata, or token status lists by URL.
- **ID token accepted as an API access token.** An OpenID Connect ID token is not an access token, and forwarding a client certificate does not preserve proof of private-key possession on the TLS connection.
  Check: API authentication rejects ID tokens (by `typ`, audience, or validation profile) and no service treats a forwarded certificate header as mTLS proof; preserve each protocol's own validation and proof requirements. Owner: `backend`. Source: Identity Propagation.

## Issuer, audience and token type binding

- **Issuer not validated or matched loosely.** Without a strict `iss` check a token from any trusted-key holder, partner tenant, or public IdP account is accepted.
  Check: `iss` is compared case-sensitively as the whole string (scheme and path included) against one expected value or an explicit allowlist of issuer identifiers, never accepted as presented. Owner: `backend`. Source: JWT.
- **Verification key resolved independently of the issuer.** A verifier that searches the union of several issuers' JWK Sets by `kid` accepts a token whose `iss` names one issuer and whose `kid` names another issuer's key.
  Check: the key set is resolved from the validated `iss` (that issuer's `jwks_uri`), and multi-issuer or multi-tenant deployments key the JWKS allowlist by issuer instead of searching every tenant's keys. Owner: `backend`. Source: JWT.
- **Audience not required to contain the recipient.** A service that does not require its own identifier in `aud` accepts tokens minted for other services (substitution attack).
  Check: the validator is given the recipient's own audience value and checks membership whether `aud` is a string or an array. Owner: `backend`. Source: JWT, OAuth2.
- **Claim checks enabled without expected values.** Some libraries' "verify issuer/audience" flags do nothing unless the expected issuer and audience are actually passed.
  Check: the decode call passes concrete expected issuer and audience values and a required-claims list (at least `exp`, `iss`, `aud`), not just verification flags. Owner: `backend`. Source: JWT.
- **Missing `iss` or `aud` tolerated where the deployment relies on them.** A token with no `iss` has nothing to bind the key to, and one with no `aud` cannot be shown to be meant for this recipient.
  Check: where the token profile relies on these claims, tokens lacking them are rejected; omission is acceptable only where a profile establishes them by other means (self-issued tokens under a dedicated key, SD-JWT key binding). Owner: `backend`. Source: JWT.
- **Expiry and not-before not enforced.** `exp` and `nbf` define token validity.
  Check: the validator requires `exp` and checks `exp` and `nbf` against current time. Owner: `backend`. Source: JWT.
- **Token kinds not distinguished (cross-JWT confusion).** A password-reset or ID token accepted as an access token grants access it was never issued for.
  Check: issuers set a purpose-specific `typ` (`at+jwt`, `logout+jwt`, or a custom `example-reset+jwt`), verifiers reject missing or unexpected `typ` where the profile provides it (compared case-insensitively, `application/` prefix optional), and where `typ` cannot be enforced, kinds are separated by distinct signing keys, required claims, or strict `iss`/`aud` isolation. Owner: `backend`. Source: JWT.
- **Shared key across JWT types without type separation.** Reusing a key for several token kinds is acceptable only if it creates no type-confusion risk.
  Check: when one key signs several token kinds, each verifier enforces a distinguishing `typ` or mutually exclusive claims. Owner: `backend`. Source: JWT.
- **Subject and role claims trusted across issuers.** `sub`, `roles`, `groups`, `entitlements`, `authorization_details` and `may_act` carry cross-issuer impersonation and spoofed-authorization risk; `iss` scopes them.
  Check: user lookups and authorization decisions key subject and role claims by the validated issuer, not by `sub` alone. Owner: `backend`. Source: JWT.
- **Authentication strength not read from the token.** `auth_time`, `acr` and `amr` are the claims for enforcing authentication freshness and strength (for example MFA).
  Check: operations that require MFA or recent login verify `acr`/`amr`/`auth_time` from the validated token rather than assuming them. Owner: `backend`. Source: JWT.

## SAML signature and response validation

- **XML not schema-validated before security use.** Unvalidated documents enable XML signature wrapping.
  Check: every SAML document is schema-validated before any security-related use, against local trusted schema copies, with automatic schema download disabled and, where possible, a hardened schema without wildcard or relaxed processing. Owner: `backend`. Source: SAML.
- **Signing key taken from the document's `KeyInfo`.** Trusting `KeyInfo` lets an attacker supply their own key.
  Check: the SP verifies with key material obtained directly from the IdP and stored locally (a static key selector for one key, a local keystore for several) and ignores `KeyInfo`. Owner: `backend`. Source: SAML.
- **Security elements selected by tag name.** Selecting elements with a by-tag-name lookup lets a wrapped, unsigned assertion be read instead of the signed one.
  Check: no by-tag-name selection of security elements without prior validation; absolute XPath expressions are used unless a hardened schema is enforced. Owner: `backend`. Source: SAML.
- **Signature does not cover the assertion actually used.** An assertion outside the validated signed content can carry any identity.
  Check: the `ds:Reference URI` resolves to the signed Assertion or Response, the exact assertion used for authentication sits inside that validated signed content, and assertions outside it are rejected. Owner: `backend`. Source: SAML.
- **Unsigned assertion or response accepted.** Each Assertion or the entire Response element must be signed.
  Check: the IdP signs each Assertion or the whole Response, and the SP rejects messages where neither is signed by an authorized IdP. Owner: `backend`. Source: SAML.
- **SHA-1 signature algorithms accepted.** NIST SP 800-131A Rev. 2 disallows SHA-1 in digital signatures.
  Check: the SP explicitly requires at least RSA-SHA-256 and rejects `xmldsig#rsa-sha1`, `xmldsig#hmac-sha1` and SHA-1 `DigestMethod`. Owner: `backend`. Source: SAML.
- **`Destination` not matched to the ACS URL.** Without it an assertion issued for another SP can be replayed.
  Check: `samlp:Response` `Destination` must exactly equal the SP's Assertion Consumer Service URL, and responses missing it are rejected. Owner: `backend`. Source: SAML.
- **Audience, validity window and subject confirmation unchecked.** These bind the assertion to this SP, this time and this request.
  Check: `saml:Audience` equals the SP EntityID; `NotBefore`/`NotOnOrAfter` are enforced; `SubjectConfirmationData` `Recipient`, `NotOnOrAfter` and `InResponseTo` are validated. Owner: `backend`. Source: SAML.
- **Response not tied to the originating request.** An `AuthnRequest` must carry a unique `ID` and the SP, and the response must return it as `InResponseTo`; its absence is what left a major IdP vulnerable.
  Check: the SP generates a unique request ID, stores it per user agent, and rejects responses whose `InResponseTo` does not match; responses contain ID, SP, IdP and a signed assertion that names ID, client, IdP and SP. Owner: `backend`. Source: SAML.
- **Protocol processing rules partially implemented.** All AuthnRequest rules (SAML Core 3.4.1.4) and Response rules (SAML Profiles 4.1.4.3) must be validated despite the cost.
  Check: the SP library or code covers each listed processing rule; no rule is skipped for performance. Owner: `backend`. Source: SAML.
- **IdP-initiated (unsolicited) SSO enabled without compensating checks.** Unsolicited responses lack login CSRF protection; best practice is to not allow IdP-initiated SSO.
  Check: IdP-initiated SSO is disabled, or the SP follows SAML Profiles 4.1.5 validation, allowlists `RelayState` URLs, and implements replay detection at the response or assertion level. Owner: `backend`. Source: SAML.
- **SAML replay window not minimized.** Long-lived or reusable responses enable stolen-assertion, browser-state and replay attacks.
  Check: SAML responses have short lifetimes and carry `OneTimeUse`. Owner: `backend`. Source: SAML.
- **SAML POST-binding messages cacheable.** A cached SAML protocol message can be reused as a stolen assertion or replay.
  Check: responses carrying SAML protocol messages are not cacheable, and the Redirect and POST bindings follow SAML Bindings 3.4 and 3.5. Owner: `backend`. Source: SAML.
- **Signer not checked against the authorized IdP.** A signature from any trusted certificate is not proof the expected IdP minted the assertion.
  Check: the SP confirms the signing certificate belongs to the IdP named as issuer of that response. Owner: `backend`. Source: SAML.
- See `injection.md` for input validation of SAML providers and consumers, and `xml-and-deserialization.md` for XML parser hardening.

## OAuth 2.0 flows, redirects and grants

- **Implicit grant in use.** `response_type=token` is deprecated (RFC 9700) and removed in OAuth 2.1: tokens land in the URL fragment, browser history and page scripts, and cannot be sender-constrained.
  Check: every client type (SPAs and native included) must use Authorization Code with PKCE; `code id_token` is used only when an ID token is needed at the authorization endpoint, and access tokens are never returned via the front channel. Owner: `backend`, `frontend`. Source: OAuth2.
- **Open redirector on client or authorization server.** A URL that forwards the browser to an arbitrary query-parameter URI exfiltrates authorization codes and access tokens.
  Check: neither client nor AS has an endpoint that redirects to a URI taken from a query parameter without validation. Owner: `backend`. Source: OAuth2.
- **Authorization flow without CSRF binding.** Without PKCE, an OIDC `nonce`, or a one-time `state` bound to the user agent, an attacker can inject their own authorization response.
  Check: the client relies on PKCE only after confirming the AS supports it, or uses OIDC `nonce`, otherwise a one-time CSRF token in `state` bound to the user agent must be used. Owner: `backend`. Source: OAuth2.
- **Authorization code injection not prevented.** PKCE (or the OIDC `nonce`) stops replay of stolen codes.
  Check: clients use PKCE; the challenge or nonce must be transaction-specific and bound to the client and the user agent that started the flow. Owner: `backend`. Source: OAuth2.
- **PKCE method exposes the verifier.** A challenge method that reveals the verifier in the authorization request (`plain`) defeats PKCE.
  Check: clients use `S256`, not `plain`. Owner: `backend`. Source: OAuth2.
- **AS does not enforce PKCE consistently.** Authorization servers must support PKCE, enforce `code_verifier` when a `code_challenge` was sent, and reject a `code_verifier` when no `code_challenge` was sent (PKCE downgrade).
  Check: the token endpoint validates both directions of the challenge/verifier pairing. Owner: `backend`. Source: OAuth2.
- **Mix-up with multiple authorization servers.** A client talking to several AS can be tricked into sending a code to the wrong one.
  Check: multi-AS clients validate the `iss` response parameter or ID token `iss`, or, when no other countermeasure exists, use distinct redirect URIs per AS. Owner: `backend`. Source: OAuth2.
- **Resource Owner Password Credentials grant used.** It exposes the user's credentials to the client.
  Check: the password grant is not enabled on the AS or used by any client. Owner: `backend`. Source: OAuth2.
- **Authorization server forwards credential-bearing requests.** An AS can accidentally redirect a request that contains user credentials.
  Check: AS redirects issued after credential submission cannot carry the submitted credentials on to the redirect target. Owner: `backend`. Source: OAuth2.
- **Authorization responses over plaintext.** Authorization responses must not travel unencrypted.
  Check: registered redirect URIs use `https`; `http` is allowed only for native clients using loopback redirection; end-to-end TLS is used. Owner: `backend`, `mobile`. Source: OAuth2.
- **Client authentication weak or absent.** AS should authenticate clients where possible, preferably asymmetrically so no symmetric secrets are stored.
  Check: confidential clients authenticate with mTLS or `private_key_jwt` rather than shared secrets. Owner: `backend`. Source: OAuth2.
- **Clients can influence `client_id`, `sub` or owner-like claims.** A client that controls a value confusable with a genuine resource owner can impersonate one.
  Check: dynamic registration and client metadata cannot set `client_id`, `sub` or other claims that resource servers treat as user identity. Owner: `backend`. Source: OAuth2.

## Access token scope, sender constraint and refresh

- **Resource server does not verify token audience per request.** Access tokens should be restricted to one Resource Server, and every RS must check on every request that the token was meant for it and refuse otherwise.
  Check: RS validation compares `aud` (or introspection result) to its own identifier on each request; the AS issues audience-restricted tokens via `resource` or `scope`. Owner: `backend`. Source: OAuth2.
- **Token not checked for the specific resource and action.** The RS must verify that the token was issued for this action on this resource and refuse otherwise.
  Check: handlers check `scope` or `authorization_details` against the operation and object, not only token validity. Owner: `backend`. Source: OAuth2.
- **Access token privileges broader than needed.** Least-privilege tokens limit leakage impact and stop clients exceeding the owner's grant.
  Check: requested scopes are the minimum for the use case; combine with sender-constrained tokens for defense in depth. Owner: `backend`. Source: OAuth2.
- **Refresh token neither sender-constrained nor rotated.** A stolen refresh token mints access tokens indefinitely.
  Check: refresh tokens are bound with DPoP or mTLS, or rotated on each use with the previous token invalidated immediately to detect replay; combining both is defense in depth. Owner: `backend`. Source: OAuth2.
- **High-value APIs use plain bearer tokens.** Sender-constraining (DPoP RFC 9449, mTLS RFC 8705) limits replay of leaked tokens for sensitive data, high-value transactions, long-lived tokens, B2B, mobile and multi-hop architectures.
  Check: for those cases the AS binds tokens via `cnf` and the RS validates the DPoP proof (signature, access-token hash) or that the TLS client certificate matches the bound thumbprint. Owner: `backend`. Source: OAuth2, JWT.
- **DPoP key reachable by untrusted code.** Sender constraint does not prevent token disclosure, and a signing key usable by injected script defeats it.
  Check: tokens are only sent over HTTPS, and the client's DPoP private key cannot be used by untrusted code in the client. Owner: `frontend`. Source: JWT.

## Token lifetime, replay and revocation

- **JWT used as a stateless session with no invalidation.** Session JWTs need a revocation mechanism, which removes most of the stateless benefit.
  Check: if JWTs carry user sessions there is a revocation path (denylist or status list); otherwise prefer a server-side session (see `sessions-and-cookies.md`). Owner: `backend`. Source: JWT.
- **Denylist keyed on the raw token or its hash.** JWT malleability (non-strict parsing, ECDSA signature malleability) yields an alternate encoding of a revoked token that still verifies.
  Check: denylist entries are keyed on claims such as (`jti`, `iss`) and expire at `exp`, never on the token string or `SHA-256(token)`. Owner: `backend`. Source: JWT.
- **Issuer revocation built ad hoc.** Token Status Lists (`status` claim) are the scalable mechanism for issuer-side JWT revocation.
  Check: where issuer revocation is needed, consider a status list before a custom denylist. Owner: `backend`. Source: JWT.
- **Long-lived tokens with no freshness binding.** Short expiry limits reuse, and a session-bound `nonce` gives freshness and replay protection.
  Check: token lifetimes are short and OIDC `nonce` is bound to the session and checked. Owner: `backend`. Source: JWT.

## Identity propagation between services

- **Identity assertion accepted from any issuer.** Accept assertions only from configured issuers authorized to make them, and validate signature, allowed algorithm, issuer, audience, token type and validity per the token profile.
  Check: each internal verifier has an explicit issuer allowlist and the full claim set validated, not signature only. Owner: `backend`. Source: Identity Propagation.
- **Opaque token treated as self-describing.** Opaque access tokens must be validated with the issuer's supported mechanism.
  Check: opaque tokens go through introspection or the issuer's documented validation, and the representation is never taken as permission for an operation. Owner: `backend`. Source: Identity Propagation.
- **Valid identity context treated as authorization.** A valid signature proves issuer and integrity, not permission.
  Check: each receiving service rejects missing or invalid context and still authorizes the requested action and resource. Owner: `backend`. Source: Identity Propagation, Authorization Patterns.
- **Calling service not authenticated separately from the user.** Possessing user context does not establish the caller's service identity.
  Check: service-to-service connections are authenticated independently of the propagated user token. Owner: `backend`. Source: Identity Propagation.
- **Audience widened to make forwarding work.** Forwarding a bearer token to more services increases where it can leak and gives no isolation between recipients.
  Check: forwarded external tokens go only to services already in their audience; no change broadens `aud` to accommodate forwarding. Owner: `backend`. Source: Identity Propagation.
- **Arbitrary services act as identity issuers.** A forwarding service's signature proves who sent the attributes, not that it may assert them.
  Check: user identity and privileges crossing several boundaries come from a designated issuer, not from self-signed objects of ordinary services. Owner: `architect`. Source: Identity Propagation.
- **Trusted proxy identity header spoofable.** Client-supplied copies of trusted headers, an unauthenticated proxy, or a bypassable proxy let callers forge identity.
  Check: the edge strips client-supplied copies before setting the header, services authenticate the proxy, and direct requests that bypass it are blocked. Owner: `backend`. Source: Identity Propagation, Authorization Patterns.
- **Token exchange not authorized by the STS.** The requesting service must authenticate to the STS, and the STS must authorize the exchange and constrain issued privileges; asking for a narrower token is not enforcement.
  Check: STS policy restricts which services may exchange which subject tokens for which audiences and scopes, and preserves the user/actor distinction (`act`) where policy depends on it. Owner: `backend`. Source: Identity Propagation.
- **STS outage handled by accepting invalid credentials.** Exchange adds an issuance dependency.
  Check: when the STS is unavailable, downstream calls fail closed rather than falling back to unvalidated or wider tokens. Owner: `backend`. Source: Identity Propagation.
- **Internal assertion issuer over-privileged or long-lived.** Issuance and verification privileges must be separate, and assertion recipients and lifetime limited.
  Check: only the designated issuer holds signing keys, verifiers hold only verification material, and assertions carry a narrow audience and short expiry. Owner: `backend`. Source: Identity Propagation.
- **Transaction tokens assumed replay resistant.** They are propagated unmodified within a trust domain and are not replay resistant.
  Check: recipients validate signature, trust-domain audience and expiry, then authorize their own operation. Owner: `backend`. Source: Identity Propagation.
- **Propagated identity carries more than recipients need.** Signing does not hide claims, and mapping identifiers does not prevent correlation.
  Check: assertions include only needed attributes (pseudonymous identifiers where appropriate), internal assertions never appear in client responses, and identity events are logged without excluded data. Owner: `backend`. Source: Identity Propagation.

## Workload identity federation for CI/CD

- **Static long-lived cloud keys in the pipeline.** Prefer OIDC workload identity federation where both platforms support it.
  Check: deployment jobs obtain short-lived cloud credentials via the provider's federation integration, not stored keys, and the pipeline does not implement its own token validator. Owner: `platform`. Source: Workload Identity Federation.
- **Trust policy matches only the shared CI issuer.** Trusting a shared issuer alone admits other tenants' jobs.
  Check: the cloud trust policy pins exact `iss`, `aud` and `sub` (or equivalent attributes), restricts organization, repository and deployment context using immutable IDs where supported, and has no wildcard over repositories or job contexts. Owner: `cloud`. Source: Workload Identity Federation.
- **Branch or environment restriction not enforceable.** A claim present in the token is not necessarily usable as a policy condition, and environment-based GitHub subjects do not contain the branch.
  Check: the trust condition matches the configured subject format, and branch/tag restriction is enforced via environment protection or another supported condition. Owner: `cloud`. Source: Workload Identity Federation.
- **Federated role over-privileged.** A tight trust policy does not compensate for an administrative deployment role.
  Check: the permissions policy grants only the deployment's operations and resources, production and non-production use separate identities and trust rules, and federation and permission administration sit outside deployment roles. Owner: `cloud`. Source: Workload Identity Federation.
- **OIDC token permission granted broadly.** The CI permission to request an OIDC token (`id-token: write` in GitHub Actions) permits token requests but does not itself grant cloud permissions.
  Check: the permission is set at job level and only on jobs that need cloud access. Owner: `platform`. Source: Workload Identity Federation.
- **Untrusted code can reach the federated identity.** Federation does not make a compromised job trustworthy.
  Check: jobs that can obtain production credentials do not run untrusted pull request code, and changes to trusted deployment workflow files require review. Owner: `platform`. Source: Workload Identity Federation.
- **Federated credentials leaked or outliving the job.** Issued cloud credentials have their own lifetime independent of the job and OIDC token.
  Check: the shortest supported credential lifetime is requested, and neither the OIDC token nor issued credentials are printed, stored in artifacts or caches, or passed to unrelated jobs. Owner: `platform`. Source: Workload Identity Federation.
- **Replaced static keys still valid.** Leftover keys bypass federation restrictions.
  Check: after migration the old static keys are revoked and pipeline secret copies removed. Owner: `cloud`. Source: Workload Identity Federation.
- **Federation boundary never negatively tested.** Unauthorized repositories, branches and job contexts must be shown unable to obtain production credentials.
  Check: there is a recorded test of permitted and denied contexts and of out-of-scope resource access, repeated after trust-policy, claim-format or workflow changes. Owner: `platform`. Source: Workload Identity Federation.
- **Token exchange not audited.** Workflow attribution is not automatic.
  Check: cloud audit or data-access logs for token exchange and role use are enabled in IaC with an unambiguous subject mapping. Owner: `cloud`. Source: Workload Identity Federation.
- **No alerting or kill switch for federated access.** Removing a trust relationship does not end existing sessions.
  Check: alerts exist for unexpected identities and changes to federation trust or permissions, and a runbook covers stopping issuance and revoking issued sessions with propagation delay. Owner: `sre`. Source: Workload Identity Federation.

## Token confidentiality and JWE

- **Sensitive data in a signed JWT.** JWS payloads are only base64url-encoded and readable from logs, storage, referrers and TLS-terminating intermediaries.
  Check: JWTs omit privacy-sensitive claims; prefer an opaque reference token with data kept server-side, and use JWE only when claims must travel to a party that cannot resolve them. Owner: `backend`. Source: JWT.
- **Authorization based on an unsigned JWE.** With a public-key `alg` anyone with the recipient's public key can produce a token that decrypts.
  Check: no authorization decision uses claims from a JWE that is not a nested signed JWT. Owner: `backend`. Source: JWT.
- **Nested JWT not validated at both layers.** Sign then encrypt; the outer JWE `cty` must be `JWT`, and both outer decryption and inner signature must be validated.
  Check: the consumer rejects the token if either decryption or inner signature verification fails. Owner: `backend`. Source: JWT.
- **JWE algorithm chosen by the header.** Letting the header pick the algorithm enables a downgrade that can recover the CEK.
  Check: only an allowlisted `alg`/`enc` pair is accepted (for example `RSA-OAEP-256` or `ECDH-ES+A256KW` with `A256GCM`) and each key is bound to one algorithm. Owner: `backend`. Source: JWT.
- **JWE claims compressed.** `zip` compression before encryption leaks plaintext information.
  Check: the `zip` header is not used. Owner: `backend`. Source: JWT.

## JWT signing algorithms and secrets

- **Not-recommended signature algorithm.** EdDSA, ECDSA (`ES256`/`ES384`/`ES512`) and RSASSA-PSS (`PS*`) are recommended; RSASSA-PKCS1-v1_5 (`RS*`) is not; `HS256`/`HS384`/`HS512` are the recommended MACs; post-quantum ML-DSA is probably not justified unless signatures need long validity.
  Check: issuer configuration uses a recommended algorithm. Owner: `backend`. Source: JWT.
- **Randomized ECDSA on weak-entropy devices.** On embedded systems with questionable randomness the implementation must use deterministic ECDSA (RFC 6979).
  Check: embedded issuers use an RFC 6979 implementation. Owner: `backend`. Source: JWT.
- **MAC used across parties.** With a MAC any audience holding the secret can forge tokens; a different secret must be used per (issuer, audience) pair.
  Check: MAC-signed tokens are limited to cases where the issuer is the audience, otherwise public-key signatures are used; no MAC secret is shared with another issuer or audience. Owner: `backend`. Source: JWT.
- **Weak or mis-sourced HMAC secret.** The secret must come from a local cryptographically secure generator, have at least 160 bits of entropy and at least the output size (256, 384, 512 bits for HS256, HS384, HS512), and must not be a password or hardcoded.
  Check: the secret is generated by a CSPRNG of adequate length and loaded from a secret store, never a literal or passphrase. Owner: `backend`. Source: JWT.
- **Signing key reused for another purpose or published.** Key pairs and MAC secrets must not be reused for encryption or other purposes, and private keys or secrets must not be published.
  Check: signing keys are dedicated to JWT signing and only public keys appear in JWKS endpoints or repositories. Owner: `backend`. Source: JWT.

## SAML deployment, keys and certificates

- **SAML signing key stored as a plain file.** IdP signing keys are a top attacker target; file keys are trivially exfiltrated.
  Check: IdP operators strongly consider an HSM (FIPS 140-2 or 140-3) for signing keys. Owner: `cloud`. Source: SAML.
- **SP trust established by emailed certificate.** An attacker can convince an SP to trust the wrong certificate.
  Check: IdP signing certificates are consumed from the IdP metadata URL over WebPKI-trusted TLS, or exchanged over properly configured TLS, never by email. Owner: `backend`. Source: SAML.
- **Shared key for signing, encryption and TLS.** Signing and encryption must use separate key pairs, and the IdP TLS server certificate must never be the SAML signing certificate.
  Check: distinct certificates per use; KU limited to `digitalSignature` for signing certificates (other KUs disallowed); EKU `id-kp-documentSigning` (1.3.6.1.5.5.7.3.36) may be standardized on. Owner: `backend`. Source: SAML.
- **Weak certificate keys or hashes.** RSA keys must be at least 2048 bits; ECC from 256 bits is preferred when all parties support it; certificate signing hash is at least SHA-256 (never SHA-1), with SHA-384/512 preferred.
  Check: certificate parameters meet these values. Owner: `backend`. Source: SAML.
- **Certificate validity mistaken for key rotation.** Renewing a certificate with the same key does not rotate the key, and CA-issued certificates must not outlive the key's approved usage period.
  Check: certificate replacement is planned before `notAfter`, key usage periods follow the key management policy, and the same lifetime policy applies to self-signed and CA-issued certificates. Owner: `cloud`. Source: SAML.
- **Revocation information ignored.** If a CRL distribution point or OCSP URL is present on any certificate in the chain, the validating party should check it.
  Check: the SP validates CRL/OCSP when present and inspects each issuer in the path to the root. Owner: `backend`. Source: SAML.
- **Third-party private CA over-trusted.** An improperly scoped CA can become trusted for TLS or code signing.
  Check: third-party private CAs are WebTrust, ETSI or SOC 2 Type II audited and trusted only for IdP signature validation; self-signed certificates with secure exchange are the preferred option. Owner: `backend`. Source: SAML.
- **No key-compromise rotation plan.** Revoking without coordinated replacement causes an outage, and many libraries do not check revocation.
  Check: a runbook with partner contact lists exists for rapid certificate rotation. Owner: `sre`. Source: SAML.
- **IdP assertion hygiene.** The IdP should synchronize to a common time source, define levels of assurance, offer strong authentication, and prefer pseudonymous identifiers over PII such as SSNs.
  Check: IdP configuration covers NTP, assurance levels and non-PII subject identifiers. Owner: `backend`. Source: SAML.
- **SAML transport and crypto not hardened.** Assertions must be exchanged only over TLS, sensitive attributes may be XMLEnc-encrypted, all elements should use strong encryption, and insecure XMLEnc algorithms (RSA 1.5) should be deprecated.
  Check: ACS and metadata endpoints are TLS-only and RSA 1.5 key transport is disabled. Owner: `backend`. Source: SAML.
- **SP session, logout and authorization context undefined.** The SP must define session management, logout criteria, and the granularity of authorization context (groups, roles, attributes) taken from assertions.
  Check: the SP validates session state, has documented logout and session rules, and maps assertion attributes to authorization explicitly. Owner: `backend`. Source: SAML.
- **Per-partner endpoints without IP filtering.** IP filtering per partner endpoint, where appropriate, counters stolen assertions and MITM.
  Check: consider separate ACS endpoints per trusted partner with IP filters at the edge. Owner: `cloud`. Source: SAML.
