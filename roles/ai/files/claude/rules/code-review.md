# Code review policy

The bar for reviewing a diff, and therefore the bar for writing one.
It applies to `/code-review`, to a review you run by hand, and to any agent asked to assess a change.

Producing an actual review report means invoking the `review-mechanics` skill first.
It carries the verification bar every finding must clear, the effort levels, the seat routing, the skip rules and the report format.
What stays here is the vocabulary and the boundaries, because those have to hold whether or not a skill was loaded.

## Severity: four words, no others

| Severity | Means | Effect |
|---|---|---|
| `blocker` | The change is wrong, unsafe, or unshippable as written | Do not merge |
| `important` | Real cost, but the change can ship if it is recorded | Fix now or file it |
| `nit` | Preference, polish, or a small local improvement | Optional, and capped |
| `pre-existing` | The diff exposed it, the diff did not cause it | Named once, never blocks |

Other artifacts speak their own dialects (Critical/Required/Nit, P0-P2, nitpick/warning).
Translate into these four before reporting, because a reader holding four vocabularies at once ranks nothing.

## The eight axes, in this order

The order is load-bearing.
When the output cap forces a cut, cut from the bottom: a correctness bug always outranks a convention breach.

1. **Correctness and data integrity** (`blocker`). Add what the diff cannot show on its own: the invariants this codebase relies on, and whether a real caller can reach the path.
2. **Contract and compatibility** (`blocker`). Ask the question the diff cannot answer alone: if this ships and must be rolled back an hour later, what breaks?
3. **Security and privacy** (`blocker`). Escalate, never fix quietly. Authentication mistaken for authorization is the one that keeps recurring: an id taken from a request without an ownership or tenant check.
4. **Failure visibility and operability** (`important`). The most under-reviewed axis here. Does a failure surface at all, and does it carry the request or tenant id needed to correlate it?
5. **Test adequacy** (`important`). Judge assertion strength, not coverage. A test asserting a call happened while the behaviour changed underneath it is worse than no test, because it reports green.
6. **Performance and resource cost** (`important`). Name a mechanism (N+1, unbounded fetch, missing index, re-render cascade) or it is a guess, and a guess sends someone optimising the wrong thing.
7. **Convention and repo fit** (`nit`, or `important` when it breaks a stated rule). The rules in `CLAUDE.md` are the standard, and a breach names the rule. Also: does this belong at this altitude, in this module, in this layer.
8. **Simplification and dead weight** (`nit`). Report it, never apply it.

## Boundaries that hold without the skill

**The reviewer does not mutate.**
A review reports.
It does not edit, stage, commit, delete, or run a fixer.
Read, Grep, Glob and read-only `git` are the tools.
Fixes are a separate turn the user asks for, so the diff under review stays the diff that was reviewed.

**Nits are capped at three, and zero when a blocker is present.**
An appendix of nits costs a reader the same as reporting them.

**Report nothing in** generated or vendored trees, lockfiles, snapshots asserting only shape, or `roles/ai/files/claude/skills/<upstream>` in the dotfiles repo, since `claude-kit update` discards a finding there on the next sync.

**A finding that cannot state a concrete failure scenario is an opinion.**
Drop it rather than dressing it as a risk.
Never claim a behaviour you have not read.
