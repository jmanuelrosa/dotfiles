# macos

Applies macOS user preferences (`defaults write`) and a few firmware-level tweaks. Scope is intentionally narrow: anything settable via `osx_defaults`, `nvram`, `pmset`, or `chflags`. Broader macOS tooling (Xcode CLT, FileVault, etc.) does NOT belong here.

## What it does

- Loops `community.general.osx_defaults` over `OSX_DEFAULTS` to set keyboard repeat, Finder/Dock options, screensaver password, etc.
- Mutes the boot sound (`nvram SystemAudioVolume=" "`).
- Disables hibernation and the sleep image (`pmset`, `chflags`).
- Disables the SSD-irrelevant sudden motion sensor.

## Vars

- `OSX_DEFAULTS` (defaults/main.yml) — list of `{domain, key, type, value, state}` dicts. Override per-profile in `host_vars/<profile>.yml`.

## Side effects

- Some tweaks (`nvram`, `pmset`, `chflags`) require `become: true`.
- Many settings only take effect after killing the relevant app (Finder, Dock) or rebooting.

## Notes

Tasks intentionally use `changed_when: false` for the firmware-level commands — they're idempotent in effect, but their stdout doesn't expose state.
