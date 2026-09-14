# Shoo extraction

**Status:** Complete (`v0.2.0` published and installed)
**Date:** 2026-09-13
**Updated:** 2026-09-14
**Parent design:** [Standalone script apps](./standalone-script-apps.md)
**Backlog:** [Standalone script apps backlog](./standalone-script-apps-backlog.md)
**Scope:** Extract the `port` Fish application from dotfiles as standalone command `shoo` and install an explicitly versioned release through the shell Ansible role.

## Objective

Move the behavior owned by `port` out of dotfiles so the application owns its tests, documentation, and releases.
Keep dotfiles responsible for installing an exact release and integrating it into the configured shell.
Preserve the interface, output, exit statuses, and macOS behavior while renaming the command to `shoo` to avoid the MacPorts collision.

The completed extraction follows the standalone-app pattern used by `hostof` and `kura`:

- Publish a clean-snapshot public `jmanuelrosa/shoo` repository without transferring Git history.
- Retain the initial `port` asset as historical `v0.1.0` and publish `shoo` as `v0.2.0`.
- Install the `shoo` asset at `~/.local/bin/shoo` with an exact SHA-256 checksum.
- Remove only the checksum-matched `port v0.1.0` executable and role-owned legacy Fish function.
- Remove the old source from dotfiles only after explicit approval.

## Original application boundary

The original application was contained in:

- `roles/shell/files/fish/functions/port.fish`, 539 lines of behavior.
- `roles/shell/files/fish/functions/_port_usage.fish`, 36 lines of help text.
- The runtime portions of `roles/shell/files/fish/functions/_ui.fish`, which provide output kinds, colors, glyphs, indentation, path rendering, and `NO_COLOR` / `FORCE_COLOR` behavior.

The shell role originally installed every Fish function by globbing `roles/shell/files/fish/functions/*.fish` and symlinking each file into `~/.config/fish/functions/`.
Fish autoloaded `port.fish`, so the function shadowed any executable named `port` on `PATH`.
There were no behavior-bearing consumers of the public `port` command elsewhere in dotfiles.
The `_port_usage` helper was private to `port`.
The shared `_ui` function remains in dotfiles because other Fish commands still use it.

The original application had no dedicated tests.
The configured Fish test root contained only `test_wt.py`, so extraction began by recording behavior rather than claiming an existing suite as a baseline.

## Behavior contract

### Commands and flags

```text
shoo
shoo --udp
shoo --long
shoo PORT
shoo PORT --long
shoo PORT --kill
shoo --help
```

- With no port, list TCP listeners.
- With `--udp`, include bound UDP sockets that have a concrete local port and are not outbound conversations.
- With a port, show every TCP and UDP socket using that port, including TCP `LISTEN` and `ESTABLISHED` rows.
- With `--long`, add process age, working directory, connected-client count, and lookup-only command-line detail.
- With `--kill`, identify only processes bound to the requested port, confirm once, send SIGTERM, and report survivors without escalating to SIGKILL.
- With `--help`, print the existing 36-line help text.

### Presentation

- Sort listing rows numerically by port.
- Merge duplicate TCP or UDP rows for the same process and port across address families.
- Mark loopback-only bound sockets as `local`.
- Mark wildcard and specific non-loopback bound sockets as `exposed`.
- Do not attach reachability scope to established TCP connections.
- Resolve Docker proxy rows to a container name when Docker is available.
- Print process detail once per process in long output.
- Suppress a process working directory of `/` as noise.
- Trim long command lines according to `COLUMNS`, with a minimum content width of 60.
- Preserve the current `_ui` vocabulary and stream-aware color behavior.

### Exit statuses

- Return 0 for help, a successful listing, an empty listing, a successful lookup, and a successful SIGTERM operation whose targets release the port.
- Return 1 for invalid arguments, a missing `lsof`, a lookup with no records, `--kill` without a port, a kill request with no bound process, declined confirmation, failed signaling, or surviving bound processes.
- Preserve `argparse` diagnostics on stderr.

### Approved compatibility correction

Characterization found that the original successful kill path cannot reach its intended success result.
When both survivor checks return no PID, `printf '%s\n'` produces one empty Fish list element, so the function reports a blank survivor and exits 1.
The code comments, help text, and success message all establish that an empty survivor set should return 0.
The standalone application filters empty survivor values, returns 0, and prints the existing `Freed port` message.
The command rename and this correction are the only approved behavior differences from the original function.

### Runtime inputs and side effects

Required runtime:

- macOS.
- Fish from the shell role.
- `lsof`, `ps`, `sort`, `uniq`, `tail`, `seq`, and `kill`, all present in the configured macOS environment.

Optional runtime:

- Docker CLI, consulted only when a displayed command starts with `com.docker`.

Environment:

- `COLUMNS` controls command-line trimming.
- `NO_COLOR` disables color.
- `FORCE_COLOR` enables color unless `NO_COLOR` is non-empty.
- `HOME` is used only to collapse paths to `~` in output.

State and mutation:

- The application writes no configuration, cache, or state files.
- The only process mutation is the confirmed SIGTERM operation requested through `--kill`.
- Application tests must replace `lsof`, `ps`, `docker`, and `kill` with controlled executables and must never signal a real process.

## Technical design

### Standalone executable

Keep the Fish implementation rather than rewriting it in another language.
A rewrite would expand the extraction into a behavior migration and make parity harder to prove.

The repository's checked-in `shoo` file is also the release asset:

```fish
#!/usr/bin/env fish

# Private output helpers
function _shoo_ui
    # ...
end

# Usage and application functions
function shoo
    # ...
end

shoo $argv
exit $status
```

The real implementation retains descriptive private names and the existing behavior.
The sketch only shows the executable shape.

The executable privately bundles the output behavior that the original `port` function received from `_ui`.
It does not source dotfiles, inspect a checkout, or require adjacent files.
Keeping source and artifact identical removes the need for a generated build and makes the released bytes directly reviewable.
The executable bit, syntax check, tests, and checksum are the release gates.

The public command is `shoo` so it does not collide with MacPorts.
The historical `v0.1.0` asset remains named `port`; `v0.2.0` is the first `shoo` release.

### Repository structure

```text
shoo/
├── .github/
│   └── workflows/
│       └── pull_request.yml
├── tests/
│   └── test_shoo.py
├── AGENTS.md
├── LICENSE
├── README.md
└── shoo
```

- `shoo` is the self-contained executable and release asset.
- `tests/test_shoo.py` uses Python's standard `unittest` library to drive the executable through controlled command fixtures.
- The workflow runs on macOS, installs Fish, checks syntax, runs the suite, and verifies the executable shape.
- `README.md` documents behavior, runtime requirements, installation, development, testing, release, rollback, uninstall, and the MacPorts name collision.
- `LICENSE` preserves the repository's MIT attribution.
- `AGENTS.md` records the small repository's commands and boundaries.

No runtime package or shared `dotkit` package is introduced.
Python is a development-only test harness and uses only its standard library.

### Dotfiles installation

The shell role owns installation because it already installs Fish and currently owns the function.
The role runs after coreutils, which creates `~/.local/bin` for every supported profile.

Declare in `roles/shell/defaults/main.yml`:

- Repository URL.
- Release label `v0.2.0`.
- Exact release asset URL.
- SHA-256 checksum.
- Legacy `port v0.1.0` checksum.
- Destination `{{ HOME }}/.local/bin/shoo`.
- Mode `0755`.

Install with `ansible.builtin.get_url` using the declared checksum.
Remove `~/.local/bin/port` only when it is a regular file whose SHA-256 matches the historical managed asset.
Refuse any other object at the old or new command destination.
Refresh the installed `ansible-doc` contract before implementation and cover first install, repeat run, check mode, checksum mismatch, upgrade, rollback, and uninstall behavior.

Before installation, inspect `~/.config/fish/functions/port.fish` without following it.
Remove it only when it is the known legacy symlink into this shell role.
Refuse an unexpected file or symlink because it would continue to shadow the managed executable.
The role inspects and removes `_port_usage.fish` separately because generic stale-link discovery does not report its broken symlink reliably.

After the standalone checkpoint and explicit source-removal approval:

- Remove `port.fish` and `_port_usage.fish` from the shell role.
- Retain `_ui.fish` for the Fish commands that still consume it.
- Update `roles/shell/README.md` to describe the pinned release and lifecycle.
- Add lightweight dotfiles tests for the release declaration, installer safety, checksum wiring, executable mode, legacy-link handling, and absence of the old implementation.
- Keep application behavior tests only in the standalone repository.

An already-running Fish process may still hold an autoloaded `port` function after provisioning.
The README will instruct users to run `functions -e port` or start a new shell once when switching to the executable.

## Commands

### Current behavior capture

```sh
fish --no-config -n \
  roles/shell/files/fish/functions/_ui.fish \
  roles/shell/files/fish/functions/_port_usage.fish \
  roles/shell/files/fish/functions/port.fish

fish --no-config -c '
  source roles/shell/files/fish/functions/_ui.fish
  source roles/shell/files/fish/functions/_port_usage.fish
  source roles/shell/files/fish/functions/port.fish
  port --help
'
```

### Standalone repository

```sh
fish --no-config -n ./shoo
python3 -m unittest discover -s tests -v
./shoo --help
shasum -a 256 ./shoo
```

### Dotfiles repository

```sh
make test
make syntax
make check-role ROLE=shell
make run-role ROLE=shell
make verify
```

`make syntax`, `make check-role`, and `make run-role` require the credentials described in the repository instructions.
Publication uses `gh` only after explicit approval.

## Code style

Match the existing Fish implementation and preserve behavior-bearing comments.
Use Fish builtins for parsing and collection work.
Prefix private application functions with `_shoo_`.
Retain the privately bundled `_ui` helper names to minimize migration risk, and keep all styled output behind them.
Do not add a `--version` flag during extraction.
Do not add abstractions for future standalone Fish applications.

## Testing strategy

### Characterization first

Build a deterministic command fixture around the original function before changing its source.
The fixture supplies controlled `lsof`, `ps`, `docker`, and `kill` executables through `PATH` and records their arguments.
Capture the expected stdout, stderr, exit status, and side-effect calls for each behavior.

The minimum behavior matrix covers:

- Help and argument errors.
- Missing `lsof`.
- Empty listing and missing-port lookup.
- TCP listing and numeric sort order.
- UDP inclusion and filtering.
- Single-port TCP and UDP lookup.
- Dual-stack row merging.
- Local and exposed scope classification.
- Long process age, cwd, command line, connected count, and width trimming.
- Docker container annotation with and without Docker available.
- Kill target selection, PID de-duplication, decline, successful SIGTERM, signal failure, and surviving listeners.
- `NO_COLOR`, `FORCE_COLOR`, piped stdout, and redirected stderr.

Run the matrix against the original implementation first.
Then run the same expectations against the standalone executable.
The standalone isolation test must fail before the executable is self-contained and pass only when no dotfiles file or Fish autoload path is available.

### Standalone completion gates

- Fish syntax passes.
- The complete standard-library test suite passes on macOS.
- Help output and behavior fixtures match the recorded original.
- The executable runs from a temporary directory with an empty Fish configuration.
- No test or runtime path resolves into the dotfiles checkout.
- The release asset is executable and its SHA-256 is recorded.

### Dotfiles completion gates

- Focused installer tests pass.
- `make test` passes after old application tests and sources are absent.
- `make syntax` and `make check-role ROLE=shell` pass.
- A first apply installs a regular executable file with the declared checksum.
- A second apply reports no change.
- Check mode reports the intended change without mutating the installation.
- `shoo --help` resolves to `~/.local/bin/shoo` in a new Fish process.
- The checksum-matched `~/.local/bin/port` migration artifact is absent.
- `make verify` passes.

## Boundaries

### Always

- Preserve the current CLI behavior unless a difference is documented and approved first.
- Work in behavior-capture, standalone, release, installer, and retirement checkpoints.
- Keep every step idempotent and rollback-friendly.
- Verify the exact asset checksum before changing dotfiles ownership.
- Keep application tests in the standalone repository and only installer tests in dotfiles.

### Ask first

- Publishing `jmanuelrosa/shoo` or any release.
- Removing `port.fish` or `_port_usage.fish` from dotfiles.
- Adding a runtime or development dependency.
- Renaming the command again or changing its flags, output, or exit statuses.
- Changing the release format or installation destination.

### Never

- Signal a real process from automated tests.
- Read runtime code from a dotfiles checkout.
- Follow a moving branch or `latest` release during provisioning.
- Replace an unexpected Fish function file or symlink.
- Publish shared `_ui` or `dotkit` as part of this extraction.
- Transfer unrelated dotfiles files, configuration, secrets, or Git history.

## Delivery sequence

1. Record deterministic behavior against the original function.
2. Create `~/Developer/port` as an unpublished clean snapshot.
3. Add the isolated executable and tests until parity and isolation pass.
4. Add repository documentation and pull-request verification.
5. Verify executable bytes and prepare `v0.1.0` release notes and checksum.
6. Stop for publication approval.
7. Publish the initial `port v0.1.0` asset and verify its remote checksum.
8. Approve and implement the command and repository rename to `shoo`.
9. Publish `shoo v0.2.0` and verify its remote checksum.
10. Add the checksum-pinned shell-role installer and retained installer tests.
11. Verify check mode, migration, repeat apply, and command resolution.
12. Stop for source-removal approval.
13. Retire the old Fish sources, update documentation, and run full verification.
14. Exercise upgrade and rollback when a later release exists.

The implementation plan and file-level task list are recorded under `tasks/`.

## Success criteria

- `shoo` works without a dotfiles checkout or Fish autoloaded functions.
- Flags, output semantics, exit statuses, and kill safety remain compatible except for the approved command rename and empty-survivor correction.
- Automated tests never inspect or mutate real listener processes.
- `v0.2.0` contains one executable `shoo` asset with a verified SHA-256 checksum.
- Dotfiles installs the exact asset as a regular file at `~/.local/bin/shoo`.
- Dotfiles removes only the checksum-matched historical `~/.local/bin/port` asset.
- Repeated provisioning is idempotent and check mode is non-mutating.
- An unexpected Fish function override is preserved and reported rather than overwritten.
- Dotfiles no longer contains the `port` implementation or its private usage helper.
- `_ui.fish` and unrelated Fish functions remain unchanged.
- Upgrade and rollback require only a release-and-checksum pair change.

## Decisions

| Decision | Choice | Status |
|---|---|---|
| Candidate | Extract `port` next | Approved |
| Scope | Full standalone-app pattern, with publication and source-removal pauses | Approved |
| Repository | Public `jmanuelrosa/shoo`, clean snapshot originally published as `port` | Approved |
| Command name | Rename `port` to `shoo` to avoid the MacPorts collision | Approved |
| Implementation language | Retain Fish | Approved |
| Release shape | Checked-in self-contained `shoo` executable is the `v0.2.0` asset | Approved |
| Installer owner | Shell role | Approved |
| Install destination | `~/.local/bin/shoo` | Approved |
| Version identity | Release label plus exact SHA-256, no new `--version` flag | Approved |
| Tests | Python standard-library black-box suite with controlled process-command fixtures | Approved |
| Shared output helpers | Private bundled Fish functions, no public shared package | Approved |
| Legacy function | Remove only the known role-owned symlink and refuse an unexpected override | Approved |
| Empty kill survivors | Filter the empty Fish list element and reach the intended success path | Approved |

## Open questions

There are no unresolved extraction questions.
Upgrade and rollback verification waits for a later release.
