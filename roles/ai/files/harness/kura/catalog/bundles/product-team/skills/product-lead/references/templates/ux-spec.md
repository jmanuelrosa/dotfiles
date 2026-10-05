---
initiative: "{slug}"
stage: 4-tech-shape
status: draft
authors: ["ux-shaper", "{design gate owner}"]
date: "{YYYY-MM-DD}"
sources: ["02-prd.md"]
---

# UX spec: {initiative name}

<!-- Written by ux-shaper before 04-design-doc.md, because states drive the data contract: a paginated empty state changes the API sketch, an optimistic interaction changes the mutation contract. Where .github/CODEOWNERS names a design owner for this path, they are a required approver on the commit that adds it, and they revise this file directly rather than only commenting: it is their document. -->

## Design system inventory

<!-- What this spec is allowed to compose from, read out of the codebase rather than assumed. Token layers and their source file, the components available with their real variants and slots, and the two or three existing screens with the closest state handling. Cite path:line for every entry. A component named here that does not exist is the failure this section exists to prevent. -->

| Piece | Where | Variants / notes |
|---|---|---|
|  |  |  |

## Flows

<!-- One section per user flow, because a stage-5 story is a vertical slice and a slice is a flow. This is what a story's Design/UX note points at. Keep the heading to the flow name alone and put the R# ids on the line beneath it: a heading carrying them changes its own anchor whenever a requirement is renumbered, silently breaking every story that pointed here. -->

### {Flow name}

**Requirements:** R{#}, R{#}

<!-- One paragraph on the path the user takes, then one Surface block per screen or surface it touches. A surface appearing in a second flow is cross-referenced back to its first definition, never respecified: two copies of a state matrix drift. -->

#### Surface: {name}

| State | What the user sees | Components |
|---|---|---|
| Default |  |  |
| Loading |  |  |
| Empty |  |  |
| Partial |  |  |
| Error |  |  |
| Offline |  |  |
| Permission denied |  |  |

<!-- Every row is filled or struck with a reason. "Not applicable" is an answer; a blank row is an unanswered question that reaches implementation as an invented state. -->

- **Focus order**:
- **Responsive**: <!-- what reflows, what collapses, what the smallest supported width does -->
- **Copy owner**: <!-- who writes the strings, or "reuses existing" -->

## New system pieces needed

<!-- Tokens, components or variants that do not exist yet. This section is the brief for the design seat and the input to architect's design slice, and it is the single fact stage 5 reads to set a story's "Needs design seat" row. Empty means every flow above composes from what already ships. -->

| Piece | Kind | Why the existing system cannot express it |
|---|---|---|
|  | token \| component \| variant |  |

## Deferrals

<!-- A question this spec deliberately leaves to the design, which is the common and healthy case: whether a list paginates, whether an interaction is optimistic, whether a state is reachable at all are often data-contract questions wearing UX clothes. Naming one here is what lets this spec stop hedging about it.

Forwards only, so the resolver is 04-design-doc.md or 05-tasks.md. 04-design-doc.md must mention the id and settle it; pt.py check fails the initiative if it does not. Delete this section when there are none. -->

| id | Question | Resolved by |
|---|---|---|
| D{n} |  | 04-design-doc.md |

## Open questions

<!-- Numbered, each with an owner. An unknown never becomes an assumption; see conventions.md hard rules. A deferral is closed by the next artifact, an open question by a person: that is the whole difference. -->

## Mockups

<!-- Optional. Links the design gate owner attaches, input to their revision of this file. Never the gated artifact, never a precondition for writing this spec, and nothing in the pipeline generates one. -->

## No user-facing surface

<!-- Used INSTEAD of ## Flows when the initiative ships no UI. Argue it per R#: name each requirement and say what makes it invisible to users (a background job, an internal API with no console, a data migration). A bare "N/A" is what this section exists to replace, and stage 5 points every story's Design/UX note here. -->
