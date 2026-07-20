# Research Specification

## Intent

Turn an ad-hoc work question - "can we build X", "how does this area work", "investigate Y" - into a cited, verified decision memo without requiring the Product Team pipeline. It fills the gap between `deep-research` (web only, never reads code or work tools) and `4-tech-shape` (codebase feasibility, but gate-locked behind an approved PRD).

## Scope

In scope:

- Feasibility questions, unfamiliar-code deep dives, and general/external investigations.
- Context pulled from Jira (`acli`), Notion (`ntn`), GitHub (`gh`), GitLab (`glab`), library docs (`ctx7`), the web, and user-pasted Slack threads.
- Read-only code exploration across one repo or a parent dir spanning several.
- Memos written to `.claude/state/research/YYYY-MM-DD-research-<topic>.md` plus an `INDEX.md` line.
- Ask-first delivery to Notion or as a Jira comment.

Out of scope:

- Any code, config, or `.gitignore` modification.
- Market/user/competitive research for product initiatives (that is `/1-research`).
- Design docs and ADRs (that is `/4-tech-shape`).

## Users And Trigger Context

- Primary users: the repo owner doing job investigations.
- Common user requests: "investigate if we can do X", "research this ticket", "is this feasible", "understand how X works", a Jira key or Notion URL plus a question.
- Should not trigger for: quick factual questions answerable inline, code changes, product-pipeline stages.

## Runtime Contract

- Required first actions: restate the question, classify the mode, decompose into sub-questions, detect repo scope, check `INDEX.md` for prior work.
- Required outputs: the memo file, the `INDEX.md` line, the printed path.
- Non-negotiable constraints: every claim cited or labeled assumption; per-finding confidence; adversarial verification before finalizing; no publishing without explicit confirmation; volume reads (source pulls, code sweeps, claim re-checks) run in parallel subagents that return distilled findings, keeping raw material out of the main context.
- Expected bundled files loaded at runtime: `references/memo-template.md` (memo shape), `references/sources.md` (per-source CLI recipes).

## Source And Evidence Model

Authoritative sources:

- The code as read (`path:line` citations) via Explore agents.
- Tool records: Jira issues, Notion pages, PRs/MRs, current library docs via `ctx7`.

Data that must not be stored:

- Secrets, tokens, customer data.
- Full Slack thread pastes beyond what the memo needs to quote.

## Reference Architecture

- `SKILL.md` contains: the 8-step workflow, mode table, rigor rules, boundaries.
- `references/` contains: `memo-template.md`, `sources.md`.

## Validation

- Lightweight validation: `quick_validate.py` from the skill-writer skill.
- Deeper validation: dogfood on a real investigation in a work repo; the memo must have a TL;DR verdict, per-finding confidence, `path:line` citations, and verification notes.
- Acceptance gates: `make check-role ROLE=ai` passes with the skill in `GLOBAL_CLAUDE_SKILLS`.

## Known Limitations

- Slack is a manual paste: no Slack CLI or MCP exists on this machine. Revisit if one is installed (then add a recipe to `references/sources.md`).
- `.claude/state/research/` is a convention this skill establishes; nothing else reads it yet, and gitignoring it is a per-repo decision left to the user.
- The registry dependency on `jira` exists because the delivery step follows that skill's ADF and humanization rules.

## Maintenance Notes

- When to update `SKILL.md`: workflow-step or boundary changes, new source types.
- When to update `references/sources.md`: CLI syntax changes (`acli`, `ntn`, `glab` are all evolving), new tools gaining CLIs (Slack).
- When to update this file: scope, trigger, or storage-convention changes.
