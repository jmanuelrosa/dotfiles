---
initiative: "{slug}"
stage: 2-prd
status: draft
authors: ["{human}", "2-write-prd"]
date: "{YYYY-MM-DD}"
sources: ["00-brief.md", "01-research/summary.md"]
---

# PRD: {initiative name}

## Context & problem

<!-- Two short paragraphs max. Link 00-brief.md and the research summary; do not restate them. -->

## Goals & success metrics

<!-- Every metric needs all four columns. A baseline you do not have is written exactly as `UNKNOWN -> Open Question #n`; inventing one is the cardinal sin of this pipeline. -->

| Metric | Definition | Baseline | Target |
|---|---|---|---|
|  |  |  |  |

## Non-goals

<!-- Mandatory, minimum 3. What this initiative deliberately does not do, so scope arguments happen here and not in code review. -->

1.
2.
3.

## Target users

<!-- Only segments evidenced in 01-research/. A segment without research backing needs explicit human sign-off, recorded here. -->

## Requirements

<!-- Numbered R1..Rn. Each one testable: a QA engineer could write a pass/fail check from the sentence alone. No implementation detail; that belongs to the design doc. -->

- **R1**:
- **R2**:

## User flows

<!-- Step-by-step happy path plus the failure paths that matter. Reference requirements by R#. -->

## Open questions

<!-- Numbered, each with an owner. Unknown baselines from the metrics table land here. -->

| # | Question | Owner | Status |
|---|---|---|---|
| 1 |  |  | open |

## Dependencies & risks

<!-- Teams, systems, decisions this depends on; risks with likelihood/impact one-liners. -->

## Red-team status

<!-- Filled after /3-red-team runs. -->

| Field | Value |
|---|---|
| Report | PENDING (03-red-team-report.md) |
| Blockers raised / resolved |  |
| Revision date |  |
