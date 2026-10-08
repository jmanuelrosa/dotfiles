# Mobile Applications and Pinning

When to read: the brief, diff, or assessed surface touches an iOS, Android, or cross-platform mobile app: local storage, Keychain or Keystore, biometrics, deep links or universal links, App Intents, Siri, Shortcuts or widgets, network security config or ATS, certificate or public key pinning (including OpenSSL or Electron clients), app attestation, obfuscation, or the backend endpoints a mobile app calls.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Mobile Application Security](https://cheatsheetseries.owasp.org/cheatsheets/Mobile_Application_Security_Cheat_Sheet.html), [Pinning](https://cheatsheetseries.owasp.org/cheatsheets/Pinning_Cheat_Sheet.html)

## Contents

- Authentication and authorization
- Credentials, keys and local storage
- Lock-screen surfaces and deep links
- Network communication
- Certificate and public key pinning
- Sessions and sensitive operations
- Data leakage and privacy
- App integrity and attestation
- Supply chain, updates and testing

## Authentication and authorization

- **Authorization decided on the device.** Authentication and authorization run server-side and data loads onto the device only after successful authentication; every client-side control is assumed bypassable and is repeated server-side, and every backend function performs an authorization check.
  Check: each API the app calls enforces authentication and authorization itself, with no endpoint relying on the app hiding a button or screen. Owner: `backend`. Source: Mobile.
- **Spoofable device identifier used for authentication.** Device identifiers and similar spoofable values are never treated as proof of identity.
  Check: no server-side login or session path accepts a device ID, advertising ID, or install ID as a credential. Owner: `backend`. Source: Mobile.
- **User password stored on the device.** User passwords and credentials are not stored on the device; the app holds device-specific, revocable access tokens instead.
  Check: no code path writes the password to storage, Keychain, Keystore, or preferences after login. Owner: `mobile`. Source: Mobile.
- **Credentials or API keys hardcoded in the app.** Credentials are never hardcoded in the app, are encrypted in transmission, and API keys or tokens the app uses are regularly updated and rotated; backend authentication uses OAuth2, JWT, or a similar standard.
  Check: no secrets, keys, or passwords in source, resources, or build config shipped in the binary. Owner: `mobile`. Source: Mobile.
- **Short PIN or composition-rule password policy.** Account passwords allow long passphrases without character-composition rules and block common or compromised passwords per NIST guidance; short PINs such as 4 digits are not allowed.
  Check: PIN length validation rejects 4-digit PINs and password rules have no composition requirements. Owner: `mobile`. Source: Mobile. See `authentication.md` for password length and strength controls.
- **Custom biometric check or no fallback.** Biometric authentication uses platform-supported methods (on iOS, `LAContext` `evaluatePolicy` through the Secure Enclave so biometric data never reaches the app) and always offers a fallback such as a PIN.
  Check: biometrics go through the platform API and a non-biometric path exists. Owner: `mobile`. Source: Mobile.
- **Permissions beyond what the app needs.** Request only the device permissions the app needs and only the backend permissions it needs, ship the most secure settings by default, keep app files from overly permissive file permissions, and declare privacy configuration in `Info.plist` for features requiring user permission.
  Check: the manifest or entitlements request no unused permission and created files are app-private. Owner: `mobile`. Source: Mobile.

## Credentials, keys and local storage

- **Sensitive local data unencrypted or its key unprotected.** Sensitive data at rest is encrypted with platform crypto APIs (never custom algorithms), kept on internal storage, and its keys live in platform key storage (Keychain on iOS, Keystore on Android), hardware-backed when available (Secure Enclave, StrongBox or TEE). Password-derived keys use a dedicated password-based key derivation function with a unique random salt and an appropriate work factor; a password or a fast hash of it is not an encryption key.
  Check: encryption keys come from the platform keystore rather than constants, preferences, or a plain hash of the user's password. Owner: `mobile`. Source: Mobile. See `cryptography-and-keys.md` for algorithm choices.
- **Key not hardware-backed or not bound to user authentication.** On Android, generate keys with `setIsStrongBoxBacked(true)` where available (Android 9+), verify with `KeyInfo.isInsideSecureHardware()`, fall back to the regular hardware-backed keystore, and set `setUserAuthenticationRequired(true)` for sensitive operations; on iOS, create keys with `SecKeyCreateRandomKey` and `kSecAttrTokenID` set to `kSecAttrTokenIDSecureEnclave`, with access control such as `kSecAccessControlBiometryAny` or `kSecAccessControlUserPresence` when user authentication should gate key use.
  Check: key generation code sets these hardware-backing and user-authentication flags for sensitive keys. Owner: `mobile`. Source: Mobile.
- **Sensitive data in preferences, plist files, or backups.** Sensitive data is not stored in Android `SharedPreferences` or iOS `plist` files, Android backup mode is disabled so sensitive data does not land in backups, authentication tokens are stored securely with expiry handled gracefully, and App Groups shared with widgets have appropriate security configuration.
  Check: `allowBackup` is false (or backup rules exclude sensitive files) and tokens are read from Keychain or Keystore-protected storage. Owner: `mobile`. Source: Mobile.

## Lock-screen surfaces and deep links

- **Sensitive App Intent or Shortcut runs on a locked device.** Shortcuts can run from widgets, the Action Button, Control Center, Siri, the lock screen, or on a schedule while the device is locked, so sensitive App Intents (iOS/iPadOS 16+) set `authenticationPolicy` to `.requiresLocalDeviceAuthentication` and still enforce the app's session and authorization checks; `isProtectedDataAvailable` reports file availability and is never used as an authentication check.
  Check: every App Intent that performs a sensitive action declares the device-authentication policy. Owner: `mobile`. Source: Mobile.
- **Sensitive Siri action allowed while locked.** Siri can reach app functions by voice or Type to Siri while locked, so sensitive Siri actions use the App Intent authentication policy, destructive work calls `requestConfirmation()` and stops on cancel (confirmation does not replace authentication or authorization), and legacy SiriKit intents are set to Restricted While Locked (`INIntentsRestrictedWhileLocked`).
  Check: sensitive intents carry the authentication policy or appear in `INIntentsRestrictedWhileLocked`. Owner: `mobile`. Source: Mobile.
- **Deep link opens a protected screen without authentication.** Every view controller or endpoint reachable by deep link performs authentication checks and redirects unauthenticated users to login, Universal Links are configured and validated through `apple-app-site-association`, and every deep-link parameter is validated and sanitized against injection.
  Check: the deep-link router checks session state before navigating to protected screens and validates each parameter. Owner: `mobile`. Source: Mobile.
- **Lock-screen widget exposes sensitive data.** Mark sensitive widget views with `privacySensitive(_:)` and provide redacted placeholders, enable Data Protection with `NSFileProtectionComplete` for the widget extension when content must stay hidden while locked, and configure background refresh so sensitive data does not update while locked.
  Check: widget views showing account data are marked privacy-sensitive. Owner: `mobile`. Source: Mobile.

## Network communication

- **TLS certificate validation overridden.** The app never overrides certificate validation to accept self-signed or invalid certificates, uses certificates signed by a trusted CA, and treats all network communication as interceptable.
  Check: no custom trust manager, hostname verifier, or `URLSession` delegate that accepts every certificate, and no debug trust override reachable in release builds. Owner: `mobile`. Source: Mobile.
- **Cleartext or weak transport.** All network communication uses HTTPS with strong, industry-standard cipher suites and key lengths, avoids mixed-version SSL sessions, and is enforced by ATS on iOS; sensitive data is encrypted even when sent over TLS, and sensitive data is not sent by SMS.
  Check: ATS has no arbitrary-loads exception and Android network security config disallows cleartext traffic. Owner: `mobile`. Source: Mobile. See `http-headers-tls-and-caching.md` for TLS configuration.

## Certificate and public key pinning

- **Pinning adopted where it should not be.** There is almost no situation where pinning should be considered, since outage risk almost always outweighs the security gain; do not pin unless you control both client and server, can update the pinset securely, can update without disruptive redeployment (forced updates inside a corporation are a possible exception), can predict the key pair before it goes into service, and the client is a native mobile app.
  Check: any new pinning config is backed by a documented threat model and a pinset update path. Owner: `mobile`. Source: Pinning, Mobile.
- **Pin learned on first use or over an unpinned channel.** Preload pins out of band at development time rather than trusting on first use or updating them over an unpinned channel, which lets an attacker taint the pin.
  Check: pins are compiled into the app or its declarative config, not fetched at runtime. Owner: `mobile`. Source: Pinning.
- **Root CA pinned, or leaf pinned without a backup.** Pinning a root CA is not recommended; pin the leaf certificate with a backup (an intermediate CA or alternate pins) for rotation and failover, and prefer the `subjectPublicKeyInfo` over the whole certificate or a concrete key type (a hash of it is acceptable). Renewing a certificate with the same key to keep a pin valid is bad key management and only an emergency measure.
  Check: the pinset contains at least two pins, none of them a root CA. Owner: `mobile`. Source: Pinning.
- **Pin mismatch bypassable by the user.** On a pin mismatch the connection fails, the event is logged client-side, and the user is alerted, with no option to proceed past the pin.
  Check: the pin-failure path has no "continue anyway" branch. Owner: `mobile`. Source: Pinning.
- **Hand-rolled pin validation.** Use the platform's declarative configuration (Android Network Security Configuration `<pin-set>`, iOS ATS identity pinning in `Info.plist`) or a vetted library (OkHttp `CertificatePinner`, TrustKit, electron-ssl-pinning or `setCertificateVerifyProc` on Electron) rather than writing validation from scratch, where mistakes are likely and severe.
  Check: pinning is configured declaratively or through a maintained library, not a custom trust evaluator. Owner: `mobile`. Source: Pinning.
- **OpenSSL client accepts a missing peer certificate.** With OpenSSL, call `SSL_get_verify_result` and require `X509_V_OK`, call `SSL_get_peer_certificate` and require a non-NULL certificate (a server sending no certificate yields `X509_V_OK` with NULL), and fail the connection and tear down the socket on error.
  Check: OpenSSL client code checks both results before sending data. Owner: `backend`. Source: Pinning.
- **Interception proxy allowlisted around pinning.** Do not allowlist DLP interception proxies, since they break end-to-end security indistinguishably from attackers; add a proxy's public key to the pinset only when instructed by risk acceptance.
  Check: no pin bypass for corporate proxies without a recorded risk acceptance. Owner: `mobile`. Source: Pinning.

## Sessions and sensitive operations

- **Session never expires or cannot be revoked remotely.** Sessions time out after inactivity, use randomly generated tokens, are protected on both client and server, and users can log out remotely.
  Check: the server enforces an inactivity timeout and exposes a revoke-all-sessions path. Owner: `backend`. Source: Mobile. See `sessions-and-cookies.md` for session lifetimes.
- **Sensitive operation without re-authentication.** Require re-authentication for sensitive operations such as changing the password or updating payment information, and consider it before displaying highly sensitive information.
  Check: password, payment, and similar change endpoints demand a fresh authentication proof. Owner: `backend`. Source: Mobile.
- **No security-activity notifications.** Inform the user about security-related activity such as logins from new devices.
  Check: a new-device login emits a user notification. Owner: `backend`. Source: Mobile.

## Data leakage and privacy

- **Sensitive data leaked through caches, logs, or snapshots.** Sensitive data is kept out of caching, logging, and background (app-switcher) snapshots, and sensitive UI fields are masked against shoulder surfing.
  Check: the app obscures its window when backgrounded on sensitive screens, disables caching of sensitive responses, and logs no tokens or PII. Owner: `mobile`. Source: Mobile. See `logging-and-error-handling.md` for data to exclude.
- **PII collected beyond necessity or kept indefinitely.** Minimize PII, replace it with less critical data where possible, reduce collection frequency (for example location updates), expire and delete it automatically, and obtain user consent before collecting or using it.
  Check: PII collection is gated on consent and stored PII has an expiry. Owner: `mobile`. Source: Mobile. See `privacy-and-payments.md` for user privacy protection.
- **Unvalidated input or output in the app.** Validate and sanitize user input, and validate and sanitize output to prevent injection and execution attacks.
  Check: values rendered in WebViews or passed to queries are encoded or parameterized. Owner: `mobile`. Source: Mobile. See `injection.md` for input validation.

## App integrity and attestation

- **Debuggable or unprotected release build.** Disable debugging, obfuscate the binary (ProGuard on Android), validate code integrity, and add runtime anti-tampering: detect debugging, hooking, or code injection, detect emulators and rooted or jailbroken devices, verify the app signature at runtime, and respond proportionately (for example by limiting functionality); higher-risk apps add runtime behavioral monitoring.
  Check: release build config sets debuggable false and enables obfuscation, and tamper checks are present. Owner: `mobile`. Source: Mobile.
- **Integrity verdict trusted on the device.** Use Google Play Integrity (the SafetyNet Attestation API was turned down in January 2025 and all developers must migrate) and Apple App Attest (iOS 14+, `DCAppAttestService`), complemented by DeviceCheck for persistent device state, and validate verdicts and assertions server-side, acting when checks fail.
  Check: the server verifies the integrity token or assertion before honoring sensitive requests, and no SafetyNet calls remain. Owner: `backend`. Source: Mobile.

## Supply chain, updates and testing

- **Unsigned app or unvetted third-party libraries.** Sign the app, use only trusted and validated third-party libraries kept up to date, establish security controls for updates and releases, and monitor third-party products for security incidents.
  Check: release signing is configured in CI and dependencies are pinned and scanned. Owner: `mobile`. Source: Mobile. See `supply-chain-and-dependencies.md` for dependency management.
- **No forced-update path.** Plan for regular updates, because store review and user update delays slow patch rollout, and have a mechanism to force users onto a fixed version when necessary.
  Check: the app checks a server-provided minimum version at launch and blocks below it. Owner: `mobile`. Source: Mobile.
- **Security behavior untested.** Automated tests verify security features and access-control enforcement (including calling backend functions with session tokens removed), static analysis runs on the code, code reviews focus on security, penetration tests cover cryptography, and usability testing ensures security features do not push users to bypass them.
  Check: the test suite includes unauthenticated and cross-user API calls for the app's endpoints, and SAST runs in CI. Owner: `qa`. Source: Mobile.
- **No mobile incident response or monitoring.** Keep a clear incident response plan and real-time monitoring to detect and respond to threats.
  Check: a runbook exists for app compromise (key rotation, forced update, token revocation). Owner: `sre`. Source: Mobile.
- See `secure-sdlc.md` for secure-by-design principles (least privilege, defense in depth, separation of concerns) applied from the start of development.
