---
name: security-failure-modes
description: >-
  Vulnerability-class checklists for read-only security assessment work, split by assessed surface.
  Use when assessing attack surface and trust boundaries, authentication and sessions,
  authorization and tenancy, injection and input handling, secrets and configuration,
  supply chain and build, data protection and leakage, detection and evidence,
  or LLM and agent integrations.
  Read only the reference files whose triggers match the assessed surface.
---

# Security failure modes

Checklists of the vulnerability classes a security assessment must rule out having missed, one reference file per assessed surface.
This skill is a router: match the assessed surface against the trigger table, read only the files that fire, and treat every checklist item as a check to perform against the actual code.
An item you could not verify goes in the Not assessed section; silence is never read as safety.
These checks audit an existing surface whole (every entry point, all config, git history, build output); preventing the same defects in a pending diff belongs to the implementer seats' failure-mode skills and to /security-review, never here.

## Trigger table

| The assessed surface includes... | Read |
|---|---|
| Anything that accepts input or crosses a trust boundary; entry-point, boundary, and identity mapping (every assessment starts here) | [references/attack-surface-and-boundaries.md](references/attack-surface-and-boundaries.md) |
| Login, credentials, tokens, sessions, MFA, SSO, password recovery | [references/authn-and-sessions.md](references/authn-and-sessions.md) |
| Roles, permissions, object ownership, tenancy, admin surfaces | [references/authz-and-tenancy.md](references/authz-and-tenancy.md) |
| Handlers that build queries, commands, paths, templates, or outbound requests from external input; parsers and deserializers | [references/injection-and-input-handling.md](references/injection-and-input-handling.md) |
| Environment and config handling, CORS, debug flags, error paths; any whole-repo assessment | [references/secrets-and-config.md](references/secrets-and-config.md) |
| Dependency manifests and lockfiles, install scripts, CI workflows, base images, release pipelines; any whole-repo assessment | [references/supply-chain-and-build.md](references/supply-chain-and-build.md) |
| Personal or sensitive data flows; logging, analytics, exports, client bundles | [references/data-protection-and-leakage.md](references/data-protection-and-leakage.md) |
| Logging of security events, audit trails, alerting; every assessment's closing lens | [references/detection-and-evidence.md](references/detection-and-evidence.md) |
| LLM API calls, agents and tool-use loops, MCP servers or clients, rendering of model output | [references/llm-and-agent-surface.md](references/llm-and-agent-surface.md) |

Most real assessments fire several rows (a typical whole-repo assessment fires at least attack-surface-and-boundaries, secrets-and-config, supply-chain-and-build, and detection-and-evidence).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: vulnerability classes the assessment could have missed, each with a `Check:` you can perform read-only against the assessed code and config.
- **Escalation triggers (report immediately)**: conditions that lead the assessment or interrupt it rather than queueing in the ranked findings list.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: framework- and scanner-specific guidance belongs to the stack skills the caller has installed, not here.
Every check is performed by reading code and config: nothing here ever requires installing a tool, sending traffic to a live target, or attempting exploitation.
