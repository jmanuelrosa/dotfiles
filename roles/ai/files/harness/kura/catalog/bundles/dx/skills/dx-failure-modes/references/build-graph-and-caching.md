# Build graph and caching

When to read: the brief or diff touches task-graph orchestration, affected or incremental builds, local or remote build caches, or cache keys and hashing.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Cache key missing an input.** A task cached on a key that omits something it actually reads (an env var, a sibling package's output, a config file, the tool version) replays a stale artifact, and the wrong build ships under a green cache hit.
  Check: every input the task reads is in its cache-key set (source globs, upstream outputs, relevant env vars, tool and runtime versions); nothing it consumes is left implicit, and narrowing a task's own input list preserves the shared defaults rather than dropping them, since some tools replace the default set unless it is re-included.
- **Cache-key membership by secrecy, not effect.** Deciding what belongs in the hash by whether a value is secret, rather than whether it changes the output, gets both wrong: a rotating token in the key thrashes the cache on every rotation, and an output-affecting value left out serves a false hit.
  Check: a value is hashed into the cache key if and only if it changes the task's output; secrets that do not change output are passed through unhashed, output-affecting env or config is always hashed.
- **Undeclared task dependency.** A task that reads another package's output without a declared graph edge sometimes runs before that output exists, so it is flaky under parallelism, not reliably broken.
  Check: the graph declares every producer-to-consumer edge; a clean run at max parallelism still succeeds.
- **Side effect escaping the output set.** Files a task writes outside its declared outputs are dropped on a cache hit, so a cached run leaves the workspace different from a fresh run.
  Check: every file a task produces is in its declared outputs; a cache hit reproduces the full effect of a cache miss.
- **Non-deterministic output.** Timestamps, absolute paths, map ordering, or embedded machine identity in an output make its hash unstable, so the cache never hits and downstream keys churn.
  Check: outputs are byte-identical across two clean runs on different machines; nondeterministic inputs are normalized or excluded.
- **Affected detection off a wrong base.** Affected or incremental selection computed against the wrong merge base, or a shallow clone missing history, silently skips tasks for changed packages.
  Check: affected is computed against the real merge base with the history it needs; a change to a leaf package selects that package and everything downstream.
- **Remote cache crossing a trust boundary.** A remote cache writable from untrusted contexts (forks, unreviewed branches) lets a poisoned artifact serve a trusted build.
  Check: writes to the shared cache come only from trusted contexts; untrusted runs are read-only or use a separate scope.
- **Global state defeats hermeticity.** Tasks depending on ambient state (a globally installed tool, a mutable home-dir cache, a running service) behave differently in a fresh checkout than on the author's machine.
  Check: task inputs are hermetic, declared, versioned, and derived from the repo, not the host.
- **Cache hit hides a real failure.** Caching a task that can pass while doing nothing (a test task that exits 0 over skipped work) stores the green result and replays it forever.
  Check: only tasks whose success is total and reproducible are cached; a task that can silently skip work is not cached over that skip.

## Escalation triggers (`needs-decision`)

- Introducing a new build orchestrator or a remote-cache backend where none exists (also an ask-first boundary in the agent).
- Changing a cache-key scheme or task-graph contract that other packages or CI already depend on.

## What good looks like

- Two clean runs on two machines produce identical hashes and the second is a full cache hit.
- The task graph is explicit end to end; a clean run at max parallelism succeeds every time.
- Affected selection is trustworthy enough that "not affected" is safe to skip.
