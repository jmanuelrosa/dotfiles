---
name: review-mechanics
description: Machinery for producing a code review report, covering the verification bar, effort levels, seat routing, skip rules and report format. Invoke before writing any review, from /code-review or by hand.
---

# Producing a review

The severities, the eight axes and the reviewer's boundaries live in `~/.claude/rules/code-review.md` and are already loaded.
This skill is the machinery for turning a read diff into a report.

## The verification bar

Every finding carries three things, or it is not reported:

1. A `file:line` in the **source**, read and confirmed. Not inferred from a name, a path, or a convention.
2. A concrete failure scenario: the inputs or state, then the wrong output, crash, or cost. "This could be a problem" is not one.
3. The mechanism, in one clause. What is actually wrong, not that something feels wrong.

A finding that cannot state a failure scenario is an opinion.
Drop it rather than dressing it as a risk.
When you are unsure whether a path is reachable, say so in the finding and lower the severity rather than hedging the wording.

Never claim a behaviour you have not read.
If the diff changes a function, open its callers before asserting anything about the effect.

## Effort

Effort changes the bar, not the axes: at `low` and `medium` report only what you are most confident in, and from `high` up cast a wider net and let the verification bar do the filtering.

`/code-review` takes the level as its first argument, and this table is the authority on which one.
Every other artifact that tells you to run a review names a level consistent with it.

| Situation | Effort |
|---|---|
| A hook, a config tweak, or a one-file fix you already understand | `low` |
| An ordinary single-concern diff before `/commit` | `medium` |
| One seat's completed slice, or any diff against a stack you do not know | `high` |
| A multi-seat or multi-worktree integration, or a release | `max` |
| A deep pass you do not want to spend local tokens on | `ultra` |

`xhigh` sits between `high` and `max` and needs a reason to pick over either.
`ultra` is not a step up from `max`: it runs in the cloud, is billed separately from the session, and needs claude.ai account access, so it is a deliberate choice rather than the top of the ladder.

## Seat routing

A seat's `<seat>:<seat>-failure-modes` skill is the deep checklist for its axes, and its own trigger table picks which references to open.
Invoke the skill rather than naming reference files, so retitling a reference upstream does not strand this guidance.

| Axis | Seats |
|---|---|
| Contract and compatibility | `database:database-failure-modes`, `backend:backend-failure-modes`, `platform:platform-failure-modes` |
| Security and privacy | `security:security-failure-modes`, plus `frontend`, `mobile` and `desktop` for their own security references |
| Failure visibility and operability | any installed seat's `failure-visibility` reference, and `sre:sre-failure-modes` for alerting and tracing |
| Test adequacy | `qa:qa-failure-modes` |

Seats are plugins, so they load only when the plugin is installed in this project, the workspace is trusted, and the session has been restarted.
Check, then route.
If the seat is absent, review the axis from the policy and say in the summary that the deep checklist was unavailable.
Never assume a seat is present because the axis needs it.

## Skip rules

Report nothing in: generated or vendored trees, lockfiles, snapshots and fixtures asserting only shape, and `roles/ai/files/claude/skills/<upstream>` trees in the dotfiles repo, since `claude-kit update` replaces those wholesale and a finding there is discarded on the next sync.

Do not spend the output cap on what a hook already blocks:

- Em and en dashes. `em-dash-gate.sh` refuses them at Write time.
- Lint and typecheck failures. `pre-commit-verify.sh` runs both before any commit.
- Attribution lines and `--no-verify`. `git-skill-gate.sh` hard-blocks them.

A finding that duplicates a hook teaches the reader that the report is padding.

## Nit discipline

At most three nits per review, and zero when a blocker is present.
Pick the three with the highest ratio of clarity gained to churn caused.
Everything else is dropped, not deferred to a list, because an appendix of nits is the same cost as reporting them.

## What is out of scope, because it writes

The reviewer does not mutate, so none of these run during a review:

`/code-review --fix`, `code-simplification`, `/simplify`, `knip --fix`, `coderabbit`, `pr`, `performance-optimization` steps 3 onward, `cc-review`'s apply step.

`--fix` is named first because it is the one the harness itself ships, so a ban that skipped it would read as forbidding only other people's tools.
`cc-staff-reviewer` reviews the Claude Code setup and never application code, so no code finding routes there.

`code-review-and-quality` is superseded as a reviewer, not as a skill.
Its five axes are a subset of the policy's eight (it covers none of contract and rollback, failure visibility, or test adequacy) and its five-word scale is one of the dialects the policy exists to collapse.
What it is still good for is review technique the policy does not cover: change sizing, describing a change, handling disagreement, dependency discipline.

## Reporting

Lead with the verdict in one line: ship, ship after fixes, or do not ship, and the count per severity.
Then findings in the axis order the policy gives, blockers first within each axis.
Group by file only when a file carries three or more findings.

When there is nothing to report, say so plainly and name what you checked.
A clean review that lists its axes is useful; a clean review that says "looks good" is indistinguishable from a review that did not happen.
