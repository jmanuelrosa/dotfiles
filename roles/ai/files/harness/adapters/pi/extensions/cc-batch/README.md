# cc-batch

## Why it exists

Claude Code's `/batch` plans a large change, splits it into independent units, and runs one worktree-isolated background agent per unit that each open a PR.
Pi ships no equivalent, so this extension ports it under a `cc-` prefix that can never collide with a Claude Code built-in.

## What it does

`index.ts` registers `/cc-batch <instruction>`.
It reads `prompt.md` beside the module once at load time, substitutes the instruction for `{{instruction}}`, and sends the result as a user message, queued as a follow-up when the agent is busy.
An empty instruction prints a usage line, and a directory outside any git repository is refused, because every worker needs a worktree.

`prompt.md` keeps the three phases of Claude Code's prompt and changes only the mechanics Pi does differently:

- **Plan.** Pi has no plan mode, so the plan is written to `docs/plans/YYYY-MM-DD-<slug>.md` and approved through `ask_user` from the `pi-ask-user` package.
- **Workers.** One top-level `pi-subagents` workflow, launched with `async: true` and `worktree: true`, starts the packaged `worker` agent once per unit through `runs.all`. The script lives in a temporary file passed as `workflowScriptPath`, because raw workflow `args` are too small for 5 to 30 self-contained prompts.
- **Clean checkout.** Managed worktrees refuse a dirty source checkout, and the plan file is a dirty path, so the orchestrator stops and asks the user to resolve it, recommending a commit because approved plans are committed. `baseRef` is pinned to the remote-tracking branch the PRs target, so that local plan commit never enters a worker's PR.
- **Questions.** Workers cannot reach the user, so a worker that needs a decision asks through `contact_supervisor`, and the orchestrator relays it with `ask_user` and returns the answer through `subagent_supervisor`.
- **Tracking.** `bg_wait`, supervisor polling and run status re-render the `| # | Unit | Status | PR |` table until the run settles, then the final table and an "N/M units landed as PRs" summary.

## Why workers stop before committing

Claude Code's `/batch` workers commit, push and open a PR themselves.
Here the `commit` and `pr` skills carry `disable-model-invocation: true`, which Pi honours as well: a model cannot invoke them, and only a user-typed `/skill:commit` or `/commit` writes the `<skill name="...">` marker the guardrails git-skill gate opens on.
So each worker leaves its change uncommitted on the unit's planned branch and ends with `PR: none - commit skill is user-invoked; worktree <path>, branch <name>`.
pi-subagents captures those uncommitted changes as a patch in a handoff manifest and may remove the worktree afterwards, so the patch, not the branch, is the authoritative copy.
The final report gives each ready unit's branch, handoff manifest and any retained worktree, and the user lands it with `/commit` and `/pr`, applying the patch first when the worktree is gone.

## Verification

Usage, prompt substitution, and busy-session delivery are covered by `lib/python/tests/test_pi_cc_batch.py`.
End to end, `pi -ne -e <path>/index.ts --no-session --mode json -p "/cc-batch <instruction>"` submits the orchestration prompt as the session's input.
Print mode has no UI for the usage line, so an empty `/cc-batch` shows it as a `notify` request only in `--mode rpc`.
