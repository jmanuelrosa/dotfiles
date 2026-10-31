# RFC Writing Sources

## Evidence

| Source | Authority and confidence | Contribution |
|---|---|---|
| User request in this session | Required behavior, high | One `to-rfc` entry point, context intake up front (code, docs, Slack), a grill-with-docs interview, no duplication of existing skills, local draft only, template bundled in the skill, global scope |
| Default RFC template (`assets/rfc-template.md`, generalized from a team template in use) | Proven outline, high | Section outline, writing rules, the decision log |
| Sibling `to-plan/SKILL.md`, `SPEC.md` and `SOURCES.md` | Local precedent, high | Fixed chaining of research then interview then document; planning-groundwork research; one-question-per-call interview adaptation; explicit invocation |
| Sibling `research/SKILL.md` and `references/sources.md` | Local contract, high | Source recipes for Jira, Notion, GitHub, GitLab, Slack and docs; memo reuse; adversarial verification |
| Sibling `grilling/SKILL.md` and `grill-with-docs/SKILL.md` | Upstream contract as installed, high | Design tree, frontier rounds, recommended answers; the grilling plus domain-modeling pairing |
| Sibling `domain-modeling/SKILL.md` and `ADR-FORMAT.md` | Upstream contract as installed, high | Glossary updates inline; ADRs only when hard to reverse, surprising, and a real trade-off |
| Sibling `unslop/SKILL.md` | Upstream contract as installed, high | Final prose pass |
| `docs/skill-registry.md` | Repository policy, high | Dependencies live in the registry; `global: true` selects the machine roots |
| Catalog sweep of agents, skills and bundles | Local inventory, high | No existing RFC artifact; `4-tech-shape` writes a design doc but requires the product-team pipeline and an approved PRD |
| Dogfood review of a real RFC (2026-10-13 and 2026-10-14): 31 review comment threads from engineering and product leads on the template-shaped draft | Human-verified negative and fix examples, high | No meeting references in the body; ticket requirements versus our proposals; sources ready for "where is this coming from?"; no code-only hypothetical risks; no operational claims inferred from code; drop sections with nothing to decide; options in section 6 grouped by subsection, without "Rejected:"; drawbacks are costs, not constraints; define introduced statuses; plain, self-contained bullets; existing-customer rollout states; replies before page updates |
| Technical refinement on the same RFC (2026-10-15, AI meeting summary) and 3 later Notion comments from the product manager | Human-verified decisions, high once confirmed with the user | The RFC is technical only and product gaps go to the tickets; states by stored value with the design's names, never invented colors; independent states kept apart; extend an existing table before adding one; narrowest cached query on large tables; untrusted input stays inert; superseded designs deleted, not moved to Alternatives; re-collect comments right before publishing; confirm garbled summary points |

## Decisions and coverage

| Dimension | Decision |
|---|---|
| Artifact type | Skill, not agent: the core is an interview with the user, which a subagent cannot run |
| Reuse | Compose `research`, `grilling`, `domain-modeling` and `unslop`; no copied text from any of them |
| Not a `to-plan` mode | The outputs conflict: a plan ends in tasks with file paths, which the template excludes, and a plan settles every question while an RFC keeps the open ones for reviewers |
| Template source | Bundled asset per the user's choice; a project `docs/templates/rfc.md` overrides it |
| Interview | Full grill-with-docs per the user's choice; Tier 2 adaptation from `to-plan` kept: independent frontier questions only per user-tool call, completeness preserved through section 8 |
| Settled rule | A sort into author verdict, technical question or product gap, because grilling's "frontier empty" stop does not fit a document whose section 8 is meant to stay open |
| Technical only | Removed section 8.1 product decisions after the CTO ruled that an RFC validates the technical solution and is no product source of truth; this reverses the 2026-10-14 rule that turned open ticket values into product decisions |
| ADRs | Allowed during the interview, gated by domain-modeling's three conditions plus author ownership, marked overturnable until the RFC is accepted |
| Output | Local `docs/rfcs/YYYY-MM-DD-<slug>.md` only; Notion paste is manual per the user's choice |
| Model pin | `opus`, matching `to-plan` and `research`: the work is long-context synthesis and judgment calls (sorting verdicts from reviewer questions), and a fixed pin keeps runs comparable whatever the session default is |
| Additional machinery | Rejected a word-count script, a references directory, and a Notion publishing step |

| Options placement | Moved weighed options out of `3.x` tables into section 6, because the CTO asked that section 3 hold only the accepted solution; this overrides the reference RFCs' "(chosen)" tables |
| Architecture over UI | Section 3 architects the new components, data and contracts rather than explaining what the UI should do, per reviewer feedback; rollout-day states are framed as data questions, and UI behaviour stays in the design |
| Review response | Added as a step 5 sub-procedure, not a separate skill: it shares the sources, the draft and the checklist, and still publishes nothing |

## Changelog

- 2026-10-14: iterated from the dogfood review. Template: new writing rules, Release line, section 3 without options tables, sections 4 to 6 and 9 guidance. `SKILL.md`: origin tags in research, unchanged behaviour sorted out, open ticket values as product decisions, rollout-day states, a wider checklist with an anti-pattern table, and the review response. Precision: replaced the 3.x options rule, narrowed the drawbacks and alternatives guidance, added the rest with reason (each one maps to a reviewer comment).

- 2026-10-16: iterated from the technical refinement. Template: technical-only rule, states by stored value, section 8 without product decisions, superseded designs deleted, untrusted input in section 9, decision-log rows replaced on reversal. `SKILL.md`: meeting notes as an input, the product-gap outcome, table and query challenges, checklist lines, six anti-pattern rows, summary confirmation and a re-collect before publishing. Precision: replaced the product-decision rules and the 8.1 anti-pattern row rather than adding beside them.

- 2026-10-14: architecture-first focus from reviewer feedback. Template: a writing rule and section 3 guidance (components, not screens). `SKILL.md`: rollout-day states as data questions, a checklist line, and an anti-pattern row.

## Precision and remaining validation

Added `SKILL.md`, `SPEC.md`, this file and the template asset; no existing skill was edited.
The research step's section table and the writing checklist were derived from the template's guidance lines so the body of the template stays verbatim.
Dogfooded on the domains management epic through two review rounds; the second round's comments are the source of the 2026-10-14 changes.
Live validation pending: a fresh draft through the updated checklist, checked against the anti-pattern table.
