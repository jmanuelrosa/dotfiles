# RFC Writing Specification

## Intent and shape

Provide one explicit entry point that takes an RFC from context intake to a reviewer-ready local draft in the team's template.
Use a workflow-process skill with fixed prompt chaining and a bundled template asset; dependency skills own research, interviewing, domain vocabulary and prose cleanup, while `to-rfc` owns intake, the verdict-versus-reviewer-question sort, the template fill and its writing rules.
A standalone inline guide would duplicate `research` and `grilling`; an agent could not run the interview, since a subagent has no user to ask.

## Scope and invocation

Accept a subject, epic key, PRD or Notion URL, or an existing RFC path.
Use `/to-rfc` in Claude Code and `/skill:to-rfc` in Pi.
Keep automatic invocation disabled.

In scope: context intake, read-only investigation, the design interview, glossary updates, proposed ADRs for author-owned verdicts, the RFC draft and its revision after review.
Out of scope: task breakdowns, implementation, publishing to Notion, Jira or Slack, PRDs, and editing accepted ADRs.

## Runtime contract

- Dependencies: `research` in planning-groundwork mode, `grilling`, `domain-modeling` and `unslop`, declared in the skill registry.
- Sequence: intake, research, grill with docs, write from the template, review and hand over.
- Template: `assets/rfc-template.md`, the team's RFC template copied into the skill; the project's own `docs/templates/rfc.md` wins when it exists.
- Output: `docs/rfcs/YYYY-MM-DD-<subject-slug>.md`, unless explicit user/project instructions require another path; revisions keep the original filename.
- Sorting rule: every open point ends as a `3.x` verdict, an `8.1` product decision, or an `8.2` technical question with an owner and a recommendation; nothing is deferred without an owner.
- Evidence: the research memo keeps `path:line` and URLs; the RFC body carries links and short contracts only, never file references, per the template's writing rules.
- Safety: only the RFC draft, `GLOSSARY.md` and new ADRs may change; delegation needs request or user/project authorization; nothing is published.
- Portability: load dependency files from discovered skill locations; use the current harness's user-question and subagent controls.
- Interview adaptation: ask only independent frontier questions per user-tool call, each with a recommended answer first, while preserving grilling's frontier-completeness check through section 8.

## Validation

Run the skill-writer structural validator and `make test`.
The catalog suite checks that declared dependencies and their transitive sources are registered.
Dogfood on a real epic with a PRD, a Slack thread and code in scope, then revise the same RFC after a review comment to check the `Answered (date):` and decision-log paths.
Static checks do not establish the quality of a live interview or of the sorting into section 8.

Should apply: "write the RFC for SER-1411", "turn this plan into an RFC", "revise this RFC after review".
Should not start automatically: "plan this feature" (`to-plan`), "write a PRD" (`spec-driven-development`), "record this decision" (`documentation-and-adrs`).

## Known limitations

- The template is team-specific; another team's outline needs a different asset or a project override.
- Word count is checked by hand; no script enforces the 2,000 to 4,000 range.
- Slack reading depends on a read-only Slack MCP being available; otherwise the user pastes the thread.

## Maintenance

Keep the runtime workflow and the writing checklist in `SKILL.md`; keep provenance and decisions in `SOURCES.md`.
When the team template changes, replace `assets/rfc-template.md` and re-check the section table in `SKILL.md` step 2 and the checklist in step 4 against it.
Update the registry dependencies together with the composition.
