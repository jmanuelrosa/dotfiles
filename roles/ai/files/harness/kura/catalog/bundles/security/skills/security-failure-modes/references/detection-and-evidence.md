# Detection and evidence

When to read: the assessed surface includes logging of security events, audit trails, or alerting; every assessment's closing lens. Fixes here route to the SRE seat.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **Exploitation would be silent.** For each top threat in the threat model, no log line would fire if it happened tonight.
  Check: for every P0 and P1 threat recorded, answer "what would this look like in the logs" and find the emitting statement; no answer is a detection-gap finding routed to the SRE seat.
- **Auth failures logged without context.** Failed logins and permission denials logged without actor, resource, and origin (or not at all) cannot be alerted on or investigated.
  Check: read the authentication-failure and authorization-denial paths: a structured log with actor, resource, outcome, and source exists on each.
- **Privileged actions without an audit trail.** Role grants, data exports, config changes, and deletions that leave no attributable record make incidents unreconstructable.
  Check: trace the privileged mutations found in authz-and-tenancy for audit events attributing actor and change.
- **Logs that leak or lie.** A log that captures secrets becomes the target; a log that records client-supplied identity fields records what the attacker typed.
  Check: audit the security-relevant log statements: no secrets or tokens in payloads, and identity fields taken from the authenticated principal, not from request headers alone.
- **Detection killed by level or sampling.** Security events emitted at debug level, or sampled out by the production config, exist only in development.
  Check: confirm from the production logging configuration that security events survive at their configured level and channel.
- **Signal nobody consumes.** Log statements without an alert rule, monitor, or review path are storage, not detection.
  Check: look for alerting or monitor definitions in the repo that consume the security events found above; where alerting lives outside the repo, record the question in Not assessed with its owner instead of assuming it exists.
- **Evidence with no retention.** Logs that rotate away in days erase the window most incidents are discovered in.
  Check: read retention configuration where visible in the repo; unknown retention goes to Not assessed, not into the posture summary.
- **Automated security signal unowned.** Dependency alerts, audit steps, and scanner findings piling up unowned train everyone to ignore them.
  Check: whether automated security checks exist in CI and whether their current findings are triaged or stale; a stale pile is itself a process finding.

## Escalation triggers (report immediately)

- Evidence of active compromise found while reading logs and configs (unattributable access, tampered or gapped logs, unknown admin identities): incident response, beyond assessment scope; say so and stop.

## What good looks like

- Every threat in the model maps to an observable event, and the mapping is short enough to review.
- Auth failures and denials are structured, attributable, and alert-worthy by design.
- Someone owns the security signal: alerts have a destination, automated findings have a triage path.
