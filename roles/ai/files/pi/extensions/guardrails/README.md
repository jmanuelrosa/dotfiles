# Guardrails

## Why it exists

Claude Code and Pi should enforce the same repository gates without maintaining two copies of each policy.

## What it does

`index.ts` adapts Pi `tool_call` events to the JSON input expected by the Python hooks under `roles/ai/files/claude/hooks/`.
It bridges edit payloads, active skill detection, Pi-specific refusal guidance, and the cloud read-only decision shape.
It also exposes the shared rtk and Cursor footer statuses.

The policy decisions remain in the Python hooks.
This extension only translates events and maps hook exit status back to Pi.
Guard execution fails open so an adapter failure does not create a refusal that no user can resolve.

## Verification

Adapter behavior and policy-boundary checks are covered by `lib/python/tests/test_pi_guardrails.py`.
The two-layer Pi permission design is documented in `docs/internals/pi-harness.md`.
