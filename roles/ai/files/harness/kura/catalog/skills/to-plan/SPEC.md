# Task Planning Specification

## Intent and shape

Provide one explicit planning entry point that composes code and external research with a decision-tree interview, then produces an implementation-ready plan.
Use a workflow-process skill with fixed prompt chaining; dependency skills own research and interviewing, while `to-plan` owns scope, durable decisions, task breakdown, and approval.
A standalone inline design guide would duplicate those dependencies and leave their handoff implicit.

## Scope and invocation

Accept a task, ticket, source link, existing research memo, or plan revision.
Use `/skill:to-plan` in Pi and `/to-plan` in Claude Code.
Keep automatic invocation disabled.

In scope: read-only investigation, factual external comparisons, decision questions, task ordering, acceptance criteria, verification planning, and plan revision.
Out of scope: implementation, automatic publication, config changes, dependency installation, and automatic ADR creation.

## Runtime contract

- Dependencies: `research` in planning-groundwork mode and `grilling`, declared in the skill registry.
- Sequence: scope and prior work, research or targeted evidence reuse, decision-tree interview, implementation tasks, review and approval.
- Output: a dated file at `docs/plans/YYYY-MM-DD-<task-slug>.md`, unless explicit user/project instructions require another path.
- Evidence: local `path:line` citations and external URLs, with confidence and unresolved assumptions kept distinct from agreed decisions.
- Persistence: research uses its existing memo/index convention; the plan links the memo and records decisions as they are settled.
- Revision: keep the original plan filename and creation date; do not replace another plan's work.
- Safety: only planning/research artifacts may change; delegation needs request or user/project authorization; approval does not itself authorize implementation.
- Portability: load dependency files from discovered skill locations instead of requiring Claude's `Skill` tool; use the current harness's user-question and subagent controls.
- Interview adaptation: ask one focused decision per interaction while preserving the dependency's frontier-completeness check.

## Validation

Run the skill-writer structural validator and `make test`.
The catalog suite checks direct dependencies and their transitive registered sources.
Dogfood separately on an unfamiliar task with both code and external constraints, then resume from its memo to check evidence reuse and decision persistence.
Static checks do not establish the quality of a live interview.

Should apply: "plan this refactor", "plan a task from this ticket", "revise this existing plan".
Should not start automatically: "fix this typo", "what does this function do", "implement the approved plan".

## Maintenance

Keep the runtime workflow and task template in `SKILL.md`; keep provenance and decisions in `SOURCES.md`.
Update the research contract and registry dependencies together when changing composition.
No new runtime references, scripts, alias commands, or external dependencies are required.
