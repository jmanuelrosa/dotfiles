# Deny the five never-invoked built-in tool schemas

## Context

A fresh session in this repo now starts at ~4% of the window, down from 5% after `d7d0b18` cut the always-loaded memory layer from 11.9k to 8.5k tokens.
The two remaining lines in `/context` are `System tools: 17.6k` and `Memory files: 8.5k`, and neither had ever been attributed to a specific artifact.

Both were measured rather than estimated, using the print-mode harness as a token oracle (`claude -p "reply with exactly: ok" --output-format json`, summing `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`) and re-running it with one thing removed at a time.

**Memory files = 7,962 tokens**, confirmed by the `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` delta: global `CLAUDE.md` ~1.7k, project `CLAUDE.md` ~2.7k, `rules/` ~3.5k (code-review 1.4k, skill-precedence 1.2k, context-hygiene 0.9k).
This is exactly the layer yesterday's pass already right-sized, so it is out of scope here by decision: what remains is local knowledge and gotchas, and a further cut trades capability for under 1.5k.

**System tools = 17.6k, of which ~14.5k is schemas for tools that have never been invoked.**
Usage was counted across all 462 transcripts in `~/.claude/projects/`:

| Tool | Measured cost | Invocations, 462 sessions |
|---|---|---|
| `Workflow` | 7,900 | 0 |
| `Artifact` | ~3,600 (interactive-only, estimated from the bundle string) | 0 |
| `ScheduleWakeup` | 1,695 | 0 |
| `ReportFindings` | 821 | 1 |
| `ShareOnboardingGuide` | 470 | 0 |
| Bash, Read, Edit, Write, Skill, ToolSearch, Agent, AskUserQuestion, ListAgents | ~3,100 | 12,956 / 3,092 / … / 288 / 386 / 27 |

The five unused schemas are 82% of the line.
`Workflow` alone is 7.9k, which is more than every tool actually in use put together, and the session already carries an instruction not to use workflows.

### Intended outcome

`System tools` 17.6k to ~3.1k, session baseline ~4% to ~2.5%, on every request of every session in every project, since `~/.claude/settings.json` is a symlink into this repo.

## Change 1: five tool-name denies in `settings.json`

`roles/ai/files/claude/settings.json`, at the head of the existing `permissions.deny` array (before the `Read(~/.ssh/**)` path patterns, which are a different kind of entry):

```json
"deny": [
  "Workflow",
  "Artifact",
  "ScheduleWakeup",
  "ReportFindings",
  "ShareOnboardingGuide",
  "Read(~/.ssh/**)",
```

`permissions.deny` on a bare tool name strips the schema from the request rather than merely refusing the call, which is the whole point and was verified before proposing it: denying `Workflow` plus `ShareOnboardingGuide` through a `--settings` file dropped the prompt by 8,370 tokens, matching the sum of their individual deltas.

Mechanism choice: `CLAUDE_CODE_DISABLE_WORKFLOWS=1` produces an identical 7,900 saving, but env flags exist only for workflows, artifacts and cron, so `permissions.deny` is the one mechanism that covers all five. One mechanism, one place to read.

What this gives up, all of it unused here:

- `/workflows` and any multi-agent orchestration through `Workflow`. The `Agent` tool, the seats, `Explore` and `SendMessage` are untouched, and those are the delegated paths actually in use (288 / 272 / 27 calls).
- Publishing a page to claude.ai from the CLI. The org path for branded collateral is Claude Design, and this tool has never been called.
- `/loop` in dynamic self-paced mode. Fixed-interval `/loop` uses `CronCreate`, which is deferred and unaffected.
- Findings rendered as UI chips by the bundled `/code-review`. `review-mechanics` defines this repo's report format as text, which is why the tool has one invocation in 462 sessions.

## Change 2: record the finding in `docs/internals/context-hygiene.md`

Without this, the next reader finds five bare tool names in a deny list full of path patterns and no way to tell a measurement from a whim.

- Under **Things that cost tokens for nothing**: built-in tool schemas are not deferred the way MCP schemas are, so an eagerly loaded tool costs its full schema on every turn whether or not it is ever called; name the five, their measured sizes, and that they are denied in `settings.json`.
- Under **Measure before pruning**: the print-mode token oracle, since it generalises to any prompt-size question and is cheaper than reading transcripts. Include the `--disallowedTools` / `--tools ""` / `--settings` deltas as the way to attribute a `/context` line, and the two traps found here: print mode ignores `ENABLE_TOOL_SEARCH` entirely, so it reports the undeferred set, and it never loads the claude.ai connectors, so `Artifact` and other interactive-only tools cannot be measured this way.
- While in the file: line 50 still says to default to `sonnet` in `settings.json`, which `d7d0b18` reversed to opus at high effort. One-line correction so the doc matches the committed setting.

## Out of scope, deliberately

- **Memory files.** Cut yesterday; not reopened.
- **The auto-memory instruction block** (706 tokens, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`). Measured and kept by decision, since the intent is to start using persistent memories.
- **`ENABLE_TOOL_SEARCH` tuning.** `auto:N` takes N as a percentage governing how much of the tool set stays eager (`auto:0` defers everything, `100` disables deferral), so a lower N is the alternative for a tool worth keeping but rarely used. It is not worth touching here: after Change 1 the eager set is ~3.1k of tools called thousands of times, and print mode cannot measure the effect anyway.
- **The bundled skills listing** (~1.9k). `artifact-design`, `artifact-diagramming`, `artifact-capabilities` and `dataviz` become dead weight once `Artifact` is denied, but the only lever is `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS=1`, which would also take `claude-api`, `code-review`, `simplify`, `loop`, `schedule` and `run`. Known residue, no change.

## Verification

1. `python3 -c "import json;json.load(open('roles/ai/files/claude/settings.json'))"` - the file is a symlink target read by every session, so a syntax error is machine-wide.
2. `make test` - no suite asserts on `settings.json` today, but the python suites are the unattended target and should stay green.
3. Start a **fresh** session (settings are read at startup; the symlink means no `make run` is needed) and run `/context`. Expect `System tools` ~3.1k rather than 17.6k, `Memory files` unchanged at ~8.5k, and the total baseline near 2.5%.
4. In that session, confirm the five tools are actually gone rather than merely blocked: they should not appear in the tool list, and no `Workflow` or `Artifact` schema should be offered. `ToolSearch`, `Skill`, `Agent` and `AskUserQuestion` must still work, since the plan's whole claim is that nothing in use was touched.
5. Re-run the oracle for the record: `CLAUDE_CODE_DISABLE_WORKFLOWS=1 claude -p "reply with exactly: ok" --output-format json` should stay at 47,125 against the 55,025 baseline, which is the number Change 2 documents.
