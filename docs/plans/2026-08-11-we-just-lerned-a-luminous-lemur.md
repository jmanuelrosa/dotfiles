# Port the comparison-arm lessons into product-team, without the tool

## Context



Every miss in that arm fell inside a stage it does not have; none fell in the four the two share.

The decision here is to take the lessons and not the engine, so that engine stays out of the dependency set and the seven agents, the strategy layer and the board export stay exactly where they are.
That decision has a price worth stating first: two of the nine items are engine features of that tool (stateless sequencing, requirement-level spec merge), so this plan hand-rolls them in a small tested script instead of getting them free.
Expect the full profile to land near **$65 to $70** and the light profile near **$35**.
The irreducible remainder is generation: the PRD, the UX spec, the design and the task list are the product, and its $7.33 was partly the cost of producing less of it.

Two claims on the input list were checked and are wrong as stated, and the plan reflects the corrected version:

- Given/When/Then already exists (`templates/story.md:36-38`, enforced by `dor-checklist.md:9`). What is missing is the requirement carrying its own scenario, three stages earlier.
- **Nothing describes the build spine.** Requirement coverage is not the weak spot (route-catalog carried 18 of 18); the spine is. Its task groups would need `1. Toolchain and skeleton`, `12. Deployment` and `13. Field acceptance`, and the 15 route-catalog stories have none of the three. The cause is one line: `5-decompose/SKILL.md:39`, "a story with no R# reference does not get written".

The deferral handshake is not a feature of that engine at all.

What the rubric saw was emergent behaviour in a single run, so this is ours to invent and it needs a checker or it is a comment.

## Changes

### 1. Requirements are born with their scenarios

`templates/prd.md`: replace the `- **R1**:` bullet list with a block per requirement.

```
### R3: Route note
The Catalog SHALL store an editable note per Route whose length is bounded only by device storage.

#### R3.S1
- **WHEN** a note longer than 100 kB is saved
- **THEN** it is stored and rendered in full, with no truncation and no warning
```

Scenario ids are `R{n}.S{k}` and they become the unit of traceability everywhere downstream.
This is what failed as R3 in the arm ("no length contract is stated anywhere") and it is the same fix the schema's spec instruction already carries.

`agents/ac-writer.md` changes contract: it **claims and completes** rather than invents.
Per story it lists the scenario ids the slice satisfies, and writes a story-local Given/When/Then block only where the slice needs a scenario the PRD does not have, which is still a reportable PRD gap rather than something it may author.
That preserves the refusal mechanism that forced R10 into existence, and it is where two Opus-scale dispatches turn into one Sonnet-scale one.

### 2. A task layer, and stories that stop repeating it

New `templates/tasks.md`, written by `5-decompose` to `05-tasks.md`: dependency-ordered one-liners under numbered groups, each citing the scenario id or design decision it serves, ordered from an empty repo to a shipped and accepted product.
Sixty-two lines of this replace the 1,489 lines of stories on route-catalog, and it is what `architect` currently re-derives at full price.

`templates/story.md` becomes a board header of roughly 20 lines: the field table, the user story, the scenario ids claimed, the UX anchor, and the task groups that implement it.
The story stops carrying restated acceptance criteria because the scenarios now live in one place.
This is the largest single token lever in the plan: stories are read again by `6-verify`, by stage 7, and by every implementer afterwards.

`7-push-to-board` must then **expand** the claimed scenario text into the issue body when it pushes.
A board issue reading "satisfies R3.S1" is unreadable where it is used, and the docs stay canonical because an issue is a throwaway projection of them.

The R#-only rule is scoped to stories and lifted for task groups, which is what lets toolchain, deploy and acceptance work exist at all.
`5-decompose` gains an obligation that the task list start from nothing and end at shipped, so the spine is covered or its absence is argued.

### 3. Two gates, in-session by default

`conventions.md`: Gate 0 (worth building, kill first-class) and Gate 1 (are these the right requirements) survive.
The design gate goes, because the genuinely-open decisions at that stage resolve unaided, and the ones that do not are reached at implementation whether or not a gate sat there.
The DoR gate goes, because across three initiatives it produced one repeated mechanical FAIL for $21.92 a run.

Gate medium becomes config, not circumstance: `gate_medium: session` is the default and uses `AskUserQuestion` in the same turn, `pr` opts into the branch-and-PR protocol for a repo with real reviewers.
Local mode stops being a special case and becomes what `gate_medium: session` plus an unset `github_repo` already means, which deletes a documented variation instead of adding one.

Two consequences have to be paid for in the same change, or the gate cut is a straight loss of record:

- **A session gate row records the reason, not just the verdict.** A PR gate leaves the reviewer's thinking in comments; an `AskUserQuestion` leaves nothing. So the STATUS.md gate row gains a one-line reason and any concern raised, captured from the answer.
- **`docs/adr/` goes under CODEOWNERS.** Gate 2 is today the only approval an ADR gets, and route-catalog produced 17 of them (589 lines). ADRs are the one artifact class this repo treats as immutable and hard to reverse, so losing their review is not acceptable collateral. A CODEOWNERS entry puts the approval on the `/commit` plus `/pr` the human already does, without reinstating a pipeline gate. `setup-strategy` scaffolds it, after the `/docs/initiatives/` line so the more specific pattern wins.

### 4. The deferral handshake

Any artifact may carry a `## Deferrals` table: an id, the question, and the **downstream** artifact that must resolve it.
A resolver that is not downstream in the stage order is a hole, not a deferral.
The resolving stage must close each one pointed at it, either by deciding it or by restating it as an owned Open Question, and `pt check` verifies closure.

Add the section to `templates/prd.md`, `templates/ux-spec.md` and `templates/design-doc.md`, and the protocol to `conventions.md`.
The point is not bookkeeping: an artifact that may legally say "not mine, the design decides" does not have to hedge, so upstream artifacts get shorter.

### 5. STATUS.md keeps the decisions and loses the state machine

The eight-row stage table goes.
Sequencing is derived from file existence by `pt status`, which is what that engine's DAG actually is (`artifact-graph/state.js` is pure `existsSync`), and every stage stops spending tokens parsing and rewriting a markdown table twice per run.

What stays in `templates/status.md` is what a DAG cannot hold: the two gate rows with decider and date, the skip notes, and the kill reason with its folder kept forever.

### 6. The config file, out of CLAUDE.md

New `templates/config.yml`, scaffolded by `setup-strategy` to `docs/strategy/product-team.yml`:

```yaml
profile: full            # full | solo
gate_medium: session     # session | pr
github_repo: UNSET
project_number: UNSET
gate_owners: { gate_0: "@handle", gate_1: "@handle", strategy: "@handle" }
roster:
  research: [competitive-researcher, user-evidence-researcher, market-sizer]
  ux_spec: ux-shaper     # ux-shaper | inline
  red_team: pm-red-team  # pm-red-team | inline
extra_codebase_paths: []
```

`roster` is the answer to "which product team is involved": an empty `research` list skips that stage's dispatches, and dropping `market-sizer` is how an internal tool with no market stops paying for a sizing pass.
`ux_spec` deliberately has no `none`: the artifact always exists, and an initiative with no interface argues the absence per requirement, which is the rule that keeps a bare "N/A" from passing.

`templates/claude-md-section.md` shrinks to three lines pointing at that file.
Today the whole config block is loaded on every turn of every session in the repo for the benefit of eight skills that could read it on demand.

### 7. The light profile drops the expensive half

`profile: solo` keeps research, red-team, ux-spec and both gates, and drops `05-backlog/` (tasks only), `6-verify`, `7-push-to-board` and all PR machinery.
That is roughly half the cost and nearly all of the latency with no finding given up.

The existing expedited path (`conventions.md:93`) is **deleted**, not kept alongside: it skips research and red-team, which is 13% of the cost and the two highest-yield stages, and the cost plan already calls it the wrong trade.

Mechanism is deliberately thin so the profile does not tax every run: `product-lead` reads the config and names the next command, `5-decompose` reads one line to know whether stories are produced, and stages 6 and 7 simply are not invoked.

### 8. Living capability specs

`pt spec-merge <slug>` upserts `docs/specs/<capability>/spec.md` from the PRD requirements whose task groups are fully checked, merging at requirement level.
This is mechanical only because change 1 gave every requirement a SHALL and scenarios, and because `templates/prd.md` gains a `## Capabilities` section (kebab-case names) with each requirement naming its capability.

Sequence this last: it is the one deliverable that can be dropped without unpicking the others.
Its real risk is not correctness but attendance, since nothing in the pipeline is present at ship time.
Mitigation is visibility rather than hope: a thin `8-living-spec` skill, a line in `skills/feature-team`'s completion step, and `pt status` reporting shipped requirements not yet merged.

The `docs/LEARNINGS.md` append **moves here from `7-push-to-board`**.
A retrospective written at board-export time is written before anything shipped, and the light profile does not run stage 7 at all, so today a solo initiative would produce no retro whatsoever.
Ship time is both the honest moment for it and the only one both profiles reach.

### 9. Port the three instruction hardenings already written

The eleven misses found on route-catalog were each written up as an explicit obligation while they were still fresh.
Copy them into the stages that own them, which costs a paragraph each and targets the misses directly:

- `2-write-prd`: the self-knowledge class (how many items it holds, when data was last refreshed, when a record was created), and the requirement that makes each key result measurable. This is R14, R17 and R18.
- `4-tech-shape`: where validity is enforced relative to deploy, and who can read the deployed thing. This is ADR 0007, 0011 and 0016 plus story 1.4.
- `2-write-prd`: a constraint is a requirement, so an unbounded value or a survival condition is stated as a SHALL with a scenario rather than left implicit.

**Moving `3-red-team` after the design was considered and rejected.** It would catch the design-level misses directly, but it costs a renumbering of three commands and their artifact filenames while initiatives are parked mid-pipeline, and the two hardenings above reach the same three findings for a paragraph. The fresh-eyes pass keeps its cheapest position.

### 10. `6-gate-check` becomes `6-verify`

A stage that is no longer a gate must not be named one.
It runs `pt check` first and judges only what a script cannot: scenario testability and dependency cycles.
It carries `model: sonnet` and `effort: medium`, which is the cost plan's item 2 finally applied to a stage small enough to deserve it.

## The `pt` script

Lives at `skills/product-lead/scripts/pt`, beside the shared library every stage already reads, and travels with the plugin symlink.
Stdlib only, `dotkit.ui` for output, a committed relative `dotkit` symlink beside it, tests at `skills/product-lead/scripts/tests/` and a new `pytest.ini` root (which `lib/python/tests/test_suites.py` then asserts).
Read-only apart from `spec-merge`.

| Subcommand | Does |
|---|---|
| `pt status <slug>` | derives stage state from file existence, reads the gate rows from STATUS.md, prints the next command and any unmerged shipped requirement |
| `pt check <slug>` | scenario ids resolve into the PRD, every PRD scenario is claimed by some story or task, UX anchors resolve, deferrals are closed, `L` carries its split rationale |
| `pt spec-merge <slug>` | idempotent requirement-level upsert into `docs/specs/<capability>/spec.md` |

`pt check`'s coverage assertion is new and is the machine-checkable half of item 2's complaint: a scenario nobody claimed is a requirement nobody implements, and no amount of Opus judgment finds that as reliably as a set difference.

## Files

- `plugins/product-team/skills/product-lead/references/conventions.md`: gate medium, two gates, deferral protocol, config location, local mode collapsed, expedited path deleted.
- `.../references/templates/`: rewrite `prd.md`, `story.md`, `status.md`, `dor-checklist.md`, `claude-md-section.md`; add `tasks.md` and `config.yml`; add `## Deferrals` to `ux-spec.md` and `design-doc.md`.
- `.../scripts/pt`, its `dotkit` symlink and its `tests/`; `pytest.ini`.
- Stage skills: all eight, plus `setup-strategy` (scaffold the config) and `product-lead` (read it, new map). `6-gate-check` renamed `6-verify` with the Sonnet pin. New thin `8-living-spec`.
- `agents/ac-writer.md`: claim-and-complete contract.
- `roles/ai/files/claude/GETTING-STARTED.md`, `README.md`, and this repo's `CLAUDE.md` product-team section: the map, the gate count, the config file, the renamed command.

## What a new project gets

Measured against `route-catalog` as it stands at HEAD: 18 requirements, 15 stories, 74 acceptance criteria, 29 initiative files, 3,307 lines, plus 17 ADRs and 589 lines in `docs/adr/`.
Projected column assumes the same initiative re-run under this plan.

| Artifact | Now | After |
|---|---|---|
| `STATUS.md` | 32 | ~14 (2 gate rows, kill reason) |
| `00-brief.md` | 105 | 105 |
| `01-research/` | 364 in 3 files | 364, roster-controlled |
| `02-prd.md` | 204 | ~270 (SHALL + scenarios + capabilities + deferrals) |
| `03-red-team-report.md` | 209 | 209 |
| `04-ux-spec.md` | 509 | 509 |
| `04-design-doc.md` | 324 | 324, two decisions now obligatory |
| `05-tasks.md` | absent | ~110, dependency-ordered, empty repo to shipped |
| `05-backlog/` | 1,489 in 19 files | ~420 in 19 files |
| `06-dor-report.md` | 71 | ~40 |
| `docs/specs/` | absent | ~250, and it survives ship |
| **total** | **3,307 / 29 files** | **~2,365 / 30 files** |

The 1,069 lines that go are restated acceptance criteria, which is the part `6-verify`, stage 7, `architect` and every implementer read again.

Setup is one command and produces one file more than today: `docs/strategy/product-team.yml`, plus a `docs/adr/` CODEOWNERS line, plus a `CLAUDE.md` section that drops from 23 lines loaded every turn to 3.

Per initiative: **8 commands, 2 in-session decisions, 0 PRs by default** (against 8 commands, 6 decision points and roughly 5 gate PRs today), and three new script commands available at any point.

Seven things exist that did not before, and only two of them are savings:

1. **Scenario coverage as a set difference.** Requirements decompose into ids, and `pt check` names any scenario no story and no task claims. Nothing today can detect an unimplemented requirement; that is how R14, R17 and R18 went missing, and the pipeline caught them only by spending Opus on judgment.
2. **A build spine.** Toolchain, deploy and acceptance task groups, which the "no story without an R#" rule made structurally impossible. The 15 stories have none of the three.
3. **Specs that survive ship.** Today the 17 ADRs are the only durable artifact and the other 3,307 lines begin rotting the day the last story merges.
4. **Deferral closure, checked.** An artifact can legally hand a question downstream and the handoff is verified rather than hoped for.
5. **Stateless sequencing.** No stage parses or rewrites a state table; 8 stages stop doing two STATUS.md writes each.
6. **A roster.** Dropping `market-sizer` for a repo with no market is a config line, not a skill edit. Note that route-catalog already has no `sizing.md`, so this is retrofitting a decision that was made by hand.
7. **Two profiles**, with the light one dropping cost rather than dropping findings.

## What this costs us

Seven losses, each with what survives it:

1. **The design gate as a human checkpoint.** `04-design-doc.md` ships without approval. The 17 ADRs keep theirs, moved to a CODEOWNERS line on `docs/adr/` so it rides the commit the human makes anyway. Affordable because the genuinely-open decisions at that stage resolve unaided; not free, because a design doc nobody signed off is a design doc nobody argued with.
2. **The DoR gate as a human checkpoint.** Nothing measurable: across three initiatives it produced one repeated mechanical FAIL and burned gate PRs #5 and #6 on it. The check itself gets stronger, since coverage is new.
3. **Gate PRs as documentation.** Roughly 5 per initiative to 0 by default. The reviewer's reasoning in PR comments is the real loss, so the gate row now carries decider, date and a one-line reason; `/commit` still puts every artifact in git; and `gate_medium: pr` restores the whole protocol for any repo that wants it.
4. **Stage transition history.** The 8-row table with its `in-progress` to `gate-open` to `approved` trail and its skip notes goes. Recoverable but not at a glance: every artifact's YAML header already carries `date` and `authors`, and git log carries the rest.
5. **Stories that read standalone.** 74 acceptance criteria become claimed ids, so a story needs the PRD open. Stage 7 expanding scenario text into issue bodies is what keeps the board usable, and it is a required part of the change rather than a nicety.
6. **The expedited path.** Deleted outright. Anyone who wanted "skip research and red-team" loses the documented option, which is the point: it bought 13% and gave up the two highest-yield stages.
7. **In the light profile only:** no epics, no stories, no board, no DoR report. Research, red-team, ux-spec, both gates, the task list, the ADRs, the living specs and the retrospective all still run.

Untouched, and worth saying because it is what the cut could plausibly have hit: the strategy layer, `strategy-checker` and the kill criteria, kill as a first-class option at both surviving gates, all seven agents, research and red-team and the UX spec in full, the ADR practice, and 18-of-18 requirement coverage. The traceability chain is not weakened but inverted: it stops being prose a model verifies and becomes ids a script verifies.

## In-flight initiatives

`multi-device` is parked on the Gate 3 mechanical FAIL that this plan deletes, and route-catalog and game-finder are past it.
Nothing migrates: `pt status` derives state from files that already exist, the two surviving gates are already recorded in their STATUS.md rows, and an initiative that never gets a `05-tasks.md` simply has no task layer.
Do not rewrite old PRDs into SHALL form. `pt check` skips a PRD with no `### R{n}:` blocks and says so, so the old shape degrades rather than fails.

## Verification

1. `make test` passes, including the new script suite and `test_suites.py`'s assertions about the new root and the new committed symlink.
2. `pt check` against `outdoor-maps/route-catalog`'s 19 backlog files reports what its third Gate 3 report concluded by hand, and against `pickleballontime/multi-device-responsive-ui` reproduces exactly the two known `L`-without-rationale FAILs and nothing else.
3. `pt status` on all three initiatives on disk agrees with each STATUS.md's stage table before that table is deleted. This is the one check that must run before the rewrite, not after.
4. `pt spec-merge` run twice on route-catalog produces a byte-identical `docs/specs/` the second time.
5. One real initiative through the light profile end to end, then `tokencost <project> --match product-team`. The number to beat is $100.83 and the target is $35; if the light profile does not land under $50, the remaining cost is generation and the next lever is scope, not structure.
6. No stage writes a STATUS.md stage row, checked by grep across the plugin.
7. The four loss mitigations are present, since each is a thing that silently does not happen: `setup-strategy` scaffolds a `docs/adr/` CODEOWNERS line after the `/docs/initiatives/` line, a session gate row has a reason column, `7-push-to-board` expands scenario text rather than emitting ids, and `docs/LEARNINGS.md` is appended by `8-living-spec` and by nothing else.
