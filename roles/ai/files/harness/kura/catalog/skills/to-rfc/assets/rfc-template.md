# [Team] Subject

<!--
How to use this template
- It follows the sections of the company template in the Notion "List of RFCs" database ("[Team] Subject"), so reviewers find the usual outline. Create the RFC from that database, then paste this content.
- Title: "[Team] Subject (EPIC-KEY)", for example "[Addingwell] Domains management (SER-1411)". Prefix with [WIP] while it is a draft.
- Notion properties: Authors, Date, a one-sentence Description, Status (DRAFT while writing, Open for Comments when shared).
- Delete every italic guidance line and this comment before sharing.

Writing rules
- The RFC gives a rough idea of what we build and what still needs a solution. Everything else is a to-do or context, and goes elsewhere.
- Architect what is new: components, data, contracts and the flows between systems. Describe what the UI does only where it drives an architectural decision; screens, states and copy belong in the design file, linked.
- Aim for 2,000 to 4,000 words. If a section grows past a page, it is probably context: link it instead.
- Include only what changes or needs agreement. A section that restates behaviour we keep, or an alert that already exists, has nothing to decide: drop it.
- State a decision when one option clearly wins, and let reviewers push back. Ask a question only when the options are really open.
- The RFC validates the technical solution and is never the product's source of truth. A product gap (behaviour, copy, a limit or threshold the tickets leave open) goes back to the ticket's acceptance criteria; the RFC keeps only the technical value any answer needs (a date, a state).
- Keep the problem or the options of each question (or both), never pages of background.
- Write what we propose, not who said it or which meeting decided it. Provenance goes in the decision log only.
- Separate what the tickets require from what we propose. A number, threshold, rule or rejection the tickets do not contain is worded as our proposal ("we propose a one-hour cache"); never write "was rejected" for an option nobody discussed.
- Every claim must survive "where is this coming from?": keep its source (ticket scenario, code reference, transcript timestamp) in your notes, ready to quote in a reply.
- No hypothetical risks from reading code alone. A risk goes in with data, or with the measurement that would size it. What the code supports is not how production runs.
- Define every status or term you introduce where it first appears, by the value the system stores (`PENDING`, `LIVE`); quote the design's name for a state when one exists, and never invent UI names such as colors. Independent states (is it deployed, does it receive events) stay separate values.
- Each bullet must read on its own: give the consequence, not only the mechanism, and cut sentences that add nothing.
- Name out-of-scope work once, in Non-goals, and keep it out of the verdicts.
- Leave out: task breakdowns (Jira), code state and file:line references (link the repo or a plans doc), deployment checklists, full schemas, raw measurements. A short snippet is fine when it is a contract reviewers must agree on.
- No people's names for blame or attribution; use roles ("the product side", "support").
- One sentence per line, plain words, first-person plural ("we propose").
- Link every ticket key to Jira and every PR to GitHub.
-->

## 1 Executive Summary
*Five to ten lines. A reader who stops here knows what we build and what we need from them.*

- **What:** *one or two sentences.*
- **Scope:** *the stories or tickets covered, linked.*
- **Non-goals:** *what this RFC does not cover, and where it lives instead.*
- **Release:** *one line (feature flag, order), unless reviewers must agree on something about it, in which case it gets a 3.x subsection.*
- **Needs from reviewers:** *the number of technical questions in section 8, or sign-off when none is open.*
- **Links:** *epic, PRD, design, related RFCs.*

## 2 Motivation
*Half a page at most.*

*Current state in two or three lines, then its limitations as a numbered list, then why now.*

1. *Limitation one.*
2. *Limitation two.*

## 3 Proposed Implementation
*Most of the document, and only the solution we propose: the options we weighed go to section 6.*

*Open with a small diagram when the flow spans systems. Prefer a top-down flowchart with one subgraph per owner, and a sequence diagram for steps over time, to one long left-to-right chain. In Notion, set each Mermaid block to Preview so the code is hidden.*

*One subsection per decision or component that changes in the system, not per screen. Each opens with a bold one-line verdict, then the reasoning in a few lines.*

### 3.1 *Decision or component*
**Verdict:** *we do X.*

*Why, in three to six lines.*

*Put long research or measurements in a Notion toggle under the subsection, so the body stays short.*

### 3.2 *Decision or component*
**Verdict:** *...*

## 4 Metrics & Dashboards
*What we measure to know it works, and which new alerts fire when it does not. Check what already exists, and list only what is new. Include storage growth for new tables or columns.*

## 5 Drawbacks
*Three to six bullets: costs and risks of the chosen design that we accept, one line each, with the mitigation when there is one. A constraint to keep in mind (an order of work, a dependency) is not a drawback: it goes in section 7.*

## 6 Alternatives
*Grouped under the section 3 subsection they belong to. For each one, say how it would work, then why we don't do it. No "Rejected:" label. Only options weighed for a current verdict: a design an earlier draft had and a later decision replaced is deleted, not moved here.*

**3.1 *Decision or component*.**
- *Alternative.* *How it would work. Why we don't do it.*

## 7 Potential Impact and Dependencies
*Other teams, repos, epics and open PRs this touches, and the order between them.*

| Area | Impact | Dependency or risk |
|---|---|---|
| *repo / team / epic* | | |

## 8 Unresolved questions
*Only technical questions that are really open: architecture, data, infrastructure, rollout. Everything with a clear winner is a verdict in section 3. Write "None open." when nothing is.*

*Each item: a bold question, the owner, two or three lines of context citing its source, the options one line each, and our recommendation. Ten lines at most.*

*When an item is answered, keep it here with "Answered (date):" and the answer, or move the outcome into section 3.*

**T1. *Question?***
*Owner: ...*
*Context.*
1. *Option.*
2. *Option.*

**Our recommendation:** *option and one-line reason.*

## 9 Security considerations
*Two to five plain bullets: new inputs, permissions, tenant isolation, personal data, abuse. Each says what we do, in words a non-engineer can follow. Data built from input anyone can send (request headers) stays inert until a user acts on it.*

## 10 Conclusion
*Two to four sentences: why this is the right design now, and the main risk we accept.*

## Decision log
*Optional. One row per decision agreed in a meeting or a comment thread, so the outcome survives once comments are resolved. Mark our own proposals as such. When a later decision reverses a row, replace that row.*

| Date | Decision | Where | Section |
|---|---|---|---|
| | | *technical refinement, Slack thread, Notion comment, "proposal, after a Notion comment"* | |
