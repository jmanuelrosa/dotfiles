---
name: to-plan
description: Plans a task through code and external research, a decision-tree interview, and an actionable implementation plan in docs/plans/. Use explicitly to plan a feature, refactor, architecture change, or unfamiliar task before implementation. Internally composes research and grilling; reuses existing evidence and waits for explicit implementation authorization.
model: openai-codex/gpt-5.6-sol
disable-model-invocation: true
---

# Task planning

Own the planning workflow from evidence to an approved implementation plan.
Load `research` and `grilling` internally; never ask the user to invoke them separately.
Keep research facts, proposed options, and agreed decisions distinct.

## Invocation and boundaries

- Invoke explicitly: `/skill:to-plan <task, ticket, source URL, or existing research/plan path>` in Pi, or `/to-plan` in Claude Code.
- If no task is supplied, ask what the user wants to plan.
- For a trivial fix or a change that exactly matches an existing pattern, offer a short plan instead of manufacturing a design exercise.
- Resolve dependency skills from the available skill locations and read their `SKILL.md` and required references for the active phase.
  Pi loads skills by reading their files; do not require a `Skill` tool or send bare slash commands to the model as a substitute.
- Keep user interaction and approval in the main conversation.
  Delegate source gathering, code exploration, and claim verification only when the current request or applicable user/project instructions authorize it.
  Follow the current harness's subagent controls; this skill does not grant delegation permission.
- Modify only planning and research artifacts.
  Do not modify implementation code, configs, dependencies, or accepted ADRs, and do not publish externally.
- Do not infer implementation authorization from silence, "looks good", or completion of a review.

## 1. Scope and prior work

Restate the task, intended outcome, acceptance boundary, and non-goals.
Read project instructions and supplied tickets, documents, or source links.
Find existing plans for the same work and any supplied or indexed research memo.

Choose `docs/plans/YYYY-MM-DD-<task-slug>.md` using today's date and a descriptive kebab-case slug, unless the user or project explicitly requires another path.
When revising the same plan, keep its filename and creation date and record the revision date.
Do not overwrite, rename, or discard a different or concurrently owned plan; ask the user to resolve the conflict.

Reuse relevant evidence rather than restarting.
Check only the citations, code seams, installed versions, or sources that changed or are missing.
If the scope or desired outcome is ambiguous, ask one focused question before research.

## 2. Research the planning groundwork

Load `research` in **planning-groundwork** mode with the task, confirmed repo scope, source links, and prior evidence.
Use its source recipes, citation and confidence rules, contradiction handling, and adversarial verification.
Research both the relevant code and external evidence: official documentation, standards, upstream changes, or factual comparisons when the task depends on them.
Skip irrelevant sources, not the external half merely because a codebase exists.

Require a findings pack containing:

- Current behavior and integration seams, with `path:line` citations.
- Relevant existing patterns and enforcement layers.
- External facts with source URLs and compatibility with the installed version.
- Constraints, contradictions, assumptions, and confidence.
- Decision questions that evidence alone cannot answer.
- Verification outcomes and the research memo path.

For authorized volume reads, keep raw material in read-only subagents and merge distilled findings.
When delegation is not authorized, use narrow direct reads and report verification as a self-check rather than independent review.

Do not recommend a solution during this phase.
Do not publish the memo or ask where to deliver it.
Reuse a relevant current memo and investigate only its gaps.

Present the factual findings and contradictions briefly.
Create or update the draft plan's goal, evidence, constraints, and open questions before proposing a design.
Exit when the load-bearing facts are verified or explicitly marked unresolved.

## 3. Grill the decisions

Load `grilling` with the research findings, draft plan, and user constraints.
Use its design-tree model: resolve prerequisite decisions before asking about dependent ones, recompute the frontier after every answer, and continue until no blocking branch remains.

Ask **one focused decision at a time** through the current harness's user-question tool.
Include the evidence, concrete alternatives, trade-offs, and your recommended answer.
Do not inherit the dependency's whole-frontier batching or emoji format.
Preserve its completeness check by keeping every unanswered frontier decision in the plan's open questions.

Look up facts yourself instead of asking the user to supply discoverable information.
Turn competing approaches and counterexamples into questions, not silently selected defaults.
Challenge decisions with concrete scenarios, failure cases, compatibility, and task-specific risks.
Record each agreed decision and its rationale in the plan as it lands.

If an answer changes a load-bearing premise, return to targeted research and verification before asking downstream questions.
If the user stops early, leave the plan Draft and list the unresolved decisions.
Exit when blocking branches are settled and the user confirms shared understanding.
Explicitly deferred non-blocking questions must name their owner and impact.

## 4. Write the implementation plan

Complete the same draft plan using the template below.
Keep sections proportional to the task; omit architecture diagrams, API sketches, or behavior matrices unless they clarify a real decision.
Do not create a second design document or duplicate task list.

Order small, verifiable tasks by dependency.
Prefer vertical slices that leave a working system, and put uncertainty-reducing spikes before dependent implementation.
Each task must name its intended behavior, likely files, dependencies, acceptance criteria, and verification using the repository's actual commands or checks.
Distinguish checks to run during implementation from checks already performed during research.

```markdown
# Plan: <task>

**Status:** Draft
**Created:** <YYYY-MM-DD>
**Updated:** <YYYY-MM-DD, when revised>
**Scope:** <repos and affected areas>
**Research:** <relative link to the memo, when present>

## Goal and non-goals

<Outcome, success criteria, and explicit exclusions.>

## Evidence and constraints

<Current behavior, existing patterns, external facts, contradictions, and remaining assumptions, with citations and confidence.>

## Agreed decisions

<Decision, rationale, alternatives considered, and the user's agreed choice.>

## Implementation tasks

### 1. <Small, verifiable outcome>

- [ ] <Behavior to implement>
- **Files:** <likely paths>
- **Depends on:** <earlier tasks, or none>
- **Acceptance criteria:** <specific, testable conditions>
- **Verification:** <actual commands or observable checks>

### 2. <Next outcome>

<Same structure.>

## Risks and open questions

<Risk, mitigation or investigation, owner, and whether it blocks implementation.>

## Approval

<Pending review, then what the user approved and when.
Implementation requires an explicit request, not merely plan approval.>
```

## 5. Review and approval

Check the plan against the original goal, research constraints, agreed decisions, and task dependencies.
Do not declare it ready while a blocking assumption or decision remains unresolved.
If verification uncovers a contradiction, revise the affected evidence, decision, and tasks before requesting approval.

Present the plan path and remaining decisions.
Offer a step-by-step walkthrough if the user wants one; do not require a turn for every section by default.
Apply accepted refinements to the same plan.

Ask for plan approval through the current harness's user-question tool.
Mark the plan Approved only after explicit approval.
Finish planning here; begin a separate implementation workflow only when the user explicitly asks to implement.
