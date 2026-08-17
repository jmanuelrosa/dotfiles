# Context hygiene

What to do about the fact that everything read into the main thread is paid for again on every later turn.

The cost of a session is `context size × number of requests`, so it is the area under the context-growth curve rather than the number of things asked for.
A file read at turn 10 is still being re-read at turn 180.
Measured over one week here: 94% of all tokens moved were cache reads, and the median session carried 162k tokens per request.

This is a bar for how to work, not a licence to do less.
Skipping work to save tokens is the wrong trade every time; the point is to stop paying repeatedly for the same bytes.

## Keep reading out of the main thread

- **Send broad searching to a subagent.** `Explore` for locating code across unknown files, `general-purpose` for a multi-step hunt. A subagent's reading is discarded when it returns, so the main thread pays only for the conclusion.
- **Read narrowly when you already know the target.** Use `offset` and `limit` for the part you need instead of pulling a whole large file.
- **Never re-read a file to confirm an edit landed.** `Edit` and `Write` fail loudly, and the harness tracks file state.
- **Do not let a command dump its output into the context.** Filter, slice or count at the source (`| head`, `| wc -l`, a `grep` pattern, a `--json` flag with a projection) rather than printing everything and reading past it.
- **Read a file once.** If it is already in context, work from what is there.

## Say something before the session gets expensive

Past roughly 35% of the context window, say so and offer a handoff rather than quietly continuing.
Running a session to the ceiling is what makes every remaining turn cost the most it ever will, and the work does not need the history to survive a topic change.

Offer, in this order: finish the current thread, write the state down (the `handoff` skill exists for this), then `/clear`.
Never clear or compact on your own initiative; the decision is the user's.

## When the task is itself about cost

Measure before recommending, and report what the measurement says even when it kills the recommendation.
Real per-request usage lives in `~/.claude/projects/*/*.jsonl`, with `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` and `output_tokens` per record.
An artifact set is not waste because it is large; count invocations first, since agents and skills reached through the `Agent` tool never appear as `/` commands.
State the size of a saving in tokens, so a change that recovers under 1k per session is visibly not worth the churn it causes.

The full reasoning, the worked example of an optimisation that measurement rejected, and the numbers this rule is derived from are in `docs/internals/context-hygiene.md` in the dotfiles repo.
