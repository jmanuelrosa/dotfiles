# Research Specification

## Intent

Turn an ad-hoc work question - "can we build X", "how does this area work", "investigate Y" - into a cited, verified decision memo without requiring the Product Team pipeline. It fills the gap between web-only investigation and `4-tech-shape` (codebase feasibility, but gate-locked behind an approved PRD).

## Scope

In scope:

- Feasibility questions, unfamiliar-code deep dives, general/external investigations, and fact-only planning groundwork invoked by `to-plan`.
- Context pulled from Jira (`acli`), Notion (`ntn`), GitHub (`gh`), GitLab (`glab`), library / CLI / cloud service docs (`ctx7`), the web, and available read-only Slack access or user-pasted threads.
- Read-only code exploration across one repo or a parent dir spanning several.
- Memos written to `.claude/state/research/YYYY-MM-DD-research-<topic>.md` plus an `INDEX.md` line.
- Ask-first delivery to Notion or as a Jira comment.

Out of scope:

- Any code, config, or `.gitignore` modification.
- Market/user/competitive research for product initiatives (that is `/1-research` on the product-team bundle).
- Implementation plans (owned by `to-plan`), design docs, and ADRs.

## Users And Trigger Context

- Primary users: the repo owner doing job investigations.
- Common user requests: "investigate if we can do X", "research this ticket", "is this feasible", "understand how X works", a Jira key or Notion URL plus a question.
- Internal planning invocation: `to-plan` requests planning-groundwork mode, which returns facts and unresolved decisions without a recommendation or delivery prompt.
- Should not trigger for: quick factual questions answerable inline, code changes, product-pipeline stages.

## Runtime Contract

- Required first actions: restate the question, classify the mode, decompose into sub-questions, detect repo scope, check `INDEX.md` for prior work.
- Required outputs: the memo file, the `INDEX.md` line, the printed path.
- Non-negotiable constraints: every claim cited or labeled assumption; per-finding confidence; adversarial verification before finalizing; no publishing without explicit confirmation; planning-groundwork remains fact-only and skips delivery.
- Delegation: use authorized read-only subagents for volume reads and independent claim checks, returning distilled findings; otherwise use narrow direct reads and label verification as a self-check.
- Composition: the caller retains scope, interview, plan output, and implementation authorization; research supplies the cited memo and evidence.
- Expected bundled files loaded at runtime: `references/memo-template.md` (memo shape), `references/sources.md` (per-source CLI recipes).

## Source And Evidence Model

Authoritative sources:

- The code as read (`path:line` citations) via Explore agents.
- Tool records: Jira issues, Notion pages, PRs/MRs, current library / CLI / cloud service docs via `ctx7`.

Data that must not be stored:

- Secrets, tokens, customer data.
- Full Slack thread pastes beyond what the memo needs to quote.

## Reference Architecture

- `SKILL.md` contains: the 8-step workflow, mode table, rigor rules, boundaries.
- `references/` contains: `memo-template.md`, `sources.md`.

## Validation

- Lightweight validation: `quick_validate.py` from the skill-writer skill.
- Deeper validation: dogfood on a real investigation in a work repo; the memo must have a mode-appropriate TL;DR, per-finding confidence, `path:line` citations, and verification notes.
- Acceptance gates: the structural validator and `make test` pass with the skill registered and its dependencies present.

## Known Limitations

- Slack depends on an available authenticated read-only tool; otherwise it remains a manual paste.
- `.claude/state/research/` remains the research convention across harnesses; `to-plan` reuses and links its memos, and gitignoring them is a per-repo decision left to the user.
- The registry dependency on `jira` exists because the delivery step follows that skill's ADF and humanization rules.

## Maintenance Notes

- When to update `SKILL.md`: workflow-step or boundary changes, new source types, or changes to the planning-groundwork contract consumed by `to-plan`.
- When to update `references/sources.md`: CLI syntax changes (`acli`, `ntn`, `glab` are all evolving), new tools gaining CLIs (Slack).
- When to update this file: scope, trigger, or storage-convention changes.
