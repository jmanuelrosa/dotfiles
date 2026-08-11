# Measure OpenSpec against product-team on one initiative

## What this settles

Whether `idea-refine` + OpenSpec produces an implementable work list for materially less cost than the product-team pipeline, on the same initiative, from the same starting input.

The product-team arm is **already run and already measured**, so this experiment only has to produce the OpenSpec arm.
`outdoor-maps` ran `route-catalog` from 2026-08-06 to 2026-08-08 and shipped four of its stories over the following two days, which gives the comparison a ground truth neither arm can game.

Measured product-team arm, stages 0 through 7, priced at Opus 5 rates ($5/$25 per MTok, 1-hour cache write at 2x input, cache read at 0.1x):

| | |
|---|---|
| Cost | $100.83 |
| Largest stages | 6-gate-check $21.92, 5-decompose $21.65, `ux-shaper` $9.64 |
| Wall clock, spec phase | 3 days (08-06 to 08-08) |
| Human decision points | 6 (Gates 0 to 3, plus 2 wasted Gate 3 re-runs, plus the stage-7 dry-run confirm) |
| Output | 18 requirements, 4 epics, 15 stories, 74 ACs, 11 ADRs, 8 UX flows, 22 UX anchors |
| Artifacts | 6 documents totalling ~160 KB, plus 19 backlog files and 3 research files |

## What OpenSpec actually produces

Read off the installed CLI (1.7.0) rather than assumed, because it decides what the rubric can fairly ask for.

The `spec-driven` schema is four artifacts in a `requires:` DAG, `proposal → specs → design → tasks`, and `/opsx:propose` walks all four in a single run.
Its guardrails say to prefer reasonable decisions to keep momentum and to ask the user only when context is critically unclear, so there is no gate anywhere in it.

| OpenSpec artifact | product-team equivalent |
|---|---|
| `proposal.md` | `00-brief.md` + `02-prd.md` |
| `specs/<capability>/spec.md` | the R1 to R18 behaviour contracts |
| `design.md` | `04-design-doc.md` |
| `tasks.md` | `05-backlog/` (15 stories) |
| nothing | `01-research/` |
| nothing | `03-red-team-report.md` |
| nothing | `04-ux-spec.md` |
| nothing | `06-dor-report.md` |
| nothing | `07-push-to-board` |

Four of nine stages, no gates.
So a cost win for OpenSpec is close to structurally guaranteed and is not by itself an interesting result: report cost against the four shared artifacts, and treat the five it omits as a scope difference rather than a saving.
The rubric is the experiment.

`/opsx:explore` is **not** a stage and is not a prerequisite for `propose`.
Its own skill states it is "a stance, not a workflow" with no fixed steps and no mandatory outputs, so it is the counterpart of the `idea-refine` conversation rather than of a pipeline stage.
The arm uses one or the other, never both.

## Scope boundary: specification only

Both arms stop at an implementable work list.
product-team's end state is the merged Gate 3 backlog (15 stories with ACs); OpenSpec's is `openspec/changes/<change>/` with its proposal, spec deltas, design and `tasks.md`.

Implementation is excluded, and the reason is that implementation cost is dominated by the code rather than by the tool that specified it: the four shipped stories cost far more than the $100.83 that specified fifteen.
Including it would bury the signal we are looking for.
The user's stated pain (gates, and tokens from idea to MVP) lives entirely in the spec phase.

## Phase 0: fix the setup

`outdoor-maps-openspec` held `.claude/` and `openspec/` and nothing else.
Three asymmetries had to be closed before the arm runs, or the comparison would measure the setup rather than the tool.

1. **Give it the same inputs product-team read, in the slots OpenSpec designates for them.** Stage 0 read `docs/ideas/route-catalog.md`, `docs/strategy/strategy.md`, `docs/strategy/okrs.md` and `CONTEXT.md`.
   - The standing context (stack, conventions, domain, strategy, OKRs) goes in `openspec/config.yaml` under `context:`, which the scaffold documents as "shown to AI when creating artifacts" and which `openspec instructions <artifact> --json` returns as a constraint on every artifact. Pasting it there is what makes it a standing input rather than something read once.
   - `docs/ideas/route-catalog.md` is copied in as a file, because it is the change description `/opsx:propose` takes as input.
   - Copy no artifact from `docs/initiatives/`.
2. **`git init`.** OpenSpec tracks changes as a directory of proposals and expects a repo; the diff is also how we count what the arm produced.
3. **No source code, deliberately.** `outdoor-maps` was greenfield at `05a9054`, the commit before the initiative: story 1.1 introduced `package.json` and the Astro config. product-team had no codebase to read either, so an empty directory is the faithful starting state rather than a handicap.

Also promote the measurement instrument out of the scratchpad.
`scratchpad/fixed.py` is the corrected pricer and the scratchpad is session-scoped, so it will be gone before the arm finishes.
Move it to `roles/ai/files/scripts/tokencost/tokencost` with the repo's script conventions: `dotkit.ui` for output, a committed relative `dotkit` symlink beside it, tests beside the subject, and a `tokencost` entry in `AI_SCRIPTS`.
This also repairs the existing plan, whose verification step 4 points at a scratchpad path that cannot survive.

### Phase 0 record

Done, and the provenance choices matter to the result:

- **`tokencost` is the instrument**, at `roles/ai/files/scripts/tokencost/tokencost`, registered in `AI_SCRIPTS` and in `pytest.ini`, with 26 cases pinning the arithmetic against the rate table. It reproduces the product-team arm's per-stage figures exactly (`6-gate-check` $21.92, `5-decompose` $21.65, `ux-shaper` $9.64, `1-research` $8.70, `3-red-team` $4.29).
- **The baseline is $100.83, not $99.32.** Re-running the sum with the instrument surfaced a bug in the scratchpad script it replaces: its hardcoded agent list matched `pm-red-team`, but the transcript slug is `agent-aprd-red-team`, so the PRD red-team dispatch ($1.52) was never counted. Use $100.83.
- **For scale, the pipeline is 9% of what `outdoor-maps` cost in total** ($1085.16 across 135 buckets, with implementation and `/pr` dominating). Worth stating in the results so neither arm's figure is mistaken for the cost of shipping the initiative.
- **`CONTEXT.md` is taken at `581ded5`** (the Gate 0 commit), not at `HEAD`: three implementation commits amended it afterwards, and the later version describes decisions the arm is supposed to reach on its own. `strategy.md`, `okrs.md` and `docs/ideas/route-catalog.md` are unchanged since before the pipeline ran, so `HEAD` is the pipeline-time version for those.
- **`CLAUDE.md` is authored rather than copied.** The base version is mostly product-team scaffolding (gate owners, the `STATUS.md` state machine, the gate-PR branch convention), which would have instructed the arm to run the pipeline. The arm's version keeps the domain-language pointer and the never-invent-numbers rule, states that nothing has been built and no stack decision exists yet, and replaces the pipeline section with the OpenSpec equivalent plus the specification-only boundary. `product-team:setup-strategy` cost $1.00 of the baseline, so an equivalent setup step on this side is symmetric rather than a favour.
- **`config.yaml`'s `context:` holds pointers, not pasted content**, so artifacts are written against the source documents rather than against an unreviewed summary of them. `rules:` and `operations:` are deliberately unset: tuning them would make the comparison a comparison of the tuning.

## Phase 1: pre-register the rubric

Write the scoring sheet **before** running the arm, because the answer is already on disk in the sibling directory and a rubric written afterwards will be fitted to whatever OpenSpec happened to produce.

Score the OpenSpec output on three fixed lists taken from the product-team arm:

- **Requirement coverage.** Does the proposal capture each of R1 to R18? Count hits, not prose quality.
- **Implementable fidelity on shipped work.** The four stories that actually shipped are 1.1 publish one route, 1.2 nested categories, 1.3 unbounded route note, 1.4 block an invalid catalog from publishing. For each, does the OpenSpec output specify enough to implement it without a further design pass?
- **Decision surfacing.** product-team wrote 11 ADRs at Gate 2 and needed 6 more during implementation (`0012` to `0017`). Which does the OpenSpec output settle, which does it defer, and which does it not raise at all? The 6 late ADRs are the fair-baseline column: product-team missed those too.

Written, blank, at [docs/research/openspec-arm-rubric.md](../research/openspec-arm-rubric.md).
Four sheets rather than three: A the 18 requirements, B implementable fidelity on the four shipped stories, C the 17 decisions split into the 11 Gate 2 ones and the 6 that surfaced late, and D the five omitted stages recorded as scope rather than scored as failures.
It carries five scoring rules whose only purpose is to stop the sheet being argued into a better score once numbers exist, the counts table with product-team's column filled, and the decision rule restated so the verdict cannot drift.

## Phase 2: run the arm

One dedicated session, doing nothing else.
That constraint is load-bearing for the measurement: much of OpenSpec's work is main-thread `openspec` CLI calls that carry no `attributionSkill`, so they land in `<main>` and are unattributable per stage. A session containing only this arm makes the whole session total the arm's cost, and the per-stage split becomes a nice-to-have rather than the measurement.

1. Record the installed OpenSpec version (`openspec --version`; 1.7.0 today, 1.8.0 is published) so the run is reproducible.
2. Read `docs/ideas/route-catalog.md` first and decide whether it is already `idea-refine` output or a raw human idea. If it is already refined, the arm starts from the file, which is exactly the hypothesis under test; if it is raw, run `idea-refine` on it first. Record which, because it decides whether `idea-refine`'s cost belongs in the arm's total.
3. `/opsx:propose` pointed at the idea doc, then `openspec validate --strict`. Stop there. Do not run `/opsx:apply`.
4. Do not run `/opsx:explore` as well. It is a thinking stance with no mandatory output, so running it alongside `idea-refine` would double-count the same conversation and inflate the arm.
5. Do not read `../outdoor-maps` at any point in the session. The arm is blind to the product-team artifacts by construction, not by good intentions.
6. Record wall clock and every point where the run stopped for a human. Expect close to zero: `propose` is instructed to keep momentum and to ask only when context is critically unclear.

Then `tokencost` over that session id, and over the `outdoor-maps` sessions again with the promoted instrument, so both numbers come from the same code.

## Phase 3: report

Results go to `docs/research/product-team-vs-openspec.md`, which is the prior study this experiment was designed to settle.
Replace its cost row (currently "~284k subagent tokens", which measures the smallest component) with both arms' measured figures.

Report five numbers per arm: cost, wall clock, human decision points, rubric score, and rework cycles.

## Fairness ledger

Both known biases point the same way, which is what makes the result cheap to interpret.

| Bias | Direction |
|---|---|
| OpenSpec runs second, on a solved problem, with a human who knows the answer | favours OpenSpec |
| The $99.32 baseline is the pre-fix pipeline (Opus gate-check, no mechanical DoR checker, and 2 of its 6 human decisions were wasted re-runs) | favours OpenSpec |
| Two of product-team's gates were wasted on one mechanical defect that the other plan fixes | favours OpenSpec |

Nothing in the setup favours product-team, and the first bias cannot be removed at any price.
So the decision rule is asymmetric:

- **product-team still wins** despite three handicaps: settled, keep it, stop measuring.
- **OpenSpec wins by a wide margin** (say under half the cost at comparable rubric score): settled the other way.
- **OpenSpec wins narrowly**: the margin is plausibly the handicaps rather than the tool. Land the pipeline fixes from the other plan, then re-measure on a fresh initiative before deciding.

## The third option this uncovered

The choice is not necessarily "product-team or OpenSpec", because OpenSpec is a rival to the pipeline's **state machine** rather than to its content, and its engine is extensible in exactly the direction needed.

Two mechanisms make that concrete:

- `openspec schema fork <source>` and `openspec schema init <name>` create a project-local schema, with its own artifacts, `requires:` edges, templates and per-artifact `instruction`.
- The propose skill states twice that "if the `instruction` field directs you to use a specific skill or command to create the artifact, invoke it instead of writing the artifact directly."

So a custom schema can carry `research`, `red-team` and `ux-spec` artifacts whose `instruction` delegates to `competitive-researcher`, `pm-red-team` and `ux-shaper`, with `requires:` edges enforcing order and `validate --strict` checking completion.
That would replace `STATUS.md`, the hand-rolled gate protocol and the DoR checklist while keeping every agent, and it delivers the other plan's item 3 (machine-checkable stage output) and the prior study's still-unimplemented recommendation 2 (living capability specs, via the archive delta merge) without writing either.

This is not part of the experiment, and it should not be built before the result is in.
It is recorded here because it is the likeliest good outcome and the rubric should be read with it in mind: an OpenSpec arm that scores well on structure and badly on decision surfacing is evidence *for* the hybrid, not for either pure option.

## Out of scope

- **Implementation cost.** Excluded above, with the reason.
- **A second product-team run.** The four existing runs are the baseline; a fresh one would cost another $100 to re-measure something already measured, and it would carry the order advantage in the wrong direction.
- **Building the hybrid schema.** Scoped in the section above; this experiment measures the stock tool, and building a custom schema before knowing the stock result would prejudge it.
- **Registering OpenSpec in the skill registry.** It is a CLI plus its own slash commands, installed by the user outside this repo. If the result says adopt, packaging it is its own change.

## Verification

1. `outdoor-maps-openspec` holds the four copied input files plus an authored `CLAUDE.md`, a git repo, `openspec/` and the `init`-scaffolded `.claude/`, with no file traceable to `docs/initiatives/`. Done: `openspec doctor` reports the root ok, and a grep for `STATUS.md`, `product-team`, `gate-check`, `02-prd`, `04-ux-spec` and `initiatives` across the tree returns nothing.
2. The `context:` block reaches every artifact, not just the first. Done: `openspec instructions <artifact> --change … --json` returns the same 1524-character context for all four of `proposal`, `specs`, `design` and `tasks`. Verified in a throwaway root rather than in the arm, so the arm has no probe change in it.
3. The pre-registered rubric is committed with blank counts before the arm's session starts. Written; the commit is what makes the ordering checkable, so it must land before the run.
4. `tokencost` reproduces the product-team arm's per-stage figures, confirming the promoted instrument matches the scratchpad one it replaces. Done: the stage figures match exactly and the arm total corrects to $100.83.
5. `make test` passes with `tokencost`'s suite included and its `pytest.ini` root registered. Done: 1232 passed.
6. The OpenSpec session transcript contains no read of `../outdoor-maps`.
