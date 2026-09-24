# Velocity

## Why it exists

The shared status line should show the scale of changes made during the current Pi session without running a fresh diff on every render.

## What it does

`index.ts` counts added and removed lines from the unified patches Pi records for successful edit results and publishes a compact footer status.
Writes count as additions because the replaced content is no longer available after the event.
The result is a glanceable activity measure, not an audit substitute for `git diff --stat`.

The glyph comes from `roles/ai/files/harness/statusline.json` so Claude Code and Pi use the same vocabulary.

## Verification

Patch counting, session restoration, status updates, and shared configuration are covered by `lib/python/tests/test_pi_velocity.py` and `lib/python/tests/test_statusline_shared.py`.
