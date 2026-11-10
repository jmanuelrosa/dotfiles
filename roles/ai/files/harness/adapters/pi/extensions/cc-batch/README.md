# cc-batch

## Why it exists

Claude Code's `/batch` plans a large change and runs independent worktree-isolated workers.
This extension provides `/cc-batch <instruction>` in Pi, using `@tintinweb/pi-subagents`.

## What it does

`index.ts` reads `prompt.md`, substitutes the instruction for `{{instruction}}`, and sends it as a user message, queued as a follow-up when the agent is busy.
An empty instruction prints usage; a directory outside a Git repository is refused.

The orchestration prompt has three phases:

- Research with foreground `Agent` calls using `Explore`, write the plan under `docs/plans/`, and get approval through `ask_user`.
- Fetch and pin the target branch's commit, create one ordinary Git worktree and planned branch per unit, and launch a background `SubagentWorkflow` using `parallel()` and `agent()` with `general-purpose` workers.
- Wait for the completion notification, report every unit's branch and retained worktree, and relay any blocked worker's question to the user before restarting that unit.

Every task includes its absolute worktree path and instructs the worker to scope all file operations and shell commands to it, because workflow agents initially start in the source checkout.
The workflow script lives beside the retained worktrees under the durable root approved in the plan and is passed through `scriptPath`.
Uncommitted worker code is never kept in an OS temporary directory.
Pi's `/agents` menu shows workflow progress and lets the user stop or skip workers.

## Why worktrees are retained

The package's automatic worktree cleanup commits changes with hooks skipped and removes the worktree.
That conflicts with this harness's commit policy, so `subagents.json` disables automatic worktree isolation.
The coordinator creates ordinary worktrees with `git worktree add -b`, and neither the workflow nor the workers remove them.

Workers review and test their changes, then leave them uncommitted on the planned branches.
The user runs `/commit` and `/pr` inside each ready worktree.
Failed and blocked units retain their worktrees too, so their partial changes remain available.
The source checkout's uncommitted files stay untouched; workers start from the pinned remote commit, not the local plan.

## Verification

Usage, prompt substitution, busy-session delivery, and execution of the workflow example are covered by `lib/python/tests/test_pi_cc_batch.py`.
The workflow test exercises ready and failed worker results without invoking a model or creating worktrees.
Actual multi-agent execution still requires a configured provider and manual verification in Pi.
