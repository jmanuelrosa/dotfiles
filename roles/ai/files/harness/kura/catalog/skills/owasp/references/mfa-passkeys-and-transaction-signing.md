# MFA, Passkeys and Transaction Signing

When to read: the brief, diff, or assessed surface touches MFA enrollment or enforcement, OTP/TOTP/SMS codes, push approval, WebAuthn or passkey registration and authentication, authenticator recovery or factor changes, step-up or risk-based authentication, or confirmation of high-value operations (payments, transfers, signing).
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Multifactor Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html), [Passkey Security](https://cheatsheetseries.owasp.org/cheatsheets/Passkey_Security_Cheat_Sheet.html), [Transaction Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html), [Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [Credential Stuffing Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html)

## Contents

- Transaction authorization
- WebAuthn ceremony verification
- Passkey registration binding
- MFA coverage and downgrade
- Factor changes, credential lifecycle and recovery
- OTP, SMS and push handling
- Risk signals and notification

## Transaction authorization

- **Transaction authorization enforced client-side.** Transaction authorization must be enforced on the server; tampering with transaction parameters, adding or removing parameters, or triggering an error must never change the authorization result. Apply default deny and remove debugging functionality from production.
  Check: the execute handler re-checks authorization state server-side and fails closed on any exception or missing field. Owner: `backend`. Source: Transaction Authorization.
- **Authorization method selectable by the client.** When several authorization methods exist, the server must enforce the user's chosen method or the policy-mandated one, and the client must not be able to downgrade it by parameter; when adding a stronger method, make sure the old method's code path can no longer authorize transactions.
  Check: the method is read from server-side user settings, not the request, and legacy method handlers reject requests once a user migrated. Owner: `backend`. Source: Transaction Authorization.
- **Transaction data shown for signing comes from the client.** All significant transaction data must be generated and stored on the server, verified by the user, and passed to the authorization component without any possibility of client tampering.
  Check: the challenge or signing payload is built from the server-stored pending transaction, not echoed request fields. Owner: `backend`. Source: Transaction Authorization.
- **User cannot see what they are approving.** Apply What You See Is What You Sign: the authorization method must let the user identify and acknowledge the significant transaction data (for example target account and amount), and when the user enters data into an external device, prompt for a specific value such as the target account.
  Check: the SMS, push or device prompt includes the significant fields of the transaction. Owner: `backend`. Source: Transaction Authorization.
- **Transaction steps executable out of order.** The flow (enter data, request authorization, initialize mechanism, confirm, submit credential, execute) must run sequentially; steps cannot be skipped or reordered, and a final control gate tied to execution must verify the transaction was properly authorized (blocking TOCTOU and skipped checks).
  Check: the transaction has a server-side state machine and the execute step asserts the authorized state on the same record. Owner: `backend`. Source: Transaction Authorization.
- **Transaction data modifiable after authorization starts.** Any modification of transaction data during authorization must invalidate previously entered authorization data and the challenge and reset the process; such attempts must be logged, monitored and investigated.
  Check: updates to a pending transaction clear the challenge and emit a security event. Owner: `backend`. Source: Transaction Authorization.
- **Authorization credential reusable across transactions.** Each transaction needs unique authorization credentials, unique per operation (timestamp, sequence number or random value in the signed data or challenge), and valid only in a limited time window between challenge generation and completion.
  Check: the challenge is bound to one transaction id, has an expiry, and is consumed on use. Owner: `backend`. Source: Transaction Authorization.
- **Transaction authorization credential brute-forceable.** After a set number of failed authorization attempts, restart the entire transaction authorization process.
  Check: the verify handler counts failures per transaction and discards the transaction after the limit. Owner: `backend`. Source: Transaction Authorization.
- **Authentication and transaction signing look identical to the user.** Make authentication and transaction authorization distinguishable (different methods, different device modes, a clear message about what is being signed) so malware cannot replay a fake login prompt to obtain a transaction approval.
  Check: the transaction prompt differs from the login prompt and states the operation. Owner: `architect`. Source: Transaction Authorization.
- **Authorization token or method changed without current credentials.** Changing the authorization token (for example the SMS phone number) or the authorization method must be authorized with the current token or method, and users should be informed of the risks of weaker methods.
  Check: the change-phone or change-method handler requires a code from the current factor. Owner: `backend`. Source: Transaction Authorization.
- **Transaction data exposed in transit.** Protect the confidentiality of transaction data in all client-server communications during authorization.
  Check: authorization endpoints are TLS-only and do not put transaction data in URLs. Owner: `backend`. Source: Transaction Authorization.
- **Signing keys unprotected during device pairing.** Use cryptographic operations to protect transaction integrity, confidentiality and non-repudiation; protect device signing keys during pairing as carefully as the signing protocol itself, and protect them with a second factor or a secure element (TEE, TPM, smart card). Treat anti-malware only as an additional layer.
  Check: the pairing flow authenticates the device before key provisioning and the key is stored in platform secure hardware. Owner: `mobile`. Source: Transaction Authorization.

## WebAuthn ceremony verification

- **Hand-rolled WebAuthn verification.** Do not implement CBOR parsing, COSE key handling, attestation validation or assertion verification yourself; use a maintained server-side WebAuthn library, keep it updated, and test successful and failing ceremonies in automated tests. The application still owns challenge issuance, RP ID and origin choice, session binding, UV policy and credential lifecycle.
  Check: a maintained WebAuthn library is in the manifest, and tests cover rejected ceremonies. Owner: `backend`. Source: Passkey Security.
- **Challenge weak, reusable, or unbound.** Generate each registration and authentication challenge with a CSPRNG of at least 16 bytes, expire it promptly, accept it once, and bind it in server-side state to the ceremony type, session and intended account, expected RP ID and origin policy, UV and attestation policy, and expiry. Never accept an authentication challenge for registration or a challenge for another account; invalidate on success or terminal failure.
  Check: challenge storage records type, account, expiry and a consumed flag, and the verify path checks all of them. Owner: `backend`. Source: Passkey Security.
- **Origin built from request headers or matched by pattern.** Keep an explicit allowlist of permitted origins (scheme, host, port) and use the same expected RP ID for registration and authentication; never derive the expected origin from an untrusted header. Native app origins (`android:apk-key-hash:...`, Apple HTTPS origin) must be explicit entries, never patterns, and `assetlinks.json` and `apple-app-site-association` must be under the same change control as the allowlist.
  Check: expected origins and RP ID come from config as exact strings. Owner: `backend`. Source: Passkey Security.
- **RP ID scoped to a broad parent domain.** Use the narrowest stable domain that covers the application as RP ID; do not use a registrable parent domain just to share credentials with unrelated subdomains.
  Check: the configured RP ID equals the app's host or the narrowest shared parent actually needed. Owner: `architect`. Source: Passkey Security.
- **Registration response stored before full verification.** Verify client data type `webauthn.create`, exact challenge match, origin in the allowlist, RP ID hash, UP set and UV set when required, an offered and permitted algorithm, structurally valid credential id and public key, extensions per policy, and attestation when policy requires; store the credential only after every check passes.
  Check: the registration handler persists only after the library's verify returns success with the expected origin, RP ID and UV requirement passed in. Owner: `backend`. Source: Passkey Security.
- **Assertion accepted with incomplete checks.** Verify client data type `webauthn.get`, an unexpired unused challenge, origin, RP ID hash, that the credential id exists and belongs to the account from the verified ceremony context, the signature under the stored key, UP and required UV, that a returned user handle matches the credential's account, and extension outputs and cross-origin indicators per policy. Create the session only after all pass, and rotate the session id at authentication.
  Check: the assertion verify call receives the stored public key, expected challenge and origins, and session creation follows it. Owner: `backend`. Source: Passkey Security.
- **UP treated as UV.** User presence and user verification are different properties; when a passkey must satisfy MFA or high assurance, request UV and verify the returned UV flag on the server. A touch confirming presence alone is not a second factor.
  Check: the options set `userVerification: required` for MFA policies and the verify step enforces the UV flag. Owner: `backend`. Source: Passkey Security, Multifactor Authentication.
- **Username-less login trusts client identity claims.** For discoverable credentials, omit `allowCredentials`, then resolve the account from the returned user handle and credential id and require both to resolve to the same account; never trust a display name or other client-provided identity.
  Check: account lookup uses the credential record, and a user-handle mismatch fails. Owner: `backend`. Source: Passkey Security.
- **Account-first passkey flow enumerates accounts.** For account-first login, send only the selected account's credential ids in `allowCredentials`, and use generic responses and consistent behavior so the step does not reveal whether the account exists. Treat conditional mediation as another entry to the same ceremony and policy.
  Check: the options endpoint returns the same shape for unknown accounts. Owner: `backend`. Source: Passkey Security.
- **Failed passkey ceremony returns specific errors.** Return generic errors that do not distinguish unknown account, unknown credential, failed signature, or policy rejection, keep timing consistent where practical, and rate-limit by account and network or device signals without creating a trivial lockout denial of service.
  Check: all verification failures map to one error response. Owner: `backend`. Source: Passkey Security.
- **Signature counter anomaly auto-locks accounts.** A non-increasing nonzero counter is a risk signal, not universal clone detection (synced credentials and some authenticators do not count monotonically); record it, evaluate it with other risk signals, document the response policy, and do not lock out automatically on the counter alone.
  Check: counter regression logs an event and feeds risk scoring rather than throwing a hard failure. Owner: `backend`. Source: Passkey Security.
- **Attestation required without a documented need.** Most public applications should request no attestation and not restrict authenticator models. Require attestation only for a documented enterprise or regulatory need, and then define formats, trust anchors, metadata and failure behavior, validate the full chain and status, plan metadata updates, and keep a reviewed exception path.
  Check: attestation conveyance is `none` unless a recorded requirement exists. Owner: `backend`. Source: Passkey Security.
- **Hardware-backed keys assumed without verification.** Do not assume authenticator keys are hardware-backed and non-exportable unless verified via authenticator properties or attestation; where device binding matters, prefer hardware-backed non-exportable keys (TPM, Secure Enclave, StrongBox) and validate attestation when policy requires.
  Check: policies relying on non-exportable keys check attestation or authenticator data. Owner: `backend`. Source: Authentication, Multifactor Authentication.
- **WebAuthn pages exposed to script injection or embedded cross-origin.** Serve registration, authentication and credential-management pages over HTTPS, protect them against script injection, and avoid cross-origin WebAuthn in iframes unless it is a reviewed design with the required Permissions Policy and origin validation.
  Check: these pages have a strict CSP and no cross-origin iframe use of WebAuthn. Owner: `frontend`. Source: Passkey Security.
- **Ceremony data written to logs.** Log structured information to investigate failures, but never challenges, full credential responses, session identifiers, or unnecessary identifying data; do not expose raw credential ids in UIs, URLs or logs.
  Check: logging in WebAuthn handlers excludes these fields. Owner: `backend`. Source: Passkey Security.

## Passkey registration binding

- **Passkey added on a long-lived session alone.** Treat registration as a sensitive account change: for existing accounts require a recently authenticated session and re-authentication before adding a passkey; for new accounts bind the ceremony to the verified account-creation transaction. Protect registration endpoints against CSRF, rate-limit them, and log successful and failed enrollments.
  Check: the registration-options handler checks authentication freshness and has CSRF protection. Owner: `backend`. Source: Passkey Security.
- **Credential associated with a client-supplied account id.** Associate a new credential with the account from server-side ceremony state, never an account id returned by the client; enforce credential id uniqueness across the RP and make the association auditable. Never silently reassign a credential record to a different account; mapping changes need integrity controls, authorization and audit logs, and a duplicate credential id is an error to investigate.
  Check: the stored credential's account comes from the session, the credential id column is unique, and migrations touching it are reviewed. Owner: `backend`. Source: Passkey Security.
- **User handle contains PII or is reused.** Generate a stable, opaque user handle with no username, email or personal data; it identifies one account and is never reassigned.
  Check: the user handle is random bytes stored per account, not derived from email or id. Owner: `backend`. Source: Passkey Security.
- **Duplicate registrations unchecked.** Include existing credential ids in `excludeCredentials` where possible, while still enforcing uniqueness on the server.
  Check: registration options list existing credentials. Owner: `backend`. Source: Passkey Security.
- **Credential metadata overstored or misread.** Store credential id, public key, user handle link, algorithm, transports, creation time, user-visible name and library-required data; store backup eligibility and state but never treat them as proof of a provider or as UV results. Minimize and restrict access to authenticator metadata.
  Check: the credential table holds these fields and no logic treats backup flags as verification. Owner: `database`. Source: Passkey Security.

## MFA coverage and downgrade

- **MFA not available or not required.** Require some form of MFA for all users where feasible, offer TOTP at least, and require MFA for administrative and other high-privileged users even where it cannot be enforced for everyone. MFA is the strongest defense against brute force, credential stuffing and password spraying.
  Check: the auth policy enforces MFA for admin roles and exposes enrollment to every user. Owner: `backend`. Source: Multifactor Authentication, Authentication, Credential Stuffing.
- **Alternate login path skips MFA.** Every way to authenticate (separate login API, mobile app, legacy protocols) must require MFA or have equivalent protections; disable legacy authentication protocols and endpoints that cannot enforce MFA consistently.
  Check: every route that issues a session or token goes through the MFA step. Owner: `backend`. Source: Multifactor Authentication.
- **Two instances of the same factor counted as MFA.** Factors must be independent and not compromisable by the same attack; password plus PIN, password plus security question, IP address, geolocation or behavioral activity signals are not MFA. Behavioral biometrics must be combined with an authenticated physical authenticator.
  Check: the MFA step requires a possession or inherence factor distinct from the first. Owner: `backend`. Source: Multifactor Authentication.
- **Fallback weaker than the primary factor.** Prefer phishing-resistant authenticators (FIDO2/WebAuthn). A failed passkey or phishing-resistant ceremony must not silently fall back to a weaker method such as OTP or SMS; if a fallback exists, make it a deliberate, logged, policy-documented path rather than default error handling. Follow OAuth 2.0 Security BCP (RFC 9700) to prevent protocol-level downgrade and mix-up.
  Check: the passkey error branch does not render an OTP or password form automatically. Owner: `backend`. Source: Multifactor Authentication, Passkey Security.
- **Sensitive actions not gated by MFA.** Require MFA (step-up) for changing passwords or security questions, changing the account email, disabling MFA, elevating to an administrative session, large currency transactions, and privileged configuration changes.
  Check: these handlers require a recent MFA assertion. Owner: `backend`. Source: Multifactor Authentication, Credential Stuffing.
- **Synced passkeys assumed to meet every assurance level.** Public applications should generally support synced passkeys with secure options for more authenticators and recovery; high-assurance or enterprise apps may require managed device-bound authenticators with attestation. Synced passkeys do not meet NIST AAL3.
  Check: the assurance policy states which credential types satisfy each level. Owner: `architect`. Source: Passkey Security.
- **Third-party MFA service adopted without risk review.** MFA as a service is an option, but evaluate its security: its compromise could bypass MFA for every application using it.
  Check: the vendor choice is recorded with its threat assessment. Owner: `architect`. Source: Multifactor Authentication.

## Factor changes, credential lifecycle and recovery

- **MFA factor replaced on an active session alone.** Require re-authentication with an existing enrolled factor before changing a phone number, authenticator app or token; do not rely solely on the session, treat factor replacement as high-risk with risk checks, notify via an out-of-band channel, and consider delays or step-up for high-value accounts.
  Check: the change-factor handler verifies a current factor and sends a notification. Owner: `backend`. Source: Multifactor Authentication.
- **Passkey add or remove without fresh authentication.** Provide an authenticated management page showing user-chosen name, creation and last-used dates (not raw ids). Require recent re-authentication before adding or removing a passkey, changing recovery methods, or disabling the last strong authenticator; allow multiple authenticators; notify on add and remove through an existing trusted channel; record enrollment, use, rename and revocation as security events; revoke server-side immediately on removal or reported compromise; confirm a usable method remains before removing the last passkey. WebAuthn signal methods do not replace server-side revocation.
  Check: delete-credential deletes or disables the server record and checks remaining methods. Owner: `backend`. Source: Passkey Security.
- **MFA reset path bypasses MFA.** Provide a secure MFA reset: single-use recovery codes issued at setup, multiple enrolled factor types, a one-use code or token mailed to the registered address, a rigorous support identity process, or vouching by a trusted user, chosen per the application's context.
  Check: the reset flow uses one of these and does not accept email alone for high-risk accounts. Owner: `backend`. Source: Multifactor Authentication.
- **Recovery weaker than passkey authentication.** Recovery should rely on another registered passkey, a separately secured recovery code, or a high-assurance identity process; protect recovery codes as secrets (stored securely, single-use, regenerable); rate-limit, risk-check, notify and review recovery attempts; do not let email or SMS recovery silently bypass stronger policy for high-risk accounts; after recovery rotate sessions, review or revoke credentials and notify; add delays or extra verification before high-impact actions after a risky recovery. Encourage users to register multiple authenticators.
  Check: recovery codes are hashed and single-use, and recovery completion revokes sessions. Owner: `backend`. Source: Passkey Security.
- **No incident procedure for authenticator compromise.** Document incident procedures for a compromised authenticator, sync account, RP origin, or WebAuthn library, and monitor registration, authentication, recovery and administrative mapping changes.
  Check: a runbook covers these cases and alerts exist on mapping changes. Owner: `sre`. Source: Passkey Security.

## OTP, SMS and push handling

- **OTP reusable or long-lived.** OTPs should have a short TTL, be single-use, have strict attempt limits, and be invalidated on successful verification; on resend, generate a new OTP and overwrite the old record.
  Check: the OTP record has expiry, attempt counter and is deleted on success or resend. Owner: `backend`. Source: Multifactor Authentication.
- **OTP stored or logged in plaintext.** Do not log OTP values or store them long-term in plaintext; hash them (for short-term exposure protection, given the small keyspace). Generate them with a CSPRNG and consider 8 or more digits where usability allows.
  Check: OTP generation uses a CSPRNG and the stored value is hashed. Owner: `backend`. Source: Multifactor Authentication.
- **Proprietary TOTP variant.** Use standards-based TOTP (RFC 6238, default 30-second step, same step on app and server) so users can choose any authenticator app.
  Check: the TOTP library follows RFC 6238 with a configured shared time step. Owner: `backend`. Source: Multifactor Authentication.
- **SMS or voice OTP protecting PII or money.** SMS and PSTN codes are restricted authenticators (SS7 interception, SIM swap, number porting) and should not protect high-value, financial, healthcare or PII-handling applications. Where SMS is the only option, document the risk acceptance, enforce per-account rate limits (also to stop cost exhaustion), monitor SIM-swap and phone-number-change signals, encourage carrier account PINs or port-out protection, and plan migration to TOTP, push or WebAuthn.
  Check: SMS factor use is limited by policy and the send endpoint is rate limited per account. Owner: `backend`. Source: Multifactor Authentication.
- **Push approval allows blind acceptance.** Use challenge-response push (for example number matching), rate-limit or cap push prompts, and monitor for bursts of prompts or new-device token reuse.
  Check: the push payload requires the user to enter or match a code, and a per-user push limit exists. Owner: `backend`, `mobile`. Source: Multifactor Authentication.
- **Client certificates not bound to the user.** Certificates used as a factor must be linked to an individual account so they cannot authenticate other accounts.
  Check: the cert-to-account mapping is verified on login. Owner: `backend`. Source: Multifactor Authentication.

## Risk signals and notification

- **Risk-based step-up spoofable or weaker than MFA.** Risk-based authentication (new device or location, IP reputation, high-risk geography, time of access, known-compromised credentials) can reduce prompts, but risk signals must not be spoofable and fallback mechanisms must not be weaker than the primary MFA.
  Check: risk inputs come from server-observed data and the step-up path uses an enrolled factor. Owner: `backend`. Source: Multifactor Authentication.
- **Failed second factor after correct password is silent.** When the password is correct but MFA fails, prompt for another factor, allow MFA reset, and notify the user (time, browser, location) at next login and optionally by email, encouraging a password change.
  Check: the MFA-failure branch emits a user notification. Owner: `backend`. Source: Multifactor Authentication, Credential Stuffing.
- **Session and MFA anomalies not monitored.** Monitor for impossible travel, new ASN, sudden MFA method changes, unexpected phone-number changes and push bursts that indicate reverse-proxy phishing or SIM swap.
  Check: alerts exist for these events in the security monitoring config. Owner: `sre`. Source: Multifactor Authentication.
