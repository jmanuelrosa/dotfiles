---
name: gtm-failure-modes
description: >-
  Failure-mode checklists for Google Tag Manager and server-side tagging work, split by domain.
  Use when implementing or reviewing changes that touch the dataLayer contract, tags/triggers/variables,
  consent and privacy, server-side tagging, custom templates, server-to-server Conversion APIs,
  GA4 integration, or measurement integrity and container releases.
  Read only the reference files whose triggers match the change.
---

# GTM failure modes

Checklists of the ways tagging and measurement changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| dataLayer keys, event and parameter names, push timing and ordering, value types, schema evolution | [references/datalayer-contract.md](references/datalayer-contract.md) |
| Triggers and exceptions, tag firing and sequencing, variables and their defaults, container naming and structure | [references/tags-triggers-variables.md](references/tags-triggers-variables.md) |
| Consent Mode signals, consent gating, regional rules, redaction, url passthrough, any tag that reads or writes personal data | [references/consent-and-privacy.md](references/consent-and-privacy.md) |
| Server container clients and tags, request claiming, transport, logging, statefulness, first-party server-set cookies | [references/server-side-tagging.md](references/server-side-tagging.md) |
| Custom tag, client, or variable templates: permissions, sandboxed APIs, injected script, template tests | [references/custom-templates.md](references/custom-templates.md) |
| Server-to-server destinations (Meta CAPI, Google Ads, GA4 Measurement Protocol): event dedup, PII hashing, API versions, auth | [references/conversion-apis.md](references/conversion-apis.md) |
| GA4 tags, events, and parameters, client and session identity, cross-domain, Measurement Protocol, GA4 consent wiring | [references/ga4-integration.md](references/ga4-integration.md) |
| Publishing a container version, cross-path double-counting, attribution and identity continuity, QA before publish, tag monitoring | [references/measurement-integrity-and-release.md](references/measurement-integrity-and-release.md) |
| Error handling, failed or dropped sends, server-side error tracking, tag health monitoring | [references/errors-and-observability.md](references/errors-and-observability.md) |

Most real changes fire two or three rows (a typical conversion-tag brief fires at least datalayer-contract, consent-and-privacy, and conversion-apis).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: vendor- and tool-specific guidance (a given CMP, a specific destination's field list) belongs to the stack skills the caller has installed, not here.
