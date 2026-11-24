# Cursor model policy

## In one sentence

A billing guard: pi can only send requests to the Cursor models listed in `cursorModels`, whatever asks for them.

## Why it exists

The Cursor subscription covers a fixed set of models.
Any other Cursor model draws on Cursor's separate "Other Models" allowance or on-demand billing.
`pi-cursor-sdk` registers the whole Cursor catalog, and several paths can select a model from it without going through any pin or setting this repository controls:

- picking a model by hand with `/model`;
- resuming a session that was saved on an old Cursor model;
- an explicit `model` passed to a subagent launch;
- a bare `opus` resolving to Cursor's literal `opus` alias;
- `/cursor-refresh-models`, which re-registers the full catalog.

Pi's `enabledModels` setting only limits model cycling and selection, so it does not close those paths.

## What it does

`index.ts` wraps the provider registered by `pi-cursor-sdk` and enforces the allowlist from `roles/ai/files/harness/adapters/pi/model-routing.json` (`cursorModels`) in two places:

1. **Catalog:** models outside the list are removed from the Cursor provider, so pi cannot resolve or select them.
2. **Request:** a request for a model outside the list throws before either stream method reaches the SDK, so nothing is billed.

The wrapper is re-applied at lifecycle boundaries because `/cursor-refresh-models` replaces the Cursor registration.
A global marker keeps it idempotent when parent and child sessions share one provider registry.
Authentication, request options and transport remain owned by `pi-cursor-sdk`.

## Example

With the current allowlist:

| Request | Result |
|---|---|
| `/model cursor/composer-latest` | Selected, and requests go to Cursor |
| `/model cursor/grok-4.7@256k` | Selected, and requests go to Cursor |
| `/model cursor/claude-opus-5` | Not offered: the model is filtered out of the catalog |
| Request from a resumed session still using `cursor/claude-opus-5` | Rejected before reaching Cursor; the error lists the allowed models |
| Skill pinned to `opus` with no redirect | Cannot land on Cursor's `opus` alias, because the alias is filtered out |

To allow another Cursor model, add its id to `cursorModels` and to `enabledModels` in pi's `settings.json`.

## What it is not

It is not a fallback.
It never switches a request to a different model; it only refuses.
Model translation lives in `redirects` in `model-routing.json`, applied by [skill-model](../skill-model/README.md) to skill pins and selected session models, including subagents that load normal extensions.
A redirect from a Cursor model to another provider rewrites a pin, but a hand-picked model or a resumed session can still reach Cursor, and that is the gap this policy covers.

## Limits

This policy applies only while the extension is loaded.
It does not control standalone Cursor clients, Cursor-native delegation inside the SDK, or account-level on-demand billing, which must be disabled in the Cursor account.

## Verification

Registry, transport, refresh and cross-session wrapping are covered by `lib/python/tests/test_pi_model_routing.py`.
