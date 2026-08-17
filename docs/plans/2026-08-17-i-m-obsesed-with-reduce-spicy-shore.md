# Cut weekly Claude Code token spend

## Context

The weekly allowance hit 43% with three days left in the billing week.
The usage report blamed "subagent-heavy sessions" (99%), requests above 150k context (72%), and sessions active 8+ hours (67%), naming `database:database-staff-engineer` (6%) and `design:design-staff-engineer` (5%) as top agents.

A first measurement pass scanned only `~/.claude/projects/*/*.jsonl` and concluded subagents were 0.29% of spend.
That was wrong by more than two orders of magnitude.
Subagent transcripts live in a tree that pass never walked:

```
~/.claude/projects/<slug>/<session-id>/subagents/agent-<id>.jsonl
~/.claude/projects/<slug>/<session-id>/subagents/agent-<id>.meta.json
```

The sidecar carries `agentType`, `model`, `taskKind`, `teamName`, `spawnDepth` and `toolUseId`, so per-agent spend is fully attributable today, retroactively, with no instrumentation.
This layout is undocumented and is not a stability contract, so anything built on it must degrade quietly when `subagents/` is absent.

Re-measured over 14 days (2026-08-03 to 08-17), deduped by `message.id`, weighted at input 1x / cache_creation 1.25x / cache_read 0.1x / output 5x because raw counts overweight cache reads:

| Bucket | Invocations | Requests | Weighted share |
|---|---:|---:|---:|
| Main thread | - | 7,557 | 50.1% |
| `in_process_teammate` (agent teams) | 159 | 6,437 | **36.6%** |
| Plain `Task` dispatches | 109 | 2,778 | 13.3% |
| of which nested (`spawnDepth` 2) | 21 | 493 | 1.8% |

Four findings drive the work below.

**Delegated work is 99.6% opus.** Only 0.3% of subagent tokens were sonnet. 112 teammate invocations carry an explicit `model: opus` from agent frontmatter (32.0% of all spend on their own); 42 more inherit `claude-opus-5` from the session default; 109 inherit with no pin recorded. So two edits, the seat frontmatter and `settings.json`, reach essentially all of it.

**Agent teams are the largest single bucket.** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` is enabled, and teammates issue nearly as many requests as the main thread across 21 team-only sessions in 14 days.

**Nested fan-out is not a problem.** `spawnDepth` 2 is 1.8% across 21 invocations, so the unrestricted `Agent` tool on the seats stays as it is. This workstream is dropped on the measurement.

**Context growth is not confined to the main thread.** Every teammate is a mini-session averaging 40 requests at ~127k cache_read each. On the main thread, all 71 sessions with 20+ requests grew, median 80.6k in the first fifth to 186.7k in the last fifth. Subagent cost is 55% cache_read and 39% cache_creation; output is only 5.4%. On the main thread output is 14.8%.

`docs/internals/context-hygiene.md:50` already prescribes a sonnet session default; `settings.json:199` still says `"model": "opus"`. The argument was written down and never applied.

## Decisions

| Question | Decision | Evidence |
|---|---|---|
| Session default model | `opus` to `sonnet` | Main thread is 50.1% of spend, 90.7% opus |
| Seat model pins | ~~Default to `sonnet`; keep `opus` on architect, security, database~~ Superseded below: kept `opus` fleet-wide | Delegated work is 99.6% opus |
| Agent teams | Keep the capability; teammates inherit whatever the seat pin says | 36.6% of spend |
| Main-thread effort | `effortLevel` `high` to `medium` | Output is 14.8% of main-thread cost |
| Seat effort | Leave `xhigh` alone | Output is 5.4% of subagent cost; ~2% saving across 14 files |
| Session hygiene | Statusline threshold marker plus a `UserPromptSubmit` nudge | 100% of long sessions grew, 49% of requests read >150k |
| Nested fan-out | No change | Measured at 1.8% |

### Superseded: seat model pins reverted to opus

Applied, then reverted the same day. All 15 flipped agent files (`agents/architect.md` was never flipped, so 13 plugin seats plus `ux-shaper.md` and `cc-staff-reviewer.md`) were set back to `model: opus`.
The decision: hold implementation depth on the delegated path and take the whole saving from the main thread instead (session default and `effortLevel`, section 1 below).
The 99.6%-opus and 36.6%-teammate figures above are still accurate measurements; they no longer describe an open question, since the pin is staying put on the measurement available today.
`docs/internals/seat-plugins.md:6` and `docs/internals/context-hygiene.md:52` were corrected to match: no seat-tiering claim survives, and the "which three seats" phrasing was removed since nothing differs by seat now.
Section 2 and section 3 below describe work that was done and then undone; they are left as the record of what was tried.

## Work

### 1. Model and effort defaults

`roles/ai/files/claude/settings.json`:

- `"model": "opus"` to `"sonnet"` (line 199). `fallbackModel` and `availableModels` already list sonnet, so no other edit.
- `"effortLevel": "high"` to `"medium"` (line 383).
- Leave `"alwaysThinkingEnabled": true` (line 382). Thinking is what makes the opus-to-sonnet drop survivable on the main thread; flipping it is the next step only if the following week's number stays high.

### 2. Seat model pins

Flip `model: opus` to `model: sonnet` in the frontmatter of 15 agent files.

Keep `opus` on exactly three, which the measurement earns: `agents/architect.md` (3.5% of all spend across 5 invocations, the single largest agent type), `plugins/security/agents/security-staff-engineer.md`, `plugins/database/agents/database-staff-engineer.md`.

Flip the other 12 seats under `roles/ai/files/claude/plugins/<seat>/agents/<seat>-staff-engineer.md`: analytics, backend, cloud, data, design, desktop, dx, frontend, gtm, mobile, platform, qa, sre.

Also flip `roles/ai/files/claude/agents/ux-shaper.md` and `roles/ai/files/claude/agents/cc-staff-reviewer.md`.
Neither was named in the decision; both are spec/review agents rather than deep implementers, so they take the default. Override at review time if either feels degraded.

Leave every `effort: xhigh` untouched.

### 3. Record the superseding rationale

`docs/internals/seat-plugins.md:6` currently justifies the blanket `model: opus` pin as "a deliberate refusal to follow a `/model fable` session, so the cost of a delegated implementation stays predictable".
That reasoning is now overturned by measurement and must be replaced in place, naming the three seats that keep the pin and why.
Do not leave the old sentence standing beside the new behaviour.

### 4. Statusline threshold marker

`roles/ai/files/claude/statusline.sh` already renders the meter: `context_segment` (lines 75-95) reads `data["context_window"]` and draws an 8-cell `gradient_bar` (line 56) plus a percentage.
This is a modification, not an addition.

Add a visible threshold at the 60% wrap-up point named in `context-hygiene.md:34`, so the number stops being ambient and starts being a prompt.
Use `context_window.used_percentage` directly rather than recomputing; note it is input-only (`input + cache_creation + cache_read`, excluding output), and that `current_usage`, `used_percentage` and `remaining_percentage` are all `null` before the first API call and again after `/compact`, so the existing `// 0`-style fallbacks must cover the new branch too.

The file hand-rolls its own ANSI constants (lines 21-22, `rgb()` at 27) and does not use `dotkit.ui`; match that, since a statusline emits a status line rather than CLI output.

### 5. Context nudge hook

New `roles/ai/files/claude/hooks/context-nudge.sh`, bound to `UserPromptSubmit`.

That event is the right host: it fires once per turn and is the only frequent event that can address both the user and the model in one payload.
No hook receives `context_window`, so the script derives usage from the last assistant record's `usage` in `transcript_path`, applying the same input-only formula.
Budget for a 30-second timeout, lower than the default.

Output shape, above the threshold:

- `systemMessage` for the user. `skill-recap.sh:9-17` documents that this is shown to the user and **not** added to the model's context, so it costs zero tokens and is the default vehicle.
- `hookSpecificOutput.additionalContext` for the model, only when crossing each 10% band above 60%, so the reminder is not re-paid every turn. It must be nested inside `hookSpecificOutput`; at the top level it is silently ignored.

Track the last-announced band per `session_id` in a tempdir JSON file, following the statusline's cache precedent (`statusline.sh:149-188`: `tempfile.gettempdir()`, `json.load`/`json.dump`, `except OSError: pass`).

Match the hook conventions exactly, since all six existing hooks share them: `#!/usr/bin/env python3` with a `.sh` name, `# vim: ft=python`, the comment explaining why the extension lies, a docstring with an explicit fail-open paragraph, stdlib only, `json.load(sys.stdin)` inside a bare `try/except`, and `isinstance(data, dict)` before use.
Never block: this hook is advisory, so it always exits 0.

Register it in `settings.json` under a new `UserPromptSubmit` event with `"timeout": 10`.
No Ansible change is needed: `roles/ai/tasks/main.yml:86-93` globs `files/claude/hooks/*`, and `fileglob` filters through `isfile` so `hooks/tests/` stays out.

Verify the stdin key for the prompt text by logging raw stdin once; docs give `user_prompt`, `user_input` and `prompt` inconsistently. The hook does not need the prompt text, so prefer not reading it at all.

Tests go in `roles/ai/files/claude/hooks/tests/test_context_nudge.py`, following `test_plan_date_stamp.py`: `HOOK = Path(__file__).resolve().parents[1] / "context-nudge.sh"`, a fixture that runs it via `subprocess` against a fabricated transcript in `tmp_path`, and assertions on the JSON contract rather than the wording.
That root is already in `pytest.ini`, so no edit there.
`lib/python/tests/test_suites.py` requires the module basename to be unique across all suites.

### 6. Make the measurement repeatable

`roles/ai/files/scripts/tokencost/tokencost` currently reads only `~/.claude/projects/<slug>/*.jsonl` and buckets by `attributionSkill`, which is exactly the blind spot that produced the 0.29% error.

Extend it to walk `<slug>/<session-id>/subagents/agent-*.jsonl`, join each file to its `.meta.json`, and report by `agentType`, `taskKind` and `teamName` alongside the existing skill buckets.
Dedupe by `message.id` before summing: Claude Code writes one record per content block repeating the same `usage`, which caused a 2x overcount in the first pass here.
Report weighted input-equivalents next to raw tokens, because raw counts put cache reads at 95.6% of volume and roughly a third of cost.

Preserve the existing rule in its docstring: bucket by what the sidecar states, never by a slug parsed out of a filename.
Degrade quietly when `subagents/` is missing, since the layout is undocumented.

Extend `roles/ai/files/scripts/tokencost/tests/test_tokencost.py`; that root is already in `pytest.ini` and `AI_SCRIPTS` already lists `tokencost`, so no wiring changes.

### 7. Correct the record

`docs/internals/context-hygiene.md` states "Subagent usage is not recorded in `~/.claude/tasks/`, so any total computed this way understates the real figure" (line 61).
Replace that with the `subagents/` tree, the sidecar fields, the weighted-cost method, and the 50.1 / 36.6 / 13.3 / 1.8 split, so the next person to measure does not repeat the same undercount.
Note that the layout is undocumented and may move.

## Verification

1. `make test` passes, with the two new suites collected. Confirm collection explicitly rather than trusting a green run, since `pytest.ini` only warns on an empty `testpaths` entry and four suites once went dark that way.
2. Hook contract, without a live session: pipe a fabricated `UserPromptSubmit` payload with a `transcript_path` pointing at a temp JSONL into `context-nudge.sh`, and assert it exits 0 and emits nothing below the threshold, a `systemMessage` above it, and `additionalContext` only on a band crossing. Repeat with malformed JSON and with a missing transcript to prove it fails open.
3. Statusline, without a live session: pipe a payload with `context_window.used_percentage` at 30, 62 and 85 into `statusline.sh` and confirm the marker appears only above the threshold, plus a `null` `current_usage` case for the post-compact path.
4. `tokencost` against real data: run it and reconcile the subagent total against the figures in this plan (main thread 50.1%, teammates 36.6%, plain dispatches 13.3%, nested 1.8%). A material divergence means the dedupe or the join is wrong, not that the numbers moved.
5. Model pins: `rg "^model:" roles/ai/files/claude/agents roles/ai/files/claude/plugins/*/agents` returns `opus` for exactly architect, security and database, and `sonnet` everywhere else. Confirm no `effort:` line changed.
6. End to end, after a day of normal use: re-run `tokencost` and check that new `agent-*.meta.json` sidecars record `"model": "sonnet"` for teammates. This is the only check that proves the frontmatter edit actually reaches the teammate dispatch path, which is the assumption the 36.6% saving rests on.
7. `make lint` and `make check` stay clean; `make run-role ROLE=ai` applies with the new hook symlinked into `~/.claude/hooks/`.

Re-measure at the end of the next billing week and compare weighted totals, not raw tokens.
