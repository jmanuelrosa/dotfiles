# Guardrails

## Why it exists

Claude Code and Pi should enforce the same repository gates without maintaining two copies of each policy.

## What it does

`index.ts` adapts Pi `tool_call` events to the JSON input expected by the Python hooks under `roles/ai/files/harness/hooks/`.
It also runs the table's `prompt_submit` hooks on Pi's `input` event, before `/skill:name` expands, and refuses a blocked prompt with a notification.
A prompt hook's `systemMessage` is shown as a notice and its `additionalContext` is handed to the model as a hidden message on the run that prompt starts, which is what `context-nudge.sh` needs; the context percentage it reads is published from `getContextUsage()` first.
The table's `session_start` hooks run on `session_start`, a `command` entry in the session's directory, and its `stop` hooks run on `agent_settled` (skipped after an interrupt) with a transcript of the finished turn, which is what `skill-recap.sh` reads.
Both are notification-only: a failure is shown and never stops the session.
A hook's `ask` decision opens a `ctx.ui.confirm` dialog, Pi's counterpart to Claude's permission prompt; declining refuses the call, and a session without a UI refuses it unasked, as Claude's print mode does.
It bridges edit payloads, active skill detection, Pi-specific refusal guidance, and the cloud read-only decision shape.
Pi has no Skill tool, so a `read` of a SKILL.md the prompt lists is written into git-skill-gate's transcript as the Skill call Claude would log; a model-started `/ship` then opens the gate after a human answer, as in Claude.
`Agent` and `SubagentWorkflow` calls reach the shared dispatch gate; inline scripts, script paths and local saved workflow names are inspected before execution.
For a package-provided workflow or a replay without source, supply its `scriptPath` so the gate can inspect it.
Direct user-typed `@agent` starts do not emit an `Agent` tool call, so they intentionally bypass the parent-only dispatch check; the user chose direct invocation with this limitation.
The spawned agent's own tools still pass through guards when it loads normal extensions.
It also exposes the shared rtk and Cursor footer statuses.

The policy decisions remain in the Python hooks.
This extension only translates events and maps hook exit status back to Pi.
Guard execution fails closed when configuration, a hook process, or skill evidence is unavailable, or a hook returns an invalid response.
Repair the reported failure and retry; reload Pi after hook-table changes.
An unchecked call is never treated as allowed.
Optional rtk rewriting remains best-effort and preserves the original command on failure.

## Verification

Adapter behavior and policy-boundary checks are covered by `lib/python/tests/test_pi_guardrails.py`.
