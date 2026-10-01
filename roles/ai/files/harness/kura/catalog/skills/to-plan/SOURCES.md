# Planning Workflow Sources

## Evidence

| Source | Authority and confidence | Contribution |
|---|---|---|
| User request in this session | Required behavior, high | One `to-plan` entry point, internally composed skills, registry dependencies, and `docs/plans/` output |
| Existing `to-plan/SKILL.md` and its introducing change in git history | Local behavior, high | Research before design, iterative review, and explicit implementation authorization |
| Sibling `research/SKILL.md`, `SPEC.md`, and memo/source references | Local contract, high | Code plus external investigation, citations, confidence, contradictions, and adversarial verification |
| Sibling `grilling/SKILL.md` | Upstream contract as installed, high | Dependency-aware decision tree, recomputed frontier, and shared-understanding gate |
| `docs/internals/skill-registry.md` | Repository policy, high | Runtime dependencies belong in the registry and are resolved transitively |
| `docs/internals/plan-files.md` | Repository policy, high | Dated, tracked plans under `docs/plans/` |
| Installed Pi `docs/skills.md` | Official local documentation, high | Explicit `/skill:name` invocation and loading dependency instructions by reading files |
| Installed `pi-subagents` skill and global instructions | Execution boundary, high | Skills cannot independently authorize delegation; one focused question per user-tool call |
| Luka's [research skill](https://github.com/LukaPrebil/harness-config/blob/main/skills/research/SKILL.md) and linked Slack message | Workflow comparison, high | Evidence-only research followed by grilling, rather than recommending a design during research |

The upstream comparison informed workflow separation only.
No upstream text was copied; existing local skills remain the reusable implementations.

## Decisions and coverage

| Dimension | Decision |
|---|---|
| Shape and order | Adopted fixed prompt chaining: research, interview, actionable plan, approval |
| Research scope | Adopted code and external sources; added planning-groundwork mode without changing standalone recommendation modes |
| Interview completeness | Tier 2: grilling wanted whole-frontier batching; replaced it with one focused question to obey the user-tool contract while satisfying its frontier-completeness check through persisted unresolved decisions |
| Output | Replaced `docs/design/` and the mandatory design walkthrough with a dated implementation plan and optional walkthrough |
| Reuse and repair | Adopted memo reuse and targeted re-verification when a decision changes a premise |
| Safety | Preserved explicit implementation authorization and separate publishing permission; recorded delegation ceilings |
| Triggering | Preserved explicit invocation and removed conflicting proactive-trigger instructions |
| Registration | Adopted direct `research` and `grilling` dependencies rather than asking the user to invoke multiple skills |
| Failure and stop conditions | Leave unresolved plans Draft, surface inaccessible evidence, and do not claim independent review for self-checks |
| Additional machinery | Rejected scripts, a third task-breakdown dependency, new aliases, and duplicate design/task artifacts |

## Precision and remaining validation

Replaced duplicated research dispatch rules, the single-round interview, the design-only template, and forced section-by-section narration.
Narrowed research recommendations to non-planning modes and external delivery to standalone research.
Replaced the assumption of a built-in external-research skill with the current harness's available web tools, and made code exploration conditional on relevant code scope.
Added maintenance files because the skill's output, composition, and approval contract changed materially.

Further source collection is low-yield: the local dependency contracts, harness loading behavior, repository storage conventions, and safety boundaries cover the requested change.
Static validation covers format and dependency registration; a live planning session is still needed to evaluate interview quality and task usefulness.
