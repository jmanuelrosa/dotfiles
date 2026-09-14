# Minion trusted-session implementation

Status: In progress against [the approved simplified specification](../specs/minion.md).
The detached runner, persistent SDK goal loop, trusted checkout execution, and optional publication path are complete; a representative live mission is not yet run.

## Scope rule

Build the smallest unattended version of a normal Pi session.
Do not add Docker, a daemon framework, a database, an event journal, a formal evaluator, a policy layer, or crash recovery.
If an implementation task starts needing one, stop and challenge the scope before adding it.

## Increment 1: detached runner and visibility

Owner: platform staff engineer.

Deliver one fake worker process that can be started explicitly, survives the launching process exiting, updates a small status file, writes a log, and can be watched or cancelled.
It does not load a model or edit a repository.

Likely files:

- `roles/ai/files/pi/extensions/minion.ts`
- `roles/ai/files/pi/minion/runner.ts`
- `roles/ai/files/pi/minion/state.ts`
- `lib/python/tests/test_pi_minion.py`
- one or two disposable test fixtures under `lib/python/tests/fixtures/`

Acceptance:

- [x] Extension load alone starts nothing.
- [x] Start requires an explicit confirmed command.
- [x] The fake runner remains alive after its launcher exits and has no terminal standard input.
- [x] Status reports running, elapsed time, PID identity, and last activity.
- [x] Watch reads the runner log without opening a second writer.
- [x] Cancel stops the fake runner's known process group and records that cancellation is best effort.
- [x] A stale or reused PID is not signalled without matching start identity.

Verified with focused offline pytest and Node syntax checks.
The four new runner/extension tests pass, and the focused Minion suite passes all 122 tests.
The latest full repository run reports 1079 passed, 22 failed, and 21 errors; the failure/error IDs match the pre-existing non-Minion Git and sandbox baseline.
A pre-existing deadline fixture could record an exit one millisecond before its asserted deadline because Node timers may wake early; its callback now rechecks the clock before recording the deadline exit.
No real model ran and nothing was published.
The extension is inert by default and registers `/minion` only when `MINION_ENABLE=1` is set explicitly during development.

## Increment 2: one SDK goal loop

Owner: DX staff engineer.

Replace the fake work callback with one persistent Pi SDK session driven by deterministic fake model responses.
Add the structured `minion_report` tool and the fixed continuation loop.

Likely files:

- `roles/ai/files/pi/minion/runner.ts`
- `roles/ai/files/pi/minion/goal-loop.ts`
- `roles/ai/files/pi/minion/runtime.ts`
- `lib/python/tests/test_pi_minion.py`
- deterministic fake-model fixtures

Acceptance:

- [x] One session performs several cycles without resetting context.
- [x] `continue`, `done`, and `blocked` produce distinct state transitions.
- [x] Missing or malformed reports receive one correction request and then count as no progress.
- [x] Elapsed, cycle, and no-progress limits stop the loop.
- [x] SDK abort stops new prompts and settles the known runner path.
- [x] No separate planner, evaluator, reviewer, or subagent scheduler is introduced.

Verified entirely offline with Pi's faux provider.
The focused Minion suite passes all 138 tests, including detached completion, blocking, correction, no-progress, elapsed and cycle limits, and cancellation during an active fake model stream.
Node syntax checks pass for every changed TypeScript file and the fake-provider fixture.
No live model request ran and the extension remains opt-in through `MINION_ENABLE=1`.
The full repository run reports 1095 passed, 22 failed, and 21 errors; the failure and error IDs match the pre-existing Git and sandbox baseline.

## Increment 3: trusted checkout execution

Owner: platform staff engineer.

Run the loop in a disposable Git repository through Pi's normal trusted resources and tools.
Add clean-checkout admission and one cooperative checkout lease.

Acceptance:

- [x] Dirty checkout and unresolved Git operations refuse without mutation.
- [x] A second Minion for the same canonical checkout refuses.
- [x] The worker receives the approved goal, priorities, project instructions, and routine-decision delegation.
- [x] Normal Pi guard or permission startup failures become `blocked`.
- [x] A deterministic worker edits a file and runs a local check in the current checkout.
- [x] Unexpected external changes stop the loop without reset, stash, or overwrite.
- [x] Docker and adversarial-containment diagnostics are not runtime prerequisites.

Verified offline with disposable checkout fixtures, Pi's faux provider, and a deterministic Git facade because this Pi sandbox denies the real Git binary access to `~/.gitconfig`.
The focused Minion suite passes all 145 tests.
It covers clean-checkout admission, unresolved operations, lease contention and release, project instruction loading, real Pi write and bash tools, guard startup failure, external checkout changes, deadlines, and cancellation.
Node syntax checks pass for every changed TypeScript and JavaScript file.
No live credentials or model request were used.
The latest full repository run reports 1101 passed, 23 failed, and 21 errors.
The existing 22 failures and 21 errors remain the Git and sandbox baseline; the additional unrelated failure is `test_pi_mcp_adapter_imports_existing_host_configs_from_a_linked_config`, where the checked-in expectation is empty but the current linked Pi MCP config contains Slack.

## Increment 4: delivery and representative use

Owners: DX staff engineer for the loop, parent session for integration.

Add the optional approved publication path using the existing commit and PR skills.
Then run one small real mission only after the user explicitly authorizes that mission and its model usage.

Acceptance:

- [x] Publication authority is displayed at start and cannot be added by the worker.
- [x] Unapproved commit, push, and PR creation do not occur.
- [x] Approved delivery invokes the existing skill commands rather than raw publication logic.
- [x] Publication failure preserves local work and reports `blocked`.
- [ ] A small feature or bug-fix mission reaches a review-ready branch or PR with local checks reported.
- [x] The human can inspect status and log while it runs without being asked routine questions.

Verified offline with deterministic Git fixtures, disposable commit and PR skill installs, and Pi's faux provider.
The focused Minion suite passes all 167 tests.
It covers complete start confirmation, post-confirmation checkout revalidation, all-or-nothing publication authority, report escalation refusal, mission-branch creation, reuse, conflict refusal and failed-launch rollback, lease-before-mutation ordering, skill expansion, commit evidence, recorded PR URLs, delivery-state visibility, external delivery changes, and publication failure with committed work preserved.
Node syntax checks pass for every changed TypeScript and JavaScript file.
The latest full repository run reports 1127 passed, 23 failed, and 21 errors.
All full-suite failures are the existing Git/sandbox and linked Slack MCP configuration baseline; the Minion suite has no failures.
No live credentials, forge access, or model request were used.
The representative live mission still requires explicit human authorization for its goal, model usage, and publication authority.

No merge, deployment, PR-comment monitoring, or automatic restart is added.

## Verification

Focused loop:

```sh
UV_OFFLINE=1 make test PYTEST='uv run --with pytest --with pyyaml pytest lib/python/tests/test_pi_minion.py -q'
```

Repository regression check:

```sh
UV_OFFLINE=1 make test
```

`make syntax` and `make lint` require vault input and remain human-run checks.
A passing Minion test proves the behavior named by that test, not adversarial process containment.

## Historical diagnostics

The superseded [guarded-runtime plan](2026-09-11-minion-implementation.md) records useful findings about provider host tools, project policy mutation, and detached descendants.
Those findings explain the trusted-session warning and best-effort cancellation language.
They do not justify rebuilding the rejected Docker architecture inside this MVP.

## Decisions

The user explicitly chose a trusted current-checkout session over both Docker containment and a trusted worktree.
The trusted-session MVP accepts the same machine authority and residual process risk as a manually launched Pi session.
The previous container checklist and base-image decisions no longer apply because V1 adds no container dependency.
The user chose one all-or-nothing `--publish` launch flag rather than granular delivery flags.
The user approved an exact `--minion-approved-at-launch` internal argument so the existing commit and PR skills treat the parent start confirmation as their delegated approval and do not prompt the detached worker again.
