# macos

Applies macOS user preferences (`defaults write`) and a few firmware-level tweaks. Scope is intentionally narrow: anything settable via `osx_defaults`, `nvram`, `pmset`, or `chflags`. Broader macOS tooling (Xcode CLT, FileVault, etc.) does NOT belong here.

## What it does

- Loops `community.general.osx_defaults` over `OSX_DEFAULTS` to set keyboard repeat, Finder/Dock options, screensaver password, etc.
- Mutes the boot sound (`nvram SystemAudioVolume=" "`).
- Disables hibernation and the sleep image (`pmset`, `chflags`).
- Switches off the system shortcuts in `MACOS_DISABLED_HOTKEYS` and reloads them so the change applies without logging out. `Ctrl+Space` (previous input source) is freed this way for Herdr's prefix.

## Vars

- `OSX_DEFAULTS` (defaults/main.yml) — list of `{domain, key, type, value, state}` dicts. Override per-profile in `host_vars/<profile>.yml`.
- `MACOS_DISABLED_HOTKEYS` (defaults/main.yml): list of `{id, parameters}` dicts, one per `AppleSymbolicHotKeys` entry to disable. `parameters` is the chord macOS stores for that shortcut.

## Side effects

- Some tweaks (`nvram`, `pmset`, `chflags`) require `become: true`.
- Many settings only take effect after killing the relevant app (Finder, Dock) or rebooting.

## Notes

Only the task that reads firmware and power state (`nvram`, `pmset -g`, `ls -lO`) uses `changed_when: false`.
Each mutating firmware task is `changed_when: true` and gated by a `when` on that read, so it runs and reports a change only when the state differs.
