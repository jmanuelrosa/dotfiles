# Orchestration and scheduling

When to read: the brief or diff touches DAG or asset dependencies, schedules, sensors, retries, catchup, run overlap, or timezones.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Catchup surprise.** A pipeline deployed with a past start date and catchup or backfill-on-deploy semantics left at their default immediately schedules every missed historical run.
  Check: catchup behavior is explicit in the pipeline definition, and a new or changed schedule states which historical windows, if any, it should run.
- **Cron hope instead of data readiness.** A schedule that fires at a fixed time hoping upstream landed by then processes partial or missing data on every late day.
  Check: upstream dependencies are expressed as sensors, asset or dataset dependencies, or event triggers where the orchestrator supports them; a bare cron time carries a stated justification.
- **Hidden cross-pipeline dependency.** Pipeline B reads what pipeline A writes with no declared edge; the ordering is a scheduling coincidence that breaks on the first slow day.
  Check: every data handoff, between tasks or across pipelines, is a declared dependency (task edge, dataset or asset trigger, sensor), or the gap is flagged in the report.
- **Retry without design.** Default retries re-execute non-idempotent tasks; zero retries turn a transient blip into a failed run and a page.
  Check: retries are deliberate per task, with backoff, and every retried task passes the idempotency-and-replay checks.
- **Run chained on its past.** A run gated on the previous run's success serializes backfills and stalls every future run behind one failure.
  Check: prior-run dependencies exist only where the transform genuinely needs prior state, and that need is stated.
- **Top-level code at parse time.** Expensive or side-effectful code at module level runs on every scheduler parse loop, not once per run (called out explicitly in Airflow's best-practices doc).
  Check: connections, queries, and API calls live inside task callables, not at definition level.
- **Handoff through local disk.** Inter-task state written to the local filesystem vanishes when the next task lands on a different worker.
  Check: data moves between tasks via shared storage keyed by the run's window; only small values ride the orchestrator's own payload mechanism.
- **Overlapping runs.** A slow run still executing when the next fires; both mutate shared state or double-process the window.
  Check: max active runs or an equivalent concurrency policy is explicit, with a deliberate queue, skip, or cancel choice.
- **Timezone and DST drift.** A schedule defined in local time shifts against UTC data twice a year, and a "daily" window is 23 or 25 hours on DST transition days.
  Check: schedules and window boundaries declare an explicit timezone, and the DST behavior for that timezone is stated, not assumed.
- **Failure absorbed silently.** A task allowed to fail without failing the run, or a pipeline whose failure notifies nobody, converts breakage into stale data nobody notices.
  Check: every pipeline has an on-failure path someone sees (alert, callback, failed-run visibility), and any tolerated failure states why.

## Escalation triggers (`needs-decision`)

- Enabling catchup or changing a schedule or start date so historical runs would execute: that schedules a backfill (also an ask-first boundary in the agent).
- Changing a schedule that downstream teams' freshness expectations depend on.
- A cross-pipeline dependency the orchestrator cannot express: propose the mechanism, don't hand-roll polling.

## What good looks like

- The dependency graph states data readiness; a run fires because its inputs exist, not because a clock struck.
- Deploying a pipeline change never runs history by surprise.
- Failures page someone; late data delays the run instead of corrupting it.
