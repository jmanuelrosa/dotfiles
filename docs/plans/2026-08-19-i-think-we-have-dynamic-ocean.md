# Fix lokl's port contract, its blind spot, and the guidance that caused the confusion

## Context

`lokl status` reported the proxy as down while `http://<domain>:<port>` kept answering, and the port a site file recorded did not match the port the dev server was told to bind.

Three of those observations turned out to be the tool working as designed, and the investigation found four real defects behind them.

**`lokl status` was correct.**
`pgrep -f "caddy run"` is empty and `brew services list` reports `caddy none`.
The role never registers Caddy at boot, so `lokl start` is required. Nothing to fix.

**A URL with a port bypasses Caddy entirely.**
Resolution turns the name into `127.0.0.1`, the kernel routes on `(address, port)` only, and the name survives solely as the `Host` header.
Verified on this machine against the one running dev server: `topo.localhost:29768`, `pot.localhost:29768`, `pot-api.localhost:29768`, `localhost:29768` and `127.0.0.1:29768` all returned 200 with an identical 79223-byte body.
The port selects the process; the hostname is decorative.
That matters because cookies key on hostname and ignore the port, so signing in through the wrong name stores a session under a domain whose real server will later be handed it.
The portless URL on `:80` is the only one where the `Host` header is the sole discriminator and therefore authoritative.

### The four defects

**1. `cmd_port`'s bare form is off by one.**
It calls `derive_port(Path.cwd(), assigned_ports(configured))`, and `assigned_ports` includes the port `derive_port` handed this same directory on an earlier `lokl add`, so the linear probe steps over it:

```
raw sha256 slot for /Users/.../personal/topo   = 27778
topo.caddyfile records                          = 27778
`lokl port` (bare, from that directory) prints  = 27779   <- off by one
```

`lokl add` has no such problem (an already-configured domain keeps its recorded port, `lokl:428-438`), so the two commands disagree and `port` is the one lying.
Feeding its answer to `--port` produces the reported symptom exactly.

**2. `parse_site` cannot see the second upstream.**
`SITE_PORT` (`lokl:86`) matches only the first `reverse_proxy` address, so a file whose two legs disagree reads back as clean.
The tool cannot round-trip a file it can be handed.

**3. `sites/pot.caddyfile` has mismatched legs**, `reverse_proxy 127.0.0.1:29770 [::1]:29768`.
`render_site` can only emit the same port twice, so this was hand-edited.
With `lb_policy first` the domain dials 29770 while it is healthy, which is `pot-api`'s port, and only reaches 29768 after a refusal.
Defect 2 is why `lokl list` reports it as a clean `:29770`.

**4. The documented `--host` invocation is unnecessary, and it is what made the ported URLs work from everywhere.**
`README.md:8` and `:90` both recommend `astro dev --host my-custom-project.localhost --port (lokl port my-custom-project)`.
Caddy dials `127.0.0.1:port` with an `[::1]:port` fallback, so a default-bound dev server on loopback is already reachable and `--host` buys nothing behind the proxy.
It does bind every interface, which is what put the dev server on the LAN and made every hostname reach it.

### One documentation claim is now false

`README.md:22-25` and the module docstring both assert that macOS does not resolve `*.localhost` and that a hosts entry is the only option left.
On macOS 26.6.1 that is not true:

```
zzz-random-9k3.localhost   -> ['127.0.0.1', '::1']    # in no file anywhere
deep.sub.localhost         -> ['127.0.0.1', '::1']
foo.test                   -> FAILS
foo.invalidtld             -> FAILS
```

Arbitrary `*.localhost` resolves through `getaddrinfo`; other non-IANA TLDs do not.
That is the system implementing RFC 6761 for the `localhost` special-use domain, not a wildcard and not the hosts entries.
The **dnsmasq** section (`README.md:33-38`) remains correct, which is why `foo.test` fails.

Also false in consequence: `README.md:131-132` claims the single-address hosts entry controls which family the dev server's resolver picks.
`topo.localhost` returns both `127.0.0.1` and `::1` despite its entry listing only the first, so native resolution supplies the pair regardless and the `reverse_proxy` failover is carrying that weight alone.

**The hosts block still gets written.** It is cheap, it is already idempotent, and it survives a DNS profile, MDM or VPN split-DNS shadowing the special-case handling. Only its stated justification changes.

Intended outcome: bare `lokl port` is safe to put in a dev script, a site file whose legs disagree is reported rather than hidden, and the docs stop recommending the flag that caused this.

## Scope

Confirmed with the user: fix `cmd_port`, add the guards, make `status` more diagnostic, and de-collide `pot` keeping `pot-app` on 29769 and `pot-api` on 29770.
Doc corrections are added because the wrong guidance is the proximate cause of the original confusion.

Out of scope: replacing the `pgrep -f "caddy run"` predicate. It depends on Caddy's `start` re-execing itself as `caddy run`, which is a real fragility, but it reported correctly here and an admin-API probe on `:2019` has its own failure modes.

## Open decisions, needed before step 5

1. **`topo.caddyfile` records 27778 but topo's Astro is running on 29768**, so `http://topo.localhost` will 502 until one of them moves. Which is canonical?
2. **`pot.caddyfile`'s hand-edited `[::1]:29768` leg points at topo's Astro server.** If `pot` and `topo` are the same project under two names, the fix is removing a domain rather than renumbering one.

## Files

| File | Change |
|---|---|
| `roles/apps/files/scripts/lokl/lokl` | `parse_site`, `sites`, `cmd_port`, `cmd_list`, `cmd_validate`, `cmd_status`, module docstring |
| `roles/apps/files/scripts/lokl/tests/test_lokl.py` | Regression and guard cases |
| `roles/apps/files/caddy/sites/pot.caddyfile` | Regenerated through `lokl add`, never hand-edited |
| `roles/apps/files/caddy/README.md` | Lines 8, 22-25, 90, 131-132 |

## 1. Fix the bare `lokl port` off-by-one

In `cmd_port` (`lokl:539`), before the probing call, prefer the raw hashed slot when a site file already holds it:

- `derive_port(Path.cwd())` with an empty `taken` set is the unprobed answer, the number `lokl add` would have derived here first.
- If that slot is in `assigned_ports(configured)`, print it. A site file holding precisely this directory's hash slot is, in every case but a genuine collision, the assignment made from this directory, and it is the number Caddy is pointing at.
- Otherwise keep the existing `derive_port(Path.cwd(), assigned_ports(configured))` call unchanged, so an unconfigured directory still gets a collision-free suggestion.

Because a collision is possible in principle, name the domain holding the slot on **stderr** and suggest `lokl port <name>` for certainty.
Stdout keeps its exemption from the line vocabulary: one bare number, nothing else, per the `cmd_port` docstring.

Do not touch `derive_port`. Its golden values are pinned at `tests/test_lokl.py:117-124` and its probing is correct for its real job, assigning a new port.

## 2. Teach `parse_site` to read both legs

- Replace the single-capture `SITE_PORT` with a match on the whole `reverse_proxy` upstream list, then `re.findall(r":(\d+)", upstreams)`.
- Change `sites()` to yield a `collections.namedtuple("Site", "port path ports")` rather than the `(port, path)` pair. `Paths` (`lokl:89`) sets the precedent, and field access makes the ripple mechanical instead of a hunt for positional unpacks.
- Update every consumer to field access: `assigned_ports` (`lokl:159`, currently `for port, _ in`), `cmd_add` (`existing.get(domain, (None, None))[0]`, the `(taken, _)` unpack in the `clashes` comprehension, `existing[domain][1]`), `cmd_remove` (`existing[domain][1]`), `cmd_list` (`for domain, (port, _) in`).
- Keep the existing tolerance for a hand-written file with no port at all (`test_parse_site_reports_a_hand_written_file_without_a_port`): absent stays `None`.

## 3. Guards in `list` and `validate`

`cmd_list` (`lokl:572`) gains two reports:

- A domain whose `ports` disagree renders as such in the state column, with a `ui.note` naming both numbers and the fact that `lb_policy first` means only the first is used while it answers.
- After the loop, any port claimed by more than one domain gets one `ui.warn` naming the port and every claimant. This matches the stance `cmd_add` already takes at `lokl:485-486`.

`cmd_validate` (`lokl:689`) only asks Caddy to parse, and Caddy parses both defects happily. Add lokl's own semantic pass after the `validate(paths)` call:

- **Mismatched legs fail** with `EXIT_INVALID`. `render_site` cannot produce one, so it is never intentional.
- **A duplicate port warns** and still exits `EXIT_OK`, consistent with `add`.

## 4. Make `status` explain the confusion that started this

`cmd_status` (`lokl:666`) is a summary and stays short. Two additions:

- When the proxy is down, note that `http://<domain>` needs it while `http://<domain>:<port>` reaches the dev server directly. That one line is the whole misunderstanding.
- Surface a count of sites with disagreeing legs or a colliding port, pointing at `lokl validate`, so the problem is visible without running `list`.

## 5. Regenerate `sites/pot.caddyfile`

Through the tool, so it is generated rather than hand-written a second time:

```
lokl add pot 29771
```

29771 is the first port in the window no site file claims and nothing is listening on. `pot-app` keeps 29769 and `pot-api` keeps 29770, untouched.
**Resolve the two open decisions above first**, since the answer may be `lokl remove` instead.

The three `pot*.caddyfile` files are currently untracked and get committed as part of this change.

## 6. Correct the docs

- `README.md:8` and `:90`: drop `--host <domain>` from the recommended invocation, leaving `astro dev --port (lokl port my-custom-project)`. Add one line that `--host` is only for reaching the server from another device, and that it exposes the dev server on every interface.
- `README.md:22-25` and the module docstring's `/etc/hosts` paragraph: replace "macOS does not resolve `*.localhost` at all" with what is actually true on macOS 26.6.1, and restate the block's purpose as insurance against a DNS profile, MDM or VPN split-DNS shadowing the special-case handling, plus an older macOS on a fresh machine. Keep the dnsmasq section as it is.
- `README.md:131-132`: the single-address claim no longer holds, since native resolution returns both families regardless. Say that the `reverse_proxy` pair is what handles family selection.
- Add a short note on why the portless URL is the one to use: the cookie jar keys on hostname and ignores the port, so on `:80` the `Host` header is the only discriminator.

## Verification

```
make test                      # the only unattended target; pytest.ini:19 registers the lokl suite
lokl validate                  # must fail on pot.caddyfile before step 5, pass after
lokl list                      # pot must show disagreeing legs before step 5
```

Then the path the bug broke, from a project directory, with no `--host`:

```
lokl port topo                 # 27778, from the site file
lokl port                      # must now print 27778 too, not 27779
cd <project> && astro dev --port (lokl port)
sudo -v && lokl start
curl -sS -o /dev/null -w '%{http_code}\n' http://topo.localhost        # 200, through Caddy
curl -sS -o /dev/null -w '%{http_code}\n' http://topo.localhost:27778  # 200, direct
lokl status                    # reports the running proxy
lokl stop
```

The portless 200 is the assertion that matters: it is the only one of the two that proves Caddy is in the path, and it also proves the dev server is reachable without `--host`.

`make lint` and `make syntax` need the vault password, so run them interactively only if Ansible files end up touched. Nothing in `roles/apps/tasks/development.yml` needs changing: `lokl` and the site directory are already symlinked, so script edits take effect immediately.
