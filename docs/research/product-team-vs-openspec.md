# Product Team pipeline vs OpenSpec: research, worked example, and recommendation

Date: 2026-07-12.
Question: should the Product Team pipeline (this repo's `roles/ai/files/claude/skills/` + agents) be kept, replaced by, or combined with [OpenSpec](https://openspec.dev) for two jobs: (1) new project idea to concrete proposal, (2) new feature idea to concrete, buildable feature?
Method: web research on OpenSpec v1.6.0, plus the same worked example (`"let customers export their data as CSV"` on a small synthetic API called Trackly) executed end-to-end through both systems in sandboxes under `$TMPDIR/pt-vs-openspec/`.

## Verdict up front

**They are not competitors. They are different layers that overlap only in the middle.**

- The Product Team pipeline is a **decision system**: it exists to kill bad ideas cheaply, force evidence over assumption, and produce an approved, traceable backlog. It ends where code begins.
- OpenSpec is an **execution system**: it assumes the decision to build is already made, and structures the path from "agreed change" to implemented, spec-recorded code. It begins roughly where the pipeline's stage 4 begins, and reaches further (working code, living specs) than stage 7 does.
- For job 1 (new project idea) OpenSpec offers literally nothing: `openspec init` on an empty directory produces one `config.yaml` and the message "Start your first change". The pipeline's `/idea-refine` + `/setup-strategy` + stages 0-3 have no OpenSpec equivalent, and third parties (Fowler's team, codemyspec) confirm this is by design across the whole SDD tool category.
- For job 2 (feature idea) the honest answer is a hybrid: the pipeline's stages 0-3 caught things in the worked example that OpenSpec structurally cannot catch, while OpenSpec's execution loop produced working, smoke-verified code plus a durable living spec, which the pipeline never produces.

**Recommendation: keep the Product Team pipeline as the product layer, and steal OpenSpec's one genuinely missing idea (living capability specs merged at ship time) rather than adopting the tool wholesale. Optionally pilot OpenSpec as the post-Gate-3 execution lane for one initiative.** Details in the final section.

## What OpenSpec is (research summary, verified 2026-07-12)

- MIT CLI by Fission AI (`@fission-ai/openspec`), v1.6.0 released 2026-07-10, ~60,200 GitHub stars, roughly monthly minors, active beta track (Stores for cross-repo specs, Worksets). One breaking pivot: v0.x to v1.0 (2026-01-26) replaced the rigid `/openspec:*` trio with the artifact-graph `/opsx:*` model and swapped per-tool memory files for Agent Skills in `.claude/skills/`.
- Design principles (their words): "fluid not rigid - no phase gates", "iterative not waterfall", "easy not complex", "brownfield-first".
- Artifacts: `openspec/specs/<capability>/spec.md` is the living source of truth of current behavior; `openspec/changes/<name>/` holds an in-flight change (proposal.md, design.md, tasks.md, delta specs with `## ADDED/MODIFIED/REMOVED Requirements`). Requirements are `### Requirement:` SHALL statements, each with at least one `#### Scenario:` WHEN/THEN block. On archive, deltas merge into the living specs at requirement level.
- Workflow: `/opsx:explore` (optional) -> `/opsx:propose` -> `/opsx:apply` (implement tasks) -> `/opsx:sync` / `openspec archive`. `openspec validate --strict` checks structure; `/opsx:verify` is advisory and does not block.
- Explicit non-goals, confirmed by both docs and third parties: product discovery, PRDs, market/user research, adversarial review, formal ADRs, blocking verification, enterprise orchestration.
- Positioning vs peers: lighter than GitHub Spec Kit (no Python, no constitution, ~3 commands), no lock-in vs AWS Kiro (IDE + Bedrock credits). Reenbit's one-liner: "OpenSpec wins on brownfield."

## The worked example

Same input to both systems: the raw idea "let customers export their data as CSV" against a seeded, dependency-free Node API (Trackly: accounts, users, expenses, `X-Api-Key` auth).
Track A ran the pipeline skills verbatim from this repo's working tree with real subagent dispatches; Track B installed OpenSpec 1.6.0, ran `openspec init --tools claude`, and followed the generated skills exactly.

**Methodological caveat, stated plainly: Track B ran after Track A in the same session, by the same agent.** The OpenSpec proposal inherited knowledge Track A had to earn (the formula-injection guard, the EU-Excel locale problem, the copy-paste recipe for non-technical admins, the account-credential auth reality). A cold OpenSpec run would very likely have missed several of these, because nothing in OpenSpec's flow exists to surface them. This contamination flatters Track B, and even so the structural gaps below remain visible.

### Track A: Product Team pipeline (setup-strategy, stages 0-6)

| Stage | What actually happened | Artifact |
|---|---|---|
| /setup-strategy | Vision, 3 bets, 3 non-bets, 2 OKRs with baselines (2 honest `UNKNOWN` + owner), CODEOWNERS, CLAUDE.md config | `docs/strategy/` |
| /0-refine-idea | 6-question brief; evidence labeled (2 evidence, 2 assumption); kill criteria agreed up front; **strategy-checker (real dispatch) returned "aligned with Bet 2, serves KR2.2, proceed" and flagged a productive Bet 2/Bet 3 tension** | `00-brief.md` |
| /1-research | 3 concurrent researchers did real web research. Competitive: nobody ships zero-setup provider-agnostic CSV; flagged that churn may be all-in-one substitution a CSV cannot fix. User evidence: verbatim Capterra quotes; the real complaint is "export doesn't land cleanly in the accountant's system"; honestly downgraded two 403-blocked sources. Sizing: usage frame, 23-69 accounts/month bounded by the brief's own kill bar and OKR target, $2,800-$8,400/yr ARR rescue range, named its weakest number (x4 churn annualization, n=1 quarter) | `01-research/` (4 files) |
| /2-write-prd | 10 requirements R1-R10, 5 metrics (one baseline `UNKNOWN -> OQ#5`), 5 non-goals, 6 owned open questions | `02-prd.md` |
| /3-red-team | **Fresh-eyes agent (read only the PRD) raised 2 blockers, 4 concerns, 1 note.** Blocker 1: the JSON API already existed and users retyped anyway, so the barrier is the access mechanism, not the format; an API-only v1 contradicts its own 30% reach target. Blocker 2: R4's "admin-only" had no identity primitive to enforce (auth is per-account keys). Both changed the PRD materially | `03-red-team-report.md` + PRD revision |
| /4-tech-shape | Design doc grounded in real `path:line` citations (e.g. the from/to bounds in `src/store.js:23-24` were already inclusive, exactly R3's contract); 5 rejected alternatives; CSV formula injection and bulk-egress threat analysis; adr-scribe extracted 4 ADRs and defensibly declined a 5th | `04-design-doc.md`, `docs/adr/0001-0004` |
| /5-decompose | 2 epics, 5 vertical stories; **ac-writer refused to fabricate an AC for the formula-injection guard because no requirement covered it, forcing a Gate 1 revision that added R10**; re-dispatch closed the gap (21 ACs, all traced) | `05-backlog/` (7 files) |
| /6-gate-check | DoR verifier: ALL PASS, 5/5 stories, dependency graph acyclic, no unowned open questions | `06-dor-report.md` |
| /7-push-to-board | Not run (sandbox has no GitHub repo/Project); would create 2 epic parents + 5 sub-issues after a mandatory dry-run confirm | n/a |

Output: 24 markdown artifacts, 1,336 lines, plus 4 ADRs that persist beyond the initiative. **No code.**
Cost: 8 subagent dispatches totaling ~284k subagent tokens, plus substantial main-session work; wall time measured in hours.
Human involvement (simulated here, real in production): 2 interview sessions plus 4 PR gates plus 1 revise-or-send decision.

### Track B: OpenSpec (init, propose, apply, archive)

| Step | What actually happened | Artifact |
|---|---|---|
| `openspec init --tools claude` | 6 skills + 6 slash commands + `openspec/config.yaml` in seconds | `.claude/`, `openspec/` |
| `/opsx:propose add-csv-export` | CLI-guided loop: `new change` -> `status --json` (dependency graph: proposal -> specs+design -> tasks) -> `instructions <artifact> --json` per artifact. Wrote proposal.md (why/what/capabilities/impact), a delta spec (7 SHALL requirements, 12 WHEN/THEN scenarios), design.md (6 decisions with alternatives), tasks.md (12 checkboxes in 4 groups) | `openspec/changes/add-csv-export/` |
| `openspec validate --strict` | "Change 'add-csv-export' is valid"; the format is machine-checked (4-hashtag scenarios, requirement blocks) | n/a |
| `/opsx:apply` | **Implemented the feature for real**: `src/csv.js` (23 lines, RFC 4180 + BOM + formula guard + integer-cents math), export route in `src/routes.js`, extended smoke script. 16/16 checks pass, including tenant isolation, boundary dates, 422s, header-only empty export, BOM bytes on the wire, formula neutralization | working code |
| `openspec archive --yes` | Warned about the 1 deliberately incomplete task (manual Excel matrix) but proceeded with `--yes`; **merged 7 requirements into `openspec/specs/expense-csv-export/spec.md`** (the living spec); change moved to `changes/archive/2026-07-12-add-csv-export/` | living spec |
| Greenfield check | `openspec init` on an empty dir: one `config.yaml` + "Start your first change: /opsx:propose". **No strategy, no discovery, no validation step exists** | n/a |

Output: 7 markdown artifacts, 264 lines, plus ~90 lines of working, smoke-verified code and 2 launch docs.
Cost: 0 subagent dispatches; wall time under an hour including the npm-cache detour.
Human involvement: none required between "propose" and "archive" unless the agent chooses to ask.

## What each system caught that the other could not

**Only the pipeline caught:**
1. The delivery-mechanism blocker (JSON API existed, users retyped anyway), which reframed the product decision. Nothing in OpenSpec reads the idea adversarially.
2. The unbuildable requirement (admin-only export with no user identities). OpenSpec's validate checks markdown structure, not whether a requirement has an enforcement primitive.
3. The evidence base and its limits: real citations, an explicit contradiction (ticket demand vs all-in-one substitution churn), quantified stakes with the weakest number named. OpenSpec has no research surface at all.
4. The traceability refusal: ac-writer would not invent coverage for the formula guard, and the pipeline routed the fix through a PRD revision. In OpenSpec I simply wrote the requirement into the delta spec myself; no independent party checks that specs cover the design.
5. Strategy alignment and a kill option: the strategy-checker verdict and pre-agreed kill criteria exist before any investment. OpenSpec treats every proposed change as worth building.

**Only OpenSpec produced:**
1. Working, verified code: the 16-check smoke run against the live app is a stronger artifact than any prose promise. The pipeline stops at a board export by design.
2. A durable, current-behavior spec: after archive, `openspec/specs/expense-csv-export/spec.md` describes what the system NOW does, requirement by requirement, and future changes will modify it via reviewed deltas. In the pipeline, the PRD and design doc are initiative-scoped snapshots that begin going stale at ship time; only ADRs persist.
3. Machine-validated artifact structure: `validate --strict` catches malformed specs; the pipeline's formats are enforced only by skill prose and the stage-6 verifier's judgment.
4. Stateless progress tracking for the agent: `status --json` tells any fresh session exactly which artifact is next, without a STATUS.md convention to maintain.

**Frictions observed, both sides.**
Pipeline: hard preflight on an `origin` remote and `gh` (fails in a remote-less repo); every gate assumes the GitHub PR machinery; the commit hook correctly reserved gate commits for the human `/commit` flow, which an autonomous dogfood cannot exercise; and the artifacts have no post-ship maintenance story.
OpenSpec: the telemetry notice prints to stdout and breaks `--json` piping until `OPENSPEC_TELEMETRY=0`; the merged living spec ships with a literal "Purpose: TBD" hole; archive only warns on incomplete tasks; brownfield adoption starts with an empty `specs/` (Trackly's existing auth and expenses endpoints remain unspecified until something changes them); no ADR registry, so the "why" behind decisions lives only inside each archived change's design.md.

## Dimension-by-dimension

| Dimension | Product Team pipeline | OpenSpec 1.6.0 |
|---|---|---|
| Job 1: idea -> proposal | Full path: ideation, strategy fit, evidence, sizing, PRD, adversarial review, kill option at every gate | Nothing; assumes the decision is made |
| Job 2: feature -> buildable | Ends at a ready backlog on a board; build belongs to feature-team | Ends at working code + updated living spec |
| Evidence discipline | Enforced (labels, citations, UNKNOWN baselines, confidence levels) | None; quality = whatever the driving agent knows |
| Adversarial checking | Structural (red-team, ac-writer, gate-check, all fresh-eyes and single-artifact) | None; validate is structural, verify advisory |
| Human control | 4 PR gates + dry-run confirm; kill is first-class | No gates by philosophy ("fluid not rigid") |
| Durable knowledge | ADRs (repo-wide, immutable, superseded) + LEARNINGS.md; PRD/design go stale | Living capability specs + archived changes; no ADRs |
| Traceability | story -> AC -> R# -> brief -> bet, verified at stage 6 | requirement -> scenario within one change; no upstream anchor |
| Ceremony floor | High: 8 stages even for small features (mitigable by skipping to stage 4, but that is convention, not tooling) | Low: propose/apply/archive; own docs admit overkill for tiny fixes |
| Tooling maturity | Self-maintained prose skills (~1,430 lines); no validators | CLI with strict validation, JSON introspection, 60k-star project, monthly releases, one breaking pivot in history |
| Maintenance / bus factor | You maintain everything; zero external risk | MIT dependency; healthy but young; telemetry on by default |
| Cost per feature (observed) | ~284k subagent tokens + hours + 5 human decision points | Well under half that, no dispatches, minutes-to-hour |

## Recommendation

**1. Keep the Product Team pipeline as your product layer. Do not replace it with OpenSpec.**
For job 1 there is no contest, and for job 2 the worked example showed the pipeline's checkers catching decision-changing problems (both red-team blockers, the trace refusal) that OpenSpec has no mechanism to catch.
The pipeline's real product is not the documents; it is the kill decisions, the evidence discipline, and the traceability chain, and those survived contact with a real run.

**2. Steal the living-spec idea; it is the pipeline's one genuine structural gap.**
Today, when an initiative ships, the PRD and design doc start rotting and only ADRs persist.
OpenSpec's `specs/` directory solves exactly that, and its requirement format (SHALL + scenario blocks) is nearly isomorphic to what ac-writer already produces (Given/When/Then traced to R#s), so the mapping is cheap.
Concretely: add a convention (a stage-7 substep or a feature-team completion step) that upserts `docs/specs/<capability>/spec.md` from the shipped stories' requirements and ACs, delta-style.
That gives future agents and humans a current-behavior source of truth without adopting any new tool.

**3. Optionally, pilot OpenSpec as the execution lane below the pipeline for one initiative.**
The seam is clean: an approved PRD + design doc compresses naturally into `proposal.md` + `design.md`, R#s and ACs map onto delta-spec requirements and scenarios, and stories map onto task groups.
You would gain `validate --strict`, `status --json` statelessness, and the archive-to-living-spec merge for free, at the price of a second artifact tree (`openspec/` next to `docs/`), a young dependency with one breaking pivot in its history, and no ADR concept (keep `docs/adr/` authoritative regardless).
If the dual-tree overhead annoys in practice, drop the tool and keep recommendation 2.

**4. Small pipeline fixes this exercise surfaced** (independent of OpenSpec):
- The stage-0/setup-strategy preflight hard-requires an `origin` remote; consider a degraded local mode (gates recorded in STATUS.md only) so dogfooding and offline use are possible.
- Consider a documented "expedited path" (stage 0 brief -> stage 4) for small, low-risk features, so the 8-stage ceremony stays proportional; OpenSpec's own "overkill for tiny changes" critique applies to the pipeline doubly.
- `skills/domain-modeling/ADR-FORMAT.md` still describes a lighter ADR shape than the unified `templates/adr.md`; reconcile or annotate it so two shapes do not coexist.

## Appendix

**Sandboxes** (ephemeral, `$TMPDIR`): Track A at `/tmp/claude-501/pt-vs-openspec/sandbox/` (24 docs, 1,336 lines; STATUS.md shows the full state machine), Track B at `/tmp/claude-501/pt-vs-openspec/sandbox-openspec/` (change + living spec + implemented code, `npm run smoke` = 16/16).

**Deviations from real pipeline use, logged during Track A**: no git branches/commits/PRs (no remote; the commit hook correctly reserves `git commit` for the human `/commit` flow), gates simulated by editing STATUS.md with a note, interviews answered by a scenario PM persona, stage 7 described but not executed.

**Track A subagent usage**: strategy-checker 16.7k, competitive-researcher 59.8k, user-evidence-researcher 40.1k, market-sizer 42.1k, pm-red-team 22.4k, adr-scribe 34.3k, ac-writer 32.9k + 35.9k (resume) = ~284k tokens, 8 dispatches.

**OpenSpec sources**: [openspec.dev](https://openspec.dev), [GitHub README](https://github.com/Fission-AI/OpenSpec), docs (concepts, cli, commands, supported-tools), [v1.0.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.0.0) and [v1.6.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.6.0) release notes, npm registry + GitHub API (2026-07-12: v1.6.0, ~60.2k stars, MIT), [Martin Fowler: understanding SDD tools](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html), [codemyspec: Kiro vs OpenSpec](https://codemyspec.com/blog/kiro-vs-openspec), [Augment Code roundup](https://www.augmentcode.com/tools/best-spec-driven-development-tools), [Reenbit: BMAD vs Spec Kit vs OpenSpec](https://reenbit.com/bmad-vs-spec-kit-vs-openspec-choosing-your-spec-driven-ai-framework/).
