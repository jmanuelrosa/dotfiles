# cc-loop

## Why it exists

Claude Code's `/loop` repeats a prompt on an interval or lets the model pace itself, and pi has no equivalent.
`/cc-loop` ports it to pi as closely as pi's extension API allows, under a `cc-` prefix so it never collides with a Claude built-in or a future pi command.
Every rule and constant is copied from the `/loop` prompt, the `ScheduleWakeup` tool, and the cron scheduler compiled into the Claude Code binary (2.1.293), not reconstructed from memory.

## What it does

`index.ts` registers `/cc-loop` and parses its input in Claude's order: a leading `^\d+[smhd]$` token is the interval, otherwise a trailing `every N<unit>` or `every N minutes` clause is, otherwise there is no interval.

- **Fixed mode** (an interval and a prompt) registers a recurring job, confirms the job id, cron expression, cadence and expiry, then runs the prompt immediately.
  The interval becomes a 5-field cron expression by Claude's table, rounding to the nearest interval cron can express evenly and saying so.
  Each tick resends the prompt through `pi.sendUserMessage`; a slash prompt is expanded, and `/name` becomes `/skill:name` when only a skill has that name.
  Ticks only fire while the agent is idle, collapse when several land during one turn, and carry Claude's deterministic per-job jitter (up to 10% of the period, at most 15 minutes).
  A 5-minute cron fires 15 seconds before each period ends instead, as Claude's scheduler does to stay inside a 5-minute prompt cache, so it drifts off the `:05` marks.
  Jobs auto-expire after 7 days: they fire one final time, then are deleted. Up to 50 jobs can run per session.
- **Dynamic mode** (a prompt, no interval) shows Claude's self-pacing instructions and runs the prompt now.
  The model re-arms with the `schedule_wakeup` tool, which has `ScheduleWakeup`'s shape (`delaySeconds`, `reason`, `prompt`, `noop`, `stop`), its error messages, and its clamp to [60, 3600] seconds rounded up to the next whole minute.
  A wakeup re-enters `/cc-loop` with the same input. One wakeup is pending at a time, and a new one supersedes the old.
  When a tick ends without a re-arm or a stop, Claude's keepalive arms one 1200-second fallback; a second miss ends the loop. Any user abort cancels the pending wakeup, as Claude's does, even when the aborted turn was not a loop tick. A dynamic chain ages out after 7 days.
- **No prompt** reads the first non-empty task file among `.pi/loop.md`, `~/.pi/agent/loop.md`, `.claude/loop.md` and `~/.claude/loop.md`, so one file serves both harnesses, truncated at Claude's 25000 characters.
  Without a file it uses Claude's autonomous-loop preamble. An empty input paces dynamically; an interval alone (`/cc-loop 5m`, `/cc-loop every 5 minutes`) schedules a fixed job, exactly as Claude's command does before its prompt is ever consulted.
  The `<<loop.md>>`, `<<loop.md-dynamic>>`, `<<autonomous-loop>>` and `<<autonomous-loop-dynamic>>` sentinels resolve at fire time to the full instructions on first delivery (or after loop.md changes) and to Claude's short reminder afterwards.
  The immediate run counts as that first delivery, so the first tick sends the reminder rather than repeating the instructions it just inlined.
- `/cc-loop list` and `/cc-loop stop <id>` mirror `CronList` and `CronDelete`, including their output lines, and cover a pending wakeup as well as recurring jobs.
  The model gets the same operations as the `cron_list` and `cron_delete` tools.

## Runtime surface

The extension registers the `/cc-loop` command and the `schedule_wakeup`, `cron_list` and `cron_delete` tools.
The tools are registered inactive, activated when a loop starts, and deactivated when the last job, wakeup and in-flight tick are gone, so their schemas only ride along while a loop is live.
It listens to `session_start`, `agent_start`, `agent_before_settle`, `agent_settled` and `session_shutdown`.
Live jobs, the pending wakeup and the dynamic chains still within reach of a wakeup are mirrored with `pi.appendEntry` under the `cc-loop-state` custom type, so resuming a session restores them; jobs past their expiry and wakeups already due are dropped.
Every timer is cleared on `session_shutdown`.
Confirmations are `cc-loop` custom messages, displayed and visible to the model the way Claude's `CronCreate` result is.

## Gaps against Claude Code

- Claude's background-event branch (arming a `Monitor` whose `<task-notification>` wakes the loop) has no pi equivalent, so the instructions and the tool description tell the model to poll at a cadence matched to the state it waits on.
- The cloud-schedule offer for intervals of an hour or more and the `/schedule` hand-off are not ported: pi has no cloud routines.
- Push notifications on stop, brief mode, and terminal collapsing of consecutive `noop: true` ticks have no pi surface. `noop` is still required, so the model's contract is unchanged.
- Jobs are session-only. Claude's `durable: true` (`.claude/scheduled_tasks.json`) is not ported; the session entry restores jobs on resume instead.
- Claude prints `CronList` rows with an em dash; house style forbids it, so rows use a hyphen.
  A pending wakeup is listed as `Once at <time>` rather than Claude's `Every day at <time> (one-shot)`, which reads as a daily job.
- A tick whose message never starts a turn (an input handler swallowed it, or the model errored) releases the queue after 5 seconds so later ticks still fire.
- Print and JSON modes (`pi -p`) are single-shot: `/cc-loop` waits for its immediate run so the output is complete, and the loop ends with the process. Use the TUI or RPC mode for loops that tick.
- `/cc-loop stop <word>` is a subcommand, so a dynamic prompt of exactly two words starting with `stop` needs rephrasing.

## Verification

Parsing, cron conversion, clamping, loop.md resolution, ticks, expiry, keepalives, abort, list, stop and resume are covered by `lib/python/tests/test_pi_cc_loop.py`, which drives the extension against a fake pi and a fake clock.
