# Code review policy

The bar for reviewing a diff, and therefore the bar for writing one.
It applies to `/code-review`, to a review you run by hand, and to any agent asked to assess a change.
It is not a coding style guide: the conventions live in `CLAUDE.md` and are cited here as one axis among eight.

## Severity: four words, no others

| Severity | Means | Effect |
|---|---|---|
| `blocker` | The change is wrong, unsafe, or unshippable as written | Do not merge |
| `important` | Real cost, but the change can ship if it is recorded | Fix now or file it |
| `nit` | Preference, polish, or a small local improvement | Optional, and capped |
| `pre-existing` | The diff exposed it, the diff did not cause it | Named once, never blocks |

Use these four everywhere, including when routing to a skill or agent that speaks its own dialect.
`code-review-and-quality` says Critical/Required/Nit/Optional-Consider/FYI, `cc-review` says P0-P2, and CodeRabbit says nitpick/warning.
Translate into the four above before reporting, because a reader holding four vocabularies at once ranks nothing.

`code-review-and-quality` is superseded as a reviewer, not as a skill.
Its five axes are a subset of the eight below (it covers none of contract and rollback, failure visibility, or test adequacy) and its five-word scale is one of the dialects this section exists to collapse, so when both are present the axes and severities here win.
What it is still good for is review technique the policy does not cover: change sizing, describing a change, handling disagreement, dependency discipline.

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

## The eight axes, in this order

The order is load-bearing.
When the output cap forces a cut, cut from the bottom: a correctness bug always outranks a convention breach.

**1. Correctness and data integrity** (`blocker`)
Wrong or inverted conditions, off-by-one, null dereference, missing `await`, dropped errors, removed guards, broken callers, races, lost writes.
This is the axis the built-in review already hunts hardest, so add only what it cannot infer: the invariants this codebase relies on and whether a real caller can reach the path.

**2. Contract and compatibility** (`blocker`)
Public API and schema backward compatibility, migration ordering against deploy, whether the change is reversible, feature flag or kill switch presence, and what happens to in-flight work during rollout.
Ask the question the diff cannot answer on its own: if this ships and must be rolled back an hour later, what breaks?
Seats: `database:database-failure-modes`, `backend:backend-failure-modes`, `platform:platform-failure-modes`.

**3. Security and privacy** (`blocker`)
Secrets or credentials in the diff, authentication mistaken for authorization (an ID taken from a request without an ownership or tenant check), injection, unvalidated external input, PII collection and retention, and dependency provenance.
Escalate, never fix quietly: a security finding goes to the user and to `/security-review`.
Seats: `security:security-failure-modes`, plus `frontend`, `mobile`, `desktop` for their own security references.

**4. Failure visibility and operability** (`important`)
Does a failure surface at all, and does it carry the identity needed to correlate it?
Swallowed exceptions, bare catches, logs with no request or tenant id, retries with no ceiling, an error path that returns success.
This is the most under-reviewed axis here, which is why eleven of the fifteen seats carry a `failure-visibility` reference.
Seats: any installed seat's `failure-visibility` reference, `sre:sre-failure-modes` for alerting and tracing.

**5. Test adequacy** (`important`)
Whether the new failure mode is reachable by a test, and whether the assertions would actually fail if the code regressed.
Judge assertion strength, not coverage percentage: a test asserting a call happened while the behaviour changed underneath it is worse than no test, because it reports green.
Seats: `qa:qa-failure-modes`.

**6. Performance and resource cost** (`important`)
A performance finding names a mechanism: N+1, unbounded fetch or loop, missing index, synchronous work on a hot path, a re-render cascade, an unpaginated list, a leak.
Without a mechanism it is a guess, and a guess here sends someone optimising the wrong thing.
Do not optimise during a review. `/performance-optimization` measures first and mutates, so it is a separate pass.

**7. Convention and repo fit** (`nit`, or `important` when it breaks a stated rule)
The rules in `CLAUDE.md` are the standard, and a breach of one is a finding that names the rule.
The ones that actually appear in diffs: TODOs, placeholders and stubs; comments that explain WHAT instead of a non-obvious WHY, same bar for JSDoc; ticket or ADR numbers in comments; hardcoded magic numbers, URLs, tokens and paths; a line width that ignores `.editorconfig` or the formatter config; a package manager that does not match the lockfile; an edited accepted ADR instead of a superseding one.
Also repo fit: does this belong at this altitude, in this module, in this layer.

**8. Simplification and dead weight** (`nit`)
Duplication, over-abstraction, a wrapper that adds nothing, a flag parameter that should be two functions, dead code.
Report it, never apply it. `/simplify`, `code-simplification` and `knip --fix` all mutate and belong to a separate, explicitly requested pass.

## Seat routing

A seat's `<seat>:<seat>-failure-modes` skill is the deep checklist for its axes, and its own trigger table picks which references to open.
Invoke the skill rather than naming reference files, so retitling a reference upstream does not strand this policy.

Seats are plugins, so they load only when the plugin is installed in this project, the workspace is trusted, and the session has been restarted.
Check, then route. If the seat is absent, review the axis from this policy and say in the summary that the deep checklist was unavailable.
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

## The reviewer does not mutate

A review reports. It does not edit, stage, commit, delete, or run a fixer.
Read, Grep, Glob, and read-only `git` are the tools.
Fixes are a separate turn the user asks for, so the diff under review stays the diff that was reviewed.

Out of scope during a review, all of them because they write: `/code-review --fix`, `code-simplification`, `/simplify`, `knip --fix`, `coderabbit`, `pr`, `performance-optimization` steps 3 onward, `cc-review`'s apply step.
`--fix` is named first because it is the one the harness itself ships, so a ban that skipped it would read as forbidding only other people's tools.
`cc-staff-reviewer` reviews the Claude Code setup and never application code, so no code finding routes there.

## Reporting

Lead with the verdict in one line: ship, ship after fixes, or do not ship, and the count per severity.
Then findings in the axis order above, blockers first within each axis.
Group by file only when a file carries three or more findings.

When there is nothing to report, say so plainly and name what you checked.
A clean review that lists its axes is useful; a clean review that says "looks good" is indistinguishable from a review that did not happen.

## Effort

Effort changes the bar, not the axes: at `low` and `medium` report only what you are most confident in, and from `high` up cast a wider net and let the verification bar do the filtering.

`/code-review` takes the level as its first argument, and this table is the authority on which one.
Every other artifact here that tells you to run a review names a level consistent with it.

| Situation | Effort |
|---|---|
| A hook, a config tweak, or a one-file fix you already understand | `low` |
| An ordinary single-concern diff before `/commit` | `medium` |
| One seat's completed slice, or any diff against a stack you do not know | `high` |
| A multi-seat or multi-worktree integration, or a release | `max` |
| A deep pass you do not want to spend local tokens on | `ultra` |

`xhigh` sits between `high` and `max` and needs a reason to pick over either.
`ultra` is not a step up from `max`: it runs in the cloud, is billed separately from the session, and needs claude.ai account access, so it is a deliberate choice rather than the top of the ladder.
