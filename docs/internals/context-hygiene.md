# Context hygiene

How to keep a Claude Code session cheap without giving up capability, and how to find out where the spend actually went.
Written after a week that consumed 35% of the allowance in a few days.
The numbers below are the Aug 11-17 2026 measurement, kept so a later reading can tell drift from noise.

## The one thing to understand

Cost is `context size × number of requests`, not the number of things you ask for.

Every request re-reads the whole conversation, so a long session pays for its own history on every turn.
That makes the cost of a session the **area under its context-growth curve**, and it is why the same work costs three to four times more in one 184-turn session than in four fresh ones.

Measured baseline:

| Metric | Value |
|---|---|
| Requests in the week | 2,580 |
| Cache reads | 395M tokens |
| Cache writes | 22M tokens |
| Output | 2.7M tokens |
| Average context per request | 162k |
| Median session | 184 turns, starts 62k, peaks 186k |
| Weighted model mix | Opus 73%, Fable 15%, Sonnet 11% |

Cache reads are 94% of the tokens moved.
Optimising anything else first is optimising the wrong term.

## Session hygiene, the largest lever

This costs nothing and needs no configuration.
It is worth more than every artifact change combined.

- **`/clear` between unrelated tasks.** The context does not need to survive a topic change, and keeping it is what turns a cheap session into an expensive one.
- **Treat 35% context as the wrap-up point**, not 95%. The statusline already renders the meter (`context [▓▓░░░░░░] 100k (19%)`), and the `context-nudge.sh` hook fires at the same threshold so the number is a decision point rather than decoration; lowered from an initial 60% once it was clear that was already 580k tokens on a 967k window before anyone was told.
- **Use the `handoff` skill to carry state across a `/clear`**, rather than avoiding the clear in order to keep the state.
- **Send searching to the `Explore` subagent** instead of reading files into the main context. A subagent's reading is discarded when it returns; a `Read` in the main thread is re-read on every subsequent turn.
- **Do not re-read a file you just edited.** The edit would have failed loudly if it had not applied.

## Keep the per-turn baseline small

Anything loaded at session start is paid for on every turn of that session.

- **`CLAUDE.md` is the expensive one**, because it loads in full on every turn and never gets smaller on its own. Keep it to the commands, the architecture and the conventions, and route deep design rationale to `docs/internals/` files opened only when working there. This repo's went from 91.5 KB to 9.2 KB that way, saving roughly 22k tokens per turn across three checkouts.
- **A routing table beats an index.** Name the file and the trigger for opening it, so a turn that does not touch a subsystem never pays for its documentation.
- **Prose that is a design record moves verbatim.** Relocating and shortening are separate decisions; mixing them loses the record while claiming to save tokens.

## Model choice

- **Opus weighs far more against the weekly allowance than Sonnet**, so it belongs on hard design work rather than on every turn. Default to `sonnet` in `settings.json` and reach for `/model opus` deliberately.
- **`/model` writes the session default back to `settings.json`**, which is a symlink into this repo, so reaching for opus in one session silently reverts the committed default and leaves the repo dirty. Check `git diff` on that file before committing, and treat an unexplained `"model": "opus"` there as a leftover rather than a decision.
- **Seat agents pin `model` in their own frontmatter**, so lowering the session default does nothing at all on the delegated path. Every seat is pinned to opus by design (see [seat plugins](seat-plugins.md)), which is what made delegated work 99.6% opus; the fleet-wide session default and `effortLevel` are where the main-thread saving has to come from instead.
- **Output tokens are the priciest class**, so `effortLevel` and always-on thinking show up in the bill even though they generate no context. Weight it by where the tokens actually are: output is 14.8% of main-thread cost but only 5.4% of subagent cost, so lowering effort on a fleet of seats buys far less than the file count suggests.

## Measure before pruning, and accept the answer

The point of measuring is to be told you were wrong.

- **Read the real usage records** in `~/.claude/projects/*/*.jsonl`. Each has `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` and `output_tokens` with a model and a timestamp, which is enough to break a week down by day, model and project.
- **Count invocations before removing anything.** Skills and agents that look like dead weight may be load-bearing: the staff-engineer seats had not been invoked through `/`, yet qa ran 23 times, frontend 22 and platform 18 through the `Agent` tool.
- **Some optimisations are not worth their churn, and measuring is how you learn which.** The whole global skill set is about 2.0k tokens of frontmatter and the never-invoked half is about 815 tokens; a seat plugin is about 265. Retagging a deliberately designed artifact set to recover under 1k tokens per session is a bad trade, and it looked like a good one until it was measured.
- **Subagent usage is recorded, in a tree that is easy to miss.** It is not in `~/.claude/tasks/` and it is not a sidechain record in the session transcript, which is how a measurement here once reported subagents as 0.29% of spend when they were half of it. Each one is its own file at `~/.claude/projects/<slug>/<session-id>/subagents/agent-<id>.jsonl`, beside an `agent-<id>.meta.json` stating `agentType`, `model`, `taskKind`, `teamName` and `spawnDepth`. Bucket by what the sidecar says, never by a slug parsed out of the filename. The layout is undocumented, so read it defensively and fall back rather than fail.
- **Weight the classes before ranking anything.** Cache reads are ~95% of tokens moved and bill at ~0.1x, so raw totals rank the wrong things first. At input 1x / cache_creation 1.25x / cache_read 0.1x / output 5x, a fortnight here split main thread 50.1%, teammates 36.6%, plain `Task` dispatches 13.3%, and nested dispatches 1.8%. `tokencost` does this arithmetic, including the sidecar join.
- **`taskKind: in_process_teammate` is worth separating from a plain dispatch.** Teammates were the single largest delegated bucket and are turned off by a different decision than a seat's model pin, so summing them into one agent row hides which lever to pull.
- **A measurement that only walks the top level is not a measurement.** Nested dispatches (`spawnDepth` 2) came to 1.8%, which is the number that argued against restricting the `Agent` tool on the seats. Getting that wrong in either direction changes what you cut.

## Things that cost tokens for nothing

- **Unauthenticated MCP connectors.** A connector that was never signed into still publishes its `authenticate` and `complete_authentication` tools, and its instruction block is not deferred. Around 30 of them were live here. They are managed at claude.ai, not in this repo.
- **`ENABLE_TOOL_SEARCH`** keeps MCP tool schemas out of the prompt until needed, so it should stay set. It defers the schemas, not the names or the server instructions, which is why disconnecting an unused connector still pays.

## Before moving prose between files

Check what reads it.
Tests that scan a file by path go quietly blind when its content moves.
`lib/python/tests/test_tv_cables.py` scans a fixed tuple of trees for retired fish function names, so `docs/internals` had to join it or the guard would have kept passing while covering less.
Rewrite repo-root-relative links for their new depth, and turn in-file anchors into cross-file links.
