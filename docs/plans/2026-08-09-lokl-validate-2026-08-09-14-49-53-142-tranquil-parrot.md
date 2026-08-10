# Fix the Caddyfile so `lokl:validate` passes

## Context

`lokl:validate` fails:

```
Error: adapting config using caddyfile: Unexpected '}' because no matching opening brace, at /opt/homebrew/etc/Caddyfile:21
```

The cause is not the working-tree edit. Every site block in this file has always been written on one line:

```
http://outdoor-maps.localhost               { reverse_proxy 127.0.0.1:3001 }
```

Caddyfile syntax does not allow that. An opening brace must end its line and a closing brace must sit on a line of its own, so the parser reaches the `}` having never opened a block. Confirmed against caddy v2.11.4: the HEAD version of the file fails the same way at its first site block (line 23), and the same domain in multi-line form validates clean. **This file has never validated**, which means the proxy has never actually served a per-project domain: `caddy run` reads the same adapter and would have refused to start.

Outcome: `lokl:validate` reports `Valid configuration`, and the docs stop teaching the form that caused this.

## Changes

### 1. `roles/apps/files/caddy/Caddyfile`

Convert the site block to the only valid form. Keep the single `outdoor-maps` entry (confirmed intentional) and the global `auto_https off` block, which is already correct.

```
http://outdoor-maps.localhost {
	reverse_proxy 127.0.0.1:3001
}
```

Tabs for the body line, matching the global block above it.

Extend the header comment with a fourth load-bearing entry, so the next domain is not added one-line again:

> `{ … }` A site block cannot be written on one line. Caddy needs the opening
> brace at end of line and the closing brace on its own, or it reports
> "Unexpected '}' because no matching opening brace" and the proxy will
> not start at all.

The file is symlinked to `/opt/homebrew/etc/Caddyfile` by `roles/apps/tasks/development.yml:121`, so the edit takes effect with no play run (see CLAUDE.md, "Config files are symlinks, not copies").

### 2. `roles/apps/files/caddy/README.md`

Three corrections, all confirmed with you:

- **"Adding a project"** (line 15): "One line in [Caddyfile](Caddyfile)" is the instruction that produced the bug. Replace with the four-line block form shown above, and state the brace rule.
- **Alias names** (lines 57-60, and `dev:start` / `dev:stop` in the prose at line 63): the aliases are `lokl:start`, `lokl:stop`, `lokl:status`, `lokl:validate`, plus `lokl:config` for the reload, which the README does not mention at all. Source of truth is `roles/shell/files/fish/conf.d/aliases.fish:59-63`.
- **sudo** (lines 57-59): the comments read `# sudo brew services run caddy`. You verified the no-sudo form works, and the working tree already dropped `sudo --preserve-env=HOME` from the three aliases, so drop it from the README too.

### 3. `roles/apps/tasks/development.yml` (comment only)

The block comment at lines 128-135 carries the same two errors as the README: it names `dev:start` / `dev:stop`, and it asserts "`brew services` under sudo is the only way to drive it". Correct both. The `become: true` on the task itself stays: that one removes `/Library/LaunchDaemons/homebrew.mxcl.caddy.plist`, which genuinely needs root, and it is unrelated to whether the client aliases do.

## Out of scope

The `sudo --preserve-env=HOME` removal in `roles/shell/files/fish/conf.d/aliases.fish` is left exactly as your working tree has it. It is already uncommitted and you confirmed it works.

## Verification

```fish
lokl:validate    # expect: Valid configuration
```

That is the failing command, and it reads the symlinked file directly, so it needs no play run.

End to end, since a passing parse is not the same as a working proxy:

```fish
lokl:start
lokl:status                                                  # Running: true
curl --resolve outdoor-maps.localhost:80:127.0.0.1 \
     -sS -o /dev/null -w '%{http_code}\n' \
     http://outdoor-maps.localhost                           # needs the dev server on 3001
```

`curl` needs `--resolve` because macOS `getaddrinfo` does not special-case `*.localhost`; only browsers do (README, "Why the hostnames need no /etc/hosts"). A browser hitting `http://outdoor-maps.localhost` needs no flag.

`make lint` for the `development.yml` comment edit. No pytest suite covers this role.
