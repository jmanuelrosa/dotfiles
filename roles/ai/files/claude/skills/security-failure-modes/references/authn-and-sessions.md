# Authentication and sessions

When to read: the assessed surface includes login, credentials, tokens, sessions, MFA, SSO, or password recovery.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **Token validation taken on faith.** A verifier that skips signature, expiry, issuer, or audience checks, or accepts the algorithm the token itself declares, makes tokens forgeable.
  Check: read the actual verification call site and its options; confirm signature, expiry, issuer, and audience are all enforced and the accepted algorithms are fixed by the verifier configuration, never taken from the token.
- **Sessions that never die.** Tokens without expiry, sessions never rotated at login or privilege change, and logout that only deletes the client copy leave stolen credentials useful forever.
  Check: trace the session or token lifecycle in code: where issued, lifetime, rotation on authentication events, and a server-side revocation path that logout actually calls.
- **Recovery as the weakest door.** Password reset and account recovery bypass authentication by design; predictable tokens, missing expiry or single-use enforcement, and existence-revealing responses undo the front door.
  Check: trace the reset flow end to end: token generated from a CSPRNG, single-use and expiring, and responses identical whether or not the account exists.
- **No brute-force resistance.** Login, reset, OTP, and MFA endpoints without rate limits or lockouts turn credential guessing into a batch job.
  Check: locate the rate-limit or lockout control covering each credential-accepting endpoint in code or gateway config; verification is finding the control, never sending traffic at it.
- **Credential storage below the bar.** Fast or unsalted hashes, reversible encryption, or plaintext columns make one database read a full account compromise.
  Check: read the hashing call site: an established KDF (argon2, bcrypt, scrypt) via a maintained library, and secret comparisons done constant-time.
- **The alternate doors.** API keys, personal access tokens, mobile or legacy login versions, and basic-auth fallbacks often skip the protections the primary flow carries.
  Check: enumerate every authentication path in the code, not just the main login, and confirm each carries equivalent validation, expiry, and rate limiting.
- **SSO glue trusted blindly.** OIDC and OAuth callbacks that skip state or nonce validation, or link accounts on an unverified email claim, let one identity claim another.
  Check: read the callback handler: state and nonce validated, tokens verified against provider keys, and account linking keyed on the issuer plus subject identifier rather than email alone.
- **MFA that can be stepped around.** Enrollment or verification endpoints reachable out of order, or remember-me shortcuts, leave a path to an authenticated session that never completed MFA.
  Check: trace the post-login state machine for any path that reaches an authenticated session while skipping a required MFA step.
- **Machine identities with human-sized privileges.** Service accounts, bot tokens, and integration credentials now outnumber human users, and they are the ones nobody rotates or scopes down.
  Check: inventory the non-human credentials referenced in code and config, and read each one's scope and rotation story; a long-lived, broadly scoped machine token is a finding, not plumbing.
- **Tokens stored where they leak.** Credentials in URLs, long-lived tokens in client storage readable by scripts, or session IDs in log lines get harvested by everything on the path.
  Check: trace where tokens live on client and server and whether any URL, log statement, or error path the flow touches captures them.

## Escalation triggers (report immediately)

- Authentication absent or bypassable on an internet-facing surface guarding sensitive data: an actively exploitable P0; lead the report with it.
- Hardcoded credentials that look current found while tracing auth flows: rotation is urgent; lead the report with it (secrets-and-config carries the custody checks).

## What good looks like

- One authentication layer and one verifier with all claims checked; alternate doors carry the same strength as the front one.
- The session lifecycle (issue, rotate, expire, revoke) is traceable in code end to end.
- Every credential-accepting endpoint shares one rate-limit control by construction.
