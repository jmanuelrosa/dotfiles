# Guardrails

## Why it exists

Claude Code and Pi should enforce the same repository gates without maintaining two copies of each policy.

## What it does

`index.ts` adapts Pi `tool_call` events to the JSON input expected by the Python hooks under `roles/ai/files/harness/hooks/`.
It also runs the table's `prompt_submit` gates on Pi's `input` event, before `/skill:name` expands, and refuses a blocked prompt with a notification.
It bridges edit payloads, active skill detection, Pi-specific refusal guidance, and the cloud read-only decision shape.
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
The two-layer Pi permission design is documented in `docs/internals/harnesses.md`.
