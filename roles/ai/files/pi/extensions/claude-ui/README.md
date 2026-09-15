# Claude-style conversation UI

## Status

Disabled.
This directory is intentionally absent from `PI_EXTENSIONS`, so Ansible does not link it into Pi's auto-discovery directory.

## Why it exists

The experiment tests a Claude Code-like visual hierarchy for Pi while preserving Pi's public extension APIs and selected theme.
Keeping the implementation documents the completed design and makes future evaluation possible without enabling it accidentally.

## What it does when enabled

`index.ts` re-registers Pi's built-in tool renderers with semantic call and result rows, bounded previews, and native expansion controls.
It also changes user, assistant, working, and hidden-thinking presentation.
It does not alter tool execution or model context.

## Why it is parked

Replacing core conversation rendering has a larger maintenance surface than the value currently gained.
The active status line and velocity extensions provide the useful persistent information without taking ownership of Pi's built-in message UI.

## Verification

The parked implementation remains covered by `lib/python/tests/test_pi_claude_ui.py`.
Its design history is in `docs/design/pi-claude-conversation-rendering.md`.
