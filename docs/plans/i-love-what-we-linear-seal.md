# Cut product-team pipeline cost, in measured-cost order

## Context

The product-team pipeline felt expensive per gate and per initiative, but the diagnosis was a feeling.
Measuring it against the session transcripts (`~/.claude/projects/**/*.jsonl`, which carry per-message `usage` plus an `attributionSkill` field) inverted the intuition: the cheap stages are the ones that produce decision-changing findings, and the expensive stages are bookkeeping and verification.

Corrected figures for `outdoor-maps/route-catalog`, priced at Opus 5 rates ($5/$25 per MTok, 1-hour cache write at 2x input, cache read at 0.1x):

| Stage | Cost | Share |
|---|---|---|
| 6-gate-check | $21.92 | 22% |
| 5-decompose | $21.65 | 22% |
| `ux-shaper` | $9.64 | 10% |
| 1-research | $8.70 | 9% |
| 3-red-team | $4.29 | 4% |
| **pipeline total** | **$100.83** | |

Research plus red-team is 13% of the run.
Decompose plus gate-check plus `ux-shaper` is 54%.
So skipping discovery (the existing expedited path) buys ~13% and gives up the two findings that changed decisions on the initiatives that ran: the stage-0 `strategy-checker` flip on `multi-device`, and the dated stop condition stage 3 installed after Gates 0 and 1 had both left it unmade.

Three defects were verified in the source, and all three sit in the expensive half.

**What this plan deliberately does not do.**
An earlier draft added `context: fork` to `/pr` and `/commit` to make their `model: sonnet` pins durable.
That is unsafe and is dropped: `AskUserQuestion` is removed from every subagent by a filter that `context: fork` does not escape (`background: false` escapes a different filter), so forking would silently delete the mandatory approval gate in `/pr` step 3 and `/commit` step 7.
No error, no symptom: the model would improvise prose consent and push.
A guard against re-introducing it is item 5 below.

## Changes

### 1. Retire the recurring Gate 3 failure class (highest confidence, 3 of 4 initiatives hit it)

The mechanism, verified across three files:

- `skills/product-lead/references/templates/dor-checklist.md:15` says an L "**should** carry a note on why it was not split" (soft).
- `skills/6-gate-check/SKILL.md:22,41` enforces "any unchecked item means FAIL, no exceptions" (hard).
- `skills/product-lead/references/templates/story.md:18` has a `Size hint` row and **no slot for the rationale**, so nothing looks blank and nobody writes it.

`multi-device`'s STATUS.md confirms the diagnosis in its own words: "in both the rationale exists in the epic and not in the story."

Fix, in `roles/ai/files/claude/plugins/product-team/skills/product-lead/references/`:

- `templates/story.md`: add a row after `Size hint` for the split rationale, required only when the size reads `L`, with a comment stating that.
- `templates/dor-checklist.md`: change the soft "should" to the same hard wording the checker enforces, so the two artifacts agree.

Cost of the class it retires: route-catalog burned Gate 3 PRs #5 and #6 on the identical single FAIL (its retro: "two gate PRs bought no new information"), game-finder burned #10 superseded by #11, and `multi-device` is parked on it now.
This also removes the 5-decompose re-run that regenerated the whole 79 KB backlog, which is the real lever on that stage's $21.65.

### 2. Route the verifier to Sonnet

`skills/6-gate-check/SKILL.md` is defined as "A verifier, not a generator" (line 22) and carries **no `model:` or `effort:` frontmatter at all**, so it inherits the session's Opus/high and cost $21.92, more than 1-research, 2-write-prd and 3-red-team combined.

Add to its frontmatter:

```yaml
model: sonnet
effort: medium
```

This is a `model:` pin, not a fork: the skill stays in the main conversation and keeps `AskUserQuestion`.
The pin is turn-scoped, which is sufficient here because the stage runs as one turn (read every story, cross-reference, write the report, stop).

Leave `5-decompose` on Opus.
It is generative and judgment-heavy (concern clustering, sizing, AC tracing), and item 1 is the cheaper lever on it.

### 3. Script the mechanical half of the DoR checklist

Four of the seven DoR items are pure syntax, so an Opus pass is the wrong tool:

- the story's `R#` ids exist in `02-prd.md`
- the Design/UX pointer resolves to a real heading in `04-ux-spec.md`
- `Needs design seat` is non-blank
- `Size hint` is set, and carries the item-1 rationale when it reads `L`

Add a stdlib-only checker beside the skill that reports these per story, so the model pass handles only the three judgmental items (AC testability, dependency cycles, unowned open questions).
Follow the repo's script conventions: `dotkit.ui` for output (`_ui`/`ui` vocabulary, no hand-rolled colours), a committed relative `dotkit` symlink beside it, and tests beside the subject per the "Where a test lives" rule.
Reference the checker from `6-gate-check/SKILL.md` step 1 so the model runs it before judging.

### 4. Unblock the gate stages in the sandbox

`skills/product-lead/references/conventions.md:57` prescribes `git fetch origin` then cutting from `origin/{default}`, and SSH is blocked here, so every gate stage improvises around a failing first command.
Route-catalog's retro asked for this and it is still open.

Add the fallback the retro already validated: compare local `HEAD` against `gh api repos/{repo}/commits/{default} -q .sha` and cut from local default once they match.
Note it as the no-remote-fetch path rather than replacing the fetch recipe, since a machine with SSH should keep using it.

### 5. Guard the gates against the change this plan rejected

Add a test asserting that neither `skills/pr/SKILL.md` nor `skills/commit/SKILL.md` sets `context:`, with a comment naming the reason (a fork strips `AskUserQuestion` and disarms the approval gate).
`lib/python/tests/test_review_policy.py` already scans skill files for policy properties and is the natural home; `frontmatter.keys` from claude-kit parses the block.

Without this, a future edit re-introduces the hole with no visible symptom, which is precisely how it nearly landed here.

### 6. Correct the pipeline's cost line

An earlier estimate reported "~284k subagent tokens" as the pipeline's cost.
Subagents are 10 to 15% of an initiative, so that headline measures the smallest component.
Replace it with the measured per-stage bands, and note the instrument (`attributionSkill` in the transcripts) so it is reproducible.

## Out of scope, and why

- **`ux-shaper` ($9.64, 10%).** It landed 2026-08-04, both post-dating initiatives are the painful ones, and route-catalog's retro says the `Needs design seat` field it introduced was degenerate (15 of 15 stories read `yes`). Whether it pays for itself is answerable for free by comparing the pre- and post-08-04 runs already on disk, but that is an analysis, not a code change, and it should not ride this plan.
- **Defaulting to the expedited path.** It buys ~13% and gives up the highest-value findings. Wrong trade.
- **Adopting a third-party spec engine.** A real option for replacing the hand-rolled STATUS.md state machine, but the machine-validation win is item 3 at no dependency cost, and reconciling an external schema against these templates rounds the saving to zero.
- **The epic `Board issue` field.** Requested in all three retros, measured cost about zero (stage 7 improvised a placement and completed both times). Worth doing, not worth ranking here.

## Verification

1. `make test` passes, including the new checker's suite and the item-5 guard.
2. The item-3 checker run against `outdoor-maps/route-catalog`'s 19 backlog files reports ALL PASS on the four mechanical items, matching what its third Gate 3 report concluded by hand.
3. The same checker run against `pickleballontime/multi-device-responsive-ui` reproduces the two known FAILs (`story-2.2`, `story-3.1`, L with no split note) and nothing else, which is the regression test for item 1's mechanism.
4. `tokencost <project> --match product-team` re-run after the next real initiative shows 6-gate-check on Sonnet and its share down from 22%. If the total is not materially down, revisit structure rather than adding more fixes.
5. Item 5 fails if `context: fork` is added to either git skill.
