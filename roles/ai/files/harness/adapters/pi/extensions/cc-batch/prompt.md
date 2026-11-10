# Batch: Parallel Work Orchestration

You are orchestrating a large, parallelizable change across this codebase.

## User Instruction

{{instruction}}

## Phase 1: Research and Plan

Pi has no plan mode, so the plan is a file under `docs/plans/` and approval is an explicit `ask_user` question.
Until the user approves, do not edit any file other than the plan.

1. **Understand the scope.** This command is the user's authorization to delegate. Launch one or more research agents in the foreground (`Agent({ subagent_type: "Explore", prompt: "...", description: "Research the batch scope", run_in_background: false })`, because you need their results) to deeply research what this instruction touches. Find all the files, patterns, and call sites that need to change. Understand the existing conventions so the migration is consistent.
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
   If you cannot find a concrete e2e path, use `ask_user` to ask how to verify this change end-to-end, offering 2 to 3 specific options based on what you found. Do not skip this: the workers cannot ask the user themselves.
   Write the recipe as a short, concrete set of steps that a worker can execute autonomously, including setup and the exact verification command or interaction.
4. **Write the plan.** Write it to `docs/plans/YYYY-MM-DD-<slug>.md`, with today's date and a short kebab-case slug of the instruction. Include:
   - A summary of what you found during research
   - A numbered list of work units: for each, a short title, its branch name, the list of files/directories it covers, and a one-line description of the change
   - The e2e test recipe (or "skip e2e because ..." if the user chose that)
   - A durable worktree root within the harness's writable paths, preferably an existing ignored directory; ask the user for a location if none exists
   - The exact worker instructions you will give each agent (the shared template)
5. **Get approval.** Call `ask_user` with the question "Approve the batch plan in `<plan path>`?", a `context` that lists the unit count and titles, and the options "Approve", "Revise" and "Cancel". On "Revise" or a freeform answer, update the plan and ask again. On "Cancel", stop.

## Phase 2: Spawn Workers (After Plan Approval)

**Pin the base and prepare retained worktrees.**
Fetch the branch the PRs will target and resolve its remote-tracking ref to a commit, so all units start at exactly the same commit without any local-only plan changes.
Create a unique batch directory under the approved durable worktree root with `mktemp -d` and an explicit path template.
Do not keep uncommitted worker changes in an OS temporary directory: a reboot or cleanup could delete them.
For each unit, run `git worktree add -b <planned branch> <absolute unit worktree path> <base commit>`.
Record each absolute path in the plan and the unit's task.
Do not commit, stash, move or delete the user's existing changes to prepare these worktrees.
If a worktree cannot be created, stop and report the error and any worktrees already created; never fall back to running workers in the source checkout.

Use ordinary Git worktrees, not the package's automatic isolation option.
`@tintinweb/pi-subagents` automatically commits changes and skips hooks when cleaning up its own worktrees, which conflicts with this harness's commit policy.
These manually created worktrees must remain available with their changes uncommitted until the user lands them.

**Write the workflow script.**
Write the script in the batch directory.
Include every unit's self-contained task, planned branch and absolute worktree path as literal data:

```js
export const meta = {
  name: "cc-batch",
  description: "Implement approved independent work units"
};
const units = [
  { "key": "u1", "title": "<title>", "branch": "<unit 1 branch>", "worktree": "<absolute unit 1 worktree>", "task": "<fully self-contained prompt for unit 1>" },
  { "key": "u2", "title": "<title>", "branch": "<unit 2 branch>", "worktree": "<absolute unit 2 worktree>", "task": "<fully self-contained prompt for unit 2>" }
];
return await parallel(units.map(unit => async () => {
  const output = await agent(unit.task, { agentType: "general-purpose", label: unit.key });
  const lines = (output ?? "").split("\n").map(line => line.trim()).filter(line => line.startsWith("PR:"));
  return {
    unit: unit.key,
    title: unit.title,
    branch: unit.branch,
    worktree: unit.worktree,
    pr: lines.at(-1) ?? "PR: none - worker failed or was skipped"
  };
}));
```

Launch the workflow with `SubagentWorkflow({ scriptPath: "<absolute script path>" })`.
It runs in the background and notifies this session when it completes.
The built-in `general-purpose` agent inherits the parent's system prompt, skills and normal extensions.
Do not pass the automatic isolation option to `agent()`; each task already has its own retained worktree.

Each task must be fully self-contained, because the worker starts from a fresh context and its worktree does not contain the plan. Include:

- The overall goal (the user's instruction)
- This unit's task (title, branch name, absolute worktree path, file list and change description)
- Any codebase conventions you discovered that the worker needs to follow
- The e2e test recipe from your plan (or "skip e2e because ...")
- The worker instructions below, copied verbatim:

```text
Work only in the supplied absolute worktree path, on its already-created branch.
Your session may start in the source checkout: use absolute paths for every read, write and edit, and explicitly change to the worktree in every shell command or use git -C <worktree>.
Never edit the source checkout or another unit's worktree.
If you need a user decision, stop and report the question and options; do not choose for the user or try to open an interactive prompt.
After you finish implementing the change:
1. **Code review**: Review your own diff against the base following the `review-mechanics` skill (it reports findings; it does not edit code). Fix every blocker and important finding before continuing.
2. **Run unit tests**: Run the project's test suite, using its documented commands. If tests fail, fix them.
3. **Test end-to-end**: Follow the e2e test recipe from the coordinator's prompt. If the recipe says to skip e2e for this unit, skip it.
4. **Leave it ready to commit**: Stay on this unit's branch and leave every change uncommitted. Do not commit, push, open a PR, remove a worktree or invoke automatic worktree isolation. The `commit` and `pr` skills are user-invoked only; the user runs `/commit` and `/pr` from the retained worktree. If a guardrail blocks a command, do not work around it.
5. **Report**: List the files you changed and the test and e2e results, then end with `PR: none - ready for /commit and /pr; worktree <absolute path>, branch <branch>`. If you could not finish, end with `PR: none - <reason>`, including any user decision needed.
```

## Phase 3: Track Progress

After launching, render an initial status table:

| # | Unit | Status | Branch / worktree |
|---|------|--------|-------------------|
| 1 | <title> | running | <branch>, <path> |
| 2 | <title> | running | <branch>, <path> |

Wait for the workflow's completion notification; do not poll or sleep waiting for it.
The user can inspect progress or stop individual workers through `/agents`, under Workflows.
When the notification arrives, render the final table from its per-unit results: mark a unit `ready` only when its report explicitly says it is ready for `/commit` and `/pr`; mark a missing, failed or skipped result `failed`, and a worker needing a user decision `blocked`.
Relay each blocked worker's question and options through `ask_user` without answering on the user's behalf.
After the user answers, start a new `Agent` task with the original unit instructions, its existing worktree and branch, and that answer; do not create another worktree for it.

Report every retained worktree and branch, including failed or blocked units, and tell the user to run `/commit` and `/pr` inside each ready worktree.
Do not remove worktrees or claim any unit was committed or opened as a PR unless that actually happened through the user's own commands.
