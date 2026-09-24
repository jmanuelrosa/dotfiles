# Minion

## Why it exists

Minion provides an explicit way to hand a coding goal to a trusted Pi session and let it continue unattended.

## What it does

`index.ts` registers `/minion` and delegates start, status, watch, and cancellation operations to the implementation under `roles/ai/files/harness/adapters/pi/minion/`.
The extension is the interactive command boundary; lifecycle state, execution, checkout handling, and delivery remain in the Minion modules.
Loading the extension never starts work by itself.

Minion is enabled only when `MINION_ENABLE=1`.

## Verification

The extension and unattended runtime are covered by `lib/python/tests/test_pi_minion.py`.
The approved product behavior is specified in `docs/specs/minion.md`.
