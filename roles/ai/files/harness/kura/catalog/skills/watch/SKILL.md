---
name: watch
description: A recurring, report-only sweep of one signal source, meant to be scheduled - `sentry` (new and regressed production errors, routed through triage) or `janitor` (dead code, unused dependencies, and agent-instruction workarounds a newer model no longer needs). Use when asked to watch production errors, run the janitor, or set up a recurring sweep. Writes one report outside the repo; files nothing, posts nothing, edits no source.
argument-hint: "sentry | janitor"
---

# Watch

A sweep that runs without me watching, so it changes nothing outside its own report.
Promoting a watcher to filing issues or opening PRs is a later, explicit decision of mine, not something a good run earns on its own.

ARGUMENTS: `sentry` or `janitor`. If empty, ask which.

Write the report to `$XDG_STATE_HOME/watch/<repo>/<mode>-<YYYY-MM-DD>.md`, with `~/.local/state` when `XDG_STATE_HOME` is unset and `<repo>` the basename of `git rev-parse --show-toplevel`. Create the directory if absent, and end the run by printing the path and the one-line summary.
The report lives outside the checkout so a later commit cannot pick it up; in a cloud run, where no local path survives, the final message is the report.
If a report for the same mode exists from an earlier run, read only its summary and item ids, so the new report can mark each item `new`, `still open` or `gone`.

## sentry

1. Load the `sentry` skill and list unresolved `error` and `fatal` issues the way it prescribes, with `--period` set to the time since the previous report, or `24h` on a first run. A missing CLI or an auth error ends the run with that error as the report.
2. Keep issues first seen inside the window or with substatus `regressed`. Sort by event count.
3. Triage the top items with the `triage` skill, capped at ten per run so a noisy day costs a bounded amount. Name how many were left untriaged.
4. Report: a table of every kept issue (short id, title, count, new/still open/gone), then the triage block for each triaged item.

Do not fix anything in this mode, even an obvious one-liner; the triage hand-off is how a fix gets dispatched.

## janitor

Three sweeps, each reported as a list of candidates with the evidence that makes each one a candidate.

1. **Unused code and dependencies.** When the repo has a JS/TS manifest, run the `knip` binary through the lockfile's package manager in its default report mode, never `--fix`. Other stacks: use the stack's own unused-code linter if one is configured; otherwise skip and say so.
2. **Complexity that earns nothing.** Read only files changed since the previous janitor report (`git log --since`) and list what the code-review policy's simplification axis would flag: dead branches, single-use indirection, duplicated logic. Report, never apply.

Do not load the `knip` or `code-simplification` skills for this: both instruct their reader to delete or rewrite, which an unattended report-only run must not do.
3. **Workarounds a newer model makes obsolete.** Read the repo's agent instructions (`CLAUDE.md`, `AGENTS.md`, `.claude/`, `.agents/`, rules, hooks, skills authored here) and list each rule, hook or skill step whose stated reason is a past model weakness (a failure it kept repeating, a check it kept skipping) rather than a project decision. For each, name the reason given and what a run without it would risk. These are candidates for me to delete, because instructions that outlive their reason still cost tokens on every turn.

Rank the report by expected payoff (lines or tokens removed against risk) and cap it at fifteen candidates; a janitor report nobody can finish reading gets ignored.

## Scheduling

`sentry` runs locally only, with `/loop 24h /watch sentry`: the `sentry` wrapper and its per-account config exist only on my machine, so a cloud routine has neither.
`janitor` needs only the checkout and the package manager, so it can also run as a cloud routine through `/schedule`, where its report is the run's final message.
Run each mode once by hand before scheduling it, and read that report: a watcher whose first report is noise will be noise every day.
