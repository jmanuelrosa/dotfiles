---
initiative: "{slug}"
stage: 5-backlog
status: draft
authors: ["5-decompose", "product-team:ac-writer"]
date: "{YYYY-MM-DD}"
sources: ["02-prd.md", "04-ux-spec.md", "04-design-doc.md"]
---

# Story {n.m}: {title}

<!-- A vertical slice: cuts through every layer end-to-end and is demoable on its own. If it only touches one layer, it is a task inside some other story, not a story. -->

| Field | Value |
|---|---|
| Epic | epic-{n}.md |
| PRD requirements | R{#}, R{#} |
| Size hint | S \| M \| L |
| Depends on | story-{n.m}.md or none |
| Needs design seat | yes \| no |
| Board issue | PENDING (filled by /product-team:7-push-to-board) |

<!-- Needs design seat: yes when this story's flow in 04-ux-spec.md draws on that spec's "New system pieces needed" section, no otherwise. Copied from the spec, never judged here: which seat owns which slice is the architect's call, and a second opinion on it here would be a second thing to keep in sync. Stage 7 labels the board issue when it reads yes, so design load is visible before implementation starts. -->


## User story

As a {user}, I want {capability}, so that {benefit}.

## Acceptance criteria

<!-- Filled by product-team:ac-writer. Every AC has an id and traces to a PRD requirement. -->

### AC-{n.m}.1 (R{#})

- **Given**
- **When**
- **Then**

## Design / UX note

<!-- A resolvable pointer into 04-ux-spec.md: the flow anchor this story implements, e.g. 04-ux-spec.md#export-a-report for the flow headed "Export a report". For an initiative with no UI, point at that spec's "No user-facing surface" argument instead. Never a freehand "N/A because ...": the absence is argued once in the UX spec and reviewed at Gate 2, rather than restated per story and reviewed by nobody. A mockup link may be added alongside the pointer, never instead of it. -->

## Notes

<!-- Implementation hints from the design doc worth surfacing; keep short, no code. -->
