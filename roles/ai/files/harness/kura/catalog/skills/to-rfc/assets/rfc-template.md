# [Team] Subject

<!--
How to use this template
- It follows the sections of the company template in the Notion "List of RFCs" database ("[Team] Subject"), so reviewers find the usual outline. Create the RFC from that database, then paste this content.
- Title: "[Team] Subject (EPIC-KEY)", for example "[Addingwell] Domains management (SER-1411)". Prefix with [WIP] while it is a draft.
- Notion properties: Authors, Date, a one-sentence Description, Status (DRAFT while writing, Open for Comments when shared).
- Delete every italic guidance line and this comment before sharing.

Writing rules
- The RFC gives a rough idea of what we build and what still needs a solution. Everything else is a to-do or context, and goes elsewhere.
- Aim for 2,000 to 4,000 words. If a section grows past a page, it is probably context: link it instead.
- State a decision when one option clearly wins, and let reviewers push back. Ask a question only when the options are really open.
- Keep product decisions and technical questions apart: they have different owners and are answered in different meetings.
- Keep the problem or the options of each question (or both), never pages of background.
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
- **Needs from reviewers:** *the number of product decisions and technical questions in section 8.*
- **Links:** *epic, PRD, design, related RFCs.*

## 2 Motivation
*Half a page at most.*

*Current state in two or three lines, then its limitations as a numbered list, then why now.*

1. *Limitation one.*
2. *Limitation two.*

## 3 Proposed Implementation
*Most of the document. Start with one overview diagram (Mermaid or an image) if the flow spans systems.*

*One subsection per decision or component. Each opens with a bold one-line verdict, then the reasoning in a few lines.*

### 3.1 *Decision or component*
**Verdict:** *we do X.*

*Why, in three to six lines. When options were weighed, show them as a table and mark the winner.*

| Option | Pros | Cons |
|---|---|---|
| *A (chosen)* | | |
| *B* | | |

*Put long research, measurements or superseded designs in a Notion toggle under the subsection, so the body stays short.*

### 3.2 *Decision or component*
**Verdict:** *...*

### 3.x Rollout
*Only what reviewers must agree on: feature flag, order between repos, migration of existing data. Not the deployment checklist.*

## 4 Metrics & Dashboards
*What we measure to know it works, and which alerts fire when it does not. Include storage growth for new tables or columns.*

## 5 Drawbacks
*Three to six bullets: honest costs and risks we accept, one line each, with the mitigation when there is one.*

## 6 Alternatives
*Rejected approaches for the whole design, one line each with the reason. Write "Covered in section 3" when the options already sit there.*

- **Rejected:** *approach, because ...*

## 7 Potential Impact and Dependencies
*Other teams, repos, epics and open PRs this touches, and the order between them.*

| Area | Impact | Dependency or risk |
|---|---|---|
| *repo / team / epic* | | |

## 8 Unresolved questions
*Only what is really open. Everything with a clear winner is a verdict in section 3.*

*Each item: a bold question, the owner, two or three lines of context, the options one line each, and our recommendation. Ten lines at most.*

*When an item is answered, keep it here with "Answered (date):" and the answer, or move the outcome into section 3.*

### 8.1 Product decisions
*Owner: the product side or design. Behaviour, copy, limits, pricing, what the customer sees.*

**P1. *Question?***
*Owner: ...*
*Context.*
1. *Option.*
2. *Option.*

**Our recommendation:** *option and one-line reason.*

### 8.2 Technical questions
*Owner: engineering. Architecture, data, infrastructure, rollout.*

**T1. *Question?***
*Owner: ...*
*Context.*
1. *Option.*
2. *Option.*

**Our recommendation:** *option and one-line reason.*

## 9 Security considerations
*Two to five bullets: new inputs, permissions, tenant isolation, personal data, abuse.*

## 10 Conclusion
*Two to four sentences: why this is the right design now, and the main risk we accept.*

## Decision log
*Optional. One row per decision agreed in a meeting or a comment thread, so the outcome survives once comments are resolved.*

| Date | Decision | Where | Section |
|---|---|---|---|
| | | *refinement meeting, Slack thread, Notion comment* | |
