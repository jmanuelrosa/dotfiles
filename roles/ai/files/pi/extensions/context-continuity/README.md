# Context continuity

## Why it exists

A Pi session keeps one branch when the active model changes, but different models do not receive an identical effective context.
Images, reasoning blocks, tools, system prompts, and context-window limits can change across that boundary.

## What it does

`index.ts` records a compact projection of the active model context in session metadata.
On a model switch it compares the new projection with the previous one and warns once when information still present in the conversation cannot survive the switch.
It does not rewrite messages or trigger compaction.

## Runtime surface

The extension listens to `session_start`, `model_select`, and `context`.
Its metadata entries use the `context-continuity` custom type.

## Verification

Behavior and public Pi API usage are covered by `lib/python/tests/test_pi_context_continuity.py`.
The wider design is recorded in `docs/design/cross-model-context-consistency.md`.
