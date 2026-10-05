# CI pipelines

When to read: the brief or diff touches workflow triggers, job graphs, conditions, path filters, concurrency, or required checks.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Silently skipped required check.** A job whose condition or path filter evaluates false never runs, and many merge gates treat an absent check as passing; untested code merges under a green light.
  Check: for every conditional or path-filtered job that gates merges, verify what the gate shows when the job does not run; make skipped block, or make the check unconditional.
- **Trigger firing wider than intended.** A trigger on broad events (all branches, all tags, schedules) runs on refs nobody considered, acting on or paying for surfaces outside the brief.
  Check: enumerate the refs and events each trigger matches and confirm each is intended; restrict with explicit filters, and confirm the filter combination is legal for the CI system rather than silently ignored.
- **Job graph that lies about dependencies.** Jobs sharing artifacts or state without a declared dependency edge run in whatever order the scheduler picks; green today, race tomorrow.
  Check: every consumer job declares its producer; nothing relies on incidental ordering or shared runner state.
- **Missing concurrency control.** Two runs on the same ref (rapid pushes, retriggers) interleave on shared resources: caches, environments, published artifacts.
  Check: runs that touch shared state carry a concurrency group with a deliberate cancel-or-queue choice.
- **Tolerated failure as a lie.** Steps marked as allowed to fail (continue-on-error, allow_failure, `|| true`) convert real failures into green checks that nobody reads.
  Check: every tolerated failure states why it is tolerable and surfaces its result somewhere a human looks.
- **Fork and bot blindness.** Pipelines behave differently for forked PRs (no secrets) and bot-authored events; a required job that cannot run on forks falsely blocks or falsely passes external contributions.
  Check: walk the pipeline as a forked PR and as a bot event; the behavior in both is intended, not accidental.
- **Retry masking a race.** A flaky job "fixed" with automatic retries hides the underlying race and multiplies queue time on every run.
  Check: retries are bounded and annotated with the known cause; an unexplained flake is investigated or quarantined visibly, not retried harder.
- **Flaky check gating merges.** A nondeterministic check in the required set ejects work from the merge queue and cascades re-runs across everything queued behind it.
  Check: checks added to the required set are deterministic; known flakes are quarantined out of the gate, never blanket-retried inside it.
- **Raw commands drifting from local.** A step that invokes raw tool commands instead of the project's own script names diverges from local behavior on the first script change.
  Check: steps call the project's lint, test, and build entry points; new logic lands in the script, not in pipeline YAML.

## Escalation triggers (`needs-decision`)

- Changing deploy triggers, target environments, or promotion rules (also an ask-first boundary in the agent).
- Changing which checks are required or how merges are gated (also an ask-first boundary in the agent).
- Removing or loosening an existing quality gate (also an ask-first boundary in the agent).

## What good looks like

- The pipeline is a DAG of explicit dependencies: cheap checks first, independent jobs in parallel.
- Every required check either runs on every merge candidate or blocks the merge when absent.
- CI steps are thin wrappers over the project's own scripts; a developer can run the same thing locally.
