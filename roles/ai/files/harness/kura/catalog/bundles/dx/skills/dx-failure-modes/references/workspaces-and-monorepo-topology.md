# Workspaces and monorepo topology

When to read: the brief or diff touches workspace layout, package boundaries, the internal package graph, or internal versioning and release.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Cyclic package dependency.** A cycle in the internal package graph breaks incremental builds, defeats affected detection, and leaves publish order undefined.
  Check: the internal dependency graph is acyclic; a new cross-package import that would close a cycle is refused, not worked around.
- **Reaching past the package boundary.** An import into another package's internal files, rather than its declared entry, couples to private structure and breaks on the next refactor.
  Check: cross-package imports go through the package's entry or `exports` only; deep internal paths are not importable.
- **Undeclared internal dependency.** A package that imports another without listing it as a dependency works until hoisting changes, then fails to resolve.
  Check: every internal import is a declared dependency of the importing package; nothing relies on hoisting to resolve.
- **Version mismatch across the workspace.** The same dependency pinned to different versions across packages ships two copies, breaks `instanceof` and singletons, and bloats output.
  Check: shared dependencies are single-versioned across the workspace, enforced by a catalog or a consistency check.
- **Internal versioning by hand.** Bumping internal package versions and changelogs manually drifts and misses transitive bumps, so a consumer ships against an unreleased change.
  Check: internal versioning and changelog are tool-driven; a change to a package others depend on records the bump that fans out to them.
- **Private package publishable.** An internal-only package with no publish guard can leak to a public registry on a mis-run release.
  Check: internal packages are marked private or scoped and access-controlled; only intentionally public packages can publish.
- **Workspace protocol leaked on publish.** A published package that still carries a `workspace:` specifier installs nothing for external consumers.
  Check: workspace-protocol specifiers are rewritten to real ranges at publish time; a published package resolves standalone.
- **Shared-package change without consumer migration.** Changing a shared package's public API and only deprecating the old shape strands every in-repo consumer, forfeiting the monorepo's atomic-change advantage.
  Check: a breaking change to a shared package updates every in-repo consumer in the same change (a codemod when the surface is wide); cross-repo consumers get a deprecation window, not a silent break.
- **New package off-template.** A hand-created package missing the standard scripts, config extension, or entry fields is invisible to the task graph and the shared config.
  Check: new packages come from the repo's scaffold, so they inherit scripts, config extension, and graph membership by construction.

## Escalation triggers (`needs-decision`)

- Changing the workspace layout, the package manager, or the internal versioning mechanism (also an ask-first boundary in the agent).
- Splitting or merging packages that others import, or making an internal package public.

## What good looks like

- The internal graph is acyclic and every cross-package edge is declared and routed through entries.
- One version of each shared dependency; internal bumps are tool-driven and fan out to dependents.
- A new package is scaffolded, not hand-assembled, so it joins the graph and the config automatically.
