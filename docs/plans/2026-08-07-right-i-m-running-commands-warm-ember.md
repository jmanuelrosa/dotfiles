# Teach `s-db` to dump and restore

## Context

Two long `pg_dump` / `pg_restore` invocations are being retyped from memory or scrollback each time a staging snapshot is needed locally:

```
pg_dump --dbname=addingwell --host=localhost --port=5433 --username=postgres --password \
  --inserts --schema=public --verbose --format=custom --no-owner \
  --exclude-table='public._dlt*' > staging_2.dump

pg_restore --no-owner --role=testuser --dbname=addingwell --host=localhost --port=5432 \
  --username=testuser --password --schema=public < staging.dump
```

Nobody is going to remember those, and three details make retyping them actively hazardous rather than merely tedious:

- **`--exclude-table='public._dlt*'` only works because of the quotes.** In fish an unmatched glob is a hard error, so dropping them does not silently pass the literal through: the command fails to launch. Getting the quoting right is a per-invocation tax.
- **`--inserts` with `--format=custom` is legal but self-defeating.** `man pg_dump` on this machine (PostgreSQL 18.4, libpq 18.4): *"This will make restoration very slow; it is mainly useful for making dumps that can be loaded into non-PostgreSQL databases."* These dumps are loaded back into PostgreSQL, so the flag buys per-row (rather than per-table) failure granularity in exchange for a much slower dump, a slower restore, and a larger file.
- **The port carries all the meaning and none of the safety.** `5433` is staging, `5432` is local, `5434` is production. One digit separates reading staging from writing production, and the shell offers no guard.

`s-db` already exists (`roles/work/files/scripts/s-db/s-db`, linked onto `PATH` by `WORK_SCRIPTS`) and already owns the environment table these commands encode by hand: staging is 5433, production is 5434, and it knows how to bring the Cloud SQL proxy up. It just cannot yet do anything *with* a database once connected. Adding `dump` and `restore` there rather than in a new script or a set of abbreviations is what keeps one environment table instead of two, and gives one `s-db --help` to read.

Outcome: `s-db dump staging` and `s-db restore` (no argument, pick from a list) replace both commands, and the environment/port mapping stops living in muscle memory.

## Decisions taken

| Decision | Choice |
|---|---|
| Shape | Subcommands on `s-db`. `s-db staging` keeps connecting the proxy, unchanged. |
| Restore target | **Local only, no flag to reach further.** Staging and production are unreachable by design, the same way `s-release`'s base and head are constants. |
| `--inserts` | Dropped from the default. COPY instead, with `--inserts` as an opt-in flag. |
| Missing proxy on `dump` | Start it detached, then dump. One command is the whole job. |
| New environment | `local` joins `staging` and `production`, so the local database is a named environment rather than a hardcoded host:port. |

## Command surface

```
s-db [connect] [production|staging] [-d]              # unchanged, including bare `s-db`
s-db dump [production|staging|local] [--out FILE] [--inserts] [--include-dlt] [-v] [--dry]
s-db restore [FILE] [--clean] [-v] [--dry]
s-db dumps
```

Dispatch in `main`: `dump` / `restore` / `dumps` / `connect` route to their own function, and **anything else falls through to `connect` with the full argument list**. That is what preserves `s-db`, `s-db staging`, `s-db -d prod` and `s-db --help` exactly as they behave today.

`s-db restore` with no file is the headline: it lists `backups/` newest-first and you pick a number, mirroring how `s-release` lists repos when given no argument. Zero arguments, nothing to remember.

## The environment table

Three facts per environment, added as `switch` functions alongside the existing `get_port` / `get_instance` rather than restructured into a table, to match the file:

| env | port | proxy | instance | user | role |
|---|---|---|---|---|---|
| `production` | 5434 | yes | `addingwell-prod:europe-west1:addingwell-prod-postgres-13` | `postgres` | - |
| `staging` | 5433 | yes | `addingwell-dev-326312:europe-west1:addingwell-dev-postgres` | `postgres` | - |
| `local` | 5432 | no | - | `testuser` | `testuser` |

Database is `addingwell` in all three. These stay hardcoded, with a comment saying so, for the reason `s-db`'s instances and `s-release`'s `ORG` already are: one org, and a layout that changes rarely enough that a config file would be a second place to look.

`local` needs no proxy, so `s-db connect local` (or `s-db local`) is not an error: it prints that local is already on `localhost:5432` with nothing to connect and exits `0`.

## Files to change

### `roles/work/files/scripts/s-db/s-db` (the whole change)

**One non-trivial refactor, and it is the only thing that can break the existing path.** `check_existing_connection` currently calls `exit 0` when it finds the proxy already up (script:106), which is right for `connect` and wrong for `dump`, where a live proxy is the happy case. Split it: the check *returns* a status (`free` / `ours` / `foreign`), `cmd_connect` keeps today's exit-0-with-notes behaviour on `ours` and `die`s on `foreign`, and `cmd_dump` proceeds on `ours` and calls the existing `start_proxy_detached` on `free`.

Second, smaller split: `validate_prerequisites` (script:74) both `cd`s to `WORK_DIR` and requires the `cloud-sql-proxy` binary. Separate the two, or `s-db restore` fails on any machine where the proxy binary is absent despite never needing it.

New pieces:

- `cmd_dump` - resolve the environment (reusing `prompt_environment_selection`, extended with `local` as a third choice), ensure the proxy where one is needed, build and run `pg_dump`, then report the output path and its size.
- `cmd_restore` - resolve the file (argument, or the picker), run `pg_restore` against `local`, report honestly.
- `cmd_dumps` - list `backups/`, newest first, with size and age.
- `pick_dump` - the shared listing-and-prompt used by `cmd_restore` and `cmd_dumps`.
- `require_pg_tool` - checks `pg_dump` / `pg_restore` is on `PATH`, pointing at `make run-role ROLE=apps` if not. `libpq` is already declared in `roles/apps/defaults/main.yml:52` and its bin is added to `PATH` by `roles/shell/files/fish/config.fish:21`, so **no provisioning change is needed** - this check only turns a confusing `command not found` into a pointer.
- `usage` - rewritten to cover the subcommands.

**Dump location:** `$WORK_DIR/backups/`, which already exists and already holds `addingwell-staging-20260807.dump`. New files are `addingwell-<env>-<YYYYMMDD-HHMMSS>.dump`, keeping that prefix but adding a time so a second dump on the same day cannot silently overwrite the first (which is what `staging_2.dump` was working around). `--out` overrides the whole path.

**The generated `pg_dump`:**

```
pg_dump --dbname=addingwell --host=localhost --port=<port> --username=<user> \
        --schema=public --format=custom --no-owner \
        --exclude-table='public._dlt*' --file=<path> [--verbose] [--inserts]
```

Differences from the command being replaced, each deliberate:

- **`--inserts` is gone** unless asked for, per the decision above.
- **`--password` is gone.** `man pg_dump`: *"This option is never essential, since pg_dump will automatically prompt for a password if the server demands password authentication"* - it only saves one round trip. Dropping it means a `~/.pgpass` or `PGPASSWORD` is honoured if one ever appears; there is none today (`~/.pgpass` absent), so the prompt behaviour is unchanged in practice.
- **`--file=` replaces `>`**, so a failed dump is reported by `pg_dump` rather than inferred from a short file.
- **`--verbose` is opt-in** (`-v`), since `_ui` already narrates the steps and the default output is otherwise a wall of per-object lines.
- **`--exclude-table='public._dlt*'` becomes the default**, quoted once, in the script, correctly. `--include-dlt` opts back in.

**The generated `pg_restore`:**

```
pg_restore --dbname=addingwell --host=localhost --port=5432 --username=testuser \
           --role=testuser --schema=public --no-owner [--clean --if-exists] [--verbose] <file>
```

`--clean` is off by default, matching today. When passed it implies `--if-exists` (otherwise it errors on objects that are not there) and it prompts for confirmation, because it drops before it loads. `pg_restore` exits non-zero on warnings as well as failures, so report the exit code as a `warn` naming it rather than printing `✓` over a partial restore - the restore that half-worked is the one worth not lying about.

**`--dry` on both**, printing the exact command without running it, mirroring `s-task --dry` and `s-release --dry`. This is the primary verification path.

**Output** goes through `_ui` only, no hand-rolled `set_color`, no new glyphs. New titles use `📦` (dump) and `🔄` (restore), both from the approved list in `CLAUDE.md`. Optional tidy while in the file: the existing `🗄️` on script:144 needs U+FE0F to render as an emoji, which `CLAUDE.md` warns renders as monochrome text on some terminals; `📦` is the drop-in. Pre-existing, not caused here, fix it or leave it.

### `roles/work/README.md`

- Replace the one-line `s-db` bullet (README:20) with the subcommand surface.
- Add a `### Database dumps` section covering: the three-environment table, why restore is local-only and has no flag to reach further, why `--inserts` was dropped (quoting the man page), the `_dlt` exclusion, and that `backups/` holds real staging and production data and therefore lives outside any checkout.

### Nothing else

`WORK_SCRIPTS` already lists `s-db`, so **no Ansible change and no re-run needed** - the script is symlinked, so edits take effect immediately. No `pytest` root to add: fish scripts here carry no suites (`s-db`, `s-task`, `s-release` have none), and `--dry` is the idiom that replaces them. Root `CLAUDE.md` does not describe `s-db`, so it needs no edit.

## Verification

Cheap, in order, before touching a real database:

```fish
fish --no-execute roles/work/files/scripts/s-db/s-db   # syntax only, no side effects
s-db --help                                            # subcommands listed
s-db dumps                                             # finds addingwell-staging-20260807.dump
s-db dump staging --dry                                # prints the pg_dump command, runs nothing
s-db dump local --dry                                  # port 5432, user testuser, no proxy step
s-db restore --dry                                     # picker, then the pg_restore command
```

Regression on the path that already worked (both proxies happen to be up right now, so the first exercises the `ours` branch of the refactored check):

```fish
s-db staging                                           # reports the live proxy, exits 0
s-db -d production                                     # detached, unchanged
s-db                                                   # still prompts, now with local as a third choice
s-db local                                             # "already on localhost:5432", exit 0
```

End to end, the thing this is for:

```fish
s-db dump staging                                      # starts the proxy if needed, writes backups/
s-db restore                                           # pick the newest, into local
psql -h localhost -p 5432 -U testuser -d addingwell -c '\dt public.*'
```

Expect no `_dlt*` tables in that listing, and a restore materially faster than the `--inserts` dumps it replaces.

`make test` and `make lint` are unaffected (no python, no Ansible change) but should still pass.
