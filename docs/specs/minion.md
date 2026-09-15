# Minion: a trusted unattended Pi session

Status: Approved simplified specification.
The user approved the trusted-session direction and explicitly rejected Docker-level containment for V1.

## Problem

I want to hand Pi a clear coding goal, leave it working, and come back to useful finished work without approving routine implementation decisions along the way.

The product is not a hardened multi-tenant agent runtime.
It is the unattended version of a Pi session I would otherwise run and supervise myself.

## Outcome

From Pi, I can explicitly start one Minion for the current repository.
The Minion keeps working after I close the launching Pi session or terminal, while the machine remains running.
It plans, edits, runs checks, fixes failures, and makes routine in-scope decisions using the same project instructions, skills, tools, credentials, and trust model as a normal Pi session.

I can check what it is doing, read its session output, or request cancellation.
It finishes with a review-ready PR when publication was approved, preserved local changes when it was not, or a concise genuine blocker.

## Product principles

- **Unattended, not adversarial.** Treat the Minion like a normal trusted Pi session running in the background.
- **Goal over plan.** The human defines success; the Minion chooses and revises the implementation path.
- **Routine decisions are delegated.** Do not interrupt for ordinary code, test, or refactoring choices inside the approved goal.
- **Safety nets over a security rocket.** Use project checks, review, bounded time, clean-checkout admission, and visible progress.
- **Simple state.** A session transcript, a small status record, and a log are enough for V1.
- **Honest stopping.** Done, blocked, cancelled, and crashed are different outcomes.

## Commands

Proposed command vocabulary:

| Command | Behavior |
|---|---|
| `/minion start <goal>` | Resolve the repository, goal, delivery authority, model, and limits; show one confirmation; then launch the background runner |
| `/minion status [id]` | Show running state, elapsed time, cycle count, last activity, branch, and result or blocker |
| `/minion watch [id]` | Show or follow the Minion's session log without taking control of the worker session |
| `/minion cancel [id]` | Request SDK abort and stop the background runner, reporting cancellation as best effort |

Starting is always an explicit human command.
Loading the extension, model output containing command text, or reopening Pi never starts work.

V1 has no prepare, inspect, resume, dashboard, scheduler, or automatic restart commands.
A crashed or interrupted Minion preserves its checkout and session for the human to inspect, then stops.

## Start approval

`start` shows a compact resolved summary:

- repository and current branch
- goal and success conditions
- non-goals or explicit constraints supplied by the user
- selected model
- maximum elapsed time and loop cycles
- whether commit, push, and PR creation are authorized
- warning that the Minion has the same machine authority and residual risk as a normal Pi session
- warning that the human should not edit the checkout while it runs

One confirmation launches it.
Cancelling the confirmation writes no mission and starts nothing.

## Execution model

The extension launches one detached Node runner with its standard input closed and output redirected to a mission log.
The runner owns one persistent Pi SDK session and one small status file.
It uses the current checkout directly and acquires a cooperative one-Minion lease for that checkout.

The runner loads the same global and project instructions and the same trusted extensions and skills a normal Pi session would load.
It does not invent a second permission system.
Provider choice and tool behavior follow the user's normal Pi setup.

The machine staying awake and the local provider remaining available are operational prerequisites.
Closing the launching terminal is supported.
Machine reboot, automatic process restart, remote execution, and migration to another machine are not.

## The goal loop

Each cycle gives the same worker session:

- the approved goal and success conditions
- the user's stated priorities and constraints
- current checkout and test state
- the instruction to make routine in-scope decisions without asking
- the instruction to report only completion, a real blocker, or the next useful work

The worker has one structured `minion_report` tool with three outcomes:

| Outcome | Meaning |
|---|---|
| `continue` | Progress remains; include the next useful action |
| `done` | The goal is satisfied; include changed areas and checks run |
| `blocked` | A specific missing authority, credential, requirement, or unavailable check requires human action |

A report ends the current cycle.
On `continue`, the runner sends a short fixed continuation prompt to the same session.
On `done` or `blocked`, it records the terminal result and stops.
If the worker ends a cycle without a valid report, the runner asks once for the report and then counts the cycle as no progress.
Repeated no-progress cycles stop as blocked rather than prompting forever.

There is no separate planner, evaluator, reviewer panel, child-agent scheduler, mission journal, or evidence database in V1.
The worker may use existing subagents when the normal Pi setup allows them, but Minion does not add orchestration of its own.

## Acting like me

The Minion gets its decision style from the same places a normal session does:

1. global and project `AGENTS.md`
2. the approved goal and its explicit priorities
3. relevant installed skills
4. the existing codebase and tests

The launch prompt makes the delegation explicit:

- prefer simple, idiomatic changes that match the repository
- make routine implementation decisions independently
- challenge a requested approach when a simpler path better serves the goal
- test observable behavior rather than declaring confidence
- do not expand the goal merely because another improvement is nearby
- stop only for a real ask-first boundary or missing information

Minion does not learn a permanent personality profile, mine unrelated sessions, or automatically modify preferences in V1.

## Checks and completion

The worker runs the repository's documented checks and fixes failures caused by its changes.
It should inspect its final diff and use existing review skills when useful, but V1 does not require a separate evaluator model.

`done` means:

- the worker believes the stated goal and success conditions are met
- required local checks were run, or an unavailable check is disclosed
- the checkout contains no unresolved conflict or partial operation
- the final report names the important changes and observed checks
- when PR delivery was approved, the expected PR exists or publication failure is reported as blocked

The runner performs cheap objective checks it can verify without reimplementing project policy, such as whether the process exceeded its limits and whether an approved PR result was actually recorded.
It does not build a formal criterion-evidence engine.

## Git and delivery

V1 requires a clean checkout and no unresolved Git operation before launch.
It creates or uses one conventional mission branch and refuses a conflicting branch.
The human agrees not to edit that checkout until the Minion stops.
Unexpected external changes make the Minion stop as blocked rather than stash, reset, or overwrite them.

If commit, push, and PR creation were approved at start, the runner invokes the existing commit and PR skills in the worker session when the implementation is ready.
It never force-pushes, merges, deploys, or edits unrelated branches.
If publication was not approved, it leaves verified local changes on the mission branch.

## Status and visibility

Each mission stores under Pi's resolved agent directory:

- one immutable launch summary
- the Pi session file path
- one replaceable status JSON file
- one append-only human-readable log
- the detached runner PID and start identity

The status record contains only what the UI needs: mission ID, state, repository, branch, goal summary, start time, elapsed time, cycle count, last activity, session path, result, and blocker.
It is operational metadata, not a transactional event store.

`watch` reads the log produced by the same background session.
It does not attach a second writer or mutate the worker conversation.

## Limits and stopping

Every launch has bounded elapsed time and loop cycles.
The resolved values are shown before confirmation.
Reaching either limit requests abort, preserves the checkout and session, records `limit-reached`, and stops the runner.
Limits do not reset because the user opens another Pi session.

Cancellation is best effort, matching the trust model of a manually run Pi session:

- stop sending new prompts
- call SDK abort
- terminate the detached runner's known process group
- preserve files and session state
- report what was requested and what was observed

V1 does not claim that arbitrary daemonized descendants are contained or killed.
That residual risk is accepted by choosing the trusted-session MVP.

## Failure behavior

| Failure | Result |
|---|---|
| Model or authentication unavailable | `blocked` with the selected provider/model |
| Required extension fails to load | `blocked` |
| Interactive permission is required while unattended | `blocked` |
| Required check unavailable | `blocked` or disclosed incomplete result, never silently passed |
| No progress across the configured cycle limit | `blocked` |
| Elapsed or cycle budget reached | `limit-reached` |
| Runner exits unexpectedly | `crashed`, preserving checkout, session, and log |
| Cancel requested | `cancelled` when the runner exits, with best-effort scope stated |
| PR publication fails | `blocked` with local work preserved |

There is no automatic retry after process crash, machine restart, uncertain push, or PR creation in V1.
The human inspects the result and starts a new Minion if desired.

## Placement

- Pi command extension: `roles/ai/files/pi/extensions/minion/index.ts`
- Background runner and small helpers: `roles/ai/files/pi/minion/`
- Integration tests: `lib/python/tests/test_pi_minion.py` and disposable fixtures beside the existing Minion fixtures

Use erasable TypeScript and the installed Pi SDK.
Add no package dependency, daemon, Docker image, database, or standalone CLI.
Install through the existing AI role symlink pattern.
While implementation is incomplete, the extension remains inert unless `MINION_ENABLE=1` is set explicitly.

## MVP acceptance

- Only explicit confirmed `/minion start` launches a runner.
- The runner continues after the launching Pi process and terminal close in a deterministic fake-model test.
- One persistent SDK session performs multiple goal cycles until `minion_report` returns `done` or `blocked`.
- The worker can edit the current checkout and run repository checks through the normal Pi tools.
- Routine in-scope decisions do not require human prompts.
- Clean-checkout and one-Minion lease failures refuse launch without changing files.
- Status and watch show current progress and the underlying session location.
- Time, cycle, no-progress, guard-load, permission, and provider failures stop with distinct states.
- Cancel stops new cycles, requests SDK abort, terminates the known runner process group, and describes its best-effort limit honestly.
- Approved publication uses the existing commit and PR skills; unapproved publication does not occur.
- A representative small feature and bug fix finish with passing local checks and a review-ready result.
- No Docker, VM, scheduler, evaluator service, evidence database, or automatic restart is installed.

## Not doing in V1

- adversarial process or filesystem containment
- Docker or VM isolation
- durable event sourcing or crash-perfect recovery
- automatic restart after reboot or runner crash
- remote machines or multi-repository queues
- multiple concurrent writers in one checkout
- formal acceptance-criterion evidence graphs
- separate planner, evaluator, and reviewer agents
- preference learning
- PR comment babysitting, merge, deployment, or CI monitoring

## References

The user-provided [Theo transcript](../../theo-trans.md) is the product reference.
Its useful pattern is a clear goal and priorities, a capable background thread, permission to make decisions, progress visibility, and testing as a safety net.
It does not demonstrate or require a hardened local execution boundary.

The previous [Docker containment design](../design/minion-docker-containment.md) records the stronger alternative that was considered and rejected for V1.
The guarded-runtime diagnostics remain useful engineering evidence, but their adversarial containment gates no longer define MVP acceptance.
