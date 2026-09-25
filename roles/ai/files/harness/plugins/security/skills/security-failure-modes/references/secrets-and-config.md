# Secrets and configuration

When to read: the assessed surface includes environment and config handling, CORS, debug flags, or error paths; fires in any whole-repo assessment.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **A clean working tree over a dirty history.** Secrets deleted in a later commit remain in every clone; checking only HEAD certifies nothing.
  Check: run the project's installed secrets scanner in history mode if one exists; if none does, sample history for high-risk paths (env files, key material, cloud credentials) and record "run a history-mode secrets scan" as the named next step in Not assessed.
- **Example files that drifted real.** Sample envs, fixtures, and seed configs accumulate real values because they are exempt from scrutiny.
  Check: read every example, sample, and fixture config; any value that looks live (a high-entropy string, a real hostname, a resolvable account ID) fires the escalation trigger below, not the ranked list.
- **Secrets in the wrong custody.** Values inlined in CI config, compose files, IaC variables, or image layers outlive every rotation policy.
  Check: trace how each secret reaches the code: store references resolved at runtime, or inline values; every inline value is a finding with its custody named.
- **CORS open with credentials.** An origin reflected without validation while credentials are allowed hands authenticated API access to any page a user visits; a literal wildcard with credentials is refused by browsers, but frameworks often quietly turn that wildcard into reflection.
  Check: read the CORS configuration: origins are an explicit allowlist, and any wildcard or unvalidated origin echo alongside credentials support is a finding.
- **Debug left on for production paths.** Debug modes, profilers, verbose errors, and stack traces in responses map the internals for anyone who asks.
  Check: read the production configuration path specifically, not the defaults: debug off, error responses generic, stack traces confined to server logs.
- **Secure defaults inverted.** Frameworks ship protections (CSRF tokens, secure cookies, TLS verification) that one config line disables.
  Check: search the config and client setup for protections toggled off (verify disabled, secure flags false, CSRF exempted) and confirm each has a stated reason and bounded scope.
- **One secret across environments.** Staging and production sharing credentials makes the weakest environment the blast radius of both.
  Check: compare environment configs for the same secret reference or value reused across trust levels.
- **Config assembled where the repo cannot see it.** Deploy-time injection from CI variables or secret stores means part of the security posture is invisible from the repo.
  Check: name which config surfaces resolve outside the repo and place them in Not assessed with the owner who can verify them, instead of assuming them safe.
- **Transport and header posture unexamined.** Missing TLS redirects, HSTS, or framing and content-type protections quietly weaken every other control.
  Check: locate where security headers and TLS enforcement are set (app middleware, proxy or platform config); if they live outside the repo, record that in Not assessed rather than assuming either way.

## Escalation triggers (report immediately)

- A secret that looks live (not a placeholder, high entropy, referenced by real config) in the working tree or history: rotation is urgent; lead the report with it and treat the credential as compromised regardless of reachability.
- Signs a leaked credential has already been used (tokens in history plus unattributable commits, identities, or infrastructure): incident response, beyond assessment scope; say so and stop.

## What good looks like

- Secrets exist only in stores; the repo holds references, and history is scanner-clean or the gap is named.
- Example files are boring: placeholder values that could not possibly work.
- Production configuration is auditable in one place, secure defaults on, every exception justified in writing.
