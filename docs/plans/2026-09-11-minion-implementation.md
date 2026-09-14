# Minion implementation

Status: Superseded by [the trusted-session plan](2026-09-13-minion-trusted-session.md).
This file is retained as the guarded-runtime diagnostic and decision history; its hardened runtime is not the V1 implementation target.

The user approved [the specification](../specs/minion.md) and explicitly authorized implementation.
Work follows its risk-first sequence, beginning with guarded-runtime validation.
No launcher, live mission, provisioning run, publication, or new dependency is needed for the first increment.

## First increment: guarded-runtime validation

Owner: platform implementation seat, with parent-session integration and verification.

- [x] Resolve the installed SDK from the actual Pi installation without embedding a Homebrew version.
- [x] Exercise an explicit headless session and collect extension-load diagnostics without a live model request.
- [x] Observe safe scratch writes succeeding and protected scratch writes failing through file tools and shell subprocesses in the user's normal-terminal environment.
- [x] Test attempts to modify or replace enforcement configuration, including project-local overrides, without weakening the approved policy.
- [x] Reject tool exercises with no explicit guards, extension-load errors, startup exceptions, error notifications, or a changed model selection.
- [ ] Prove positive enforcement readiness; absence of these diagnostic failures is not sufficient evidence.
- [x] Identify provider paths that bypass Pi's tool execution and reject them instead of changing providers.
- [x] Establish cancellation behavior and mark unproven descendant containment as blocked.
- [x] Record observed results separately from source-level findings and untested guarantees.

Likely new files: `roles/ai/files/pi/minion/` validation code and `lib/python/tests/test_pi_minion.py`.
No existing enforcement file will be weakened or made globally stricter as a side effect of this increment.
Tests use disposable scratch data, not real credentials or mission records.

Gate: the delivery loop cannot be implemented as runnable autonomous execution while required containment remains unproven.
A failed compatibility probe is a valid result, not a reason to report the gate passed.

## Approved Docker boundary revision

The user selected Docker-contained V1 after the detached-writer diagnostic disproved host-native SDK cancellation containment.
The approved detailed contract is [the Docker containment design](../design/minion-docker-containment.md).
It keeps model sessions and durable authority on the host, runs every worker-selected effect through Minion-owned tools inside one mission container, seeds a Docker-owned workspace from a read-only clean checkout, and imports only a stopped and validated candidate.
It initially refuses macOS-only and network-dependent missions.

This direction preserves the approved strict cancellation guarantee and supersedes direct autonomous writes in the human checkout.
It does not pass the containment gate by itself.
The user approved official `node:26.8.2-bookworm-slim` with no added OS packages as the containment-validation base.
Implementation remains blocked until its exact Linux arm64 digest is verified and recorded, and Docker capability, detached-descendant, filesystem, tool-mediation, and candidate-transfer probes pass.

## Subsequent increments

Each depends on the preceding gate and remains bounded by the approved specification.

1. Docker containment validation: local daemon and image identity, inspected hardening, whole-container termination, authority isolation, Minion-owned tool mediation, and safe candidate transfer.
2. Durable supervision: versioned records, journal recovery, checkout ownership, Docker identity and lifetime, cumulative clock, and cancellation tests with fake workers.
3. One delivery increment: approved mission to contained worker effects to candidate-bound evidence to structured evaluation, rejecting fabricated or stale evidence.
4. Delegation and quality: supervised child admission, one writer, aggregate usage, independent review, and bounded recovery.
5. Pi controls: explicit approval, start/status/inspect/cancel/resume, and role-owned installation without changing ordinary sessions.
6. Publication: existing commit/PR skills on the host, exact-candidate publication, and idempotent recovery from remote-operation uncertainty.
7. Representative missions: Linux-compatible feature and bug-fix acceptance plus interrupted and blocked recovery cases.

Decompose each increment into small file-owned tasks after its prerequisite passes; do not build later runtime abstractions against an unproven execution boundary.
Preference learning produces proposals only, never automatic profile changes.

## Verification and baseline

Use the existing Makefile test target, passing pytest selection through `PYTEST` for focused runs.
Use cached dependencies with `UV_OFFLINE=1` in this environment; no package additions are authorized.

Baseline before implementation:

- `make test` could not fetch pytest because the PyPI connection failed.
- `UV_OFFLINE=1 make test` ran from cache: 957 passed, 22 failed, 21 errors.
- The baseline log contains Git failures reading `~/.gitconfig` and scratch-file `Operation not permitted` failures.
- `git status --short` and `git branch --show-current` also fail reading `~/.gitconfig`, so branch and working-tree state are not verified.
- Do not bypass those restrictions, discard files, change global Git settings, or claim a clean baseline.
- `make syntax` and `make lint` require vault input and are not unattended checks.

## Runtime probe observations

`roles/ai/files/pi/minion/runtime-probe.ts` is a diagnostic harness, not a launcher or a production permission boundary.
It uses explicit extensions, offline model lookup, in-memory session state, and no automatic model fallback.
Its optional host-supplied exercise callback exists for integration tests; it is not exposed as a model tool.
An empty `rejections` list means only that the implemented diagnostic checks did not reject the session, not that containment is proven.
Run probes in dedicated Node subprocesses: capturing headless notifications temporarily changes the SDK's shared no-UI object and restores it during cleanup.
The callback, when supplied, must come from trusted test code.

`lib/python/tests/fixtures/minion-tool-execution.mjs` supplies deterministic assistant messages through the SDK stream override, with an in-memory dummy key and no live provider request.
The exercise uses `session.prompt()` and the actual agent tool pipeline, not direct calls to tool executors.
Synthetic guard tests prove that allowed scratch file and shell writes execute and hook-denied operations do not execute.
They do not prove OS-level isolation or descendant containment.

Observed with Pi 0.85.1, pi-sandbox 0.6.5, and pi-permission-system 27.1.1:

- SDK resolution, explicit model preservation, extension selection, startup rejection, and shutdown cleanup work in the probe.
- The installed guard exercise loads pi-sandbox, pi-permission-system, and this repository's guardrails extension.
- It uses fresh scratch agent/work directories and copies permission configuration to `agent/extensions/pi-permission-system/config.json`, matching installation layout.
- Sandbox policy permits the scratch work directory and denies writes to scratch authority records outside it.
- Startup reports `Sandbox initialization failed: listen EPERM: operation not permitted` for its Unix socket beneath the session's temporary directory.
- That failure arrives through `ctx.ui.notify`, not the SDK's extension-error callback; loading the extension and seeing no startup exception therefore missed it initially.
- The probe now records the notification as a rejection and does not run the tool exercise.
- Earlier hook-only diagnostics showed pi-sandbox alone did not block calls after initialization failure; the permission layer separately refused external file writes requiring interactive approval, while a harmless shell command remained allowed.
- No real authority record was touched, and no shell command from the installed-stack exercise was executed.
- The user's normal-terminal run progressed to a separate harness failure: `Theme not initialized. Call initTheme() first.`
- A regression test reproduced that failure when an extension formatted its headless status.
- The probe now calls the SDK's theme initializer with watchers disabled, matching noninteractive Pi startup without enabling an interactive UI.
- The focused suite passes all 23 tests after this fix.
- The user supplied a successful normal-terminal four-operation result after the fix: allowed file and shell writes succeeded, the sandbox rejected the protected file write, and the permission layer rejected the protected shell redirection.
- That shell rejection did not demonstrate an OS-level child write denial, so the exercise now also invokes a local Node script twice, with allowed and protected targets determined inside the script.
- The expanded six-operation exercise requires the allowed child write to succeed and the protected child to report an OS permission error, not a permission-layer refusal.
- The user supplied the expanded six-operation JSON result with no startup rejections and tool error flags `[false, true, false, true, false, true]`.
- The allowed Node child completed successfully; the protected Node child reached `writeFileSync` and received `EPERM` opening the scratch authority file.
- This is user-supplied evidence of OS-level denial for that child-write path, not an inference from a permission-layer refusal.
- The supplied output identifies Node 26.8.2; it does not include pytest's final pass/fail line.
- These observations do not establish policy-tampering resistance, cancellation, arbitrary descendant containment, or provider-host coverage.

The installed-stack test passes when it correctly refuses unsafe startup or when it actually demonstrates all six scratch operations with expected outcomes.
A passing refusal test is not a passing containment gate.
Its emitted JSON and JUnit property distinguish those outcomes.
A successful six-operation result would still leave provider host paths and descendant termination unproven.

Reproduce the installed-stack observation without a live model call:

```sh
UV_OFFLINE=1 make test PYTEST='uv run --with pytest --with pyyaml pytest lib/python/tests/test_pi_minion.py -k installed_guards -s'
```

The normal-terminal exercise has supplied the expected six operation outcomes without bypassing this session's sandbox.
The cancellation diagnostic slice is implemented in the existing Minion tests and test-only fixtures, not a production supervisor:

- [x] Drive a deterministic bash tool through `session.prompt()`, wait for child readiness, then invoke `session.abort()`.
- [x] Observe requested ordinary and detached-process-group modes separately, including writes after abort returns; report group identity as unverified when inspection is unavailable.
- [x] Bound every scratch process with its own self-termination deadline and distinguish probe cleanup from SDK cancellation.
- [x] Emit installed-stack startup refusal separately from exercised cancellation outcomes, retaining a blocked containment gate.

Record ordinary child termination separately from containment of descendants that detach from their original process group.
Do not equate successful cancellation of one shell with accounting for every writer.
Do not install a launcher, start a mission, or build the delivery loop while these gates remain unproven.

### Cancellation observations

`lib/python/tests/fixtures/minion-cancellation.mjs` drives the offline tool stream and records readiness, abort return, prompt settlement, post-abort writes, process inspection, and cleanup separately.
Its companion `minion-cancellation-child.mjs` gives both launcher and writer an independent timer against a shared six-second deadline.
Only those scratch processes watch the cleanup file; cleanup does not signal arbitrary PIDs or process groups.
Dedicated tests exercise both processes' deadline paths without abort or cleanup.

Observed in the parent full-suite run:

- Both synthetic modes reached readiness before abort, and both abort and prompt settled.
- Requested same-group mode produced zero additional writes during the 300 ms observation; this is not proof of termination.
- Requested detached-group mode produced 13 additional writes after abort returned, then recorded a `probe-cleanup` exit acknowledgment.
- Process inspection failed with `spawnSync ps EPERM`; the probe stopped further inspection attempts and left group identities and OS-observed termination unknown.
- Both classifications were `group-unverified`, with `containmentGate: blocked`; raw write observations remain available separately.
- Both installed-stack modes refused startup with the sandbox's `listen EPERM` notification, so neither exercised guarded cancellation.

Reproduce both synthetic and installed-stack observations in the user's normal terminal without a live model call:

```sh
UV_OFFLINE=1 make test PYTEST='uv run --with pytest --with pyyaml pytest lib/python/tests/test_pi_minion.py -k "cancellation_observes or installed_guards_report_cancellation" -s'
```

The user subsequently supplied all four normal-terminal observations, with group identities verified and no process-inspection errors:

- Synthetic same-group launcher and writer were no longer alive before cleanup, with zero post-abort writes.
- Synthetic detached-group writer remained alive and produced 12 post-abort writes; it stopped only after acknowledging probe cleanup.
- Both installed-stack modes loaded without rejections and reached readiness before abort.
- Installed-stack same-group launcher and writer were no longer alive before cleanup, with zero post-abort writes.
- Installed-stack detached-group writer remained alive in its own process group after abort and prompt settlement, producing 13 additional writes while its launcher was already stopped.
- That guarded detached writer acknowledged `probe-cleanup`, and subsequent inspection found it no longer alive; SDK cancellation did not stop it.
- All observations ended before the independent deadline, so deadline expiry does not explain the observed cancellation outcomes.
- The pasted output did not include pytest's final summary; these are user-supplied runtime observations, not a separately verified suite result.

This demonstrates that SDK abort alone does not contain detached writers even with the installed guard stack active.
It does not demonstrate escape from filesystem sandbox policy: the continued writes targeted permitted scratch files.
The containment gate remains blocked, and any proposed supervision boundary must address this demonstrated failure rather than treating prompt settlement or probe-only cooperative cleanup as cancellation.
Next, validate policy-tampering resistance and provider-host tool coverage while keeping autonomous execution disabled.
Supervisor death, arbitrary descendants, and reliable ownership of every writer remain untested; no runtime supervision gate is passed.

Provider follow-up: repository documentation identifies `cursor` as a host-tool bypass even when Pi builtins are exposed.
The continuation's read-only investigation received `Sandbox: read access denied` for the installed SDK documentation and Cursor package files, so API identifiers, aliases, and custom-provider coverage were not verified.
No provider eligibility change or fallback was made; rejecting the known provider name alone would not prove coverage of other registrations.

### Policy-tampering diagnostic slice

The implemented slice owns only `lib/python/tests/test_pi_minion.py` and the test-only fixtures `minion-policy-tampering.mjs` and `minion-policy-child.mjs`:

- [x] Attempt file-tool writes/edits and subprocess writes/rename replacements against scratch agent sandbox and permission configuration.
- [x] Exercise existing and initially absent scratch `.pi/sandbox.json` project overrides separately.
- [x] Require an ordinary scratch-file positive control before treating a policy refusal as evidence.
- [x] Compare policy bytes/existence independently of tool error flags, retaining startup refusal and inconclusive outcomes separately.
- [x] Use a fresh session and scratch policy for each attempt; never reload or exercise more tools after successful policy mutation.

These probes test configuration immutability, not whether a changed configuration actually grants broader authority.
No real enforcement configuration is modified, and successful mutation keeps the containment gate blocked.

The matrix contains 15 cases: three existing policy targets across four operation kinds, plus three creation operations for the absent project override.
The shell child determines its target internally and records whether it reached the filesystem operation, completed it, or received `EPERM`/`EACCES`.
A hook refusal is recorded separately from a child filesystem refusal; an unexplained tool error is not classified as denial.
Snapshots also detect symlink retargeting with unchanged bytes.
Synthetic tests detect mutation despite an error result and keep no-op success, failed controls, missing attempts, and startup refusal distinct.

The parent full-suite run passed all 61 new policy tests, but all 15 installed-stack cases reported `startup-refused` with the sandbox's `listen EPERM` notification.
None executed a control or policy attempt, and none changed scratch policy.
At that point, installed policy-tampering resistance remained unproven; a passing diagnostic test is not a passing containment gate.

The user subsequently supplied all 15 normal-terminal observations, with no startup rejections and successful positive controls:

- All eight attempts against the scratch agent's sandbox and permission configuration were denied, with snapshots unchanged.
- File writes and edits were refused by tool-call hooks; shell writes and rename replacements reached filesystem operations and received `EPERM` for `open` and `rename` respectively.
- All four attempts against existing project `.pi/sandbox.json` succeeded and changed its bytes.
- All three attempts to create an initially absent project override succeeded.
- File tools and child filesystem operations could therefore mutate or introduce project sandbox configuration despite the protected scratch agent directory.
- The candidate project configuration was `{"enabled":false}`; no reload or subsequent tool exercise was performed, so effective sandbox disablement was not demonstrated.
- The pasted output did not include pytest's final summary; these are user-supplied runtime observations rather than a separately verified suite result.

Policy immutability fails for the tested project override paths, while the two tested agent-level configuration files resisted all attempted mutations.
This is a second demonstrated blocker alongside detached-writer cancellation.
No real policy was changed and no passing runtime containment gate is claimed.
A revised Minion-only boundary must protect project override creation and replacement without changing ordinary sessions; protecting only the agent directory is insufficient.

A follow-up diagnostic now derives a Minion-only scratch sandbox policy that keeps the work directory writable while adding its `.pi` directory to `denyWrite`.
The installed `pi-sandbox` 0.6.5 documentation and config source show that global and project path arrays are combined and that `denyWrite` takes precedence over `allowWrite` as a hard block.
That package evidence supports the candidate policy shape but is not runtime evidence that all seven existing/absent project-override operations are contained.
The same config source shows a separate startup risk: the project `enabled` scalar overrides the global value, and the extension reports `Sandbox disabled via config` as an informational notification rather than an error.
The runtime probe now treats any startup notification beginning `Sandbox disabled` as a rejection.
An installed-stack test supplied a disposable project override containing `{"enabled":false}` and observed that exact informational notification; the probe returned before any tool preflight or exercise, and the ordinary scratch target remained absent.
This proves refusal of the tested pre-existing disable override, not resistance to an external configuration race during startup.

The parent environment refused all seven installed-stack in-run follow-up cases at sandbox startup with the existing `listen EPERM` notification, before their positive controls or policy attempts ran.
The user subsequently supplied the complete normal-terminal matrix and its `7 passed, 111 deselected` summary:

- All seven cases loaded without startup rejections, completed their ordinary-file positive controls, attempted the policy operation, classified it as `denied`, and left the target unmodified.
- File-tool writes and edits against an existing project override were refused by the sandbox's `tool_call` hook.
- Shell writes and rename replacements against an existing project override reached their child filesystem operations and received `EPERM` from `open` and `rename`.
- File and shell attempts to create an initially absent project override were denied through the same respective layers.
- The Minion-only `denyWrite` therefore protects the tested existing and absent project `.pi/sandbox.json` paths even though the work directory remains writable.

This is user-supplied runtime evidence for the tested operations, not a parent-session rerun.
Combined with the installed disabled-project test, the candidate boundary now covers a pre-existing `enabled:false` override by startup refusal and covers in-run creation/replacement by hard denial.
It does not test an external race during startup, broader `.pi` directory surgery, or policy changes made outside the guarded session.
No real policy was changed, and the repository's ordinary Pi sandbox configuration remains untouched.

Run the original installed matrix in the user's normal terminal and retain the final pytest summary:

```sh
UV_OFFLINE=1 make test PYTEST='uv run --with pytest --with pyyaml pytest lib/python/tests/test_pi_minion.py -k installed_guards_report_policy -s'
```

Stdout omits full policy-byte snapshots, but tool results still include large edit diffs; a future output-only refinement should omit those details while retaining result text and full JUnit properties.

Run the seven-case Minion-specific candidate policy in the user's normal terminal without changing any real policy:

```sh
UV_OFFLINE=1 make test PYTEST='uv run --with pytest --with pyyaml pytest lib/python/tests/test_pi_minion.py -k installed_guards_report_minion_project_policy -s'
```

The Minion-specific sandbox candidate addresses the demonstrated project-override mutations for the tested operations, but it is still diagnostic-only and has not been integrated into a production launch boundary.
Detached writers surviving cancellation remain a demonstrated containment blocker, so autonomous execution stays disabled.

### Provider execution-path diagnostic slice

The runtime probe now loads only the explicit extension set before final model resolution and applies queued provider registrations to its scratch `ModelRuntime` without loading project or global extensions by discovery.
Provider registration failures remain load diagnostics, and successfully applied queues are cleared before session binding so the harness does not apply them twice.
No provider request is needed to inspect the selected model's effective API and provider registration provenance.

Provider admission is based on execution-path evidence rather than provider name:

- An effective `cursor-sdk` API is classified as the known provider-owned host-tool path and refused before session creation, regardless of provider ID or model alias.
- A selected provider registered by an extension through either the config or complete native-provider form is classified as unverified and refused conservatively.
- An untouched Pi built-in provider is eligible only for this provider-path check; its classification still carries `containmentGate: blocked` and does not override the cancellation or policy blockers.
- Provider-name-only tests deliberately show that the string `cursor` is not itself the decision, while a synthetic non-Cursor provider ID carrying `cursor-sdk` is refused.

Installed package source and documentation for `pi-cursor-sdk` 0.3.6 identify three callable surfaces: Cursor SDK host tools, configured Cursor MCP, and the optional Pi bridge.
They state that Pi tool toggles do not disable the first two surfaces and show the extension registering provider `cursor` with API `cursor-sdk` and a custom `streamSimple` handler.
This is source-level evidence about the installed package, not a live provider run.

The installed extension was also loaded through Pi's real `DefaultResourceLoader` with `CURSOR_API_KEY` absent, a disposable agent directory, and `PI_OFFLINE=1`.
Its fallback `cursor/auto-smart` model resolved with effective API `cursor-sdk`; the probe classified it as `known-host-tools` and returned before `session_start`, prompting, or tool execution.
This offline installed-extension observation makes no model request and does not inspect credentials.
The same classifier rejects unknown extension provider implementations rather than claiming that their internal tool handling has been proved safe.
It does not establish that every future Pi built-in provider remains mediated, so executable resources, model identity, and provider provenance still require preflight revalidation in a later runtime.

The provider slice's focused Minion suite passed all 108 tests at that point.
Autonomous execution remains disabled because provider-path refusal does not address either demonstrated containment failure.

## Implementation verification

The latest completed full-suite run reported 1075 passed, 22 failed, and 21 errors, including all 118 passing Minion tests.
Failing and errored test IDs match the continuation's non-Minion baseline exactly, with no added or resolved failure/error IDs.
The latest JUnit run selected `junit_family=xunit1` to retain observation properties without the previous xunit2 compatibility warnings; repository defaults were not changed.
The cancellation and policy classifiers were tested RED/GREEN before integration, and their Node fixtures passed syntax checks.
The pre-existing failures remain a separate limitation; no baseline test was skipped or disabled to make Minion pass.
Node syntax checks and specification/plan link, fence, and prose-character checks passed.
An earlier full-suite attempt timed out after 120 seconds and is not counted as a completed verification run.
Git inspection still fails reading `~/.gitconfig`.
Syntax and lint checks requiring vault input have not run.

No commits or pushes are part of the first validation increment.
Existing files, including the user-provided transcript, must be preserved.

## Decisions

The approved specification already defines the implementation order and has human approval, so planning does not introduce another routine approval checkpoint.
This repository's documented plan directory is used instead of the planning skill's generic `tasks/` layout.
The incremental-implementation skill's automatic commit step is deferred: publication uses the required skills, and Git state cannot currently be verified.
The user explicitly chose Docker containment over a macOS VM, weakened host-native cancellation, or stopping after diagnostics.
The platform container checklist required a pinned base image; Tier 1 dependency precedence applied, so no image was selected until the user approved `node:26.8.2-bookworm-slim` without added OS packages.
The immutable Linux arm64 digest remains a verification gate rather than an inferred value.
