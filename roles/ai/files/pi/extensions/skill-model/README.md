# Skill model routing

## Why it exists

Claude Code honors the `model:` field in shared skill frontmatter, but Pi's skill loader drops it.
The same skill should use the same model intent in both harnesses without a second declaration.

## What it does

`index.ts` detects explicit skill invocations and reads of `SKILL.md`, resolves the declared model against the session catalog, and pins it for one agent run.
It restores the previous model and thinking level when the run settles.

Redirects and account-capacity fallbacks come from `roles/ai/files/pi/model-routing.json`.
Legacy Cursor pins are redirected before lookup, and configured source models can retry on their mapped Codex fallback after authentication, quota, subscription, or spend-limit failures.
The previous state is persisted as a custom session entry so reload and resume can restore it.

## Verification

Resolution, fallback, retry, persistence, and restoration are covered by `lib/python/tests/test_pi_skill_model.py` and `lib/python/tests/test_pi_model_routing.py`.
The routing policy is documented in `docs/internals/pi-harness.md`.
