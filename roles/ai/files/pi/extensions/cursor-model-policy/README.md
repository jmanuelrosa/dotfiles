# Cursor model policy

## Why it exists

Pi's `enabledModels` setting limits model cycling and selection, but it does not prevent restored sessions, extensions, or agents from requesting another model from an installed provider.
Cursor usage must be limited to the subscription-backed models selected in this repository.

## What it does

`index.ts` wraps the provider registered by `pi-cursor-sdk`.
It filters the Cursor catalog and rejects disallowed model IDs before either streaming method reaches the SDK.
The exact allowlist comes from `roles/ai/files/pi/model-routing.json`.

The policy rechecks the provider at lifecycle boundaries because `/cursor-refresh-models` replaces the Cursor registration.
A global marker makes the wrapper idempotent when parent and child sessions share one provider registry.
Authentication, request options, and transport remain owned by `pi-cursor-sdk`.

## Limits

This policy applies only while the extension is loaded.
It does not control standalone Cursor clients, Cursor-native delegation inside the SDK, or account-level on-demand billing.

## Verification

Registry, transport, refresh, and cross-session wrapping behavior are covered by `lib/python/tests/test_pi_model_routing.py`.
The routing and billing constraints are documented in `docs/internals/pi-harness.md`.
