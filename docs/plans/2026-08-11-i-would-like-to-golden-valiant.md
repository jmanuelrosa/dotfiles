# Context reporting in tokencost, and the per-request dedupe it depends on

## Context

`tokencost` already prices Claude Code work: it walks `~/.claude/projects/<slug>/`, prices every assistant record off `message.usage`, and buckets by `attributionSkill` or by `agent:<transcript-stem>` for subagents.
What it cannot answer is the other half of the question, how much *context* a session or a skill consumed, which is the figure that decides whether a workflow fits in a window at all and whether it will compact mid-run.
Cost and context come from the same four token fields, so this belongs in the tool that already reads them rather than in a second walker of the same trees.

Getting there first requires fixing a counting bug that context reporting would otherwise inherit.
Claude Code writes **one JSONL line per content block**, each repeating the identical `usage` object: in `-Users-jmanuelrosa-Developer-dotfiles/346f4974….jsonl` there are 494 assistant lines against 248 unique `requestId`, and one request's `output_tokens: 351` / `cache_read: 69779` appears on all three of its lines.
`walk` (`tokencost:133-158`) filters on `type == "assistant"` and yields every line, so every figure the tool has ever printed is inflated by the block-count, 2.0x to 2.4x across the sessions sampled.
The docstring guards against the `iterations` double-count but not this one.

The dollar figures in `docs/research/product-team-vs-openspec.md` and `docs/plans/openspec-vs-product-team-measurement.md` are **deliberately left alone**, per the user's decision: they were produced by the tool as it stood, the inflation applies to both arms, and restating them is a separate call.

## Approach

One script, one pass over each transcript, three changes: dedupe, a context metric, a `--context` view.

### 1. Dedupe by request

In `walk`, keep a per-file `seen` set and skip a record whose key is already in it.
The key is `requestId`, falling back to `message.id`, falling back to a per-line counter so a record carrying neither is always unique.
That fallback is load-bearing rather than defensive: every fixture in `tests/test_tokencost.py` builds records through `record()`, which sets neither field, so a key defaulting to a constant would collapse each multi-record test to a single priced entry.

Per-file rather than global: a `requestId` is unique across the fleet, but scoping the set to the file keeps memory flat on a large project and makes the invariant local to the one read.

Say why in the docstring, next to the existing `iterations` paragraph, since the two are the same class of mistake and a reader who found one will look for the other.

### 2. Context per request, session, and bucket

Context size at a request is `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`, the whole prompt the model was handed.
This is validated against the harness's own accounting: for the session above the computed peak is 388,627 against `compactMetadata.preTokens` of 389,648, a 0.3% gap that is the trailing user message not yet in a request.

Three aggregates:

- **Session peak** is the max over that session's own transcript, with any `compactMetadata.preTokens` folded in as a candidate, since at a compaction boundary the harness states the true figure and it is by definition at least as high as anything a request reports.
- **Session final** is the context of the chronologically last request in the session's own transcript.
- **Bucket peak** is the max over the records attributed to that bucket.

**Subagent transcripts never contribute to a session's peak or final.** A subagent runs in its own window, so mixing it into the parent's figure would describe a context that never existed. Its peak still appears, in its own `agent:` bucket, which is where the existing cost figures for it already live. A session filtered to nothing but subagent records reports `-` rather than `0`.

No percentage of a window is printed. The sampled peak of 389k exceeds the 200,000 that `roles/ai/files/claude/statusline.sh` treats as the default, because a 1M-window session is in the data, and there is no field on a transcript stating which window was in force. Absolute tokens are the honest figure, and inventing a denominator would be exactly the hardcoded value the repo conventions forbid.

Mechanically, `walk` becomes the single reader for both record kinds and yields a namedtuple carrying a `kind` of `usage` or `compact`, so compaction boundaries (`type == "system"`, `subtype == "compact_boundary"`) are picked up without a second read of every file.
`collect` grows `peaks[bucket]` and three fields on each `sessions` row (`peak`, `final`, `compacts`); its cost, token and model accumulation is otherwise untouched.

### 3. The `--context` view

A fourth view alongside the default bucket table and `--sessions`, printing both sections the metric supports:

```
📊 Context by session, oldest first:
  session                               peak    final  compacts
  f101db7b-d643-48a2-83fb-697cef2bedf5  389.6k   14.5k  1
  78c694c6-5e74-4f7e-b73f-e72778e438e1  184.2k  184.2k  0

📊 Peak context by attribution bucket:
  bucket                                   peak
  pr                                     201.4k
  product-team:1-research                156.0k
  agent:agent-ab450ab606e698354           92.7k
✨ peak 389.6k across 12 sessions
```

`--session`, `--since` and `--top` apply as they do today (`--top` elides the bucket section with the same "N more buckets" note); `--match` is a cost subtotal and has no meaning here, so it is not read.
View precedence is `--json` > `--context` > `--sessions` > the bucket table, stated in the `--context` help text so `--context --sessions` is not a silent surprise.
A `human(n)` helper renders `389.6k` / `1.2M`; rows stay bare `print` with the existing `{name:<52}` width, matching `print_buckets`.

`--json` always carries the new fields whether or not `--context` was passed, since it is the one output whose content is facts rather than a report: `peak_context` on each bucket, and `peak_context` / `final_context` / `compactions` on each session.

## Files

| File | Change |
|---|---|
| `roles/ai/files/scripts/tokencost/tokencost` | `walk` dedupes and yields compaction events; `collect` accumulates peaks and per-session context; new `print_context` and `human`; `--context` flag; `as_json` extended; docstring gains the usage line and the dedupe rationale |
| `roles/ai/files/scripts/tokencost/tests/test_tokencost.py` | New cases, below |
| `roles/ai/README.md:10` | Drop the stale "`claude-kit` is the only one" and name `tokencost` beside it, which has been wrong since `bb1a06a` |

No Ansible change: `tokencost` is already in `AI_SCRIPTS` (`roles/ai/defaults/main.yml:41-43`) and its suite is already a `pytest.ini` testpath.

## Tests

Added to the existing suite, which drives the shim as a subprocess with `HOME` as the only seam and asserts hand-computable figures:

1. Two lines sharing a `requestId` are priced once, at `ROUND_COST`, not twice.
2. Records carrying neither `requestId` nor `message.id` are each priced, guarding the fallback that every existing fixture depends on.
3. `message.id` dedupes when `requestId` is absent.
4. Session peak is the max over deduped requests, not the sum.
5. A `compact_boundary` whose `preTokens` exceeds every request's context raises the session peak to it, and is counted in `compacts`.
6. Final context is the last record by timestamp, not the last line in the file.
7. A subagent's context contributes to its own bucket peak and to neither the session peak nor the final.
8. `--context` prints both sections, and `--top` elides the bucket one with the count note.
9. `--json` carries `peak_context`, `final_context` and `compactions` without `--context` being passed.
10. A session with only subagent records renders `-` rather than `0`.

## Verification

```sh
make test                              # the whole suite; no vault, no network
tokencost dotfiles-tokencost --context # against real transcripts
tokencost outdoor-maps --context --top 0
tokencost outdoor-maps --json | jq '.sessions[0]'
```

Cross-check the dedupe against the raw data on a project whose figures are known, and confirm the drop lands in the 2.0x to 2.4x band rather than somewhere unexplained:

```sh
f=~/.claude/projects/-Users-jmanuelrosa-Developer-dotfiles/346f4974-2d34-40bf-b65f-1dc872ec881b.jsonl
jq -c 'select(.type=="assistant")' $f | wc -l          # 494
jq -r 'select(.type=="assistant")|.requestId' $f | sort -u | wc -l   # 248
```

Cross-check the peak against the harness's own number, which is the only external oracle available:

```sh
jq -c 'select(.subtype=="compact_boundary")|.compactMetadata.preTokens' $f   # 389648
```

Colour and stream behaviour are already covered by the suite's `NO_COLOR=1` harness and the existing `errors go to stderr` case; new output uses `dotkit.ui` kinds only, with the topic emoji confined to the two `title` lines and the closing `done`.
