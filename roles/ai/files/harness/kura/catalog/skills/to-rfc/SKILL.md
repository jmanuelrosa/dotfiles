---
name: to-rfc
description: Writes or revises a team RFC from the bundled template through context intake (Jira epic, PRD, Notion docs, Slack threads, PRs, code), cited research, a grill-with-docs interview that sorts every open point into an author verdict or a reviewer question, and a local markdown draft, plus sourced reply drafts when reviewers comment. Use explicitly to "write an RFC", "draft the RFC for this epic", "turn this design into an RFC", "revise this RFC after review", or "answer the comments on this RFC". Not for task plans, PRDs, or ADRs on their own.
argument-hint: "[subject, epic key, PRD or Notion URL, or existing RFC path]"
model: opus
disable-model-invocation: true
---

# RFC writing

Own the RFC from context intake to a draft a reviewer can decide from.
Load `research`, `grilling`, `domain-modeling` and `unslop` internally; never ask the user to invoke them separately.
Keep three things apart throughout: facts with citations, decisions the author makes, and questions that belong to reviewers.

## Invocation and boundaries

- Invoke explicitly: `/to-rfc <subject, epic key, PRD URL, or RFC path>` in Claude Code, `/skill:to-rfc` in Pi.
- If no subject is supplied, ask what the RFC is about.
- Resolve dependency skills from the available skill locations and read their `SKILL.md` and required references for the active phase.
  Pi loads skills by reading their files; do not require a `Skill` tool or send bare slash commands to the model as a substitute.
- Keep user interaction in the main conversation.
  Delegate source gathering, code exploration and claim verification only when the current request or applicable user/project instructions authorize it.
- Modify only the RFC draft, its local replies file, `GLOSSARY.md`, and new ADRs under the project's ADR convention.
  Do not modify implementation code, configs, dependencies, or accepted ADRs.
- Never publish anywhere (Notion, Jira, Slack).
  The output is a local markdown file the user pastes into the Notion RFC database themselves.

## 1. Intake

Restate the subject in one sentence and name the team the RFC is for.

Ask for the full context once, in a single user-question call, before any research:

| Input | Why it matters |
|---|---|
| Epic or ticket keys | Title suffix, scope list, links in section 1 |
| PRD, design, or related RFC links (Notion, Figma, docs) | Motivation, product constraints, non-goals |
| Slack threads where the subject was discussed | Decisions already taken, objections, who owns what |
| Repos in scope, and open PRs touching them | Current state, integration seams, section 7 dependencies |
| Decisions already made and by whom | Verdicts to record, not to re-open |
| Reviewers, and the date the RFC must be open for comments | Which questions can stay open, and which must be settled now |

Accept "none" for any row; do not invent inputs.
If the subject is an existing RFC path, read it first and switch to revision: keep its title, add `Answered (date):` lines to resolved questions, move settled outcomes into section 3, and append rows to the decision log.
If reviewers have commented on it, run the review response in step 5 before changing the draft.

Find prior work: an existing `docs/rfcs/` draft on the same subject, a `docs/plans/` plan, or a research memo under `.claude/state/research/INDEX.md`.
Reuse their evidence instead of restarting; investigate only the gaps.

## 2. Research the groundwork

Load `research` in **planning-groundwork** mode with the subject, the intake inputs and every prior memo.
Use its source recipes for Jira, Notion, GitHub or GitLab, Slack and docs; when Slack access is unavailable, ask for a paste before spawning the research wave.

Brief the research so its findings pack covers every section the template needs:

| Template section | Facts to gather |
|---|---|
| 2 Motivation | Current behaviour with `path:line`, the limitations users or tickets report, why now |
| 3 Proposed Implementation | Integration seams, existing patterns, contracts other code relies on, options the sources already compared |
| 4 Metrics & Dashboards | Metrics, dashboards and alerts the project already has for this area, storage growth drivers |
| 7 Impact and Dependencies | Other repos, teams, epics and open PRs that touch the same surface, and their order |
| 9 Security | New inputs, permissions, tenant boundaries, personal data in scope |
| 8 Unresolved questions | Decisions evidence alone cannot settle, with the sources that disagree |

Tag every fact in the findings pack with its origin: ticket requirement (key and scenario quote), code fact (`path:line`), meeting statement (timestamp and quote), or our inference.
Reviewers ask "where is this coming from?", and the tag is the answer.
What the code supports is not how production runs: confirm operational claims (which providers, how many customers, how often) with data or the owning team, or mark them unresolved.
Check which metrics, alerts and behaviours already exist before anything is drafted as new.

Do not recommend a solution during this phase.
Present the facts and contradictions briefly, then open the draft RFC with sections 1, 2 and 7 filled from evidence and section 8 holding every open decision.
Exit when the load-bearing facts are verified or explicitly marked unresolved.

## 3. Grill the design, with docs

Load `grilling` and `domain-modeling` together, as `grill-with-docs` does, with the findings pack, the draft and the intake constraints.
Use grilling's design tree: settle prerequisite decisions before dependent ones, recompute the frontier after every answer, and keep going until no branch is silently assumed.
Use domain-modeling throughout: challenge terms against `GLOSSARY.md`, sharpen fuzzy language, stress-test relationships with concrete scenarios, and write resolved terms into the glossary as they land.

Ask through the current harness's user-question tool, grouping only independent frontier questions in one call, each with the evidence, the concrete options and your recommended answer first.
Look up facts yourself; put only decisions to the user.

The RFC changes what "settled" means.
Sort every frontier question into one of three outcomes and record it in the draft as soon as it lands:

| Outcome | Who settles it | Where it goes |
|---|---|---|
| The author can decide, and one option clearly wins | The user, now | A `3.x` subsection opening with a bold verdict; the weighed options go to section 6 |
| Behaviour that exists today and does not change | Nobody | Nowhere: it has nothing to decide |
| Behaviour, copy, limits, pricing, what the customer sees | The product side or design, in review | `8.1 Product decisions`, with owner, context, options and our recommendation |
| Architecture, data, infrastructure, rollout, and the options are really open | Engineering reviewers | `8.2 Technical questions`, same shape |

A question the user defers without an owner is not settled; keep it on the frontier.
A value the tickets leave open (a threshold, a count, a time window) is a product decision even when we have a good recommendation; cite the ticket scenario that leaves it open.
Challenge each verdict with failure cases, rollback, compatibility and the drawbacks it creates, and collect those for sections 5 and 6.
Include what existing customers see on the day of the rollout: missing history, empty states, statuses computed from data that does not exist yet.
If an answer changes a load-bearing premise, return to targeted research before asking downstream questions.

Offer an ADR only when domain-modeling's three conditions hold and the verdict is the author's to make.
Write it in the project's ADR format, link the RFC, and note that reviewers can still overturn it until the RFC is accepted.

Exit when the frontier is empty or every remaining item sits in section 8 with an owner and a recommendation, and the user confirms shared understanding.

## 4. Write the RFC

Load `assets/rfc-template.md` and fill every section; delete the italic guidance lines and the header comment.
Write to `docs/rfcs/YYYY-MM-DD-<subject-slug>.md` unless the project names another path; keep an existing RFC's filename when revising.

Apply the template's writing rules as a checklist before showing the draft:

- Title is `[Team] Subject (EPIC-KEY)`, prefixed `[WIP]` while a draft.
- Section 1 states the count of product decisions and technical questions in section 8.
- Every `3.x` subsection opens with `**Verdict:**` and holds only the chosen solution; weighed options sit in section 6 under that subsection's name, each saying how it would work and why we don't do it.
- Every section and bullet changes something or needs agreement; restated current behaviour and existing alerts are gone.
- Section 8 holds only what is really open; anything with a clear winner moved to section 3.
- No mention of "the meeting" or of who said what in the body; provenance sits in the decision log.
- Every number, threshold, rule and status in section 3 is traceable to its tagged source; the ones tagged as our inference read as proposals.
- No risk built only from reading code; each drawback is a cost of the chosen design, not a constraint to keep in mind.
- Every status or term the RFC introduces is defined where it first appears.
- Body is 2,000 to 4,000 words; long research, measurements and superseded designs are linked or summarised, not pasted.
- No task breakdowns, deployment checklists, full schemas, raw measurements, or `file:line` references; a short snippet only where it is a contract reviewers must agree on.
- No people's names; roles instead.
- One sentence per line, first-person plural, plain words; each bullet states its consequence and reads on its own.
- Every ticket key links to Jira and every PR to GitHub.
- A small diagram opens section 3 when the flow spans systems: a top-down flowchart with subgraphs, or a sequence diagram for steps over time.

These drafts drew reviewer comments; write the right-hand column instead:

| Drew a comment | Write instead |
|---|---|
| "The meeting chose this check 'for now'." | "We revisit this check if it does not work in practice." and a decision log row |
| "The dot warns after 3 days", when the ticket leaves N open | A section 8.1 question citing the ticket scenario, with 1 or 3 days as our recommendation |
| "Assigning the project on open was rejected", when nobody discussed it | "We propose a read-only preview instead, because ..." |
| A visitor-reset risk derived from reading the parser, with no data | Leave it out, or state the measurement that would size it |
| "Includes projects that do not run on Spacelift", because the code supports other providers | Confirm with the infrastructure owner first |
| A section on certificate validation we keep as it is | Delete the section |
| A table of rejected signals inside 3.2 | The chosen signal in 3.2; the others in section 6 under "Path liveness" |

Run `unslop` over the draft.
Then present the path, the word count, and the list of section 8 items with their owners.

## 5. Review and hand over

Walk the user through section 3 verdicts and section 8 questions if they want it; do not require a turn per section.
Apply refinements to the same file.

### Review response

When reviewers have commented, answer every thread before revising:

1. Collect all comments, including page-level ones and threads whose anchor text was deleted by an earlier revision; the Notion API lists only unresolved comments, one block at a time, nested blocks included.
2. Sort each thread: agree and change, reword because it was unclear, source request, pushback that needs the user's decision, or a design-team item that only needs an acknowledgement and no task.
3. Answer source requests from the tagged sources: quote the ticket scenario, give the `path:line`, or the transcript timestamp. When the claim was our inference, say so and own it.
4. Put pushback to the user, with the evidence and a recommendation, before editing.
5. Draft every reply in the author's voice: first person, short, humble, saying what changed and in which section. Write them to a local replies file next to the draft, numbered like the threads.
6. Revise the draft, then re-run the step 4 checklist.

Whoever publishes must post the replies before updating the page: rewriting a block detaches its comments, and the API can neither resolve nor delete another person's comment.
Finish here: pasting into Notion, opening the RFC for comments, and the follow-up implementation plan (`to-plan` reuses this RFC's memo) are separate, explicit requests.
