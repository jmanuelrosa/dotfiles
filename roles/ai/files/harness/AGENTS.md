# Global instructions

The agent-neutral core: tooling, code standards, git, context hygiene and skill precedence.
This file is the canonical one and every agent reads it under the name it expects, so it names skills and tools by concept rather than the spelling any one harness gives them (`commit` reads as `/commit` in Claude Code and `/skill:commit` in Pi).
Claude-only mechanics (settings, hooks, plan mode, sandbox) live in Claude Code's own rules directory, which is the one part of this payload no other harness is given.

## Tools & CLIs

CLI-first for these domains, never WebFetch or MCP for them.
If a CLI is missing or auth-broken, say so; don't silently fall back.

| Domain | CLI |
|---|---|
| Jira | `acli` |
| GitHub | `gh` |
| GitLab | `glab` |
| Sentry | `sentry` |
| Bruno API tests | `bru-cli` |
| Notion | `ntn` |
| Library / framework / SDK / API / CLI / cloud service docs | `bunx ctx7` |

- IMPORTANT: any question about a library, framework, SDK, API, CLI tool, or cloud service is a docs question. Training data is stale, so fetch current docs BEFORE answering: `bunx ctx7 library <name> "<q>"`, then `bunx ctx7 docs <id> "<q>"` (free anonymous tier; `npx -y ctx7` if bun is missing). Pick the id by benchmark score among high-reputation results, preferring a `/websites/...` vendor docs site over a bare repo, since the repo usually carries a fraction of the snippets. Never the Context7 MCP server, and never WebFetch as the first move. If ctx7 returns no usable match, say so, then fall back to WebSearch/WebFetch.
- ctx7 is exempt from the bash sandbox only as a **leading token** (`sandbox.excludedCommands`), the same rule `acli` follows: `cd x && bunx ctx7 ...`, a pipe into it, or a ctx7 call spawned from inside a script is confined again, and a confined ctx7 dies with a causeless `✖ fetch failed`. Under pi there is no per-command exclusion at all. When ctx7 fails to reach the API rather than returning no match, name the failure and fall back to WebSearch/WebFetch, never to training data.
- Three things take precedence. The domain CLIs above are for *doing* (fetch the ticket, list the PRs) while ctx7 is for *how it works*, so "list my open PRs" is `gh` and "what does `gh pr list --search` accept" is a docs question. For a CLI installed on this machine, `cmd --help` / `man` beats ctx7 on flags and syntax. Claude Code, the Agent SDK and the Anthropic API belong to the `claude-api` skill, not to ctx7.
- `glab` has multiple authenticated hosts: inside a repo it auto-selects; repo-agnostic `glab api` calls must iterate every host (recipes live in the `pr` skill and the `weekly-recap` script).
- JS package manager: match the lockfile. No lockfile but the README names one, follow the README.

## Code standards

- Default to zero comments; prefer explicit names. A comment must earn its place by explaining a non-obvious WHY, never WHAT. Same bar for JSDoc.
- Never reference issue/PR/ticket/ADR numbers in code comments; that context belongs in branch names, PR descriptions, and git blame.
- No hardcoded values (magic numbers, URLs, tokens, paths); derive them from data or the environment at runtime.
- Never use em or en dashes in chat. Use a regular hyphen, comma, colon, or parentheses. (`em-dash-gate.sh` catches them in files; conversation is the surface no hook sees.)
- Never hard-wrap prose or Markdown to a fixed column width. Write one sentence per line (semantic line breaks) and let the editor soft-wrap. Applies to chat, docs, skills, agents, commit and PR bodies. Match the file you are editing rather than reflowing existing prose to a different wrap.
- Match the length of a written document to what the task needs: cover the substance, and do not pad with filler sections, redundant summaries, or boilerplate.
- Prefer free, zero-key, zero-install integrations (anonymous tiers, `bunx`) over API-key or brew-based setups.
- ADRs match the shape and numbering of the repo's existing `docs/adr/`, over any skill's own format. Never edit an accepted ADR; supersede it with a new one.
- Planning documents go in the repo's `docs/plans/`, except where a skill names its own path.

## Git

- Commits and pushes go through the `commit` and `pr` skills, never a raw `git commit` or `git push`.
- Branch names follow `<type>/<slug>` or `<type>/<TICKET>-<slug>` using the Conventional Branch set (`feature`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`, `style`, `revert`); create with `git switch -c`, never `git checkout -b`. `<TICKET>` is a Jira key (`PROJ-123`) or a GitHub issue (`gh-456`); `s-task <ref>` scaffolds either from the issue itself, auto-detecting the provider. If an existing branch doesn't follow this convention, don't derive commit types or PR titles from its name: stop and ask the user.

## Context hygiene

Everything read into the main thread is paid for again on every later turn.
The cost of a session is `context size × number of requests`, so it is the area under the context-growth curve rather than the number of things asked for.
A file read at turn 10 is still being re-read at turn 180.

This is a bar for how to work, not a licence to do less.
Skipping work to save tokens is the wrong trade every time; the point is to stop paying repeatedly for the same bytes.

### Keep reading out of the main thread

- **Send broad searching to a subagent.** A read-only search agent for locating code across unknown files (`Explore` in Claude Code), a general-purpose one for a multi-step hunt. A subagent's reading is discarded when it returns, so the main thread pays only for the conclusion.
- **Read narrowly when you already know the target.** Use `offset` and `limit` for the part you need instead of pulling a whole large file.
- **Never re-read a file to confirm an edit landed.** The edit and write tools fail loudly, and the harness tracks file state.
- **Do not let a command dump its output into the context.** Filter, slice or count at the source (`| head`, `| wc -l`, a `grep` pattern, a `--json` flag with a projection) rather than printing everything and reading past it.
- **Read a file once.** If it is already in context, work from what is there.

### Say something before the session gets expensive

Past roughly 35% of the context window, say so and offer a handoff rather than quietly continuing.
Running a session to the ceiling is what makes every remaining turn cost the most it ever will, and the work does not need the history to survive a topic change.

Offer, in this order: finish the current thread, write the state down (the `handoff` skill exists for this), then start a fresh session (`/clear` in Claude Code, `/new` in Pi).
Never clear or compact on your own initiative; the decision is the user's.

### When the task is itself about cost

Measure before recommending, and report what the measurement says even when it kills the recommendation.
An artifact set is not waste because it is large; count invocations first, since agents and skills reached through a subagent tool never appear as slash commands.
State the size of a saving in tokens, so a change that recovers under 1k per session is visibly not worth the churn it causes.

Where the usage records live, how to bucket subagent spend, and a worked example of an optimisation that measurement rejected are in `docs/internals/context-hygiene.md`.

## Skill precedence

What wins when an installed skill contradicts the agent invoking it, or a checklist that agent is gated on.

A skill is expertise on loan.
It was written for a different host, against a different project, with no knowledge of the boundaries the caller agreed to.
The reasoning, the live contradictions this exists for, and the worked overrides are in `docs/internals/skill-precedence.md`.

### Tier 1, absolute: no skill grants permission

An ask-first boundary exists to route a decision to a human, and a skill sitting in the context window is not a human who approved it.
When a skill prescribes any of these, the result is a `needs-decision` naming the skill and the recommendation, **never an edit**:

- A dependency: a component, animation or icon library, an externally hosted or licensed web font.
- A new step in a system scale: spacing, type, color, motion, breakpoint, z-index.
- A brand-surface change: palette, typefaces, logo treatment.
- A raw value where the project has a token for it, or a whole parallel token system beside an existing one.
- A breaking change to a shared or published API.

This tier does not bend for confidence, for how well-regarded the skill is, or for how much better the suggestion is than what the project has.
Being right is what the recommendation is for.

One narrowing, and it is about scope rather than authority: where no prior decision exists to protect (no design system, no recorded direction, no tokens), the scale, palette and typeface gates have nothing to guard and inventing them is the brief.
Recording the choice is what arms the gate for the next brief.
The dependency and breaking-change gates never relax.

### Tier 2, defeasible: the reference is the default

Technique conflicts are not permission conflicts, and a blanket refusal here makes the agent worse rather than safer.

A reference's `Check:` is the default position, and a skill may override it **by naming the check it is trading against and satisfying it another way**, in the report.
Not by ignoring it, and not by being more specific about the technique.
An override that names no check is not an override, it is the skill winning by default, which is what this file exists to prevent.

### Output contracts are never a skill's to set

A skill may tell you how to think.
It does not get to set the shape of your final message.

A canned first-invocation greeting, a mandated review format, or an instruction to stop and await user input is void inside an agent that has its own completion-report contract, and the agent's contract wins with no exception.
A delegated agent has no user to await, so obeying that last one returns a greeting where the caller expected work.
`emil-design-eng` carries both today: read it for its motion technique, ignore its first-invocation and review-format mandates entirely.

### Reporting

A precedence call is a decision, so it goes in the report's decisions section in one line: what the skill wanted, which tier applied, and what you did.
Silent resolution is the failure mode.
A reader who cannot see that a conflict occurred cannot tell a considered override from an agent that never opened the checklist.
