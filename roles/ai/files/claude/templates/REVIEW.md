# Review instructions

Copy this to a repository root as `REVIEW.md` to steer Anthropic's hosted GitHub Code Review.
Trim it to the repo: it is pasted verbatim into every agent in the review pipeline, `@` imports are not expanded, and length dilutes the rules that matter most.
Delete this paragraph and fill the two bracketed sections before committing.

## Severity

`blocker` is a correctness, contract, or security defect: wrong or inverted logic, a dropped error, a missing ownership check, an irreversible migration, a secret in the diff, or a breaking change to a published contract.
Everything else is `nit`.
An issue the diff exposed but did not cause is `pre-existing`: name it once and do not block on it.

## Cap the nits

At most three nits per review, and none when a blocker is present.
Style, formatting, and naming preferences are not findings here; the formatter and the linter own them.

## Verification bar

Every finding needs a `file:line` in the source, read and confirmed, plus a concrete failure scenario: the inputs or state, then the wrong output or cost.
Do not infer behaviour from a name, a path, or a convention.
When a diff changes a function, open its callers before asserting an effect.
A finding with no failure scenario is an opinion. Drop it.

## Always check

Ranked. When the output cap forces a cut, cut from the bottom.

1. Correctness: inverted conditions, off-by-one, null dereference, missing `await`, dropped errors, removed guards, broken callers, races.
2. Contract and rollback: schema and API backward compatibility, migration ordering against deploy, whether the change can be reverted an hour after shipping.
3. Security: secrets in the diff, an ID taken from a request without an ownership or tenant check, injection, unvalidated external input, PII retention.
4. Failure visibility: swallowed exceptions, logs with no request or tenant id, retries with no ceiling, an error path returning success.
5. Test adequacy: whether the assertions would fail if the code regressed, not whether tests exist.
6. Performance: only with a named mechanism (N+1, unbounded fetch, missing index, unpaginated list, re-render cascade).

[Add the repo-specific checks here: the invariants this codebase relies on, the modules where a change is high-risk, the contracts other services consume.]

## Do not report

Generated and vendored trees, lockfiles, snapshot fixtures.
Anything the linter, formatter, or typechecker already fails on.
Missing tests for pure refactors with no behaviour change.

[Add paths and branch patterns to stay out of, if any.]

## Re-review

On a push that addresses earlier findings, confirm what is resolved and report only what is new or still open.
Do not restate a finding the author already fixed.

## Summary shape

One line of verdict (ship, ship after fixes, do not ship) and a count per severity, then findings grouped by the ranked axes above.
When there is nothing to report, say so and name the axes checked.
