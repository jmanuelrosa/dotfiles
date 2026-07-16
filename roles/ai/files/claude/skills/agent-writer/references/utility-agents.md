# Utility agents

When to read: the request is a narrow single-purpose agent, not a discipline seat.
Shipped examples: `pm-red-team.md`, `adr-scribe.md`, `ac-writer.md`, `competitive-researcher.md`, `strategy-checker.md`.

## The light path

No failure-modes pair, no researchers, no audit subagent, no 200-line budget.
One grounding read (the closest existing utility agent), author, wire the registry, run the sweep checks that apply (dashes, YAML frontmatter, registry JSON, ansible-lint).
The whole job is usually under 80 lines of agent file.

## Anatomy

- **Frontmatter.** `name`, `description: >-`, an explicit `tools:` allowlist as narrow as the job allows (a verdict agent gets Read/Glob/Grep; a file-writer adds Write or Edit, never both without reason). `model:` only when the default is wrong for the job.
- **Description contract.** State the caller and the exclusivity: "Use ONLY from /<skill> with <inputs>". State the output surface exactly: "writes 01-research/competitive.md and nothing else", or "it writes nothing, its final message IS the verdict".
- **Context isolation when it is the point.** A red-team or fresh-eyes agent says what it reads and what it must NOT read ("reads the PRD and NOTHING else"); the isolation is the value, so make it a hard rule in the body, not a suggestion.
- **Body.** Role paragraph, hard rules, a short operating procedure, and an output contract (file template or final-message shape). No detect-the-stack table, no skill routing, no completion-report scaffolding unless the caller consumes it.
- **Failure honesty.** Even a 40-line agent states what it does when inputs are missing or wrong: report the gap to the caller, never invent (ac-writer "reports untraceable stories instead of inventing requirements" is the model).

## Wiring

A utility agent keeps the flat-file-plus-registry model; only seats moved to plugins.
`agent-registry.json` entry with `groups` (agent vocabulary: discipline plus domain) and `note: "Locally authored"`.
`dependencies` only if the agent genuinely invokes a skill at runtime.
Add to `GLOBAL_CLAUDE_AGENTS` in `roles/ai/defaults/main.yml` only if every project needs it; utility agents owned by one skill pipeline usually ship globally with that pipeline, so check where the calling skill lives.

## Boundary with seats

If the "utility" agent starts needing ask-first boundaries, stack detection, or a completion report contract, it is a seat wearing a trench coat: stop and rerun mode selection.
