# Setup Review Across Two Harnesses - Design Doc

**Status:** Implemented
**Author:** José Manuel Rosa Moncayo
**Date:** 2026-09-03
**Scope:** `roles/ai/files/claude/skills/cc-review/` (renamed), `roles/ai/files/claude/skills/setup-review-mechanics/` (new), `roles/ai/files/claude/agents/cc-staff-reviewer.md`, `roles/ai/files/claude/agents/pi-staff-reviewer.md` (new), `skill-registry.json`, `agent-registry.json`, and the call sites and frozen test sets that name `cc-review`

## Summary

The maintenance review of this machine's agent configuration exists only for Claude Code, and pi inherits it by symlink in a form that audits the wrong directory.
This design splits the existing pair into a harness-neutral entry point (`setup-review`), a harness-neutral method (`setup-review-mechanics`), and two thin per-harness reviewer agents (`cc-staff-reviewer`, kept under its current name, and a new `pi-staff-reviewer`).
One skill invocation then reviews whichever harness the session is running in, using the same review method and the same output contract, against an inventory that is correct for that harness.

## Motivation

`cc-review` is a locally authored skill that spawns a read-only advisor over `~/.claude` and the current project's `.claude/`, and applies whatever the user accepts (`roles/ai/files/claude/skills/cc-review/SKILL.md`).
It is the only artifact in this repo that reviews the agent setup itself rather than application code, and it has no pi counterpart.

The absence is not the usual kind, where a feature simply has not been built for the second harness.
`claude-kit sync` links global skills and agents into `~/.claude/`, and the `ai` role then links `~/.pi/agent/skills` and `~/.pi/agent/agents` at those directories (`roles/ai/tasks/main.yml:277-281`, `:291-295`).
So `/skill:cc-review` is invocable from pi today.
It runs, audits `~/.claude`, and returns advice about a harness the session is not using.
A reviewer that reports confidently on the wrong subject is worse than a missing one, because nothing in its output says the subject is wrong.

Four of its five steps have no pi equivalent, and the skill states them as Claude mechanics rather than as concepts.
Step 1 reads `~/.claude/usage-data/` and names `/insights`; step 4 names `AskUserQuestion`; step 5 names `/skill-writer` and an `update-config` skill that does not exist anywhere in this repo, its only reference being the line that invokes it (`cc-review/SKILL.md:16`).
That last one is a live defect independent of pi: an accepted settings or hook change routes to a skill that will never be found.

Meanwhile the pi side of this machine has accumulated an audit surface that nothing reviews at all: seven declared packages, four extensions, a derived sandbox config, a second trust store, a per-project convergence link, and a system-prompt file whose two spellings differ by whether the harness's own instructions survive.
Every structural trap recorded in [the pi harness](../internals/pi-harness.md) is a trap precisely because it is silent, which is the definition of something a periodic review should catch.

## Non-goals

- Reviewing application source code. The subject stays the agent configuration, in both harnesses.
- Diff review. `/code-review`, `/security-review` and the `pi-review` package own that surface, and this design does not touch `rules/code-review.md` or `review-mechanics`.
- Per-definition agent craft. That belongs to `agent-audit` and the boundary at `agent-audit/SKILL.md:10-12` is preserved, with `agent-audit` referring to `setup-review` under the new name.
- A cross-harness comparison report. The reviewer audits one harness per run; naming a Claude artifact from a pi run is a finding, not a diff.
- Reviewing Cursor, Gemini or any third harness. The split makes a third seat cheap, but nothing here builds one.
- Renaming `cc-staff-reviewer`. It keeps its name.

## Background

### The existing pair

`cc-review` is a skill, not a command file: this repo has no `roles/ai/files/claude/commands/` tree, and `disable-model-invocation: true` is what makes Claude Code expose the skill as `/cc-review` (`cc-review/SKILL.md:5`).
Its body is 22 lines of orchestration.
The substance lives in the agent it spawns.

`cc-staff-reviewer.md` is 214 lines: read-only, `tools: Read, Glob, Grep, Bash, WebFetch`, `model: opus`, dual-keyed `effort: high` and `thinking: high`.
It refreshes itself from `claude --version` plus the official changelog before reasoning, audits user and project scope with an explicit precedence chain, and returns a fixed six-part report.

Reading it against the question "would this sentence still be true under a different harness" splits it cleanly, and the split is uneven in a useful way.

Harness-neutral, roughly 70 lines: the advisor stance and the two equal duties (`:10-16`); the hard rules about stale training data, decisiveness and quoting file plus key (`:17-30`); the anti-over-engineering bias `delete > merge > convert > keep > add` with its one exception; calibration; dependency safety before any deletion (`:110-113`); the deprecation check and the adoption scan as mechanisms (`:115-129`); the discipline for proposing new artifacts, meaning recurring evidence only, at most three, always ASK (`:140-147`); and the entire output contract (`:201-214`).

Claude-only, the other 140: the changelog URL and version command (`:32-42`); the scope paths and the enterprise-to-user precedence chain (`:44-58`); the input reading order, which names `settings.json`, `CLAUDE.md`, `rules/`, `commands/`, `.mcp.json`, `/insights` facets and auto-memory (`:60-81`); the whole rules-semantics section, which is about `paths` frontmatter and the 200-line target (`:82-90`); the vocabulary of the right-tool table, meaning CLAUDE.md, path-scoped rule, slash command, skill, subagent, hook, MCP, output style, plugin (`:149-176`); and all four worked examples (`:178-199`).

### What pi's inventory actually is

pi's audit surface does not overlap that second list at any point.
The facts below are the ones a reviewer needs, all from [the pi harness](../internals/pi-harness.md).

`~/.pi/agent/SYSTEM.md` **replaces** pi's system prompt while `APPEND_SYSTEM.md` adds to it, so a real `SYSTEM.md` file trades every instruction the harness provides for whatever sits below it, silently.
The `ai` role removes a superseded `SYSTEM.md` symlink and deliberately leaves a real file alone, which means a real one is exactly the thing only a review will find.

`sandbox.json` is derived from the `sandbox` block plus the path half of `permissions` in Claude's `settings.json`, and `test_pi_sandbox.py` recomputes it and fails on drift.
A hand-edit is therefore a finding rather than a fix.
Four things the derivation cannot carry are permanently absent under pi: per-command exclusions, `$TMPDIR` expansion, the 64 command-shape `Bash(...)` deny rules, and the line between Claude's two read layers.

`settings.json` has no `env` block, so any recommendation that would be an env var in Claude Code has to route to `roles/shell/files/fish/conf.d/exports.fish` instead.

Extensions are type-stripped rather than compiled, so a constructor parameter property is a startup load failure rather than a type error.
Handlers run in `readdir` order across a directory this repo does not exclusively own, which is why the rtk rewrite lives inside `guardrails.ts` rather than beside it.
And `footer.ts` replaces pi's footer outright, so an extension that fails to render `getExtensionStatuses()` silently deletes every other extension's output.

Under `defaultProvider: cursor` the guardrails reach nothing unless `PI_CURSOR_EXPOSE_BUILTIN_TOOLS` is set, and a session where no gate ran is indistinguishable from one where every command passed.

Trust is two stores that cannot be unified, and pi's differs in three derivations: the key is the cwd rather than the repo root, it is realpathed where Claude's deliberately is not, and the nearest entry wins including a refusal.

pi's skill loader reads exactly three frontmatter fields, so `allowed-tools:`, `model:` and `effort:` are silently dead on a skill under pi, while agent frontmatter is read by `pi-subagents` and is therefore dual-keyed.

Project reachability is its own class of finding: pi discovers project skills from `.agents/skills` and never from `.claude/`, `claude-kit converge --all` maintains the link, and `checks.pi_skills_unreachable` (G19) reports a project missing it.

### Precedent for the shape

Splitting a reviewing agent from a shared method skill is already how this repo works, twice over.
`review-mechanics` is registered as "the deferred half of `~/.claude/rules/code-review.md`" (`skill-registry.json:876-883`), loaded on demand by whatever is writing a review.
And every seat plugin pairs a `<seat>-staff-engineer.md` agent with a `<seat>-failure-modes` skill that the agent routes into for the domains a change touches.
An agent loading a shared skill from its own isolated context is the established pattern under both harnesses, not an invention of this design.

### Harness detection

pi sets `PI_SESSION_ID`, `PI_SESSION_FILE`, `PI_MODEL`, `PI_PROVIDER` and `PI_CODING_AGENT` per session, and none of them appear anywhere in this repo's shell exports.
The one `PI_` variable this machine's shell does set is `PI_ASK_USER_DISPLAY_MODE` (`roles/shell/files/fish/conf.d/exports.fish:6`), which is present in every shell and therefore useless as a marker.
So `PI_SESSION_ID` is the detection hook: present means pi, absent means Claude Code.

## Design rules

- **One entry point, two seats.** `setup-review` is the only thing a user invokes; which reviewer runs is derived, never asked.
- **The method is shared, the inventory is not.** Anything that would still be true under a third harness lives in `setup-review-mechanics`. Anything naming a file, key, command or feature name lives in the seat.
- **A seat audits its own harness only.** Naming an artifact belonging to the other harness is a finding about a shared file, not a cross-harness diff.
- **The orchestrator names nothing harness-specific.** Following `AGENTS.md`, it names the concept and each harness spells it, exactly as `commit` reads as `/commit` and `/skill:commit`.
- **Evidence lookup belongs to the seat.** Each seat knows where its own usage records live, so the orchestrator does not carry a Claude-shaped precondition.
- **The reviewer never mutates.** Unchanged from today, and this design keeps `setup-review`'s apply step on the named-mutator list in `docs/internals/code-review-policy.md:26`.
- **Apply edits the repo, not the home directory.** Nearly everything under `~/.claude` and `~/.pi/agent` is a symlink into this checkout, so an accepted fix edits `roles/ai/files/...` and a new artifact is registered.
- **`setup-review-mechanics` is a deep module and the seats are shallow.** The method hides the judgment (bias order, dependency safety, evidence thresholds, report shape) behind one load; a seat is a list of paths and a vocabulary, which is a shallow problem and should stay shallow.

## Design

### 1. `setup-review`, the entry point

Replaces `roles/ai/files/claude/skills/cc-review/SKILL.md` at `roles/ai/files/claude/skills/setup-review/SKILL.md`.

```markdown
---
name: setup-review
description: Review my agent configuration for the harness this session is running in (user + project scope)
argument-hint: "[claude|pi]"
effort: medium
disable-model-invocation: true
---
Maintenance review of my agent configuration.

1. Determine which harness to review. An explicit argument wins.
   Otherwise: `PI_SESSION_ID` is set means pi, unset means Claude Code.
   State which harness you detected and which reviewer you are about to spawn.
2. Spawn that harness's reviewer as a subagent at BOTH scopes, user and the current project.
   Claude Code: cc-staff-reviewer. Pi: pi-staff-reviewer.
   It reports which scopes it actually found, and what usage evidence it had.
3. Return its report verbatim: the prioritized P0-P2 findings, the adoption
   opportunities, the proposed new artifacts, the action table, and the top-3 next moves.
4. If the report lists adoption opportunities or proposed new artifacts, ask me which to
   take, as a multi-select with one option per item and the why plus how in one line.
   Skip the question entirely when there are none.
5. Act on each accepted item here in the main conversation.
   Config changes directly; new skills and agents through the skill-writing skill.
   Almost every path the reviewer names is a symlink into my dotfiles repo, so the edit
   belongs in that repo beside its registry entry, not in the home directory. Say so, and
   offer to commit there.
   Drop declined items without ceremony.

The subagent never modifies files.
In this conversation, modify files only for items I explicitly accepted in step 4.
```

Three changes from the current body beyond the harness switch.

The `/insights` precondition is gone, from five steps to five with the first replaced.
The agent already handles a missing evidence store (`cc-staff-reviewer.md:76`), so the skill's copy of that logic was both duplicated and Claude-shaped.
What the orchestrator asks for instead is that the seat states what evidence it had, which is the part the reader actually needs.

Step 4 names the concept rather than `AskUserQuestion`.
Claude Code spells it `AskUserQuestion`; pi spells it `ask_user`, already installed as the `pi-ask-user` package (`roles/ai/files/pi/settings.json`).

Step 5 drops the reference to the non-existent `update-config` skill.
Settings and hook changes are ordinary edits to files in this repo, which is what the rest of the step already says.

### 2. `setup-review-mechanics`, the shared method

New, at `roles/ai/files/claude/skills/setup-review-mechanics/SKILL.md`.
Model-invocable, because the seats load it; no `disable-model-invocation`.
Both seats open with a line instructing them to load it before reasoning, the same way a seat agent routes into its failure-modes skill.

It carries, moved verbatim out of `cc-staff-reviewer.md` with the Claude nouns generalized:

- The advisor stance, read-only, and the two equal duties: remove over-engineering, and put each use case on the right customization feature.
- The hard rules: training data is stale so every version-specific claim is untrusted until confirmed against a fetched or local source; be decisive; quote the exact file plus key or line.
- The bias `delete > merge > convert > keep > add`, and its one exception for a real, documented, recurring need nothing addresses.
- Calibration: name what is already good, do not manufacture problems, a short sharp review beats an exhaustive one.
- Dependency safety: grep the whole tree before recommending any deletion, and mark a referenced artifact KEEP while naming the dependency.
- The deprecation check and the adoption scan as mechanisms, with the source of ground truth left to the seat.
- Evidence thresholds: below roughly 30 sessions, quantitative claims are unreliable and only qualitative friction counts; cite the pattern, never a raw count.
- The proposal discipline: strongest evidence first, at most three, ASK never apply, and a healthy setup often yields none.
- The output contract, all six parts, including the P0-P2 severities.

One genuinely new rule that only exists because there are now two seats: **a finding about a file both harnesses read is a shared-file finding**, and the seat says so.
`AGENTS.md` is the case that will actually occur, since it is Claude Code's second context file and pi's only one.
A seat that recommends a change there without flagging that the other harness eats it too is how the two drift.

### 3. `cc-staff-reviewer` after the split

Keeps its name, path and subject.
The roughly 70 neutral lines are replaced by a line loading `setup-review-mechanics`, its description points at `/setup-review` rather than `/cc-review`, and `Skill` joins its Claude tool allowlist so the isolated reviewer can load those mechanics.

What stays, because it is the Claude inventory: the changelog refresh, the four-layer precedence chain, the input reading order, the rules semantics with `paths` frontmatter and the 200-line target, the `/insights` and auto-memory stores, the cross-primitive and cross-scope checks, the right-tool table, and the four worked examples.

The file lands somewhere near 145 lines from 214.

### 4. `pi-staff-reviewer`, new

At `roles/ai/files/claude/agents/pi-staff-reviewer.md`, which is where agents live in this repo regardless of harness, since `~/.pi/agent/agents` is a link to the directory `sync` converges.

Frontmatter mirrors its counterpart, dual-keyed so `test_pi_dialect.py` accepts it: `model: opus`, `effort: high`, `thinking: high`.
It deliberately carries **no** `tools:` allowlist.
That key is read by both harnesses and its values are Claude tool names, which is exactly why the security advisor stays Claude-only; a pi seat that carried it would be restricting nothing while reading as restricted.
Read-only is therefore prompt-enforced here, which the agent states in its hard rules.

Its description says it is invoked by `setup-review` under pi and must not be auto-delegated during normal coding, for the same reason its counterpart does, plus one pi-specific reason: because global agents are symlinked both ways, this agent is visible in Claude Code's agent list too.

**Step 0, refresh.** `pi --version`, then the installed package's own changelog and docs under the Homebrew Cellar path, which is what `docs/internals/pi-harness.md` already points at and what the `lastChangelogVersion` and `collapseChangelog` settings keys imply pi ships locally.
A local file is a stronger ground truth than the fetched URL its counterpart uses, and does not fail closed on a network error.
Also in scope for the refresh: the installed versions of the declared packages, since a package is where most of pi's behaviour comes from.

**Scopes.** Global `~/.pi/agent/`, project `.pi/` and `.agents/` from the session cwd walked upward, and never `.claude/`, which pi does not read.

**Inventory, and what each entry is checked for.**

| Path | Checked for |
|---|---|
| `settings.json` | declared packages that nothing references or that a builtin now supersedes; `enabledModels` against actual use; provider and model defaults against cost; no `env` block, so an env recommendation routes to the shell role |
| `SYSTEM.md` | must not exist as a real file; if it does, that is a P0, because it replaces the harness's own prompt |
| `APPEND_SYSTEM.md` | content that has a counterpart in `AGENTS.md`, which is duplication; content that contradicts it, which is worse |
| `AGENTS.md` | shared with Claude Code, so every finding here is tagged shared-file |
| `extensions/*.ts` | type-stripping load failures; a `tool_call` handler whose position matters; a footer replacement that drops `getExtensionStatuses()` |
| `sandbox.json` | derived, so hand-edit drift is the finding and the fix is to regenerate; the four things the derivation cannot carry are stated as known gaps, not proposed as work |
| `mcp.json` | servers configured but never referenced |
| `agents/`, `skills/` | reachability and shadowing, the same cross-scope checks as Claude; plus a skill carrying `allowed-tools:`, `model:` or `effort:`, which pi silently ignores |
| `trust.json` | entries the three derivation differences make misleading, especially a refusal shadowing a grant above it |
| project `.agents/skills` | missing or foreign, which is `checks.pi_skills_unreachable`; remedy is `claude-kit converge --all` |
| environment | `PI_CURSOR_EXPOSE_BUILTIN_TOOLS` unset under `defaultProvider: cursor`, meaning the gates are off |
| `~/.pi/agent/sessions/` | the usage evidence, read through `tokencost --pi`, bucketed by `provider/model` |

**Right tool for the job, pi vocabulary.**

| Use case | Correct pi feature |
|---|---|
| Always-on fact or convention | `AGENTS.md`, flagged shared |
| Behaviour with no counterpart in `AGENTS.md` | `APPEND_SYSTEM.md` |
| Enforcement that must not be skippable | a `tool_call` handler in `guardrails.ts`, never a prompt rule |
| Repeatable procedure | skill, invoked `/skill:<name>` |
| A skill spelled short enough to type | an alias in `skill-aliases.ts` |
| Delegation needing isolated context | agent under `~/.pi/agent/agents/`, dual-keyed |
| Confining what a command may touch | the `sandbox.json` derivation, never a `tools:` allowlist |
| Surfacing state the user cannot otherwise see | an extension footer segment |
| External tool or data source | `mcp.json` |
| Bundling several of the above | a package in `settings.json` |

**Gaps it must name rather than invent.**
pi has no path-scoped rule mechanism, so a convention that only applies to certain files has nowhere conditional to live and the honest recommendation is a skill or nothing.
It has no output style.
It has no per-command sandbox exclusion.
And its gate layer has no ask tier, so a three-tier Claude gate loses its middle one on translation.
The rule is the same one its counterpart already follows for a failed fetch: proceed without inventing a key, flag, or feature.

### 5. Registration and install

| Artifact | Registry | Groups |
|---|---|---|
| `setup-review` | `skill-registry.json`, replacing the `cc-review` entry | `quality`, `review`, `ai`, `global`; depends on `skill-writer` |
| `setup-review-mechanics` | `skill-registry.json`, new | `quality`, `review`, `ai`, `global` |
| `cc-staff-reviewer` | `agent-registry.json`, updated | `global`; depends on `setup-review-mechanics` |
| `pi-staff-reviewer` | `agent-registry.json`, new | `global`; depends on `setup-review-mechanics` |

Nothing in `roles/ai/tasks/main.yml` changes.
`claude-kit sync` derives both directories from the `global` tag, and the two `~/.pi/agent` links already point at them.

### 6. Rename fallout

`cc-review` is named in 17 places.
The substantive ones are `agent-audit/SKILL.md:10-12`, which draws the scope boundary; `review-mechanics/SKILL.md:83`, which lists the apply step as a banned mutator during code review; `docs/internals/code-review-policy.md:18,26`; the `README.md` effort table and `GETTING-STARTED.md`; and `claude-kit`'s catalog example string.

Two are frozen test sets and are the reason this is a decision rather than a find-and-replace.
`test_catalog.py:231-253` pins the effective global skill set, which gains two names and loses one.
`test_pi_dialect.py:326-331` pins which skills may carry frontmatter pi ignores; `cc-review` is in it because of `effort: medium`, so the entry is renamed, and `setup-review-mechanics` joins only if it carries such a key, which by default it should not.

`docs/cc-setup-review-2026-07-25.md` is a dated record of a past run and is left alone.
A historical artifact describing what `/cc-review` printed in July is not made wrong by a later rename.

## Runtime behaviour matrix

| Session | Invocation | Reviewer | Evidence | Apply target |
|---|---|---|---|---|
| Claude Code | `/setup-review` | `cc-staff-reviewer` | `/insights` facets, auto-memory | `roles/ai/files/claude/...` |
| Claude Code, no `/insights` run yet | `/setup-review` | `cc-staff-reviewer` | none; reviewer says so and proceeds config-only | same |
| pi | `/skill:setup-review` | `pi-staff-reviewer` | `~/.pi/agent/sessions/` | `roles/ai/files/pi/...`, plus the shell role for env vars |
| pi, cursor provider, exposure unset | `/skill:setup-review` | `pi-staff-reviewer` | same | same, and the gates-off state is itself a P0 finding |
| Either | `/setup-review pi` | `pi-staff-reviewer` | pi's | pi's |
| Cursor bridge, `PI_SESSION_ID` present | `/skill:setup-review` | `pi-staff-reviewer` | pi's | pi's |

## Alternatives considered

**One harness-aware agent.**
Both harnesses load the same bytes, so a single agent would carry both inventories and both vocabularies into every run, and a pi session would pay for 140 lines of Claude precedence rules it cannot act on.
It would also have to establish which harness it is in from inside an isolated context, where the orchestrator can just read an environment variable and say so in the dispatch.

**Two fully independent pairs, copied.**
The method is roughly a third of the current agent and is the part most likely to be improved over time.
Copying it guarantees the two drift, which is the failure mode this repo already treats as a first-class concern for every file it shares by symlink.

**Keep `cc-review` and add a separate `pi-review` skill.**
The name collides with the installed `pi-review` package, which reviews diffs.
Beyond the collision, two entry points means the user picks the harness by choosing a command, which is a choice the session already knows the answer to.

**Put the shared method in `review-mechanics`.**
That skill is the deferred half of the diff-review policy and is loaded when writing a code review.
Folding setup review into it would put configuration-audit machinery in the context of every diff review, and would tangle two severity vocabularies in one file.

**Ask the user which harness at invocation.**
A round-trip for a question the environment answers deterministically.
The argument remains available for the case where the answer should be overridden.

**Move both to the repo's `blocker/important/nit` vocabulary.**
Deferred rather than rejected; see open questions.

## Testing decisions

The boundary is registration and reachability, not review quality, and it is covered by suites that already exist.

`test_catalog.py` pins the effective global skill set, so both new skills must appear there and `cc-review` must not.
`test_pi_dialect.py` enforces that agents are dual-keyed on `effort`/`thinking`, which `pi-staff-reviewer` must satisfy, and freezes the set of skills carrying frontmatter pi ignores.
The existing `test_agent_dependencies_expand_a_second_level` in `test_catalog.py:256` exercises exactly the shape this design introduces, an agent depending on a skill, so the `setup-review-mechanics` dependency is checked by machinery already written.

No new suite.
A test asserting that a prompt says the right thing is a test of a string, and the repo's existing gates are the ones that catch the failures that actually happen here: an unregistered artifact, a missing link, a drifted key.

## Open questions

None. Implementation retained P0-P2 for harness setup findings, resolves pi's installed documentation dynamically rather than hardcoding a Cellar version, uses `PI_SESSION_ID` with an explicit argument override, and keeps `setup-review-mechanics` global so either reviewer can load it in isolated context.

## Appendix - affected files

Created:
- `roles/ai/files/claude/skills/setup-review/SKILL.md`
- `roles/ai/files/claude/skills/setup-review-mechanics/SKILL.md`
- `roles/ai/files/claude/agents/pi-staff-reviewer.md`

Deleted:
- `roles/ai/files/claude/skills/cc-review/SKILL.md`

Modified:
- `roles/ai/files/claude/agents/cc-staff-reviewer.md`
- `roles/ai/files/claude/skill-registry.json`
- `roles/ai/files/claude/agent-registry.json`
- `roles/ai/files/claude/skills/agent-audit/SKILL.md`
- `roles/ai/files/claude/skills/review-mechanics/SKILL.md`
- `roles/ai/files/claude/README.md`
- `roles/ai/files/claude/GETTING-STARTED.md`
- `roles/ai/files/scripts/claude-kit/README.md`
- `roles/ai/files/scripts/claude-kit/claude_kit/commands/listing.py`
- `roles/ai/files/scripts/claude-kit/tests/test_catalog.py`
- `lib/python/tests/test_pi_dialect.py`
- `docs/internals/code-review-policy.md`
- `docs/internals/pi-harness.md`

Read:
- `roles/ai/tasks/main.yml`
- `roles/ai/files/pi/settings.json`
- `roles/ai/files/pi/APPEND_SYSTEM.md`
- `roles/ai/files/pi/extensions/*.ts`
- `roles/shell/files/fish/conf.d/exports.fish`

Left alone:
- `docs/cc-setup-review-2026-07-25.md`
- `docs/plans/2026-08-17-mossy-dazzling-planet.md`
- `.claude/state/research/2026-08-04-research-global-code-review-policy.md`
