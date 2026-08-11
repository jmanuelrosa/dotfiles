# Pre-registered scoring sheet: the OpenSpec arm on route-catalog

**Status: blank.** Written and committed before the arm's session starts, because the answer is already on disk in `outdoor-maps/docs/initiatives/route-catalog/` and a sheet written afterwards would be fitted to whatever OpenSpec happened to produce.

The protocol is [docs/plans/openspec-vs-product-team-measurement.md](../plans/openspec-vs-product-team-measurement.md).
Results land in [docs/research/product-team-vs-openspec.md](product-team-vs-openspec.md).

## Scoring rules

Five rules, all of them there to stop the sheet being argued into a better score after the fact.

1. **Cite or it did not happen.** Every item marked covered names a `file:line` in the arm's own output. A claim with no citation is scored as not covered.
2. **A contract, not a topic.** Coverage means the output states behaviour someone could write a failing test against. Naming the subject ("the catalog supports notes") is not coverage of R3 ("the note is unbounded, on-device storage is the only limit").
3. **No partial credit.** Covered or not. An item that is arguably either is scored not covered, and the ambiguity is quoted in the notes column, because an experiment that awards half marks on judgement is an experiment whose result is the judgement.
4. **Score the arm's output alone**, without the product-team artifacts open alongside. This sheet already carries everything needed, which is the whole reason it is written first.
5. **Record what the arm asked.** Every point where the run stopped for a human is logged in the counts below, including questions OpenSpec asked that this sheet did not anticipate.

## Sheet A: requirement coverage

The 18 requirements the PRD settled. Abbreviated here; `02-prd.md:69-86` is the authority on wording.

| R# | Requirement, in short | Covered | Where in the arm's output |
|---|---|---|---|
| R1 | A Route has a user-chosen name, exactly one Canonical GPX, and an assigned Category | | |
| R2 | Categories nest, and a Route's Category can change after the Route exists | | |
| R3 | Each Route carries an editable note that is **unbounded**: storage is the only limit | | |
| R4 | One Enrichment link per Reference app, and a name-prefilled search where absent | | |
| R5 | Offline cold start lists every Route with name, Category, notes and Enrichment links, as of the last online visit | | |
| R6 | Offline, any on-device Route's Canonical GPX is available in full | | |
| R7 | Route data survives close, restart, and low device storage | | |
| R8 | Handoff delivers a Route's Canonical GPX to Mapy.com on the phone | | |
| R9 | A Handoff delivers the GPX and nothing else; the Catalog never acts to create Library Presence | | |
| R10 | Browse by Category, and selecting a country shows every Route on file for it | | |
| R11 | Current Trailhead weather when online, and says plainly when unavailable | | |
| R12 | A Route can be added from a laptop with name, GPX and Category | | |
| R13 | The whole Catalog exports to a form the user holds, and restores from it | | |
| R14 | The Catalog reports how many Routes it holds | | |
| R15 | There is one Catalog, not two; no laptop/phone reconciliation step exists | | |
| R16 | Online, the installed Catalog updates its on-device copy to match | | |
| R17 | The installed Catalog shows when its on-device copy was last updated | | |
| R18 | The Catalog records the date each Route was added | | |

**Count: PENDING / 18.**

R15 to R17 are the interesting rows. product-team did not have them at Gate 1 either: they were added because the PRD described authoring on a laptop and reading on an offline phone without ever saying how a Route travelled between the two. Whether OpenSpec closes that gap unprompted is the single most informative cell on this sheet.

## Sheet B: implementable fidelity on shipped work

Four stories shipped from this backlog, so what they needed is a fact rather than an estimate. For each, the question is whether the arm's output specifies it well enough to implement without a further design pass.

| Story | What it actually required | Verdict | Notes |
|---|---|---|---|
| 1.1 publish one route | A Route renders at its own URL with its GPX reachable; publishing happens by committing to the default branch; static hosting with a build step | | |
| 1.2 nested categories | Category is a first-class entity with stable identity, a Route references it, a Category's Route count includes descendants, and the tree is navigable | | |
| 1.3 unbounded route note | R3's note rendered on the Route page with no length ceiling anywhere in the pipeline | | |
| 1.4 block invalid catalog | An invalid catalog fails the build instead of publishing, with per-entry shape validation | | |

Verdicts are one of **specified** (implementable as written), **underspecified** (right subject, a designer still has to decide something material), **absent**.

**Count: PENDING specified / PENDING underspecified / PENDING absent, of 4.**

## Sheet C: decision surfacing

Seventeen decisions that this initiative genuinely had to make. Eleven were settled by product-team at Gate 2; six only surfaced during implementation, which makes them the fair-baseline column: product-team missed those too, so an arm that also misses them loses nothing.

Four rows are **pre-decided in the shared input** and are struck from the scored set, because `docs/ideas/route-catalog.md` states them outright and both arms were handed them. Crediting either workflow for settling a decision it was given would inflate both columns equally and measure nothing.

| ADR | Decision | Settled / deferred / absent |
|---|---|---|
| ~~0001~~ | ~~Deliver the Catalog as an installed PWA~~ (idea doc: "a read-only PWA on Cloudflare Pages, installed to the phone's home screen") | pre-decided |
| ~~0002~~ | ~~Git-tracked files are the entire write path~~ (idea doc: "the repo is the source of truth ... a script on the laptop is the only write path") | pre-decided |
| 0003 | A single build-emitted JSON manifest is the contract between build and service worker | |
| 0004 | Hand-write the service worker rather than adopt a plugin | |
| 0005 | Categories are a first-class collection, not derived from directory structure | |
| 0006 | Derive Trailhead at build time from the GPX, with no author override | |
| 0007 | Run the catalog check inside the hosting build command, not a CI workflow | |
| 0008 | Implement R11 live at view time rather than fetching at update time | |
| ~~0009~~ | ~~Host on Cloudflare Pages rather than GitHub Pages~~ (idea doc names Cloudflare Pages) | pre-decided |
| ~~0010~~ | ~~Use an unkeyed weather source~~ (idea doc: "Open-Meteo (free, no API key ...)") | pre-decided |
| 0011 | Accept a publicly readable deployed Catalog, reject access control | |
| **0012** | Route page URLs are flat and independent of the Category tree | |
| **0013** | Style with CSS custom properties, not a utility framework | |
| **0014** | A Category's identity is its source filename, and a Route references it by id | |
| **0015** | A Category's Route count includes Routes in descendant Categories | |
| **0016** | Compose the catalog check into the build script | |
| **0017** | The catalog check validates per-entry shape itself | |

Bold are the six that surfaced late. **Counts: PENDING settled / PENDING deferred / PENDING absent, of the 13 scored rows, and separately of the 7 scored Gate 2 ones.**

So the honest Gate 2 figure for product-team is **7 decisions genuinely made, not 11**: four of its eleven ADRs ratify a choice the idea doc had already made. That correction lands here rather than in the results, because it was found by reading the shared input before the run and it lowers the incumbent's score.

"Deferred" means the output names the decision as one to be made and does not make it. That is a legitimate outcome and is scored separately from "absent", because a spec that flags an open decision is doing its job while one that never notices is not.

## Sheet D: scope, not score

The five product-team stages with no OpenSpec counterpart. Recorded so the cost comparison is read correctly, and **not** scored as arm failures.

| Stage | Baseline cost | What the arm produced instead |
|---|---|---|
| `01-research` (competitive, user evidence) | $8.70 + agents | |
| `03-red-team` | $4.29 + agents | |
| `04-ux-spec` (`ux-shaper`) | $9.64 | |
| `06-gate-check` (DoR) | $21.92 | |
| `07-push-to-board` | $3.54 | |

The red-team row is the one to read closely: on this initiative it raised 3 blockers and 8 concerns, 3 resolved before Gate 1 closed. If the arm's output contains no adversarial pass and no equivalent, that is a structural difference worth more than the $4.29 it cost.

## Counts to fill in

| | product-team | OpenSpec arm |
|---|---|---|
| Cost, spec phase | $100.83 | PENDING |
| Wall clock | 3 days | PENDING |
| Human decision points | 6 | PENDING |
| Rework cycles | 2 (Gate 3 re-run twice on one mechanical defect) | PENDING |
| Sheet A, requirements covered | 18 / 18 | PENDING |
| Sheet B, stories specified | 4 / 4 | PENDING |
| Sheet C, Gate 2 decisions settled | 7 / 7 scored (4 more were pre-decided in the idea doc) | PENDING |
| `openspec validate --strict` | n/a | PENDING |
| OpenSpec version | n/a | 1.7.0 |

`idea-refine` is excluded from both columns. It ran once, cost $1.67, and produced the `docs/ideas/route-catalog.md` that both arms consume, so it is a shared input rather than a cost either workflow incurs. Adding it to both would move both totals by the same $1.67 and change nothing.

product-team's column is 18/18, 4/4 and 11/11 by construction: these lists were extracted from its output, so it scores full marks on its own sheet and that is not evidence of anything. The sheet measures the arm against a known-sufficient result, not two arms against each other.

## Decision rule

Restated from the protocol so the verdict cannot drift once numbers exist. Every bias in this setup favours OpenSpec: it runs second on a solved problem with a human who knows the answer, and the baseline it is measured against is the pre-fix pipeline that wasted two of its six human decisions on one mechanical defect.

- **product-team wins anyway** → settled, keep it, stop measuring.
- **OpenSpec wins wide** (under half the cost at comparable sheet scores) → settled the other way.
- **OpenSpec wins narrowly** → the margin is plausibly the handicaps. Land the pipeline fixes, then re-measure on a fresh initiative.
- **Strong structure, weak decision surfacing** (good Sheet A and B, poor Sheet C) → evidence for the custom-schema hybrid rather than for either pure option.
