# Model routing

## Why it exists

Claude Code honors the `model:` field in shared skill frontmatter, but Pi's skill loader drops it.
The same skill should use the same model intent in both harnesses without a second declaration.
Pi subagents can also pin models independently of the parent session, so account-capacity fallback must run inside their child sessions rather than only around skill invocations.

## What it does

`index.ts` detects explicit skill invocations and reads of `SKILL.md`, resolves the declared model against the session catalog, and pins it for one agent run.
It also arms the selected model's route for ordinary agent runs.
Because pi-subagents loads this extension into child sessions, built-in and custom agents use the same routing policy without changing the package.
It restores the previous model and thinking level when the run settles.

Redirects and account-capacity fallbacks come from `roles/ai/files/harness/adapters/pi/model-routing.json`.
Legacy Cursor models are redirected before lookup, and configured source models can retry on their mapped Codex fallback after authentication, quota, subscription, or spend-limit failures.
Ordinary-run routing begins in `before_agent_start`, after Pi's no-auth preflight, so it cannot rescue a source provider with no configured credentials; it handles failures returned after a provider request begins.
Skill pin state is persisted as a custom session entry so reload and resume can restore it.

## Verification

Resolution, fallback, retry, persistence, and restoration are covered by `lib/python/tests/test_pi_skill_model.py` and `lib/python/tests/test_pi_model_routing.py`.
The routing policy is documented in `docs/internals/harnesses.md`.
