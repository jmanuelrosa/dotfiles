# Data protection and leakage

When to read: the assessed surface includes personal or sensitive data flows, logging, analytics, exports, or client bundles.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **Sensitive flows unmapped.** Leakage cannot be assessed without knowing what is sensitive and where it travels.
  Check: from the schema and code, inventory the sensitive fields (personal data, credentials, tokens, financial and health data) and trace each flow: stored where, sent where, logged where. This inventory anchors every other check in this file.
- **PII in logs and error trackers.** Request logging, exception context, and query logging capture emails, tokens, and addresses; log pipelines then replicate them widely.
  Check: read the logging middleware and error-tracker configuration against the inventory: redaction or scrubbing verified in the code, never assumed from a vendor's defaults.
- **Analytics as exfiltration.** Event payloads carrying names, emails, or content ship personal data to third parties at page-view granularity.
  Check: read the analytics call sites: identifiers are opaque IDs, and payload fields check clean against the sensitive-field inventory.
- **Server env in the client bundle.** Bundlers embed referenced env vars, and public-prefix conventions invert by accident, shipping server secrets to every browser.
  Check: read the bundler config and env usage: server-only variables referenced from client-reachable code are findings; when only the source is available, name bundle inspection as the next step in Not assessed.
- **Tokens and personal data in URLs.** Query strings are logged by every proxy, kept in history, and leaked through referrers.
  Check: trace whether tokens, session identifiers, or personal data travel in URLs anywhere in the assessed flows.
- **Encryption asserted, not located.** "Encrypted at rest" is a claim until the mechanism is found.
  Check: for each store holding inventoried data, locate the encryption control in config or code (platform encryption settings, key management wiring, field-level crypto); an unlocatable claim goes to Not assessed, not into the posture summary.
- **Backups, exports, and caches as the soft copy.** Data guarded in the primary store leaks through CSV exports, report files, object-storage copies, and caches with weaker access control.
  Check: trace export, report, backup, and cache paths for inventoried fields and read the access control on each destination.
- **No deletion story.** Sensitive data with no retention or deletion path contradicts stated policy and grows breach impact monotonically.
  Check: look for deletion and retention mechanisms covering the inventoried data; their absence is a finding worth one line, not a moral essay.
- **Third-party processors unlisted.** Outbound integrations (email, support, enrichment, LLM APIs) quietly widen who holds the data.
  Check: from the outbound integrations, list which carry inventoried fields; user content flowing into an LLM API is such a flow and also fires llm-and-agent-surface.

## Escalation triggers (report immediately)

- Sensitive data confirmed publicly reachable right now from config alone (an unauthenticated bucket or endpoint serving inventoried data): an actively exploitable P0; lead the report with it.
- Evidence exfiltration has already happened (access artifacts or destinations nobody can attribute): incident response, beyond assessment scope; say so and stop.

## What good looks like

- A short sensitive-data inventory exists, and every flow on it has a named control.
- Logs, analytics, and error trackers are scrubbed by mechanism, not by author discipline.
- The client bundle holds nothing whose exposure would matter.
