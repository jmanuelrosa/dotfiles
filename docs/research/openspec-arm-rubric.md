# Pre-registered scoring sheet: the OpenSpec arm on route-catalog

**Status: scored.** The sheet below was written and committed blank before the arm ran (`8ddb068`), because the answer was already on disk in `outdoor-maps/docs/initiatives/route-catalog/` and a sheet written afterwards would have been fitted to whatever OpenSpec happened to produce. Only the verdict cells and the notes have been filled since.

The protocol is [docs/plans/openspec-vs-product-team-measurement.md](../plans/openspec-vs-product-team-measurement.md).

Arm output: `outdoor-maps-openspec/openspec/changes/route-catalog-mvp/`, one proposal, seven capability specs, a design and 62 tasks. Citations below are relative to that directory.

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
| R1 | A Route has a user-chosen name, exactly one Canonical GPX, and an assigned Category | yes | `catalog-storage:7-11`, `:34-39` (name is the user's, never a Reference app's) |
| R2 | Categories nest, and a Route's Category can change after the Route exists | yes | `catalog-storage:61-66`, `:93-96` |
| R3 | Each Route carries an editable note that is **unbounded**: storage is the only limit | no | notes exist as a field (`catalog-storage:36`) and as a Markdown body (`design:45-63`), but no length contract is stated anywhere. Grep for "unbounded" and "maximum length" returns nothing |
| R4 | One Enrichment link per Reference app, and a name-prefilled search where absent | yes | `reference-app-enrichment:7-25`, `:27-31`; `design:66` makes it one key per app |
| R5 | Offline cold start lists every Route with name, Category, notes and Enrichment links, as of the last online visit | yes | `offline-availability:22-30`, `:51-54` |
| R6 | Offline, any on-device Route's Canonical GPX is available in full | yes | `offline-availability:42-49`; `design:107-119` makes it a precache guarantee |
| R7 | Route data survives close, restart, and low device storage | no | `offline-availability:25` covers restart and eviction **from memory**. Storage-pressure eviction of the precache is a different mechanism and is unaddressed |
| R8 | Handoff delivers a Route's Canonical GPX to Mapy.com on the phone | yes | `renderer-handoff:7-11`, `design:127-134` |
| R9 | A Handoff delivers the GPX and nothing else; the Catalog never acts to create Library Presence | yes | `renderer-handoff:63-71` |
| R10 | Browse by Category, and selecting a country shows every Route on file for it | yes | `catalog-browsing:7-16` |
| R11 | Current Trailhead weather when online, and says plainly when unavailable | yes | `trailhead-weather:7-16`, `:43-51` |
| R12 | A Route can be added from a laptop with name, GPX and Category | yes | `route-ingestion:7-16` |
| R13 | The whole Catalog exports to a form the user holds, and restores from it | yes | `catalog-storage:103-111` fresh-clone scenario, `tasks:91`. Satisfied by the architecture rather than by an export feature, which is a stronger answer than a feature would be |
| R14 | The Catalog reports how many Routes it holds | no | no count anywhere. Grep for "how many" and "count of" returns nothing |
| R15 | There is one Catalog, not two; no laptop/phone reconciliation step exists | yes | `catalog-storage:103-106`, `catalog-browsing:64-67` |
| R16 | Online, the installed Catalog updates its on-device copy to match | yes | `offline-availability:56-65`, `design:107-119` |
| R17 | The installed Catalog shows when its on-device copy was last updated | no | update mechanics are specified in full; surfacing the timestamp to the user is not. Grep for "last updated" returns nothing |
| R18 | The Catalog records the date each Route was added | no | `route-ingestion:104-107` deliberately answers the underlying need a different way ("the run's own output is sufficient to time it"), which leaves KR1.4 depending on the user noticing. A considered alternative rather than an oversight, but the requirement is not covered |

**Count: 13 / 18.**

R15 to R17 were flagged in advance as the informative rows. R15 and R16 are covered well; **R17 is missed**, and it is the one that keeps R5's "every Route" honest before travelling.

## Sheet B: implementable fidelity on shipped work

| Story | What it actually required | Verdict | Notes |
|---|---|---|---|
| 1.1 publish one route | A Route renders at its own URL with its GPX reachable; publishing happens by committing; static hosting with a build step | specified | `design:121-125` (D9), `tasks:88` emits GPX as static assets, `tasks:43` app shell with a hash route per view |
| 1.2 nested categories | Category is a first-class entity with stable identity, a Route references it, a Category's Route count includes descendants, and the tree is navigable | underspecified | Tree, breadcrumb and index are fully specified (`catalog-browsing:7-21`, `tasks:44`). The **descendant Route count** is absent, so a designer still has to decide whether a country view carries counts and what they include |
| 1.3 unbounded route note | R3's note rendered on the Route page with no length ceiling anywhere in the pipeline | specified | `design:45-63` puts notes in the Markdown body, `tasks:52` renders them. Nothing material is left to decide, even though R3's ceiling is never stated as a contract |
| 1.4 block invalid catalog | An invalid catalog fails the build instead of publishing, with per-entry shape validation | underspecified | Validation itself is excellent (`route-ingestion:54-72`, `:90-93`, `tasks:11,13,38`). Where it runs **relative to deploy** is never pinned: `design:74-82` commits `catalog.json`, `tasks:88` builds on push, and nothing composes the check into the published build |

**Count: 2 specified / 2 underspecified / 0 absent, of 4.**

Both underspecified rows fail on the same axis: the behaviour is specified, the **deployment-time enforcement** of it is not.

## Sheet C: decision surfacing

Four rows are **pre-decided in the shared input** and are struck from the scored set, because `docs/ideas/route-catalog.md` states them outright and both arms were handed them. Crediting either workflow for settling a decision it was given would inflate both columns equally and measure nothing.

| ADR | Decision | Settled / deferred / absent |
|---|---|---|
| ~~0001~~ | ~~Deliver the Catalog as an installed PWA~~ | pre-decided |
| ~~0002~~ | ~~Git-tracked files are the entire write path~~ | pre-decided |
| 0003 | A single build-emitted JSON manifest is the contract between build and service worker | **settled** `design:74-82` (D4), `:91-97` (D6, the shared type is "the only contract"), `:107-119` (D8) |
| 0004 | Hand-write the service worker rather than adopt a plugin | **settled**, oppositely: `design:109` adopts `vite-plugin-pwa` and Workbox, and argues it from precache atomicity |
| 0005 | Categories are a first-class collection, not derived from directory structure | **settled**, differently: `design:68-72` and `catalog-storage:66` derive Categories from the records' paths, so they are neither directory-derived nor a declared registry |
| 0006 | Derive Trailhead at build time from the GPX, with no author override | **settled** `route-ingestion:28-31`, `:34-37`, `tasks:22` |
| 0007 | Run the catalog check inside the hosting build command, not a CI workflow | **absent** |
| 0008 | Implement R11 live at view time rather than fetching at update time | **settled** `design:136-143` (D11), `trailhead-weather:58-61` |
| ~~0009~~ | ~~Host on Cloudflare Pages~~ | pre-decided |
| ~~0010~~ | ~~Use an unkeyed weather source~~ | pre-decided |
| 0011 | Accept a publicly readable deployed Catalog, reject access control | **absent**. "No credential required" is stated (`catalog-storage:106`), but that the Catalog is therefore public on the internet is never surfaced as a decision with an alternative |
| **0012** | Route page URLs are flat and independent of the Category tree | **settled** `catalog-browsing:23-26`, `tasks:45`: a Route in two Categories resolves to the same detail from either |
| **0013** | Style with CSS custom properties, not a utility framework | **absent**. `design:99-105` settles the framework question and says nothing about styling |
| **0014** | A Category's identity is its source filename, and a Route references it by id | **absent, and moot**: with Categories derived from record paths there are no Category files to have an identity |
| **0015** | A Category's Route count includes Routes in descendant Categories | **absent**, the same gap as Sheet B row 1.2 |
| **0016** | Compose the catalog check into the build script | **absent**, the same gap as 0007 |
| **0017** | The catalog check validates per-entry shape itself | **settled** `route-ingestion:54-72`, `:90-93`, `tasks:11,38` |

Bold are the six that surfaced late. **Counts: 7 settled / 0 deferred / 6 absent, of the 13 scored rows. Of the 7 scored Gate 2 rows: 5 settled, 2 absent.**

So the honest Gate 2 figure for product-team is **7 decisions genuinely made, not 11**: four of its eleven ADRs ratify a choice the idea doc had already made. That correction lands here rather than in the results, because it was found by reading the shared input before the run and it lowers the incumbent's score.

Two findings the counts hide:

- **On the late six, OpenSpec beat product-team 2 to 0.** It settled flat Route URLs and per-entry validation ownership at spec time; product-team reached both only during implementation, as ADRs 0012 and 0017.
- **Nothing was scored "deferred", and that is a compliment rather than a gap.** Four specs explicitly defer a decision to the design (`catalog-storage:118-121`, `route-ingestion:32`, `offline-availability:60`, `trailhead-weather:11`), and `design:12-13` picks all four up and decides them. The `requires:` DAG did what it exists to do.

## Sheet D: scope, not score

| Stage | Baseline cost | What the arm produced instead |
|---|---|---|
| `01-research` | $8.70 + agents | nothing. No competitive or user-evidence pass exists in the schema |
| `03-red-team` | $4.29 + agents | nothing adversarial. `design:145-152` carries a self-authored Risks section, which is not the same act |
| `04-ux-spec` (`ux-shaper`) | $9.64 | no state enumeration and no design-system inventory. States appear inline in scenarios (empty Catalog, absent elevation, offline weather) rather than as a surface-by-surface sweep |
| `06-gate-check` (DoR) | $21.92 | `openspec validate --strict`, which passes, at a cost that rounds to zero |
| `07-push-to-board` | $3.54 | nothing. `tasks.md` is the backlog and it is not on a board |

The red-team row is the one that matters. On this initiative it raised 3 blockers and 8 concerns, 3 resolved before Gate 1 closed, and **five of the arm's eleven misses are exactly the kind an adversary catches**: the deploy-time enforcement gap (0007, 0016, story 1.4), the unexamined public-readability decision (0011), and the trust and measurement requirements nobody was asked to defend (R14, R17, R18).

## Counts

| | product-team | OpenSpec arm |
|---|---|---|
| Cost, spec phase | $100.83 | **$7.33** |
| Wall clock | 3 days | **18.6 minutes** |
| Human decision points | 6 | **0** |
| Rework cycles | 2 (Gate 3 re-run twice on one mechanical defect) | **0** |
| Sheet A, requirements covered | 18 / 18 | **13 / 18** |
| Sheet B, stories specified | 4 / 4 | **2 specified, 2 underspecified** |
| Sheet C, Gate 2 decisions settled | 7 / 7 scored (4 more were pre-decided in the idea doc) | **5 / 7** |
| Sheet C, late decisions settled at spec time | 0 / 6 | **2 / 6** |
| `openspec validate --strict` | n/a | **passes** |
| OpenSpec version | n/a | 1.7.0 |

product-team's column is 18/18, 4/4 and 7/7 by construction: these lists were extracted from its output, so it scores full marks on its own sheet and that is not evidence of anything. The sheet measures the arm against a known-sufficient result, not two arms against each other.

`idea-refine` is excluded from both columns. It ran once, cost $1.67, and produced the `docs/ideas/route-catalog.md` that both arms consume, so it is a shared input rather than a cost either workflow incurs.

## Verdict

**The fourth branch of the decision rule: strong structure, weak decision surfacing. This is evidence for the hybrid, not for either pure option.**

OpenSpec produced 72% of the requirement coverage and 71% of the Gate 2 decisions for **7% of the cost, in 18 minutes, with nobody interrupted**. Read as a rate, the last five requirements and two decisions cost product-team $93.50.

What makes this the hybrid answer rather than a win for either side is *which* items were missed. They are not scattered:

- **R14, R17, R18** are the requirements that let the product report on itself. All three trace to OKR reasoning, which is `02-prd`'s job and has no counterpart in the `spec-driven` schema.
- **0007, 0016 and story 1.4** are one gap seen three times: nothing enforces validity at deploy time. That is precisely a red-team finding.
- **0011** is an unexamined security and privacy decision, again red-team shaped.
- **0013** is a design-system decision, `ux-shaper` shaped.

Every miss lands inside one of the five stages OpenSpec does not have. None lands in the four it shares, where it matched or beat the incumbent, including beating it 2 to 0 on decisions product-team did not reach until implementation.

So the schema engine is not the weak part; the missing stages are. A custom schema that keeps `proposal → specs → design → tasks` and adds `research`, `red-team` and `ux-spec` artifacts delegating to `competitive-researcher`, `pm-red-team` and `ux-shaper` would target exactly the eleven misses, and `validate --strict` already does `6-gate-check`'s mechanical half for nothing.

**Recommended next step, and it is not another comparison:** fork the `spec-driven` schema, add the three artifacts, and run it on the next real initiative. The cost to beat is $7.33 plus three agent dispatches, against $100.83.

**Built.** [roles/ai/files/openspec/schemas/product-team/](../../roles/ai/files/openspec/schemas/product-team/README.md) is that schema: `research → proposal → specs → ux-spec → design → red-team → tasks`, validating clean, with the DAG confirmed to gate (`research` ready, all six others blocked on real edges). The three added instructions encode the eleven misses above as explicit obligations, so each one is checked by construction rather than by hoping the model thinks of it.

One caveat that survives the result. This is a single initiative, on a solved problem, with a rich idea doc that had already made four of the architectural decisions. A second initiative would test whether 13/18 holds where the input is thinner, and the hybrid run above is the cheapest way to find out, since it produces that data point as a side effect of being useful.
