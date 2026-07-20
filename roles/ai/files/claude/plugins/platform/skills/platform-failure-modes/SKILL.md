---
name: platform-failure-modes
description: >-
  Failure-mode checklists for platform and CI/CD implementation work, split by domain.
  Use when implementing or reviewing changes that touch CI pipelines, workflow security and secrets,
  build caching and speed, Dockerfiles and compose, Kubernetes manifests and Helm charts,
  artifacts and releases, scripts and hooks and local dev tooling, or shared templates.
  Read only the reference files whose triggers match the change.
---

# Platform failure modes

Checklists of the ways platform and CI/CD changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Workflow triggers, job graphs, conditions, path filters, concurrency, required checks | [references/ci-pipelines.md](references/ci-pipelines.md) |
| Workflow input from PRs, issues, or forks; token permissions, third-party step refs, secret handling | [references/ci-security-and-secrets.md](references/ci-security-and-secrets.md) |
| Any CI cache, cache keys, job parallelism, anything about pipeline speed | [references/caching-and-build-speed.md](references/caching-and-build-speed.md) |
| Dockerfiles, base images, compose files, `.dockerignore`, dev containers | [references/containers.md](references/containers.md) |
| Kubernetes manifests, Helm charts, kustomize overlays, values files | [references/kubernetes-and-helm.md](references/kubernetes-and-helm.md) |
| Build artifacts, package publishing, releases, version tags, provenance | [references/artifacts-and-releases.md](references/artifacts-and-releases.md) |
| Shell scripts, pre-commit hooks, task runners, developer setup, local-CI parity | [references/scripts-hooks-and-local-dev.md](references/scripts-hooks-and-local-dev.md) |
| Shared workflows, composite actions, golden-path templates, scaffolding | [references/templates-and-reuse.md](references/templates-and-reuse.md) |
| Silent job skips, unreadable pipeline failures, workload probes, deploy-failure visibility | [references/failure-visibility.md](references/failure-visibility.md) |

Most real changes fire two or three rows (a typical pipeline brief fires at least ci-pipelines, ci-security-and-secrets, and caching-and-build-speed).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: CI-system- and tool-specific guidance belongs to the stack skills the caller has installed, not here.
