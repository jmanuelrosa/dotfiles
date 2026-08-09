# Per-project development domains with Caddy

## Context

The goal is unchanged from where this started: give each project its own hostname so cookies and `localStorage` stop being shared, and stop worktrees fighting over a port.
What changed is the judgement about how much machinery that deserves.

`lokl` was built to do this automatically: discover each dev server's port by matching `lsof` working directories, manage an `/etc/hosts` block, and splice raw TCP from a privileged proxy of its own.
It works and it is tested, but it is roughly 1,500 lines of Python that become the owner's problem the first time macOS changes `lsof` output or a runtime stops setting a useful working directory.
Caddy does the routing half, is maintained by someone else, and reduces the part that must be maintained here to a list of hostnames.

Two findings from investigating the automatic approach carry over and shape this one:

- **Browsers resolve `*.localhost` to `127.0.0.1` themselves and never read `/etc/hosts`.** So no hosts entry is needed for browser use at all, which removes one of lokl's three jobs outright. `curl` and anything else going through `getaddrinfo` still needs a line, since macOS does not special-case the suffix.
- **Vite permits `localhost` and `*.localhost` in `allowedHosts` by default.** Keeping the `.localhost` suffix is what lets this work with no change to any project's committed config, which was the original constraint: the team must not be affected.

The remaining trade is accepted deliberately.
Ports are assigned by hand, one per worktree, instead of being discovered.
That is the whole of what is given up, and in exchange the collision problem disappears rather than being worked around: if `front` runs on 3000 and `front-e2e` on 3001, nothing needs to seize a port and no server is ever displaced.

## Remove lokl

Nothing is committed, so this is a clean removal rather than a revert of history.

Delete outright:

- `roles/apps/files/scripts/` (the whole tree: shim, `lokl_kit/`, tests, README, the `dotkit` symlink)
- `roles/shell/files/fish/conf.d/lokl.fish`
- `docs/plans/2026-08-08-i-m-working-in-multiple-linked-hamster.md`, which documents an approach not taken

Restore to `HEAD`: `lib/python/dotkit/testing.py` (drops `APPS_SCRIPTS_DIR`), `pytest.ini` (drops the lokl testpath), and `roles/apps/tasks/development.yml` (drops the user-bin link tasks).

Two files need editing rather than reverting:

- `roles/apps/defaults/main.yml`: drop `APPS_SCRIPTS`, and add `caddy` to `BREW_PACKAGES.formulas` in the same pass.
- `roles/shell/tasks/main.yml`: drop the `.config/fish/conf.d/lokl.fish` backup entry, but **keep the `with_fileglob` conf.d task**. It was written for lokl and outlives it: it fixes the same class of drift the functions task below it already guards against, where a hand-maintained list silently leaves a new file unsourced. Reverting the file wholesale would take that with it.

## Add Caddy

### 1. `roles/apps/files/caddy/Caddyfile`

One committed file, no imports and no templating.
Work client names already appear in ten tracked files including `.gitconfig` and `gh-dash/config.yml`, so there is nothing here to keep out of the repo.

```caddyfile
{
	auto_https off
}

http://front.localhost               { reverse_proxy 127.0.0.1:3000 }
http://front-e2e.localhost           { reverse_proxy 127.0.0.1:3001 }
http://front-sentry.localhost        { reverse_proxy 127.0.0.1:3002 }
http://front-ser-1227.localhost      { reverse_proxy 127.0.0.1:3003 }
http://update-dependencies.localhost { reverse_proxy 127.0.0.1:3004 }

http://app.pickleballontime.localhost     { reverse_proxy 127.0.0.1:5173 }
http://admin.pickleballontime.localhost   { reverse_proxy 127.0.0.1:5174 }
http://landing.pickleballontime.localhost { reverse_proxy 127.0.0.1:4321 }

http://drivein.localhost { reverse_proxy 127.0.0.1:4321 }
```

Three things about this are load-bearing and belong in a comment at the top of the file:

- The `http://` prefix. Without it Caddy treats the site as HTTPS, issues a certificate from its internal CA, and asks to be trusted, none of which buys anything on loopback.
- Caddy passes the original `Host` header upstream by default, unlike nginx. That is what keeps Vite's `allowedHosts` satisfied, and it must not be overridden.
- `reverse_proxy` upgrades websockets with no extra configuration, which is what makes Vite HMR work.

The upstream ports are the ones each project already declares, except where two collide.
`pickleballontime` already assigns distinct ports under `strictPort`, so it needs nothing.
The five `addingwell` worktrees all declare 3000 and are the reason the port column is assigned by hand here.

### 2. `roles/apps/tasks/development.yml`

Symlink the Caddyfile to where the Homebrew service reads it, `/opt/homebrew/etc/Caddyfile`.
No `become`, since the Homebrew prefix is user-owned on Apple Silicon.

Then start the service. Caddy must bind `:80`, so it runs as a root LaunchDaemon via `sudo brew services start caddy`, which is the one `brew` invocation Homebrew sanctions under sudo.
Made idempotent by checking `brew services list` first and setting `changed_when` off that, since the repo has no existing brew-service precedent to copy.

### 3. `roles/apps/files/caddy/README.md`

Short, and covering only what is not obvious from the Caddyfile:

- Adding a project: one line, then `caddy reload --config /opt/homebrew/etc/Caddyfile`, which needs no sudo because it goes through the admin API on `127.0.0.1:2019`.
- The port convention: pick an unused one and start that worktree with `pnpm dev -- --port N`.
- Where a project's own script hardcodes `--port` (`drivein` passes `--port 4321`), appending another may not override it, so run the binary directly instead: `npx astro dev --port 4322`.
- `curl http://front.localhost` needs an `/etc/hosts` line; browsers do not.

## Files

| Path | Change |
|---|---|
| `roles/apps/files/caddy/Caddyfile` | new |
| `roles/apps/files/caddy/README.md` | new |
| `roles/apps/defaults/main.yml` | drop `APPS_SCRIPTS`, add `caddy` formula |
| `roles/apps/tasks/development.yml` | restore to HEAD, then add symlink and service tasks |
| `roles/shell/tasks/main.yml` | drop the lokl backup entry, keep the conf.d glob |
| `lib/python/dotkit/testing.py`, `pytest.ini` | restore to HEAD |
| `roles/apps/files/scripts/`, `roles/shell/files/fish/conf.d/lokl.fish` | delete |

No new tests: nothing here is Python. `make test` must still pass, which is the check that the pytest.ini and `dotkit.testing` reverts were complete, since `test_suites.py` asserts every testpath exists.

## Known limitations

- Ports are assigned by hand. Forgetting `--port` on a second worktree lets it increment into the port you meant to give it, which works by coincidence until it does not.
- A new worktree means editing the Caddyfile and reloading. That is the deliberate trade against maintaining discovery.
- Two projects that both hardcode the same port in a committed script still cannot run together without bypassing the script.
- Caddy holds `:80` for the whole machine.

## Verification

1. `make test` from the repo root passes, confirming the lokl reverts left nothing dangling.
2. `make check-role ROLE=apps` shows the Caddyfile symlink and the service task, and no user-bin link tasks.
3. `make run-role ROLE=apps` installs Caddy and starts it. `sudo brew services list` shows `caddy started`.
4. `caddy validate --config /opt/homebrew/etc/Caddyfile` passes.
5. `pnpm dev` in `work/addingwell/front`, then `pnpm dev -- --port 3001` in `front-e2e`. Both start without either printing "port in use".
6. `http://front.localhost` and `http://front-e2e.localhost` both load in the browser, with no `/etc/hosts` entry for either.
7. Sign in on one and reload the other: the sessions are independent, which is the original problem solved.
8. Edit a file in each and confirm HMR reconnects, proving Caddy's websocket upgrade.
9. Add a line for a new project, `caddy reload --config /opt/homebrew/etc/Caddyfile`, and confirm it serves without a restart.
10. `git status` shows no trace of `roles/apps/files/scripts/` or `lokl.fish`.
