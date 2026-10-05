# Caching and build speed

When to read: the brief or diff touches any CI cache, cache keys, job parallelism, or anything about pipeline speed.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Cache key missing its inputs.** A key that omits the lockfile or content hash it derives from restores stale dependencies; the build passes against yesterday's tree.
  Check: the key derives from the exact files that define the cached content, so a changed input changes the key; fallback keys are for restore speed only and never stand in for an exact match.
- **Cache crossing a trust boundary.** A cache writable from untrusted context (forked PRs) and restored in trusted context (default branch, releases) lets an attacker inject build inputs into your artifacts.
  Check: caches are partitioned by trust level; nothing written by untrusted runs is restored by privileged ones, including through fallback key prefixes.
- **Cache as accidental source of truth.** Cached build outputs keyed loosely become the artifact; a wrong hit ships a wrong build under a green check.
  Check: everything cached is re-derivable and keyed on every input that affects it, or it is not cached.
- **Expensive checks first.** A pipeline that runs the slow suite before the thirty-second lint charges the full pipeline price for every trivial mistake.
  Check: cheap, high-signal checks run first or in parallel; the expensive tail runs only when they pass.
- **Serialized independent jobs.** Jobs with no data dependency chained sequentially stretch the critical path for no correctness gain.
  Check: dependency edges reflect data flow only; independent jobs run in parallel.
- **Repeated work across jobs.** The same dependency install or build executed in every job multiplies cost and adds drift opportunities.
  Check: shared setup is cached with correct keys or produced once and passed as an artifact.
- **Unscoped new work.** A job, matrix leg, or schedule added without path or change scoping runs on every commit forever; the cost is invisible in review and permanent afterward.
  Check: new work states where it runs and why; matrix expansions and schedules are scoped to the changes they validate, without silently skipping anything the merge gate requires.
- **Speed claims without numbers.** "Faster" asserted from intuition routinely is not, and regressions hide behind the assertion.
  Check: record pipeline or job duration before and after across several runs (durations are noisy), and state the delta and what the speed-up might have traded away.

## Escalation triggers (`needs-decision`)

- A caching change on release or publish paths, where a stale or poisoned hit ships artifacts.
- Restructuring a shared workflow's job graph where consumer-visible contracts change: check names, inputs, outputs, or artifacts (also an ask-first boundary in the agent).
- Any staleness the brief accepts for speed: how stale is acceptable is a decision, not a default.

## What good looks like

- Correctness never depends on a cache hit: misses are slower, never different.
- The critical path is measured and shaped: cheap gates first, independent work parallel, the numbers in the report.
- Cache scope and trust boundaries are explicit enough to reason about in review.
- A cache earns its keep with a measured hit rate; caching added on faith is routinely a net loss.
