# Caddy: per-project development domains

Every project on `localhost` shares one cookie jar and one `localStorage`, so signing into one admin panel clobbers another's session even on a different port.
Cookies isolate by hostname and ignore the port entirely, so a distinct hostname is the whole fix.

```
http://front.localhost        ->  127.0.0.1:3000
http://front-e2e.localhost    ->  127.0.0.1:3001
```

Both live at once, separate sessions, no repo change in either worktree.

## Adding a project

One line in [Caddyfile](Caddyfile), then reload:

```fish
caddy reload --config /opt/homebrew/etc/Caddyfile
```

No sudo: reload goes through the admin API on `127.0.0.1:2019`, which is already running as root.

## Assigning a port

Pick one nothing else uses and start that worktree with it:

```fish
pnpm dev -- --port 3001
```

This is the deliberate trade. Nothing discovers ports for you, so a second worktree started without the flag will increment into some port of its own choosing, which may or may not be the one its Caddy entry names.
When a page loads the wrong project, that is why.

Two cases need more than the flag:

- **The script hardcodes `--port`.** `drivein` runs `astro dev --host 0.0.0.0 --port 4321`, and appending a second `--port` is not reliably an override. Run the binary instead: `npx astro dev --port 4322`.
- **The project sets `strictPort: true`.** `pickleballontime` does, on every app. Those ports cannot move, and the server exits rather than incrementing if something else holds one. Leave them as they are.

## Why the hostnames need no /etc/hosts

Browsers implement RFC 6761 by resolving `*.localhost` to `127.0.0.1` internally, without consulting the hosts file.
That is also why the suffix cannot be changed to something prettier: Vite's `allowedHosts` permits `localhost` and `*.localhost` and rejects everything else over plain HTTP, so any other suffix would need `allowedHosts` written into a committed `vite.config.ts` where the team would see it.

macOS itself does not special-case the suffix, so anything using `getaddrinfo` does need an entry:

```fish
curl http://front.localhost                      # fails to resolve
curl --resolve front.localhost:80:127.0.0.1 ...  # works
echo "127.0.0.1 front.localhost" | sudo tee -a /etc/hosts   # or this
```

## Service

Caddy binds `:80`, which needs root, so it runs under launchd. It is **off until you ask for it**: nothing starts it at login or boot.

```fish
dev:start     # sudo brew services run caddy
dev:stop      # sudo brew services stop caddy
dev:status    # Running / Loaded / PID
dev:validate  # parse the Caddyfile without touching the running process
```

`run` is the load-bearing subcommand. `brew services start` writes `/Library/LaunchDaemons/homebrew.mxcl.caddy.plist`, whose `RunAtLoad` is what made Caddy come up with the machine; `run` bootstraps the keg's own plist instead and writes nothing there, so the daemon lasts until `dev:stop` or the next reboot.
The playbook keeps that boot plist deleted, so a `brew services start` typed by hand is undone on the next `make run`.

`caddy reload --config /opt/homebrew/etc/Caddyfile` is enough for a site change. A stop and start is only needed for the global block at the top of the Caddyfile.
