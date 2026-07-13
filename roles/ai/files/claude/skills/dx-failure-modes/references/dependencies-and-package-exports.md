# Dependencies and package exports

When to read: the brief or diff touches dependency versions and ranges, peer or phantom deps, dedupe, package `exports`/`types` fields, upgrade automation, or lockfiles.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Phantom dependency.** Code that imports a package it does not declare, resolving only through hoisting, breaks when the tree flattens differently.
  Check: every import maps to a declared dependency of that package; nothing resolves by hoisting alone, and a hoisting config change (a broad hoist pattern, a hoisted linker) does not silently re-enable phantom resolution the isolated layout was preventing.
- **Peer dependency unsatisfied or duplicated.** A missing or multi-versioned peer (a UI framework, a test runner) yields two instances and subtle runtime breakage.
  Check: peers are declared with honest ranges and resolve to a single instance across the workspace.
- **Range too loose or too tight.** A wildcard range pulls a breaking major on a clean install; an over-pinned range blocks security patches and fragments the tree.
  Check: ranges express real compatibility, consistent across the workspace; neither wildcard nor needlessly exact.
- **Exports map incorrect.** A package whose `exports` omits a subpath, or points `types`/`import`/`require` at the wrong file, fails for external consumers even though it works in-repo.
  Check: the `exports` map is validated against the packed tarball (what actually publishes), not the source tree, and types resolve under the consumer's module setting; in-repo success is not proof it resolves when installed.
- **Types-runtime skew.** Shipped types that do not match the shipped runtime (wrong condition, ESM-versus-CJS mismatch) type-check green and crash at import.
  Check: the package resolves and type-checks from a consumer in every module system it claims to support.
- **Upgrade automation unbatched or unpinned.** Automation that opens one PR per package, or auto-merges majors, either buries the signal or ships breakage unattended.
  Check: upgrade automation groups related deps, separates majors for review, and resolves to a pinned range; nothing majors without review.
- **Lockfile out of sync or hand-edited.** A lockfile edited by hand, or not regenerated with its manifest, installs a different tree than declared, so CI and local diverge.
  Check: the lockfile is tool-regenerated and committed, and a frozen or immutable install succeeds from clean.
- **Supply-chain surface ignored.** A new dependency with an install script, or a typosquatted name, runs arbitrary code at install with no review.
  Check: a new dependency is reviewed for necessity, name, and install scripts; adding one is a deliberate decision, not a reflex.

## Escalation triggers (`needs-decision`)

- Adding, removing, or major-upgrading a dependency beyond the brief, or changing a package's public `exports` (also an ask-first boundary in the agent).
- Changing the dependency-upgrade automation policy or the workspace version-resolution strategy.

## What good looks like

- Every import is declared; one version of each shared dep; a frozen install from clean matches the lockfile.
- `exports` and `types` validate for external consumers in every module system the package claims.
- Upgrades arrive grouped, majors reviewed, nothing auto-majors.
