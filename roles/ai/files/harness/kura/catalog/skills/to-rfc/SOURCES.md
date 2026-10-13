# RFC Writing Sources

## Evidence

| Source | Authority and confidence | Contribution |
|---|---|---|
| User request in this session | Required behavior, high | One `to-rfc` entry point, context intake up front (code, docs, Slack), a grill-with-docs interview, no duplication of existing skills, local draft only, template bundled in the skill, global scope |
| Team RFC template (`assets/rfc-template.md`, copied from the work repo's `docs/templates/rfc.md`) | Team contract, high | Section outline, writing rules, the split between product decisions and technical questions, the decision log |
| Sibling `to-plan/SKILL.md`, `SPEC.md` and `SOURCES.md` | Local precedent, high | Fixed chaining of research then interview then document; planning-groundwork research; one-question-per-call interview adaptation; explicit invocation |
| Sibling `research/SKILL.md` and `references/sources.md` | Local contract, high | Source recipes for Jira, Notion, GitHub, GitLab, Slack and docs; memo reuse; adversarial verification |
| Sibling `grilling/SKILL.md` and `grill-with-docs/SKILL.md` | Upstream contract as installed, high | Design tree, frontier rounds, recommended answers; the grilling plus domain-modeling pairing |
| Sibling `domain-modeling/SKILL.md` and `ADR-FORMAT.md` | Upstream contract as installed, high | Glossary updates inline; ADRs only when hard to reverse, surprising, and a real trade-off |
| Sibling `unslop/SKILL.md` | Upstream contract as installed, high | Final prose pass |
| `docs/internals/skill-registry.md` | Repository policy, high | Dependencies live in the registry; `global: true` selects the machine roots |
| Catalog sweep of agents, skills and bundles | Local inventory, high | No existing RFC artifact; `4-tech-shape` writes a design doc but requires the product-team pipeline and an approved PRD |

## Decisions and coverage

| Dimension | Decision |
|---|---|
| Artifact type | Skill, not agent: the core is an interview with the user, which a subagent cannot run |
| Reuse | Compose `research`, `grilling`, `domain-modeling` and `unslop`; no copied text from any of them |
| Not a `to-plan` mode | The outputs conflict: a plan ends in tasks with file paths, which the template excludes, and a plan settles every question while an RFC keeps the open ones for reviewers |
| Template source | Bundled asset per the user's choice; a project `docs/templates/rfc.md` overrides it |
| Interview | Full grill-with-docs per the user's choice; Tier 2 adaptation from `to-plan` kept: independent frontier questions only per user-tool call, completeness preserved through section 8 |
| Settled rule | Added the three-way sort (author verdict, product decision, technical question) because grilling's "frontier empty" stop does not fit a document whose section 8 is meant to stay open |
| ADRs | Allowed during the interview, gated by domain-modeling's three conditions plus author ownership, marked overturnable until the RFC is accepted |
| Output | Local `docs/rfcs/YYYY-MM-DD-<slug>.md` only; Notion paste is manual per the user's choice |
| Model pin | `opus`, matching `to-plan` and `research`: the work is long-context synthesis and judgment calls (sorting verdicts from reviewer questions), and a fixed pin keeps runs comparable whatever the session default is |
| Additional machinery | Rejected a word-count script, a references directory, and a Notion publishing step |

## Precision and remaining validation

Added `SKILL.md`, `SPEC.md`, this file and the template asset; no existing skill was edited.
The research step's section table and the writing checklist were derived from the template's guidance lines so the body of the template stays verbatim.
Live validation pending: a dogfood run on a real epic, then a revision pass after a review comment.
