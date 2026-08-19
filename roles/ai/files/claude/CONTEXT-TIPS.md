# Keeping the context small

Named to match [GETTING-STARTED.md](GETTING-STARTED.md) beside it.
That file is about getting work started; this one is about not paying three times for it.

A session's cost is `context size × number of turns`, because every turn re-reads the whole conversation.
A file read at turn 10 is still being re-read at turn 180.
So the expensive session is not the one that does the most, it is the one that carries the most for the longest.

Measured here over one week: 94% of all tokens moved were cache reads, average 162k carried per request, median session 184 turns peaking at 186k.

## The five habits

1. **`/clear` when the topic changes.** This is the single biggest lever and it costs nothing. The same work split across four fresh sessions costs roughly a third of one 184-turn session.
2. **Watch the statusline meter and act at 60%,** not at 95%. It already shows `context [▓▓░░░░░░] 100k (19%)`.
3. **`/handoff` before you clear** when the thread has state worth keeping. Writing it down is cheaper than carrying it.
4. **Ask for a subagent on broad searches.** "Use Explore to find X" keeps the reading out of your session; a normal search leaves every file in the context for the rest of the session.
5. **Run on Sonnet, switch to Opus for the hard parts.** `/model opus` when the problem is design or a nasty bug, back down after. Opus was 73% of one week's weighted spend.

## What you notice, and what to do about it

| What you notice | What to do |
|---|---|
| The meter is past 60% and the task is basically done | `/handoff`, then `/clear` |
| The meter is past 60% and the task is not done | `/handoff` and `/clear` anyway, then paste the handoff back |
| A new question that has nothing to do with the last one | `/clear` first, always |
| It just read fifteen files to answer one question | Ask for `Explore` next time |
| It is re-reading a file it already edited | Say so; it should not, and the rule now says it should not |
| Answers are getting vague late in a long session | That is the context filling, not the model. Clear and restate |
| A big repo where every session starts heavy | Check the repo's `CLAUDE.md` size; over about 10 KB it should be routing to `docs/`, not holding everything |

`/compact` is not `/clear`. Compaction rewrites the history into a summary and then keeps going, so it costs a full read plus a summarisation call and leaves you back near the ceiling. Prefer a handoff and a clear.

## What is not worth optimising

Measured, so this settles it rather than inviting another round:

- **The global skill set is about 2.0k tokens** of frontmatter in total, and the never-invoked half of it is about 815 tokens. Retagging it to save that is churn on a carefully designed set for under 1% of a session.
- **A seat plugin costs about 265 tokens.** Pruning four unused seats from a project saves roughly 1k. Do it when the seats are obviously wrong for the stack, not as an optimisation.
- **Skills you never type are not necessarily dead.** The staff-engineer seats are reached through the `Agent` tool, not through `/`, and qa, frontend and platform ran 23, 22 and 18 times in a week without appearing as commands once.

The thing that was worth doing, for scale: this repo's `CLAUDE.md` went from 24.7k tokens to 2.5k by moving deep rationale into `docs/internals/` behind a routing table. That is one change worth more than every artifact prune combined.

## Things that cost you nothing to fix

- **Disconnect unused claude.ai connectors.** One that was never signed into still publishes its `authenticate` tools and its instruction block, and around 30 were live here. Managed at claude.ai, not in this repo.
- **Leave `ENABLE_TOOL_SEARCH` set** in [settings.json](settings.json). It keeps MCP tool schemas out of the prompt until something needs them.

## Checking your own usage

`/usage` shows the allowance. For where it actually went, the per-request records are in `~/.claude/projects/*/*.jsonl`, one JSON object per line with `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` and `output_tokens` alongside a model and a timestamp. Group by day, model and project and the answer falls out.

The full reasoning and the numbers behind all of the above are in `docs/internals/context-hygiene.md` in this repo.
The always-on version both harnesses follow is the **Context hygiene** section of [AGENTS.md](AGENTS.md), which Claude Code loads as `~/.claude/CLAUDE.md` and pi as `~/.pi/agent/AGENTS.md`.
