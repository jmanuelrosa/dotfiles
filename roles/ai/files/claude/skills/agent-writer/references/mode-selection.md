# Mode selection

When to read: at the start of every agent-writer run, to pick the path before touching files.

## The four modes

- **New implementer seat.** A staff-engineer agent that edits files under a delegated brief (the shipped fleet: backend, frontend, design, mobile, platform, cloud, sre, data, analytics, gtm, database, qa, dx). Full pipeline: research, paired failure-modes skill, audit, sweep. `model: opus`. Ships as a plugin (see `packaging.md`).
- **Seat upgrade.** An existing pre-pattern agent gains the failure-modes architecture. Same full pipeline, plus an inventory of what the current file already has and what is seat-specific and must survive (see below).
- **Advisor seat.** Read-only, never edits files, output is an assessment (security-staff-engineer is the shipped example). Full pipeline with the adaptations in `advisor-adaptation.md`. Model and tools may deliberately differ from the family; preserve them.
- **Utility agent.** Narrow, single-purpose, usually invoked by one specific skill (pm-red-team, adr-scribe, ac-writer, the researchers). Light path in `utility-agents.md`: no failure-modes pair, no researchers, no audit subagent.

## Choosing between seat and utility

A seat owns a discipline surface, detects a stack, routes to skills, and returns a completion report; it exists so any project can delegate that discipline to it.
A utility agent does one job for one caller, often with a hard "Use ONLY from /X" contract and a single artifact or verdict as output.
If the description needs "Not the X seat" exclusions or an ask-first tier, it is a seat.
If the description needs "writes <one file> and nothing else", it is a utility agent.

## Upgrade inventory (before rewriting a seat)

List three things from the current file, in the final message and in your working notes:

1. **Missing family sections.** Typically: Ways of thinking, Red flags, Pre-handoff self-check, Common rationalizations, the Step 3 trigger table, blast-radius clause in loop step 1, "### Self-check" and "### Missing gates" report sections.
2. **Content to redistribute.** A "quality bar" section gets cut and its content moves into the references, red flags, and self-check; it never survives as a section.
3. **Seat-specific keeps.** Anything that is the seat's identity: unusual report sections (Migration safety, Product bugs found, Contracts and consumers, Findings), unusual gate mechanics (provably-able-to-fail, up/down/up, "not runtime-verified" wording), and the never-tier invariants. These survive verbatim or renamed to family casing, never dropped for symmetry.

## Where the files go

Canonical home is the dotfiles repo. A seat (implementer or advisor) is a plugin: `roles/ai/files/claude/plugins/<discipline>/` bundling `agents/<seat>.md` and `skills/<seat>-failure-modes/`. A utility agent is flat: `roles/ai/files/claude/agents/<name>.md`.
Project-local is the exception (a seat plugin under `.claude/skills/<discipline>/`, a utility agent under `.claude/agents/`) and skips the registry entirely; confirm with the user before choosing that path.
