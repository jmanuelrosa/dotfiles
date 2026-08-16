# Product-team PR follow-up: fix the checker, cut the per-stage load, give the living spec a lifecycle

## Context

The pipeline rework on this branch delivers what it promised: two gates instead of four, `pt.py` doing the lexical checks a model used to be paid for, scenario ids as the traceability currency, a task spine, and a `solo` profile that drops the board-facing half while keeping every finding-producing stage.
A three-way review of the branch (full diff audit, token-footprint profile, and external research into the strongest open-source spec-driven workflow) confirms the direction and finds three classes of remaining work:

- **Defects in what landed.** `pt.py` misreads the gate table one column to the right, so the decider never surfaces and the reason column is dropped entirely; a requirement claimed only by stories can never be reported shipped; a deferral pointed at `05-tasks.md` is legal but nothing documents how to close it; a legacy initiative with a `05-backlog/` and no `05-tasks.md` is blocked at stage 6 against the plan's own migration promise; deferral closure is a substring match, so `D1` closes inside `D10`. `README.md` still describes five PR gates, the old `ac-writer` contract, and an artifact trail this branch deleted.
- **Token spend that structure can still remove.** `conventions.md` (~2,300 tok) is loaded by all 11 skills and a typical stage uses ~60% of it; the `gate_medium: pr` protocol alone is ~380 tok of dead weight for the 7 ungated stages and under the default medium. The gate-removal rationale is written in four runtime-loaded places. Stage bodies carry design-history war stories re-read on every invocation, and `5-decompose` restates `story.md`'s field rules nearly line for line.
- **A lifecycle gap in the living spec.** `spec-merge` is append-or-overwrite: it has no vocabulary for a requirement that changed, was renamed, or retired, and an overwrite silently drops scenarios another initiative added. That silent-drop class is exactly what the rest of this branch was careful to eliminate.

Decisions taken with the user: keep both solo gates in-session as they are (seconds each; kill discipline is the pipeline's core value), adopt the full change vocabulary for living specs, and trim runtime-loaded rationale prose.
The external research's borrowable mechanics (a modify/remove vocabulary with mandatory reason and migration, a no-dropped-scenario merge guard, a strict/lenient checker split, and re-read-dependencies-from-disk) are folded in below without naming their source anywhere in the repo.

Key paths, all under `roles/ai/files/claude/plugins/product-team/` unless stated:
`skills/product-lead/scripts/pt.py`, `skills/product-lead/scripts/tests/test_pt.py`, `skills/product-lead/references/conventions.md`, `skills/product-lead/references/templates/`, the 11 `skills/*/SKILL.md`, `roles/ai/files/claude/README.md`, `roles/ai/files/claude/GETTING-STARTED.md`, `lib/python/tests/test_product_team.py`.

## 1. pt.py bug fixes

- **Gate row parse (pt.py:497).** Cells are `[label, status, decider, date, reason]`; change the tuple to `cells[1], cells[2], cells[3]` and carry `cells[4]` through as `reason`. `--json` gains a `reason` key beside the corrected `decided_by`/`date`; the human table keeps label/status/decider/date.
- **Story-only claims are visible, and shipping stays task-driven.** Tasks are the only artifact with a repo-visible completion signal, so `shipped()` does not change for scenario-carrying requirements. `check` gains a finding, fired only when `05-tasks.md` exists: a scenario claimed only by a story is named as one that can never ship or merge. Severity: warning (see strict mode).
- **Deferrals resolved by `05-tasks.md` get a documented close.** Keep `TASKS` in `DEFERRABLE`. A task line citing the deferral id closes it (the lexical mechanism already works). Add the obligation to `skills/5-decompose/SKILL.md`, one sentence to `templates/tasks.md`'s closing comment (avoiding the literal `## Deferrals`, which `test_product_team.py` asserts absent there), and one line to the conventions Deferrals section.
- **Legacy stage 6 unblocks.** Let a `requires` entry be a tuple of alternatives in `Stage.missing()`; stage 6 becomes `requires=((TASKS, BACKLOG),)`, rendering "needs 05-tasks.md or 05-backlog". Mirrors stage 5's `alt`.
- **Word-boundary deferral closure (pt.py:421).** `re.search(rf"\b{re.escape(identifier)}\b", ...)`.

Known pre-existing quirk to flag in the PR body, not fixed here: deferral ids and design-decision ids share the `D#` namespace, so a task citing design decision `D1` lexically closes deferral `D1`.

## 2. `pt.py check --strict`

`check(root)` returns `(errors, warnings, skipped)`; exit is `FINDINGS` on any error, or on warnings only under `--strict`. Output and `--json` group the two.

- **Errors** (wrong at any point): claims of scenarios the PRD does not define, a requirement with zero scenarios (removal blocks exempt), a dangling Design/UX anchor, dependency cycles, deferrals naming a non-artifact or pointing backwards or unclosed by an existing resolver, and every delta-vocabulary validation below.
- **Warnings** (normal mid-pipeline, defects at DoR time): uncovered scenarios, story-only claims with tasks present, a missing Design/UX pointer, unset Size hint / L without split rationale / blank Needs design seat / blank Depends on, and a deferral waiting on a resolver not yet written.

`6-verify` runs `pt.py check {slug} --strict`, and `5-decompose`'s solo handoff points at the same command since solo has no stage 6 and that run is its DoR.
The existing `Bash(python3 *product-lead/scripts/pt.py *)` allowlists already cover the flag.

## 3. Living-spec change vocabulary

PRD-side, parsed by `requirements()` via column-zero regexes in the existing `Capability:` dialect (matched before the SHALL fallback):

```
### R4: Export a report as XLSX
The system SHALL export any report the user can see as an XLSX file.
Capability: data-export
Modifies: Export a report

#### R4.S1
...
```

```
### R5: Retire CSV export
Removes: Export a report
Capability: data-export
Reason: XLSX replaced it and the CSV path has no remaining consumers.
Migration: saved CSV exports stay downloadable; new exports produce XLSX only.
```

Two verbs only: a rename is a `Modifies:` block restating the SHALL and scenarios under the new heading.
A `Removes:` block has no SHALL and no scenarios, and `Reason:` plus `Migration:` are mandatory.

Mechanics in `pt.py`:

- New helper `spec_requirements(spec_path) -> {name: scenario id set}` shared by the merge guard, check validation, and `_unmerged()`.
- `merge()` returns `(lines_or_None, problem_or_None)`: a plain upsert that would drop a scenario the existing spec holds is refused naming every dropped id and suggesting `Modifies:`; `Modifies:` replaces the named block under the new heading (drops allowed, intent is explicit); `Removes:` deletes the block; a missing target is a problem. `cmd_spec_merge` prints problems and exits `FINDINGS`.
- A removal ships when at least one checked task cites the bare `R{n}` (decommissioning is work); a removal no task cites is a check error.
- `_unmerged()` also reports a shipped requirement absent from an existing spec file, an unapplied modify, and an unapplied removal still present.
- `check` validates: `Modifies:`/`Removes:` targets exist in `docs/specs/{capability}/spec.md`, removals carry both `Reason:` and `Migration:` and no scenarios, and a plain block colliding with an existing spec requirement while dropping scenarios is a check-time preview of the merge refusal.

Doc edits: `templates/prd.md` shows both shapes in its Requirements comment; `skills/2-write-prd/SKILL.md` gains one bullet (never restate a shipped requirement without a `Modifies:`); `skills/8-living-spec/SKILL.md` documents the guard, both verbs, the removal ship signal, and the `FINDINGS` exit.

## 4. Conventions split and the token diet

New `skills/product-lead/references/gates.md`; `conventions.md` keeps a lean core.

| Section | Destination |
|---|---|
| Intro, artifact layout, slug rule, metadata header, config file, stage order, Deferrals, Profiles, Hard rules | core |
| Two-gates summary table, the no-design/no-DoR-gate paragraph, and "every gate records its decision and its reason" (pinned by `test_product_team.py`) | core, ending with a pointer at gates.md |
| Both `gate_medium` protocols, the branch table and fetch fallback, "gated stages never run git commit/push/pr create", Revision flow | gates.md |
| Interview style | deleted; folded into `setup-strategy` and `0-refine-idea` bodies |

Exactly four skills load gates.md: `0-refine-idea`, `3-red-team`, `setup-strategy`, `product-lead`; their preflight lines change accordingly, stages 1, 2, 4, 5, 6, 7, 8 keep loading only the core.
`GETTING-STARTED.md`'s mechanics row splits to name both files.
New hard-rules bullet: re-read every artifact a stage depends on from disk at invocation, never from conversation memory.

Same pass, the deduplication the token profile named:

- The gate-removal rationale stays in `conventions.md` core once; the restatements in `product-lead/SKILL.md:42`, `4-tech-shape/SKILL.md:27` and `setup-strategy/SKILL.md:78` shrink to one clause each.
- `5-decompose/SKILL.md`'s near-verbatim restatement of `story.md`'s six field rules becomes a pointer at the template, which is the authoritative format.
- Design-history war stories in stage bodies ("all fifteen stories on the first initiative...", "three initiatives in a row failed...", "it used to inherit an Opus session...") trim to the obligation plus one clause of why; the full history survives in the plan docs and git.

## 5. README.md migration and the tests that hold all of it

Fix the four stale `README.md` sections the rework missed: the Artifact trail block (add `product-team.yml`, `04-ux-spec.md`, `05-tasks.md`, `docs/specs/`; LEARNINGS at stage 8; STATUS.md as decisions-only), the "five human PR gates" and `AC-{n.m}.{k}` chain paragraph, the `ac-writer` agent-table row (claims and completes), and the per-story loop step still reading `AC-*`.
Also fix the pre-existing `claude-kit add --group product --type skill` install line (it is a plugin).

Tests:

- `test_pt.py`: all existing `check` unpacks move to the 3-tuple with severities per the table; new tests for gate row binding (decider, date, reason), error-vs-strict exit behaviour, word-boundary closure, story-only warning, legacy stage-6 unblock, every delta op (modify replaces and renames, remove deletes, missing reason/migration, missing target, refusal naming the dropped scenario, removal ship signal, idempotency of modify and remove), and `_unmerged` seeing a requirement missing from an existing spec.
- `test_product_team.py`: the PRD template shows the four delta literals; `gates.md` exists and exactly the four named skills reference it, asserting the complement too; the PR protocol text is gone from `conventions.md`; `6-verify` and `5-decompose` carry `--strict`; extend the retired-vocabulary scan with the stale README phrases fixed above ("five human PR gates", `AC-{n.m}`) so they cannot return.

## Deliberately not done

- Solo keeps both gates: each is one in-session question, and what solo already dropped is where the cost was.
- No archive lifecycle for `docs/initiatives/` folders: conventions treat dead initiatives as institutional memory in place.
- The plan's cost target ($35 solo, $50 failure threshold) is still unmeasured. It needs one real initiative run end to end in another repo and `tokencost <project> --match product-team`; that is a follow-up outside this branch, and the number belongs in the PR description when it exists.

## Verification

1. `make test` green after each block, in this order: pt.py bug fixes, strict split, delta vocabulary, conventions split and doc trims, README fixes.
2. Read-only cross-checks against the three real initiatives on disk: `pt.py status` and `pt.py check` on `~/Developer/3bitslost/pickleballontime` (both initiatives) and `~/Developer/personal/shrnk/docs/initiatives/url-shortening`; multi-device must now read stage 6 as ready (not blocked), and no new errors may appear on any of the three beyond the two known L-without-rationale findings, which are now warnings.
3. `pt.py spec-merge` run twice on a fixture stays byte-identical for plain, modify, and remove paths.
4. `grep -rn "gate_medium: pr" skills/*/SKILL.md` shows no stage body carrying the PR protocol; token re-estimate of the core `conventions.md` lands near or below ~1,500 tokens (from ~2,300), and the ungated stages load nothing from gates.md.
5. `grep -rni openspec` over the repo returns nothing.
