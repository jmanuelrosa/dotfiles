---
initiative: "{slug}"
stage: 5-backlog
status: draft
authors: ["5-decompose", "ac-writer"]
date: "{YYYY-MM-DD}"
sources: ["02-prd.md", "04-design-doc.md"]
---

# Story {n.m}: {title}

<!-- A vertical slice: cuts through every layer end-to-end and is demoable on its own. If it only touches one layer, it is a task inside some other story, not a story. -->

| Field | Value |
|---|---|
| Epic | epic-{n}.md |
| PRD requirements | R{#}, R{#} |
| Size hint | S \| M \| L |
| Depends on | story-{n.m}.md or none |
| Board issue | PENDING (filled by /7-push-to-board) |

## User story

As a {user}, I want {capability}, so that {benefit}.

## Acceptance criteria

<!-- Filled by ac-writer. Every AC has an id and traces to a PRD requirement. -->

### AC-{n.m}.1 (R{#})

- **Given**
- **When**
- **Then**

## Design / UX note

<!-- Attach the relevant design-doc section or mockup link, or write "N/A because ..." - a bare N/A fails the DoR check. -->

## Notes

<!-- Implementation hints from the design doc worth surfacing; keep short, no code. -->
