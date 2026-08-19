# Per-project development domains

Every project on `localhost` shares one cookie jar and one `localStorage`, so signing into one admin panel clobbers another's session even on a different port.
Cookies isolate by hostname and ignore the port entirely, so a distinct hostname is the whole fix.

```fish
lokl add my-custom-project
astro dev --port (lokl port my-custom-project)
```

```
http://my-custom-project.localhost        # through the proxy on :80
http://my-custom-project.localhost:3001   # straight at the dev server
```

Both spellings work, both live at once beside every other project, separate sessions, and no repo change in any worktree.

**Use the portless one.**
A port reaches the dev server whatever hostname is in front of it, so `http://anything.localhost:3001` serves whichever project holds 3001, and `localhost:3001` and `127.0.0.1:3001` do too.
Cookies key on hostname and ignore the port, so signing in through the wrong name stores a session under a domain whose real server is later handed it, which is the problem this exists to solve wearing a different hat.
On `:80` every domain shares one port, so the `Host` header is the only thing that can tell them apart and the hostname is finally authoritative.

Keep the ported URL for a healthcheck, a script, or telling a broken site file apart from a dev server that never started.

**No `--host` needed.**
Caddy dials `127.0.0.1` with an `[::1]` fallback, so a dev server on its default loopback bind is already reachable.
`--host` binds every interface, which puts the dev server on the LAN and is the reason a stopped proxy can look like a running one.

## The two halves

A dev domain is two things that have to agree, and [`lokl`](../scripts/lokl/lokl) exists because keeping them in agreement by hand is what went wrong before.

**A `/etc/hosts` entry**, so the name resolves even where the system declines to.
This half is belt and braces rather than the load-bearing thing it was written as.
macOS 26 resolves every `*.localhost` name to loopback on its own, per RFC 6761, so `getaddrinfo` and `curl` answer for a name in no file at all:

```
zzz-random-9k3.localhost  ->  127.0.0.1, ::1     # never added anywhere
foo.test                  ->  does not resolve
```

The block stays because it costs one idempotent line and it survives a DNS profile, an MDM payload or a VPN's split-DNS shadowing that handling, and because a fresh machine on an older macOS has nothing else.
Do not read it as the reason the domains work here.

**A site file in [sites/](sites/)**, so the portless URL answers.
One file per domain, imported by the [Caddyfile](Caddyfile), reverse-proxying `:80` to the port the dev server binds.

The site files are the record and are committed here; the hosts block is derived from them.
That is what makes `lokl sync` enough to bring a fresh clone up, and it is why nothing in `/etc/hosts` is worth editing by hand.

## Why not dnsmasq

Wildcard DNS through `dnsmasq` and `/etc/resolver/localhost` is the usual answer to this, and it does not work on macOS 26.
mDNSResponder intercepts every TLD absent from the IANA root zone, `.localhost` and `.test` and `.internal` alike, and answers it as multicast DNS without ever consulting the nameserver the resolver file names.
The symptom is that `dig @127.0.0.1 foo.localhost` succeeds, `ping` and `curl` and `getaddrinfo` all fail, and `tcpdump` shows zero packets reaching dnsmasq, so the setup looks correct from the one angle that does not matter.
A hosts entry is what is left, and one line per project is a cheaper price than a daemon that silently does nothing.

This is also why the suffix stays `.localhost` rather than something prettier.
Vite's `allowedHosts` permits `localhost` and `*.localhost` and rejects everything else over plain HTTP, so any other suffix would need `allowedHosts` written into a committed `vite.config.ts` where the team would see it.

## Commands

```fish
lokl add my-custom-project        # site file, hosts entry, reload, and a resolution check
lokl add my-custom-project 3001   # the same, on a port you name rather than one derived
lokl remove my-custom-project     # both halves
lokl port my-custom-project       # the bare number, for a dev script to read
lokl list                    # every domain, its port, and whether anything answers
lokl sync                    # rebuild the hosts block from the site files
lokl start                   # bind :80 (sudo), without registering anything at boot
lokl stop
lokl status
lokl reload                  # a site change into the running proxy
lokl validate                # parse the config without touching the proxy
```

`add` is idempotent: the same port again is a no-op, a different port repoints the domain and says so.
It refuses `:80` and `:2019`, which Caddy holds for itself and its admin API, since a site pointing at either proxies to itself.
It warns rather than refuses when two domains name the same port, because that is occasionally deliberate and always worth knowing.

The last thing `add` does is ask the system resolver whether the name now resolves.
Writing the file proves nothing on its own, and this is the one assumption the whole design rests on.

## Ports, which you no longer pick

Leave the port off and it is derived from the working directory:

```fish
cd ~/Developer/my-custom-project
lokl add my-custom-project          # :26445, and the same number every time
```

The seed is the directory, so two worktrees of one repo sitting side by side get different ports without anybody keeping a list.
The digest is sha256 rather than Python's `hash`, which is salted per process and would hand out a different port on every run.

The window is `20000-39999`, and both edges are chosen:

- **Below 49152**, where macOS starts the ephemeral range it hands to outbound sockets, so a derived port is never one the kernel might have already given away.
- **Above 19999**, clear of every port a dev server picks by default (3000, 3001, 4321, 5173, 8000, 8080) and of the databases beside them, so a derived port cannot collide with something started by hand.

Two projects can still hash into one slot: 20000 slots make that about a one-in-a-thousand event at ten projects, not an impossible one.
`lokl` walks forward from the hashed slot until it finds a port no other domain holds, so the answer stays a function of the directory and of what is already assigned, and the collision is invisible.
A domain that already has a port keeps it, because re-deriving would let an unrelated project taking the slot silently move a domain that was working.

To use it in a dev script, ask for the recorded port by name:

```fish
astro dev --host my-custom-project.localhost --port (lokl port my-custom-project)
```

`lokl port <name>` reads the site file, which is the number the proxy is actually pointing at and is the same on every clone.
`lokl port` with no name answers for the working directory instead, and agrees with the recorded port when run from the directory `add` was run in.
It did not always: the bare form counted a domain's own recorded port among the ports to step over, so it printed one past the number the proxy was pointing at.
Prefer the named form in anything committed anyway, because the seed is the working directory: run bare from a subdirectory and you get that subdirectory's number, not the project's.

Its output is a bare number with no glyph and no colour, which is the one place here that steps outside the shared line vocabulary, for the same reason `claude-kit list --json` does: the whole content is a fact rather than an account of what a command did.

## Naming a port yourself

Pass it explicitly and nothing is derived.
Two cases need this:

- **The script hardcodes `--port`.** `drivein` runs `astro dev --host 0.0.0.0 --port 4321`, and appending a second `--port` is not reliably an override. Run the binary instead: `npx astro dev --port 4322`.
- **The project sets `strictPort: true`.** `pickleballontime` does, on every app. Those ports cannot move, and the server exits rather than incrementing if something else holds one. Give `lokl` the port they already use.

Either way the dev server still has to be started on that port.
Nothing discovers a running server, so a worktree started with neither the flag nor `lokl port` will pick a port of its own and the domain will proxy to nothing.
When a page loads the wrong project, or none, that is why.

When a domain does not answer, this is the one command that gives the answer directly:

```fish
lsof -nP -iTCP:3001 -sTCP:LISTEN    # the address family it prints is the whole story
```

## Why the upstream is a pair

A dev server may bind IPv6 loopback only, listening on `[::1]:3001` and nothing on IPv4.
A lone `127.0.0.1` upstream is then refused and Caddy answers 502 while `lsof` plainly shows the port held, which the browser renders as "This page isn't working" without saying which leg failed.
Listing both addresses covers either choice, and covers a server on `0.0.0.0` too, since that includes loopback.

`lb_policy first` is what makes the pair a failover rather than a round robin.
Caddy's default selection policy is random, so two upstreams with no policy would send about half the requests to whichever address nothing is listening on: intermittent 502s that read as a flaky dev server rather than a config error.
`fail_duration` is what marks a refused address down instead of retrying it on every request.

**Never write `0.0.0.0` as an upstream.**
It is a bind address meaning every interface, and dialling it does not fail fast, it times out, so each request stalls for the full dial timeout instead of erroring.
A server bound to `0.0.0.0` is already reachable through the `127.0.0.1` entry.

The hosts entry lists one address, `127.0.0.1`, where the file would happily carry `::1` as well, but that no longer decides anything.
macOS answers every `*.localhost` name with both families whatever the entry says, which `lokl add` will show you:

```
✓ my-custom-project.localhost resolves to 127.0.0.1, ::1
```

So the upstream pair is what settles "which family did it bind", on its own.
The single line stays because a second one would add nothing the resolver is not already doing.

## Two symlinks, not one

The playbook links the Caddyfile into the Homebrew prefix, and links [sites/](sites/) beside it.
The second link is not redundant.
Caddy resolves an `import` path against the directory of the file it was handed and does not follow that file's symlink back into this repo, so without it the glob matches nothing.
A glob matching nothing is a warning rather than an error, so the proxy would start, validate clean, and serve no domains at all.

## Service

Caddy binds `:80`, which needs root, so `lokl start` takes sudo.
It is **off until you ask for it**: nothing starts it at login or boot.

`brew services` drives none of this, and cannot.
Its `run` is refused as root unconditionally (`Services::CLI`, `elsif System.root?`), so the combination this needs (root, and nothing on the boot path) is unreachable through it.
Its `start` is the only verb allowed as root and writes `/Library/LaunchDaemons/homebrew.mxcl.caddy.plist`, whose `RunAtLoad` is exactly what brings Caddy up with the machine.
Caddy's own `start` daemonizes and writes nothing at all, so the process lasts until `lokl stop` or the next reboot.
The playbook still deletes that boot plist, which converts a machine that ran the earlier `brew services start` and is otherwise a no-op.

Only `start` needs root, because only it binds the port.
The rest either read a file or post to the admin API on `127.0.0.1:2019`, which is unauthenticated over loopback, so running one under sudo is harmless and buys nothing.
`lokl add` reloads through that API rather than restarting anything, so an in-flight request survives a new domain being added.
A `lokl stop` and `lokl start` is only needed for a change to the global block at the top of the Caddyfile.
