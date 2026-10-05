# Attack surface and trust boundaries

When to read: every assessment starts here; the assessed surface includes anything that accepts input or crosses a trust boundary.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **The entry-point map that stops at HTTP routes.** Background jobs, webhooks, cron tasks, message consumers, CLI admin commands, and upload processors accept input too; an assessment that only maps routes audits half the surface.
  Check: enumerate entry points from the code (route registrations, scheduler and job definitions, consumer bindings, webhook handlers, CLI entry files), not from the README, and record the full list in the surface map.
- **The trust boundary that exists only in the diagram.** "Internal-only" services, admin networks, and VPN-gated panels are claims; the code may not enforce them.
  Check: for each claimed boundary, locate the enforcing control in code or config (authentication on the listener, network policy, gateway rule); a boundary with no findable control is recorded as a finding, not accepted as a fact.
- **The identity model assumed rather than mapped.** Who authenticates how (users, services, jobs, third parties) and what each identity can reach is the skeleton of the threat model; skipping it turns STRIDE into guesswork.
  Check: name every identity class and its credential mechanism from the code, and name explicitly which entry points accept unauthenticated callers (webhooks, health checks, public APIs) and why.
- **STRIDE applied to the app instead of per boundary.** One generic threat list hides the specific boundary that lacks a control.
  Check: the threat-model table records threats per boundary, keeping only those that survive contact with the controls actually found in the code.
- **Second-order input treated as trusted.** Data that entered the system earlier (database rows, queue payloads, uploaded files) re-enters processing without validation; stored injection lives here.
  Check: trace where persisted or replayed data re-enters handlers and whether those handlers treat it as untrusted input.
- **Machine-to-machine calls verified on one side only.** A caller attaching credentials proves nothing if the callee never checks them; network position is not an authorization model.
  Check: for each service-to-service edge, read the callee's verification of the caller, not just the caller's client config; inbound webhooks count, and a handler consuming payloads without verifying their signature or source is an unauthenticated entry point.
- **Files and imports off the map.** Upload, import, and parsing paths are entry points with rich sinks (archives, images, spreadsheets, user-supplied URLs).
  Check: enumerate every place files, archives, or fetched documents enter the system and add them to the surface map; each one fires injection-and-input-handling.
- **Environment-gated surfaces that fail open.** Debug endpoints, seed routes, and preview features gated on an environment flag ship to production when the flag defaults wrong.
  Check: find environment- and flag-gated routes and confirm from the production configuration that the gate fails closed there.
- **Model-facing inputs missing from the map.** If the system feeds user or external content to an LLM or agent, every such path is an entry point.
  Check: locate calls to model APIs or agent loops; when any exist, add their inputs to the surface map and open llm-and-agent-surface.

## Escalation triggers (report immediately)

- An unauthenticated administrative or debug entry point reachable from the internet: an actively exploitable P0; lead the report with it.
- Evidence of active compromise found while mapping (handlers or identities nobody can attribute, backdoor-shaped code): incident response, beyond assessment scope; say so and stop.

## What good looks like

- The surface map is derived from code and covers every process that accepts input, not just the web tier.
- Every trust boundary names its enforcing control with a file reference someone could open.
- The identity model fits in a short table a reviewer could dispute line by line.
