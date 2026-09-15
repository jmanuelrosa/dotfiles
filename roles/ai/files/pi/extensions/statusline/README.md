# Status line

## Why it exists

Pi's built-in footer reports raw session numbers but does not apply this repository's shared interpretation of context pressure, project toolchain, and edit activity.
Adding a second context display would duplicate and potentially contradict the built-in footer, so this extension replaces it.

## What it does

`index.ts` installs a two-row footer that renders context usage, model and provider, thinking level, tokens, cache use, cost, branch, package manager, and the statuses published by other extensions.
It reads shared labels, glyphs, package-manager rules, and the handoff threshold from `roles/ai/files/statusline.json`.

The footer cannot reproduce Pi's private auto-compaction and subscription markers.
A missing optional value removes only its segment.

## Verification

Rendering, width priorities, session arithmetic, package-manager detection, and public API compatibility are covered by `lib/python/tests/test_pi_statusline.py` and `lib/python/tests/test_statusline_shared.py`.
The ownership trade is documented in `docs/internals/pi-harness.md`.
