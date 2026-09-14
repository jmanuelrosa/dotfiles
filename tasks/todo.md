# Shoo extraction tasks

Specification: `docs/design/port-extraction.md`
Plan: `tasks/plan.md`

## Task 1: Create the unpublished standalone repository foundation

**Status:** Complete.

**Description:** Create `~/Developer/port` as a clean local Git repository with no remote, carrying only the repository instructions, license, initial documentation, and test directory needed for the extraction.

**Acceptance criteria:**
- [x] The repository is initialized on `main` without transferred dotfiles history.
- [x] The MIT license preserves José Manuel Rosa Moncayo's attribution.
- [x] Repository instructions name the exact syntax, test, checksum, and release verification commands.

**Verification:**
- [x] `git -C ~/Developer/port log --oneline` contains no dotfiles commits.
- [x] `git -C ~/Developer/port remote -v` is empty.
- [x] The initial files contain no path back to the dotfiles checkout.

**Dependencies:** None

**Files likely touched:**
- `~/Developer/port/AGENTS.md`
- `~/Developer/port/LICENSE`
- `~/Developer/port/README.md`
- `~/Developer/port/.gitignore`

**Estimated scope:** Medium

## Task 2: Characterize basic CLI and output behavior

**Description:** Add the black-box harness and the first expectations for help, invalid arguments, missing `lsof`, exit statuses, and stream-aware color behavior.

**Acceptance criteria:**
- [x] A temporary executable wrapper lets the suite invoke the original three Fish files without embedding a dotfiles path in committed tests.
- [x] The basic suite passes against the original function.
- [x] The same suite fails against the missing standalone executable for the expected reason.

**Verification:**
- [x] `PORT_UNDER_TEST=<legacy-wrapper> python3 -m unittest tests.test_port.BasicCliTests -v` passes.
- [x] `python3 -m unittest tests.test_port.BasicCliTests -v` fails before `~/Developer/port/port` exists.

**Dependencies:** Task 1

**Files likely touched:**
- `~/Developer/port/tests/__init__.py`
- `~/Developer/port/tests/test_port.py`

**Estimated scope:** Small

## Task 3: Implement the standalone entrypoint, private UI, and help path

**Description:** Add the executable Fish asset with its shebang, private output helpers, usage text, argument parsing, dependency check, dispatch, and process exit propagation.

**Acceptance criteria:**
- [x] `./port --help` matches the original help bytes and exit status.
- [x] Invalid arguments and missing `lsof` preserve stdout, stderr, and status behavior.
- [x] `NO_COLOR`, `FORCE_COLOR`, piped stdout, and redirected stderr match the original.

**Verification:**
- [x] `fish --no-config -n ./port` passes.
- [x] `python3 -m unittest tests.test_port.BasicCliTests -v` passes.

**Dependencies:** Task 2

**Files likely touched:**
- `~/Developer/port/port`

**Estimated scope:** Small

## Task 4: Characterize listing and lookup behavior

**Description:** Extend the black-box suite with controlled `lsof` fixtures for TCP listeners, UDP filtering, single-port lookups, numeric sorting, dual-stack merging, and reachability scope.

**Acceptance criteria:**
- [x] Listing and lookup expectations pass against the original function.
- [x] Tests cover empty results, TCP and UDP parsing, duplicate merging, row counts, sort order, and local versus exposed scope.
- [x] The new tests fail against the incomplete standalone executable.

**Verification:**
- [x] `PORT_UNDER_TEST=<legacy-wrapper> python3 -m unittest tests.test_port.ListingAndLookupTests -v` passes.
- [x] `python3 -m unittest tests.test_port.ListingAndLookupTests -v` fails before the listing and lookup implementation is added.

**Dependencies:** Task 3

**Files likely touched:**
- `~/Developer/port/tests/test_port.py`

**Estimated scope:** Small

## Task 5: Implement standalone listing and lookup behavior

**Description:** Move the existing listener collection, UDP filtering, lookup parsing, row merging, numeric sorting, port parsing, host parsing, and scope classification into the executable.

**Acceptance criteria:**
- [x] Every Task 4 expectation passes against the standalone executable.
- [x] The implementation reads only controlled command output and keeps the existing output vocabulary.
- [x] No detail, Docker, or kill behavior is changed in this slice.

**Verification:**
- [x] `fish --no-config -n ./port` passes.
- [x] `python3 -m unittest tests.test_port.BasicCliTests tests.test_port.ListingAndLookupTests -v` passes.

**Dependencies:** Task 4

**Files likely touched:**
- `~/Developer/port/port`

**Estimated scope:** Small

## Task 6: Characterize detail, Docker, and kill behavior

**Description:** Extend the suite for process age, cwd, command line, connection tallies, width trimming, Docker container resolution, kill target selection, confirmation, signaling, failures, and survivors.

**Acceptance criteria:**
- [x] Advanced expectations pass against the original function except the approved empty-survivor regression.
- [x] The empty-survivor regression fails against the original with the confirmed blank-survivor result.
- [x] Every kill test uses a fake `kill` executable and records calls instead of signaling a process.
- [x] The new tests fail against the incomplete standalone executable.

**Verification:**
- [x] The legacy advanced tests other than `test_kill_signals_each_bound_pid_once` pass.
- [x] The legacy `test_kill_signals_each_bound_pid_once` test fails with the confirmed blank-survivor result.
- [x] `python3 -m unittest tests.test_port.DetailDockerAndKillTests -v` fails before the advanced implementation is added.

**Dependencies:** Task 5

**Files likely touched:**
- `~/Developer/port/tests/test_port.py`

**Estimated scope:** Small

## Task 7: Complete standalone detail and kill behavior

**Description:** Move the existing process detail, Docker annotation, connection tally, width trimming, and confirmed SIGTERM behavior into the executable.

**Acceptance criteria:**
- [x] Every Task 6 expectation passes against the standalone executable.
- [x] Kill mode targets only bound listeners, de-duplicates PIDs, confirms once, and never escalates automatically.
- [x] Docker remains optional and errors remain suppressed as before.

**Verification:**
- [x] `fish --no-config -n ./port` passes.
- [x] `python3 -m unittest discover -s tests -v` passes.

**Dependencies:** Task 6

**Files likely touched:**
- `~/Developer/port/port`

**Estimated scope:** Small

## Checkpoint: Behavior parity

- [x] The full suite passes against the original wrapper except the approved empty-survivor regression.
- [x] The full suite, including the corrected empty-survivor behavior, passes against the standalone executable.
- [x] Syntax passes and no test touches live process state.
- [x] Original and standalone help output match byte for byte.

## Task 8: Prove isolation and add standalone documentation and CI

**Description:** Add an isolation assertion, complete the README and repository instructions, and add macOS pull-request verification for syntax, tests, and executable shape.

**Acceptance criteria:**
- [x] Tests run with an empty Fish configuration and no dotfiles path available.
- [x] README documents the full interface, requirements, MacPorts collision, development, release, rollback, uninstall, and one-time Fish function eviction.
- [x] CI runs the documented commands on macOS and requires no secret.

**Verification:**
- [x] `env -i HOME="$HOME" PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" ./port --help` passes.
- [x] `python3 -m unittest discover -s tests -v` passes.
- [x] The workflow syntax and command paths are internally consistent.

**Dependencies:** Task 7

**Files likely touched:**
- `~/Developer/port/tests/test_port.py`
- `~/Developer/port/README.md`
- `~/Developer/port/AGENTS.md`
- `~/Developer/port/.github/workflows/pull_request.yml`

**Estimated scope:** Medium

## Task 9: Prepare the exact v0.1.0 asset and release notes

**Description:** Freeze the executable bytes, compute the checksum, verify deterministic source-as-asset identity, and prepare concise release notes without publishing anything.

**Acceptance criteria:**
- [x] The release candidate is the checked-in executable itself.
- [x] Its SHA-256 checksum is recorded for the later dotfiles declaration.
- [x] Release notes describe behavior, runtime requirements, installation, and the MacPorts name collision.

**Verification:**
- [x] `test -x ./port` passes.
- [x] `fish --no-config -n ./port` passes.
- [x] `python3 -m unittest discover -s tests -v` passes.
- [x] `shasum -a 256 ./port` produces the recorded checksum.

**Dependencies:** Task 8

**Files likely touched:**
- `~/Developer/port/README.md`

**Estimated scope:** Small

## Checkpoint: Publication approval

- [x] Local release readiness is complete.
- [x] Explicit publication approval has been received.

## Task 10: Publish the repository and v0.1.0 release

**Description:** After explicit approval, create the public GitHub repository, publish reviewed commits through the repository's Git skills, create the exact release asset, and verify downloaded bytes.

**Acceptance criteria:**
- [x] `jmanuelrosa/port` is public with the reviewed source and documentation.
- [x] Release `v0.1.0` contains exactly one executable asset named `port`.
- [x] The downloaded asset checksum matches the local release candidate.

**Verification:**
- [x] `gh repo view jmanuelrosa/port --json nameWithOwner,visibility,url` reports the expected public repository.
- [x] `gh release view v0.1.0 --repo jmanuelrosa/port` reports the expected asset.
- [x] `shasum -a 256 <downloaded-port>` matches the recorded checksum.

**Dependencies:** Task 9 and publication approval

**Files likely touched:** None beyond repository metadata prepared in earlier tasks

**Estimated scope:** Small

## Task 11: Add failing dotfiles installer tests

**Description:** Add retained tests that define the shell role's release declaration, exact URL and checksum wiring, executable mode, legacy-function safety, installed-file shape, and old-source retirement contract.

**Acceptance criteria:**
- [x] Tests fail before the installer declaration and tasks exist.
- [x] Tests distinguish the expected legacy role symlink from an unexpected override.
- [x] Tests require the installed command to be a regular executable, not a Fish function symlink.

**Verification:**
- [x] The focused installer suite failed for the expected missing installer behavior before implementation.

**Dependencies:** Task 10

**Files likely touched:**
- `lib/python/tests/test_shoo_role.py`

**Estimated scope:** Small

## Task 12: Implement the shell-role installer and lifecycle documentation

**Description:** Add the pinned `shoo` release declaration, safe legacy-function and command transitions, checksum-verified `get_url`, installed-asset smoke coverage, and shell role documentation.

**Acceptance criteria:**
- [x] The role declares the `shoo` repository, `v0.2.0`, exact asset URL, checksum, destination, and mode.
- [x] Only role-owned legacy Fish links and the checksum-matched `port v0.1.0` executable can be removed automatically.
- [x] The role installs a regular `shoo` executable and does not recreate the public Fish function link.

**Verification:**
- [x] `uv run --offline --with pytest --with pyyaml pytest -q lib/python/tests/test_shoo_role.py` passes.
- [x] `make test` passes.
- [x] `make syntax` passes with credentials.

**Dependencies:** Task 11

**Files likely touched:**
- `roles/shell/defaults/main.yml`
- `roles/shell/tasks/main.yml`
- `roles/shell/README.md`
- `Makefile`

**Estimated scope:** Medium

## Task 13: Verify provisioning behavior

**Description:** Exercise check mode, first installation, repeat installation, checksum identity, legacy function removal, and command resolution before deleting the old source.

**Acceptance criteria:**
- [x] Check mode reports intended changes without mutating the command.
- [x] First apply installs the declared bytes and repeat apply reports no changes.
- [x] A new Fish process resolves `shoo` to the installed executable and its help smoke test passes.

**Verification:**
- [x] `make check-role ROLE=shell` is non-mutating.
- [x] `make run-role ROLE=shell` succeeds once and is unchanged on the second run.
- [x] `test -f ~/.local/bin/shoo && test ! -L ~/.local/bin/shoo && test -x ~/.local/bin/shoo` passes.
- [x] `shasum -a 256 ~/.local/bin/shoo` matches the declaration.
- [x] `test ! -e ~/.local/bin/port` passes after the checksum-matched migration.
- [x] `fish --no-config -c 'type -P shoo; shoo --help >/dev/null'` resolves and succeeds with the configured `PATH`.

**Dependencies:** Task 12

**Files likely touched:** None

**Estimated scope:** Small

## Checkpoint: Source-removal approval

- [x] The published release and installed asset are verified.
- [x] Explicit old-source removal approval has been received.

## Task 14: Retire old source and update extraction records

**Description:** After explicit approval, delete the old public and private Fish application files, keep shared `_ui`, update the backlog and design status, and strengthen retained tests to require implementation absence.

**Acceptance criteria:**
- [x] Dotfiles no longer contains `port.fish` or `_port_usage.fish`.
- [x] `_ui.fish` and unrelated Fish functions are unchanged.
- [x] Backlog and design records point to the standalone repository and released version.

**Verification:**
- [x] `uv run --offline --with pytest --with pyyaml pytest -q lib/python/tests/test_shoo_role.py lib/python/tests/test_suites.py` passes.
- [x] The retired `port.fish` and `_port_usage.fish` source files are absent.
- [x] `git diff -- roles/shell/files/fish/functions/_ui.fish` is empty.

**Dependencies:** Task 13 and source-removal approval

**Files likely touched:**
- `roles/shell/files/fish/functions/port.fish`
- `roles/shell/files/fish/functions/_port_usage.fish`
- `lib/python/tests/test_shoo_role.py`
- `docs/design/port-extraction.md`
- `docs/design/standalone-script-apps-backlog.md`

**Estimated scope:** Medium

## Task 15: Run final verification

**Description:** Run standalone and dotfiles gates, inspect the final ownership boundary, and record any credential-gated verification that cannot run unattended.

**Acceptance criteria:**
- [x] Standalone syntax, tests, help, and checksum pass.
- [x] Dotfiles focused tests and full unattended suite pass.
- [x] Credential-backed syntax, check, apply, and smoke results are recorded accurately.

**Verification:**
- [x] In `~/Developer/personal/shoo`: `fish --no-config -n ./shoo && python3 -m unittest discover -s tests -v && ./shoo --help >/dev/null`.
- [x] In dotfiles: `make test`.
- [x] With credentials: `make syntax`, `make check-role ROLE=shell`, `make run-role ROLE=shell`, and `make verify`.
- [x] `git status --short` in both repositories contains only intentional work.

**Dependencies:** Task 14

**Files likely touched:**
- `docs/design/port-extraction.md`
- `tasks/todo.md`

**Estimated scope:** Small
