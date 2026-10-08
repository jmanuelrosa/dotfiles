# Batch: Parallel Work Orchestration

You are orchestrating a large, parallelizable change across this codebase.

## User Instruction

{{instruction}}

## Phase 1: Research and Plan

Pi has no plan mode, so the plan is a file under `docs/plans/` and approval is an explicit `ask_user` question.
Until the user approves, do not edit any file other than the plan.

1. **Understand the scope.** This command is the user's authorization to delegate, so call `subagents_enable({})` first if the `subagent` tool is not active yet. Launch one or more research subagents in the foreground (`subagent({ agent: "scout", task: "...", async: false })`, because you need their results) to deeply research what this instruction touches. Find all the files, patterns, and call sites that need to change. Understand the existing conventions so the migration is consistent.
2. **Decompose into independent units.** Break the work into 5 to 30 self-contained units. Each unit must:
   - Be independently implementable in an isolated git worktree (no shared state with sibling units)
   - Be mergeable on its own without depending on another unit's PR landing first
   - Be roughly uniform in size (split large units, merge trivial ones)
   Scale the count to the actual work: few files means closer to 5; hundreds of files means closer to 30. Prefer per-directory or per-module slicing over arbitrary file lists.
   Give each unit its own branch name in the repository's branch convention (for example `<type>/<slug>`), since every unit becomes its own PR.
3. **Determine the e2e test recipe.** Figure out how a worker can verify its change actually works end-to-end, not just that unit tests pass. Look for:
   - A browser-automation skill or tool (for UI changes: click through the affected flow, screenshot the result)
   - A CLI-verifier skill or a non-interactive run mode (for CLI changes: launch the app, exercise the changed behavior)
   - A dev-server + curl pattern (for API changes: start the server, hit the affected endpoints)
   - An existing e2e/integration test suite the worker can run
   If you cannot find a concrete e2e path, use the `ask_user` tool to ask the user how to verify this change end-to-end. Offer 2 to 3 specific options based on what you found (e.g., "Screenshot via browser automation", "Run `bun run dev` and curl the endpoint", "No e2e, unit tests are sufficient"). Do not skip this: the workers cannot ask the user themselves.
   Write the recipe as a short, concrete set of steps that a worker can execute autonomously. Include any setup (start a dev server, build first) and the exact command/interaction to verify.
4. **Write the plan.** Write it to `docs/plans/YYYY-MM-DD-<slug>.md`, with today's date and a short kebab-case slug of the instruction. Include:
   - A summary of what you found during research
   - A numbered list of work units: for each, a short title, its branch name, the list of files/directories it covers, and a one-line description of the change
   - The e2e test recipe (or "skip e2e because ..." if the user chose that)
   - The exact worker instructions you will give each agent (the shared template)
5. **Get approval.** Call `ask_user` with the question "Approve the batch plan in `<plan path>`?", a `context` that lists the unit count and titles, and the options "Approve", "Revise" and "Cancel". On "Revise" or a freeform answer, update the plan and ask again. On "Cancel", stop.

## Phase 2: Spawn Workers (After Plan Approval)

**Clean the source checkout first.**
pi-subagents branches every worker worktree from the source checkout and refuses to launch while `git status --porcelain` lists anything (only `.pi/subagents/` is exempt); it never drops isolation on its own.
The new plan file is itself such a change.
Run `git status --porcelain`.
If it is not empty, stop, tell the user which paths block the launch, and ask them to resolve them.
For the plan, recommend committing it through `/commit`: approved plans are committed as the design record, and no worker needs it because every task is self-contained.
Never commit, stash, move, or delete their files yourself, and keep working from the plan you already hold even if its file leaves the tree.
Continue Phase 2 when they say so.

**Pin the base.**
Fetch the branch the PRs will target and pass its remote-tracking ref as `baseRef` (for example `origin/main`), so a local-only plan commit never rides along in a worker's change.

**Write the workflow script.**
Each worker prompt is too large for workflow `args`, so write the script to a file outside the repository (for example `$TMPDIR/cc-batch-<slug>.js`) and pass it as `workflowScriptPath`.
Keep the unit data as a JSON array literal, and use plain `function` helpers, because pi-subagents rejects async arrows and nested async functions in workflow scripts:

```js
const units = [
  { "key": "u1", "title": "<title>", "task": "<fully self-contained prompt for unit 1>" },
  { "key": "u2", "title": "<title>", "task": "<fully self-contained prompt for unit 2>" }
];
function prLine(output) {
  const lines = String(output || "").split("\n").map(function (line) { return line.trim(); }).filter(function (line) { return line.startsWith("PR:"); });
  return lines.length ? lines[lines.length - 1] : "PR: none - the worker reported no PR line";
}
const results = await runs.all(units.map(function (unit) {
  return { key: unit.key, agent: "worker", task: unit.task, skill: "review-mechanics" };
}));
return results.map(function (result, index) {
  return { unit: index + 1, title: units[index].title, ok: result.ok, runId: result.runId, artifactPaths: result.artifactPaths, pr: prLine(result.output) };
});
```

The packaged `worker` agent does not inherit the skills catalog, which is why each child names the skill it needs; drop it if this session does not list it.
Check the script with `subagent({ action: "validate", workflowScriptPath })`, then launch every unit in one top-level call so they run in parallel:

```js
subagent({ workflowScriptPath: "<script path>", async: true, worktree: true, baseRef: "<remote ref>", mission: { title: "cc-batch: <short instruction>" } })
```

For each unit, the `task` must be fully self-contained, because the worker starts from a fresh context in a worktree that does not contain the plan. Include:
- The overall goal (the user's instruction)
- This unit's specific task (title, branch name, file list, change description, copied verbatim from your plan)
- Any codebase conventions you discovered that the worker needs to follow
- The e2e test recipe from your plan (or "skip e2e because ...")
- The worker instructions below, copied verbatim:

```
After you finish implementing the change:
1. **Code review**: Review your own diff against the base following the `review-mechanics` skill (it reports findings; it does not edit code). Fix every blocker and important finding before continuing.
2. **Run unit tests**: Run the project's test suite (check for package.json scripts, Makefile targets, or common commands like `npm test`, `bun test`, `pytest`, `go test`). If tests fail, fix them.
3. **Test end-to-end**: Follow the e2e test recipe from the coordinator's prompt (below). If the recipe says to skip e2e for this unit, skip it.
4. **Leave it ready to commit**: Create this unit's branch with `git switch -c <branch>` and leave every change uncommitted on it. Do not commit, push, or open a PR, and do not hand-roll `git commit`, `git push` or `gh pr create`: the `commit` and `pr` skills are user-invoked only (`disable-model-invocation`), so the user runs `/commit` and `/pr` on this branch. If a guardrail blocks a git command, do not work around it.
5. **Report**: List the files you changed and the test and e2e results, then end with a single line so the coordinator can track it: `PR: none - commit skill is user-invoked; worktree <worktree path>, branch <branch>`. If you could not finish, end with `PR: none - <reason>`.
```

## Phase 3: Track Progress

After launching, render an initial status table:

| # | Unit | Status | PR |
|---|------|--------|----|
| 1 | <title> | running | - |
| 2 | <title> | running | - |

Then repeat until the workflow settles:

1. Call `bg_wait({ id: "<workflow run id>" })`. It returns when the run changes or needs attention, or with `window_elapsed` while work is still running.
2. Call `subagent_supervisor({ action: "pending" })`. Relay every worker question to the user through `ask_user`, verbatim with its options, and send the user's answer back with `subagent_supervisor({ action: "reply", replyTo, message })`. Never answer a decision on the user's behalf.
3. Call `subagent({ action: "status", id: "<workflow run id>" })` and re-render the table: a child that settled with a `PR: <url>` line is `done` with that link, a child whose `PR: none` line names its worktree and branch is `ready` with that branch, and any other settled child is `failed` with a brief note taken from its report.

When the workflow completes, its result carries every unit's `PR:` line and `artifactPaths`.
Render the final table and a one-line summary (e.g., "0/24 units landed as PRs, 22/24 ready for /commit and /pr").
pi-subagents captures each worktree's uncommitted changes as a patch in a handoff manifest (listed in `artifactPaths`) and may then remove the worktree, which leaves the unit's branch empty at `baseRef`.
The handoff patch is therefore the authoritative copy of each `ready` unit: report its branch, its handoff manifest path, and its worktree only if it still exists.
List retained worktrees with `subagent({ action: "worktree.cleanup", mode: "plan" })` and report them rather than removing anything.
Finish by telling the user how to land each unit: in a retained worktree, run `/commit` and `/pr` there; otherwise switch to the unit's branch, apply its handoff patch, then run `/commit` and `/pr`.
