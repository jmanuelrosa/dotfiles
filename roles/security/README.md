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

## Unmanaged settings

This app is installed but its settings are not restored, for the reason given.

| App | Why | Manual step |
|---|---|---|
| NextDNS | Filtering rules live in the NextDNS account; the app stores only its private configuration ID and two toggles inside its sandbox container | Open the app, enter the configuration ID from my.nextdns.io, and enable start at login |
