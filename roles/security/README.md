# security

Installs Mac App Store security apps (currently NextDNS).

## What it does

- Runs `mas list` to capture currently installed App Store apps.
- For each entry in `MAS_APPS`, runs `mas install <id>` only if not already present.

## Vars

- `MAS_APPS` (defaults/main.yml) — list of `{name, id}` dicts. Find IDs with `mas search <name>`.

## Prerequisites

- Requires `mas` (installed by the `brew` role).
- Requires the user to be signed into the App Store (`mas signin` is interactive and not scripted).

## Notes

Replaced an earlier broken implementation that ran `mas search nextdns` (a read-only search that never installed anything).
