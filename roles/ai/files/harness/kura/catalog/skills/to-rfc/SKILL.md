---
name: to-rfc
description: Writes or revises a team RFC from the bundled template through context intake (Jira epic, PRD, Notion docs, Slack threads, PRs, code), cited research, a grill-with-docs interview that sorts every open point into an author verdict or a reviewer question, and a local markdown draft. Use explicitly to "write an RFC", "draft the RFC for this epic", "turn this design into an RFC", or "revise this RFC after review". Not for task plans, PRDs, or ADRs on their own.
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
- Modify only the RFC draft, `GLOSSARY.md`, and new ADRs under the project's ADR convention.
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
| The author can decide, and one option clearly wins | The user, now | A `3.x` subsection opening with a bold verdict, options table when weighed |
| Behaviour, copy, limits, pricing, what the customer sees | The product side or design, in review | `8.1 Product decisions`, with owner, context, options and our recommendation |
| Architecture, data, infrastructure, rollout, and the options are really open | Engineering reviewers | `8.2 Technical questions`, same shape |

A question the user defers without an owner is not settled; keep it on the frontier.
Challenge each verdict with failure cases, rollback, compatibility and the drawbacks it creates, and collect those for sections 5 and 6.
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
- Every `3.x` subsection opens with `**Verdict:**`; weighed options sit in a table with the winner marked.
- Section 8 holds only what is really open; anything with a clear winner moved to section 3.
- Body is 2,000 to 4,000 words; long research, measurements and superseded designs are linked or summarised, not pasted.
- No task breakdowns, deployment checklists, full schemas, raw measurements, or `file:line` references; a short snippet only where it is a contract reviewers must agree on.
- No people's names; roles instead.
- One sentence per line, first-person plural, plain words.
- Every ticket key links to Jira and every PR to GitHub.
- A Mermaid overview diagram opens section 3 when the flow spans systems.

Run `unslop` over the draft.
Then present the path, the word count, and the list of section 8 items with their owners.

## 5. Review and hand over

Walk the user through section 3 verdicts and section 8 questions if they want it; do not require a turn per section.
Apply refinements to the same file.
Finish here: pasting into Notion, opening the RFC for comments, and the follow-up implementation plan (`to-plan` reuses this RFC's memo) are separate, explicit requests.
