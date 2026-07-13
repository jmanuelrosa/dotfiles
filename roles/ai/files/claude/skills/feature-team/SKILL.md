---
name: feature-team
description: Run a feature through the staff-engineer team - architect spec, plan approval, parallel dispatch to the installed seats, verification, integration report
disable-model-invocation: true
---
Orchestrate the staff-engineer seats through a full feature pipeline.
You (the main conversation) are the team lead: you dispatch, monitor, and integrate.
Delegate the tasks, not the judgment.

ARGUMENTS: the feature brief, optionally preceded by `--no-isolate`.
If empty, ask for it before anything else.

1. **Restate the brief** in one sentence and confirm scope.
   If it is fuzzy (multiple readings, unstated constraints), stop and suggest running /grill-me on it first; offer to continue with the current brief only if I decline.
2. **Inventory the seats.** List `.claude/agents/` and `~/.claude/agents/`.
   Report which staff-engineer seats are installed.
   If the work clearly needs a seat that is missing (tests → qa, migrations → database, pipelines → platform, IaC → cloud, data/dbt → data/analytics, SLOs → sre), give me the exact `claude-agent add <seat>` command and wait; frontend/backend cover their slices when no specialist is installed.
3. **Design.** Dispatch the architect subagent with the brief.
   It returns a spec at docs/specs/ plus dispatch briefs per seat.
   If it returns `needs-decision`, bring me the decision brief, collect my answer, and re-dispatch.
4. **Approval gate.** Show me the spec's objective, acceptance criteria, owner split, and decision items (reference the spec file, don't paste it whole).
   Wait for my explicit approval before any implementation.
   It is cheaper to fix a bad plan than bad code.
5. **Plan the dispatch.** From the spec's Work breakdown, read each slice's `Parallel` and `Depends on` fields.
   The independent wave is every slice marked `Parallel: yes`; the rest are held for their prerequisites.
   Isolate the wave in git worktrees by default when it has 2+ independent slices and I did not pass `--no-isolate`; a single-slice wave or `--no-isolate` runs in the main checkout as before.
   Isolation needs `worktree.baseRef: head` (so seats branch from the feature tip, not origin/main) and Claude Code >= 2.1.203; both hold in this setup. If baseRef is not `head`, do not isolate.
   Before an isolated wave, run `git status --porcelain`: if the working tree is dirty in the feature's blast radius beyond the spec/ADRs just written under `docs/`, tell me, since worktrees branch from committed HEAD and will not see that WIP; offer `/commit` first or `--no-isolate`.
6. **Dispatch the wave.** Spawn every independent slice's owning seat in a single message so they run concurrently; when isolating, each Agent call sets `isolation: "worktree"`.
   Each dispatch prompt carries: the goal (one sentence), the acceptance criteria numbers, the files it owns, and any pre-authorizations from the spec (schema changes, new dependencies).
   Because an isolated worktree branches from committed HEAD and will not contain the uncommitted spec, give the seat both the spec's absolute main-checkout path and the §Contracts block plus its own slice section inlined.
   An isolated brief adds: "You are in a fresh isolated git worktree branched from the feature tip. Read the spec at the absolute path above (also inlined here). If the build needs dependencies that are absent, run the repo's frozen install first. Do NOT commit. End your report with your worktree root (`git rev-parse --show-toplevel`), your branch, and the exact list of files you changed."
   Enforce one-file-one-owner: if two briefs claim the same file, fix the split before dispatching.
7. **Integrate the wave.** Read each completion report; a seat reporting `blocked` or `needs-decision` comes back to me with its question before anything depending on it runs.
   For an isolated wave, copy each seat's work into the main checkout: from its worktree root run `git -C <wt> status --porcelain`, keep only paths inside that slice's owned set, copy modified/added files into the main checkout, and replay deletions. Copy nothing outside the owned set, so build output and `node_modules` never leak in.
   If any seat added dependencies, run one install in the main checkout afterward to produce a single coherent lockfile.
   Then remove each worktree (`git worktree remove`, `--force` if it refuses on a dirty tree); confirm `.claude/worktrees/` is clean and the main checkout diff is the union of the owned files.
8. **Held slices, then report.** Dispatch the held slices in dependency order, in the main checkout (not isolated), each only after its prerequisites are integrated so it reads their work from the working tree; serialize any that would run heavy verify at the same time. Their edits land directly in the main checkout, so there is no copy-back.
   Confirm every report's verification section shows real command output; list anything "not runtime-verified" for me, then suggest `/code-review` on the combined diff.
   End with the integration report: per-seat status table, acceptance criteria met/unmet, pending ask-first items, gotchas the seats proposed for CLAUDE.md, worktree cleanup confirmed, and the suggested next step (`/code-review`, then `/commit`).
   Do not commit; that is mine to run.

Single-seat tasks don't need this pipeline - delegate directly instead.
Use this skill when the work spans two or more seats or needs the architect's spec first.
