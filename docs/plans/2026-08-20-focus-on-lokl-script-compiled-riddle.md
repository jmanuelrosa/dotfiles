# Nested dev domains in `lokl`

## Context

A four-service local project is spelled with hyphens today: `pot.localhost`, `pot-app.localhost`, `pot-api.localhost`, `pot-admin.localhost`.
Because `.localhost` is not in the Public Suffix List, its eTLD is `localhost`, so each of those four names is its own **registrable domain**.
That makes them mutually cross-site: a `SameSite=Lax` cookie set by one is not sent to another, and no `Domain=` value can cover the set.

Nesting them under one parent fixes that, which is what prompted this:

```
pot.localhost         landing
app.pot.localhost     app
api.pot.localhost     api
admin.pot.localhost   admin
```

All four then share the registrable domain `pot.localhost`, so they are same-site and a `Domain=pot.localhost` cookie is shared across them.

**One correction to the advice that prompted this.** Sharing a registrable domain fixes *cookies*, not CORS.
A different hostname is still a different origin, so `app.pot.localhost` calling `api.pot.localhost` still triggers a preflight and still needs `Access-Control-Allow-Origin` plus `Access-Control-Allow-Credentials` on the API.
Only one hostname with path prefixes removes CORS, and that was considered and rejected here as too constraining on how the apps are written.
The README must say this plainly, so the next person does not adopt nesting expecting CORS to disappear.

`lokl` cannot express any of it today: `LABEL` forbids dots, so `app.pot.localhost` is rejected outright, and `test_normalise_refuses_anything_that_is_not_a_dns_label` pins `"a.b"` as a rejection case.

**Outcome:** `lokl add app.pot 3001` works, and `lokl add pot --sub app --sub api --sub admin` creates a whole family on consecutive derived ports in one command.

Verified with the Vite docs: `server.allowedHosts` permits `localhost`, `.localhost` and all IPs by default, and a leading-dot entry covers the domain plus all subdomains at any depth.
So `app.pot.localhost` needs no `vite.config.ts` change, and the comment in `lokl` claiming `allowedHosts` permits "only `localhost` and `*.localhost`" is inaccurate and gets corrected.

## Scope decisions already made

- Nested subdomains only. No same-origin path routing.
- **Two labels under `.localhost`, maximum.** `app.pot.localhost` yes, `v2.app.pot.localhost` no. Parent plus one level of children is all a shared cookie jar needs.
- The `pot` names are illustrative. **No new project-specific site files are committed.** The existing `pot-*` files stay; migration is a set of commands the user runs (below).

## Work

All in `roles/apps/files/scripts/lokl/lokl` unless noted.

### 1. `normalise` accepts a chain (lines 136-153)

Return `(name, domain)` where `name` is the dotted chain minus the suffix (`"app.pot"`), and `domain` is `f"{name}.{SUFFIX}"`.
Callers only ever use the first element for the filename and as a validity sentinel, so the rename from `label` to `name` is local to each `cmd_*`.

Split on `.` after stripping the suffix, validate **each** part against the existing `LABEL`, and cap the count:

```python
# Parent plus one level of children is what a shared cookie jar needs: the four names of one
# project sit under `pot.localhost`, which is their registrable domain, so they are same-site.
# A third level buys nothing that the second does not already give and costs another hosts
# line and another site file per name.
MAX_LABELS = 2
```

Three distinct complaints, because "not a usable name" for a depth problem sends the reader looking at their spelling:

- empty: unchanged
- a part failing `LABEL`: the existing message, naming the offending part
- more than `MAX_LABELS`: `"v2.app.pot.localhost nests too deep. Use at most one subdomain label, as in app.pot.localhost."`

### 2. Site filenames carry the chain

`cmd_add` line 506 becomes `paths.sites / f"{name}.caddyfile"`, giving `app.pot.caddyfile`.
`Path("app.pot.caddyfile").stem == "app.pot"`, and the Caddyfile's `import sites/*.caddyfile` glob already matches, so **the Caddyfile, `roles/apps/defaults/main.yml` and the playbook need no change at all.**

`sites()` globs sorted by filename, which now interleaves families (`app.pot.caddyfile` before `pot.caddyfile`). That only affects display and hosts order, both fixed in step 5.

### 3. `derive_window` for sequential ports

New function beside `derive_port` (line 156). `derive_port` itself is **untouched**, so `test_derive_port_pins_the_algorithm` keeps passing and no existing domain's port moves.

```python
def derive_window(seed, count, taken=()):
    """`count` consecutive free ports, from the same digest `derive_port` uses.

    Sequential rather than each name hashed on its own, because one project's ports are read
    together: `29769-29772` is a range a person holds in their head and an `lsof` sweep can
    name, where four unrelated numbers are four things to look up.
    """
```

- Same `sha256(str(seed))` start as `derive_port`.
- Walk `step` over `range(PORT_SPAN)`; candidate run is `[c, c + count - 1]`.
- Reject a run crossing `PORT_CEILING` rather than wrapping it, since a wrapped window is not a range.
- Reject a run touching `taken | RESERVED`.
- Return the list, or `None` when nothing fits (caller exits `EXIT_NOT_FOUND`).

`derive_window(seed, 1) == [derive_port(seed)]` holds by construction, and is worth a test as the tie between the two.

### 4. `add` becomes family-aware (`cmd_add`, lines 469-549)

Surface: `lokl add <name> [port] [--sub LABEL[=PORT]]...`, repeatable, `action="append"`.

Extending `add` rather than adding a `project` subcommand, because `add` already owns every step a family needs (RESERVED/range refusal, the sites-dir guard, `caddy validate` with rollback, `apply_hosts`, `warn_foreign`, `reload_proxy`, `report_resolution`) and is already idempotent. A second subcommand would duplicate all of it. Re-running `lokl add pot --sub app --sub api --sub admin` after gaining a fourth service is then the natural idiom.

- A `parse_sub(raw)` helper returns `(label, port_or_None)` or a complaint. The label must be a single `LABEL`, no dots.
- With `--sub` present, the positional parent must itself be a single label. Hanging a sub off `app.pot` is the `MAX_LABELS` violation, reported as such.
- Members: the parent `pot.localhost` plus one `<label>.pot.localhost` per `--sub`.

**Port resolution, preserving the existing invariant.** README line 103 makes "a domain that already has a port keeps it" load-bearing, so:

- Explicit ports (`args.port`, `--sub app=3001`) always win and are excluded from derivation.
- If **every** member without an explicit port is new, call `derive_window(Path.cwd(), n, assigned_ports(existing))` and hand them out in declaration order: parent first, then subs.
- If **any** of them already has a recorded port, keep every recorded port and fall back to per-member `derive_port` for the genuinely new ones. Say so with `ui.note`, because the result is then not a contiguous range and the user should know why.

**Rollback becomes all-or-nothing.** Collect `(target, restore)` for every member, write every file, then run `validate(paths)` **once**, and on rejection restore or unlink all of them. Cheaper than N subprocesses and it cannot leave half a family on disk.

Reporting: one `ui.title(f"🔌 {parent}")`, then a `ui.step`/`ui.note` line per member reusing the existing already/repointed/proxying wording, then the shared hosts, foreign, reload and resolution steps once for the whole family. The final `ui.done` lists every URL.

### 5. Family-ordered output

A sort key on the reversed label chain groups a family and puts the parent first:

```python
def domain_sort_key(domain):
    return tuple(reversed(domain.split(".")))
```

`pot.localhost` gives `("localhost", "pot")`, which sorts before `app.pot.localhost` at `("localhost", "pot", "app")`, and every `*.pot.localhost` sits together.

Use it in `cmd_list` and in the `apply_hosts` call sites (lines 538, 569, and `cmd_sync`), replacing bare `sorted(...)`, so `/etc/hosts` reads as families too. Nested entries are otherwise ordinary `127.0.0.1\t<domain>` lines; nothing else about the hosts half changes.

In `cmd_list`, indent a child under its configured parent. `cmd_validate` gains a `ui.note` when a nested domain's parent is not configured: it works fine, but with nesting the usual cause is a typo.

### 6. `remove` gains `--tree` (`cmd_remove`, lines 552-577)

`lokl remove app.pot` works through `normalise` with no further change.
`lokl remove pot --tree` drops `pot.localhost` and every `*.pot.localhost`.

The flag is the confirmation: it removes files the user did not name, but the site files are committed, so `git checkout` is the undo and `lokl` has no interactive prompt anywhere to be consistent with. Output lists every domain removed. Without `--tree`, removing a parent leaves its children, which is worth a `ui.note` when any exist.

### 7. `port`, `status`, `sync`

`cmd_port` needs no change beyond `normalise`: `lokl port app.pot` reads the site file, and the bare form still derives for the working directory. `status` and `sync` are unaffected.

### 8. Docs

- `lokl` lines 61-63: correct the `SUFFIX` comment. `allowedHosts` permits `localhost`, `.localhost` and all IPs by default, and the dot-prefix form covers subdomains at any depth, so nesting needs no Vite config.
- `roles/apps/files/caddy/README.md` lines 58-59: the same correction.
- README, new section **"One project, several services"**: the registrable-domain reasoning, the `--sub` and `--tree` forms, the sequential window, and an explicit paragraph that this fixes same-site cookies and does **not** remove CORS. Name what the apps still need: `Access-Control-Allow-Origin` with `Access-Control-Allow-Credentials`, and `Domain=pot.localhost` on the session cookie.
- README lines 61-75: add the new forms to the command block.
- README line 108: drop the stale `--host` from the `astro dev` example. It contradicts lines 25-27, which say `--host` is not needed and is actively harmful.
- `roles/shell/files/fish/conf.d/aliases.fish` lines 54-64: check the comment block for the same stale `--host` advice.

### 9. Tests (`roles/apps/files/scripts/lokl/tests/test_lokl.py`)

Changed:

- `test_normalise_accepts_both_spellings` (line 92): add `("app.pot", "app.pot.localhost")` and `("APP.POT.LOCALHOST", "app.pot.localhost")`. Line 106's assertion becomes `name == expected.removesuffix(f".{tool.SUFFIX}")`.
- `test_normalise_refuses_anything_that_is_not_a_dns_label` (line 110): drop `"a.b"`, add `"a..b"`, `".pot"`, `"-a.pot"`, `"a_b.pot"`.
- `test_every_committed_site_file_is_what_the_tool_would_write` (line 698): `path.stem == domain.removesuffix(f".{tool.SUFFIX}")`.
- Any test asserting exact multi-domain hosts-block text: the order changes under `domain_sort_key`.
- `test_derive_port_pins_the_algorithm` (line 133) must pass **unchanged**. It is the regression gate on step 3.

New:

- `test_normalise_refuses_a_third_level`, covering `v2.app.pot` and `v2.app.pot.localhost`.
- `test_derive_window_of_one_matches_derive_port`, `test_derive_window_is_contiguous_and_stable`, `test_derive_window_steps_over_taken_and_reserved`, `test_derive_window_never_crosses_the_ceiling`, `test_derive_window_returns_none_when_no_run_fits`.
- `test_site_file_name_carries_the_whole_chain`, asserting `add app.pot` writes `app.pot.caddyfile`.
- `test_add_with_subs_writes_a_family_on_sequential_ports`, `test_add_with_subs_is_idempotent`, `test_add_with_subs_honours_an_explicit_sub_port`, `test_add_with_subs_keeps_a_recorded_port_and_says_the_range_is_broken`, `test_add_with_subs_rolls_back_every_file_when_caddy_rejects`, `test_add_refuses_subs_under_a_nested_parent`.
- `test_remove_tree_takes_the_parent_and_its_children`, `test_remove_without_tree_leaves_the_children`.
- `test_hosts_block_groups_a_family`, asserting parent before children and families contiguous.
- `test_port_answers_for_a_nested_domain`.

All of these run through the existing seams: the `machine` fixture's `tmp_path` Caddyfile plus `LOKL_CADDYFILE`, `LOKL_HOSTS` and `NO_COLOR=1`. Nothing needs root and nothing touches the real machine.

## Files touched

| File | Change |
|---|---|
| `roles/apps/files/scripts/lokl/lokl` | `normalise`, `MAX_LABELS`, `derive_window`, `domain_sort_key`, `parse_sub`, `cmd_add`, `cmd_remove`, `cmd_list`, `cmd_validate`, `build_parser`, the `SUFFIX` comment |
| `roles/apps/files/scripts/lokl/tests/test_lokl.py` | the changes and additions above |
| `roles/apps/files/caddy/README.md` | new section, command block, two corrections |
| `roles/shell/files/fish/conf.d/aliases.fish` | comment block only, if stale |

Deliberately untouched: `roles/apps/files/caddy/Caddyfile`, `roles/apps/defaults/main.yml`, `roles/apps/tasks/development.yml`. The `import sites/*.caddyfile` glob and both symlinks already carry nested filenames.

## Migrating the existing `pot-*` domains

Not part of the change, and no committed site file for it. Once the above lands, from the project directory:

```fish
lokl remove pot-app
lokl remove pot-api
lokl remove pot-admin
lokl remove pot
lokl add pot --sub app --sub api --sub admin
```

That deletes four site files and writes four new ones on a consecutive window, which shows up as an ordinary diff. Each dev server then needs its new port, from `lokl port app.pot` and friends.

Note during migration that a leftover `pot-app.localhost` and a new `app.pot.localhost` will happily coexist and both proxy, so the old names must actually be removed rather than left as a fallback: leaving them is how a session gets stored under the cross-site name this whole change exists to retire.

## Verification

1. `make test`, the only unattended target. Covers the whole lokl suite, no vault, no sudo, no network. This is the primary gate.
2. `caddy fmt --diff` on a generated nested site file, confirming `render_site` output is still byte-identical to what `caddy fmt` produces. `test_render_site_is_caddy_fmt_clean` already asserts this; extend it to a nested domain.
3. End-to-end against a throwaway machine, no root needed:

```fish
set -x LOKL_CADDYFILE (mktemp -d)/Caddyfile
# seed it with the global block and the import, mkdir sites/ beside it
lokl add demo --sub app --sub api
lokl list          # demo.localhost first, then app.demo.localhost and api.demo.localhost, sequential ports
lokl port app.demo # one bare number
lokl validate
lokl remove demo --tree
```

4. Real machine, once the throwaway passes: `lokl add <project> --sub app --sub api`, then `lokl start`, then `curl -I http://app.<project>.localhost` and confirm the proxy reaches the dev server. `lokl add` already ends with a `getaddrinfo` check, so an unresolved nested name reports itself as exit 5.
5. The cookie claim, which is the reason for the whole change: set a cookie with `Domain=<project>.localhost; SameSite=Lax` from the api service, load the app service, and confirm the browser sends it. That is the behaviour the hyphenated names could not produce.
6. `make lint` is not needed: no YAML changes.
