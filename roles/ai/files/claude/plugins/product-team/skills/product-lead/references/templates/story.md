---
initiative: "{slug}"
stage: 5-backlog
status: draft
authors: ["5-decompose", "product-team:ac-writer"]
date: "{YYYY-MM-DD}"
sources: ["02-prd.md", "04-ux-spec.md", "05-tasks.md"]
---

# Story {n.m}: {title}

<!-- A vertical slice: cuts through every layer end-to-end and is demoable on its own. If it only touches one layer, it is a task inside some other story, not a story.

A story is the unit a human puts on a board, so it is deliberately thin. It claims scenarios rather than restating them, because the scenario already exists in 02-prd.md and the version that gets edited is whichever copy the reader happened to open. Stage 7 expands the claimed scenarios into the board issue, so the issue is readable where it is used without a second copy living here. -->

| Field | Value |
|---|---|
| Epic | epic-{n}.md |
| Scenarios | R{#}.S{#}, R{#}.S{#} |
| Task groups | {n}, {n} |
| Size hint | S \| M \| L |
| Split rationale | {required only when the size reads L: why this was not split} |
| Depends on | story-{n.m}.md or none |
| Needs design seat | yes \| no |
| Board issue | PENDING (filled by /product-team:7-push-to-board) |

<!-- Scenarios: the ids from 02-prd.md this slice satisfies. Every scenario in the PRD is claimed by some story or some task, and pt.py check names any that is not, so this row is what makes requirement coverage countable rather than believed.

Split rationale: three initiatives in a row failed the DoR gate on an L-sized story whose rationale existed in the epic and not in the story. The row exists so the omission is visible while writing rather than at the gate.

Needs design seat: yes when this story's flow in 04-ux-spec.md draws on that spec's "New system pieces needed" section, no otherwise. Copied from the spec, never judged here: which seat owns which slice is the architect's call. -->

## User story

As a {user}, I want {capability}, so that {benefit}.

## Acceptance criteria

<!-- Filled by product-team:ac-writer, and normally empty.

The claimed scenarios above ARE the acceptance criteria. A block belongs here only when the slice needs a criterion no PRD scenario covers, which is a gap in the PRD rather than a licence to invent one: ac-writer reports it and 2-write-prd adds the scenario. What survives here is the story-local detail a requirement cannot carry, such as which of two surfaces this slice builds first. -->

## Design / UX note

<!-- A resolvable pointer into 04-ux-spec.md: the flow anchor this story implements, e.g. 04-ux-spec.md#export-a-report for the flow headed "Export a report". For an initiative with no UI, point at that spec's "No user-facing surface" argument instead. Never a freehand "N/A because ...": the absence is argued once in the UX spec and reviewed at Gate 1, rather than restated per story and reviewed by nobody. A mockup link may be added alongside the pointer, never instead of it. -->
