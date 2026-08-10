# Caddy: per-project development domains

Every project on `localhost` shares one cookie jar and one `localStorage`, so signing into one admin panel clobbers another's session even on a different port.
Cookies isolate by hostname and ignore the port entirely, so a distinct hostname is the whole fix.

```
http://front.localhost        ->  127.0.0.1:3000
http://front-e2e.localhost    ->  127.0.0.1:3001
```

Both live at once, separate sessions, no repo change in either worktree.

## Adding a project

One block in [Caddyfile](Caddyfile), then reload:

```
http://outdoor-maps.localhost {
	reverse_proxy 127.0.0.1:3001 [::1]:3001 {
		lb_policy first
		fail_duration 5s
	}
}
```

The braces are not a style choice. Caddy needs the opening brace at end of line and the closing brace on a line of its own, so the same entry collapsed onto one line fails to parse and the proxy refuses to start.

## Why the upstream is a pair

A dev server may bind IPv6 loopback only, listening on `[::1]:3001` and nothing on IPv4. A lone `127.0.0.1` upstream is then refused and Caddy answers 502 while `lsof` plainly shows the port held, which the browser renders as "This page isn't working" without saying which leg failed. Listing both addresses covers either choice, and covers a server on `0.0.0.0` too, since that includes loopback.

`lb_policy first` is what makes the pair a failover rather than a round robin. Caddy's default selection policy is random, so two upstreams with no policy would send about half the requests to whichever address nothing is listening on: intermittent 502s that read as a flaky dev server rather than a config error. `fail_duration` is what marks a refused address down instead of retrying it on every request.

**Never write `0.0.0.0` as an upstream.** It is a bind address meaning every interface, and dialing it does not fail fast, it times out, so each request stalls for the full dial timeout instead of erroring. A server bound to `0.0.0.0` is already reachable through the `127.0.0.1` entry above.

When a project does not answer, this is the one command that gives the answer directly:

```fish
lsof -nP -iTCP:3001 -sTCP:LISTEN    # the address family it prints is the whole story
```

```fish
lokl:config   # caddy reload --config /opt/homebrew/etc/Caddyfile
lokl:validate # parse it first if you want the error without touching the running process
```

Reload goes through the admin API on `127.0.0.1:2019` rather than restarting anything, so an in-flight request survives it. That API only exists while Caddy runs, so `lokl:config` against a stopped proxy fails with `dial tcp [::1]:2019: connect: connection refused`, which means "start it" rather than anything about the Caddyfile. `lokl:start` is the whole fix.

`caddy fmt` treats a comment as attached to whatever follows it, and collapses a blank line between the two. That is why the global block below the header carries a comment of its own: without it, every reload warns that the file is unformatted.

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

Caddy binds `:80`, which needs root, so `lokl:start` takes sudo. It is **off until you ask for it**: nothing starts it at login or boot.

```fish
lokl:start     # sudo caddy start --config /opt/homebrew/etc/Caddyfile
lokl:stop      # caddy stop
lokl:status    # the pid and command line, or "caddy is not running"
lokl:validate  # parse the Caddyfile without touching the running process
lokl:config    # reload a site change into the running process
```

`brew services` drives none of this, and cannot. Its `run` is refused as root unconditionally (`Services::CLI`, `elsif System.root?`), so the combination this needs (root, and nothing on the boot path) is unreachable through it; its `start` is the only verb allowed as root and writes `/Library/LaunchDaemons/homebrew.mxcl.caddy.plist`, whose `RunAtLoad` is exactly what brings Caddy up with the machine.
Caddy's own `start` daemonizes and writes nothing at all, so the process lasts until `lokl:stop` or the next reboot.
The playbook still deletes that boot plist, which converts a machine that ran the earlier `brew services start` and is otherwise a no-op.

Only `lokl:start` needs root, because only it binds the port. The other four read a file or post to the admin API on `127.0.0.1:2019`, which is unauthenticated over loopback. Running one under sudo is harmless but buys nothing.

`lokl:config` is enough for a site change. A `lokl:stop` and `lokl:start` is only needed for the global block at the top of the Caddyfile.
