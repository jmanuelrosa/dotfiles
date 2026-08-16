---
initiative: "{slug}"
stage: 4-tech-shape
status: draft
authors: ["{human}", "4-tech-shape"]
date: "{YYYY-MM-DD}"
sources: ["02-prd.md"]
---

# Design doc: {initiative name}

## Context

<!-- Link 02-prd.md. One paragraph on what the PRD asks for and the codebase reality it lands in, citing real paths you read. -->

## Technical goals & non-goals

<!-- Goals the design must hit (performance, compatibility, operability) and technical non-goals that bound the work. -->

## Proposed approach

<!-- The design. Modules, boundaries, flows. Ground every claim in code actually read; cite path:line. -->

## Alternatives considered

<!-- Minimum one rejected alternative per major decision, with why-rejected. A design doc with no rejected alternatives is a decision log, not a design. -->

### {Decision}: chose {A} over {B}

- **Rejected**: {B}
- **Why**:

## Data & API sketch

<!-- Schema changes, endpoints, events - in this repo's contract idiom. Sketch level, not implementation. -->

## Deferrals settled here

<!-- Every deferral 02-prd.md and 04-ux-spec.md pointed at this document, each with the decision that closes it. Name the id, because pt.py check follows it: an id that appears in no artifact downstream of the one that raised it is a question everyone assumed someone else had answered.

Closing it means deciding it, or restating it as an owned open question below. "Still open" with nobody's name on it is what a deferral is supposed to prevent. -->

| id | Raised by | Decision |
|---|---|---|

## Enforcement and access

<!-- Two decisions this stage reliably leaves implicit, and both were missed on a real initiative:

- **Where validity is enforced, relative to deploy.** If anything here validates anything, name the command that runs it and say whether a failure blocks publishing or merely reports. Validation that only ever runs on a developer's machine does not stop a bad artifact reaching production, and "there is a check" read as if it did.
- **Who can read the deployed thing.** State the access posture and name the alternative rejected. "No credential is required" is a decision with consequences, not the absence of one. -->

## Security & privacy considerations

<!-- Data touched, access model, PII handling, threat notes. "None" must be argued, not assumed. -->

## Rollout & rollback

<!-- Flags, migration order, how to observe it working, and the concrete rollback path. -->

## Risks & estimation ranges

<!-- Ranges, not points: "3-6 weeks" with what drives the spread. Label confidence. -->

## ADR index

<!-- Filled by product-team:adr-scribe: one row per extracted decision. The ADR files themselves live in docs/adr/. -->

| ADR | Title | Status |
|---|---|---|
|  |  |  |
