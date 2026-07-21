---
name: agent-writer
description: >-
  Create or upgrade a Claude Code subagent following the house patterns: staff-engineer seats
  with a paired failure-modes skill (researched, audited, verified), advisor seats with the
  read-only adaptation, or narrow utility agents. Covers seat scoping, the two-researcher
  protocol, agent and skill authoring, plugin packaging, the fresh-eyes audit, and the
  verification sweep. The agent-side counterpart of skill-writer.
argument-hint: "<agent name or purpose> (e.g. mobile-staff-engineer, or: upgrade qa-staff-engineer)"
disable-model-invocation: true
model: fable
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
  - Agent
  - SendMessage
  - AskUserQuestion
---

# Agent Writer

The single canonical workflow for creating or upgrading subagents, the way skill-writer is for skills.
It encodes the process that shipped the staff-engineer fleet and their failure-modes pairs as skills-dir plugins, so a new agent lands consistent with the family on the first pass instead of after three audits.

Follow the steps in order.
Load only the reference files required for the step you are on.
The shipped pairs on disk are the living exemplars; references here describe the pattern and point at them, they never replace reading them.

## References

| Open when you need to... | Read |
|---|---|
| decide whether this is a seat agent, an advisor seat, a utility agent, or an upgrade | `references/mode-selection.md` |
| write or restructure the agent file itself (section order, line budget, family style) | `references/seat-agent-anatomy.md` |
| author the paired failure-modes skill (router + reference template) | `references/failure-modes-skill.md` |
| keep agent and skill from contradicting each other (the audit-derived rules) | `references/coherence-rules.md` |
| brief and run the two background researchers | `references/research-protocol.md` |
| package a seat as a skills-dir plugin, or wire a utility agent into the registry | `references/packaging.md` |
| run the final verification sweep | `references/verification-sweep.md` |
| adapt the pattern for a read-only or advisor seat | `references/advisor-adaptation.md` |
| build a narrow single-purpose agent instead of a seat | `references/utility-agents.md` |
| emit a reusable prompt so another session can run this process instead | `references/session-prompt-template.md` |

## Step 1: Resolve mode and target

1. Read `references/mode-selection.md` and classify the request: new seat, seat upgrade, advisor seat, or utility agent.
2. Utility agents take the light path in `references/utility-agents.md` and skip Steps 3-4; everything else runs the full pipeline.
3. Canonical home is this dotfiles repo: a seat is a plugin at `roles/ai/files/claude/plugins/<discipline>/` (agent + skill bundled); a utility agent is flat at `roles/ai/files/claude/agents/`. If invoked elsewhere, ask whether the agent is project-local (a seat plugin under `.claude/skills/`, a utility agent under `.claude/agents/`) before writing anything.
4. If the user wants a prompt for a future session rather than the work done now, produce it from `references/session-prompt-template.md` and stop.

## Step 2: Ground in the canon and the current state

1. Read the two canon exemplars in full: `backend-staff-engineer.md` + `backend-failure-modes/`, and `platform-staff-engineer.md` + `platform-failure-modes/`. Never re-derive the pattern from memory.
2. If upgrading, read the seat file in full and list what it already has, what is missing, and what is seat-specific and must survive (report sections, gate wording, identity invariants).
3. Scan the `plugins/` folder and both registries for adjacent skills and sibling seats: what already exists (must not be duplicated), what the agent's Step 2 names but is not present (a gap to state, not coverage to assume), and which sibling pair carries the sharpest demarcation risk.
4. Write down the seat's scope, its excluded surfaces with the owning sibling for each, and its identity invariants (the things that must appear in the intro, the never tier, the red flags, and the rationalizations).

## Step 3: Launch research (background, in parallel)

Read `references/research-protocol.md`.
Launch `<seat>-ladder-researcher` and `<seat>-pack-researcher` as background agents before authoring starts; fold their deltas in when they report.
If one dies mid-response on a connection error, message it to resend its final report; do not relaunch.

## Step 4: Ask the one question

Propose the ~8 reference domains for the failure-modes skill, one line of scope each, and ask the user to confirm via AskUserQuestion.
This is the only question in the whole pipeline; everything else proceeds on the locked decisions and the references here.

## Step 5: Author

1. Author the failure-modes skill per `references/failure-modes-skill.md`.
2. Write or rewrite the agent per `references/seat-agent-anatomy.md` (or `references/advisor-adaptation.md` for read-only seats).
3. Apply `references/coherence-rules.md` while writing, not as a cleanup pass.
4. Package the seat as a skills-dir plugin (or wire a utility agent into the registry) per `references/packaging.md`.

## Step 6: Fresh-eyes audit

Spawn a synchronous subagent with no prior context to audit the new pair, its `plugin.json` (or the registry entry for a utility agent), and the sibling pair with the sharpest demarcation risk.
Priority order: contradictions between agent and references (annotation breadth, never-vs-ask-first coherence), packaging (trigger-table domains vs actual reference files, plugin.json or registry entry), technical wrongness (fact-check domain claims: statistics, engine behavior, security semantics), family consistency (section order, report contract, loop numbering), style.
Apply its must-fix and should-fix findings.

## Step 7: Verify and report

Run every check in `references/verification-sweep.md`; all must pass.
Final message: what shipped with paths and line counts, research adopted vs rejected, audit findings and fixes, verification results, git status.
Commit nothing: the user drives `/commit`. No research doc is committed.

## Style, non-negotiable

No em or en dashes anywhere.
Semantic line breaks: one sentence per line, no hard wrap.
Reference content is checks against a diff, never tutorials.
Checks stay stack-agnostic; tool- and framework-specific guidance belongs to installed stack skills.
