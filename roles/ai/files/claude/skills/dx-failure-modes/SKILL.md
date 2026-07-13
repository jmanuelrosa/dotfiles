---
name: dx-failure-modes
description: >-
  Failure-mode checklists for developer-experience and developer-productivity work, split by domain.
  Use when implementing or reviewing changes that touch build-graph orchestration and caching,
  generated code, shared lint and TypeScript config, monorepo workspace topology, dependencies and
  package exports, inner-loop test velocity, internal CLIs and scaffolding, or DX metrics.
  Read only the reference files whose triggers match the change.
---

# DX failure modes

Checklists of the ways developer-experience and inner-loop tooling changes go wrong, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Task-graph orchestration, affected or incremental builds, local or remote build caches, cache keys and hashing | [references/build-graph-and-caching.md](references/build-graph-and-caching.md) |
| Generated clients or types (OpenAPI/GraphQL/Prisma/protobuf), codegen config, checked-in generated files | [references/codegen-and-generated-artifacts.md](references/codegen-and-generated-artifacts.md) |
| Shared eslint/biome/prettier/tsconfig packages, TypeScript project references, incremental typecheck, editor config | [references/shared-config-and-typescript.md](references/shared-config-and-typescript.md) |
| Workspace layout, package boundaries, the internal package graph, internal versioning and release | [references/workspaces-and-monorepo-topology.md](references/workspaces-and-monorepo-topology.md) |
| Dependency versions and ranges, peer or phantom deps, dedupe, package `exports`/`types` fields, upgrade automation, lockfiles | [references/dependencies-and-package-exports.md](references/dependencies-and-package-exports.md) |
| Watch mode, test selection or sharding, local fixtures and seeds, anything about inner-loop feedback speed | [references/inner-loop-and-test-velocity.md](references/inner-loop-and-test-velocity.md) |
| Internal developer CLIs, code generators, project or package scaffolds, one-command setup entrypoints | [references/internal-clis-and-scaffolding.md](references/internal-clis-and-scaffolding.md) |
| Build/typecheck/test timing, cache hit rates, flake and queue signals, adoption or regression of the paved road | [references/dx-metrics-and-feedback.md](references/dx-metrics-and-feedback.md) |

Most real changes fire two or three rows (a typical build-tooling brief fires at least build-graph-and-caching, shared-config-and-typescript, and dependencies-and-package-exports).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks the inner loop or ships a wrong artifact, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: build-tool- and package-manager-specific guidance belongs to the stack skills the caller has installed, not here.
