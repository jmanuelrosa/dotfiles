---
name: feature-team
description: Run a feature through the staff-engineer team - architect spec, plan approval, parallel dispatch to the installed seats, end-to-end verification, agent review rounds, integration report
disable-model-invocation: true
---
Orchestrate the staff-engineer seats through a full feature pipeline.
You (the main conversation) are the team lead: you dispatch, monitor, and integrate.
Delegate the tasks, not the judgment.

ARGUMENTS: the feature brief, optionally preceded by `--no-isolate`.
If empty, ask for it before anything else.

1. **Restate the brief** in one sentence and confirm scope.
   If it is fuzzy (multiple readings, unstated constraints), stop and suggest running /grill-me on it first; offer to continue with the current brief only if I decline.
2. **Inventory the seats.** List `.claude/agents/` and `~/.claude/agents/`, and run `kura list --type bundle --json` for installed seat bundles (e.g. `backend-staff-engineer` linked from the `backend` bundle).
   Report which staff-engineer seats are installed by either mechanism.
   If the work clearly needs a seat that is missing (tests → qa, migrations → database, pipelines → platform, IaC → cloud, data/dbt → data/analytics, SLOs → sre), report that the bundle is not installed and wait until the user runs `kura add <discipline> --type bundle`. Frontend/backend cover their slices when no specialist is installed.
3. **Design.** Dispatch the architect subagent with the brief.
   It returns a spec at docs/specs/ plus dispatch briefs per seat.
   If it returns `needs-decision`, judge it first (see **Judging a decision** below), then re-dispatch with the answer.
4. **Approval gate.** Show me the spec's objective, acceptance criteria, owner split, and decision items (reference the spec file, don't paste it whole).
   Wait for my explicit approval before any implementation.
   It is cheaper to fix a bad plan than bad code.
5. **Plan the dispatch.** From the spec's Work breakdown, read each slice's `Parallel` and `Depends on` fields.
   The independent wave is every slice marked `Parallel: yes`; the rest are held for their prerequisites.
   Isolate the wave in git worktrees by default when it has 2+ independent slices and I did not pass `--no-isolate`; a single-slice wave or `--no-isolate` runs in the main checkout as before.
   Under the pi harness, never isolate: run as if `--no-isolate` was passed, because pi worktrees auto-commit each seat's work to a `pi-agent-*` branch, which step 7's copy-back of uncommitted files does not handle.
   Isolation needs `worktree.baseRef: head` (so seats branch from the feature tip, not origin/main) and Claude Code >= 2.1.203; both hold in this setup. If baseRef is not `head`, do not isolate.
   Before an isolated wave, run `git status --porcelain`: if the working tree is dirty in the feature's blast radius beyond the spec/ADRs just written under `docs/`, tell me, since worktrees branch from committed HEAD and will not see that WIP; offer `/commit` first or `--no-isolate`.
6. **Dispatch the wave.** Spawn every independent slice's owning seat in a single message so they run concurrently; when isolating, each Agent call sets `isolation: "worktree"`.
   Each dispatch prompt carries: the goal (one sentence), the acceptance criteria numbers, the files it owns, and any pre-authorizations from the spec (schema changes, new dependencies).
   Because an isolated worktree branches from committed HEAD and will not contain the uncommitted spec, give the seat both the spec's absolute main-checkout path and the §Contracts block plus its own slice section inlined.
   An isolated brief adds: "You are in a fresh isolated git worktree branched from the feature tip. Read the spec at the absolute path above (also inlined here). If the build needs dependencies that are absent, run the repo's frozen install first. Do NOT commit. End your report with your worktree root (`git rev-parse --show-toplevel`), your branch, and the exact list of files you changed."
   Enforce one-file-one-owner: if two briefs claim the same file, fix the split before dispatching.
7. **Integrate the wave.** Read each completion report; a seat reporting `blocked` comes back to me, and one reporting `needs-decision` is judged first (see **Judging a decision** below); nothing depending on either runs until it is answered.
   For an isolated wave, copy each seat's work into the main checkout: from its worktree root run `git -C <wt> status --porcelain`, keep only paths inside that slice's owned set, copy modified/added files into the main checkout, and replay deletions. Copy nothing outside the owned set, so build output and `node_modules` never leak in.
   If any seat added dependencies, run one install in the main checkout afterward to produce a single coherent lockfile.
   Then remove each worktree (`git worktree remove`, `--force` if it refuses on a dirty tree); confirm `.claude/worktrees/` is clean and the main checkout diff is the union of the owned files.
8. **Held slices.** Dispatch the held slices in dependency order, in the main checkout (not isolated), each only after its prerequisites are integrated so it reads their work from the working tree; serialize any that would run heavy verify at the same time. Their edits land directly in the main checkout, so there is no copy-back.
   Confirm every report's verification section shows real command output.
9. **Exercise the integrated change.** Tests passing per slice does not show the slices work together, so run the feature the way a user reaches it: the CLI invoked, the endpoint called, the page driven in a browser, following the project's own launch path (a project run skill, the README, the task runner).
   Delegate this to the qa seat when the repo has e2e tooling and the qa bundle is installed; otherwise do it yourself.
   Evidence is the command output or screenshot per acceptance criterion; a criterion that cannot be exercised locally is listed as "not runtime-verified" with the reason.
10. **Review rounds before I see it.** Dispatch the `code-reviewer` agent with the combined diff (`git diff` of the owned files, inline or written to a temp file whose path you pass), the spec path, and the acceptance criteria. It has no write or shell tools, so it cannot touch the diff it reviews.
    If `code-reviewer` is not installed, skip the rounds, say so in the report, and keep the `/code-review max` next step.
    Round one is review, then a fix brief per `blocker` and `important` finding to the seat owning that file, in the main checkout.
    Round two is review only: the reviewer checks each round-one finding and the lines the fixes touched. Nothing is fixed after it, so every line I see has been reviewed.
    What round two leaves open goes to me as-is rather than into a third round, since a finding one fix attempt did not close usually needs a decision, not another pass.
    `nit` and `pre-existing` findings are never sent back; they go in the report.
11. **Report.** End with the integration report: per-seat status table, acceptance criteria met/unmet with their step 9 evidence, a review-rounds table (findings per round, fixed, still open), pending ask-first items, gotchas the seats proposed for CLAUDE.md, worktree cleanup confirmed, and the suggested next step (`/code-review max` when round two left findings open or the diff spans the whole stack, then `/commit`).
   Do not commit; that is mine to run.
   Where the work came from a `docs/initiatives/` story, tick off the `05-tasks.md` lines it completed and name `/8-living-spec` in the suggested next steps. That stage merges every requirement whose tasks are all done into `docs/specs/`, and nothing in the pipeline is present at ship time to notice it was skipped.

**Judging a decision.** Dispatch the `decision-judge` agent with the decision brief verbatim, the raising agent's name, and the repo root; it answers from the repo's recorded rulings, ADRs and house rules.
On `decided`, relay the answer and its citation to the raising agent and list it in the integration report, so I can overrule it there.
On `sent-back`, return the brief to the raising agent with what the judge said is missing.
On `held`, or when `decision-judge` is not installed, bring me the one-line question and the raising agent's recommendation.
Whenever I answer a held question or overrule a `decided`, append a ruling to `docs/decisions/rulings.md` (create it with a one-line purpose header if absent): a `## <question>` heading, then the ruling, who decided, the date, and the scope it covers.
That file is what lets the next run decide the same question without me, so record the scope narrowly enough that it does not decide a different question by resemblance.
A ruling is a one-line answer to a question that came up; a hard-to-reverse design choice is an ADR instead, written by the architect, and a ruling never restates or overrides one.

Single-seat tasks don't need this pipeline - delegate directly instead.
Use this skill when the work spans two or more seats or needs the architect's spec first.

Under the pi harness, two more substitutions apply besides step 5's `--no-isolate` rule.
In step 2, inventory project seats from `.pi/agents/` and `.claude/agents/` (and `.agents/agents/` on Pi); `kura list --type bundle` reflects declared bundle intent in `kura.json`, not every link a harness may show.
In step 10, pi reads `tools:` against its own tool names, so `code-reviewer`'s Claude-named allowlist does not hold there: run a pi-review pass in its place for each round.
In step 11, suggest a pi-review run instead of `/code-review max`, which does not exist under pi.
