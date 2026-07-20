---
name: cloud-failure-modes
description: >-
  Failure-mode checklists for cloud infrastructure and IaC implementation work, split by domain.
  Use when implementing or reviewing changes that touch module and environment structure,
  state and resource lifecycle, plan safety and drift, IAM and trust relationships,
  networking and exposure, secrets and data protection, cost and tagging,
  or resilience and provisioning.
  Read only the reference files whose triggers match the change.
---

# Cloud failure modes

Checklists of the ways cloud infrastructure and IaC changes go wrong in production, one reference file per domain.
This skill is a router: match the change against the trigger table, read only the files that fire, and treat every checklist item in them as a gate.
An unresolved item blocks `done`; when the brief itself forces the failure mode, escalate with `needs-decision` instead of shipping it.

## Trigger table

| The brief or diff touches... | Read |
|---|---|
| Module interfaces, variables and outputs, module sources, environment layout, root-module structure | [references/iac-structure-and-modules.md](references/iac-structure-and-modules.md) |
| State backends, resource renames or moves, imports, lifecycle guards, anything touching state | [references/state-and-lifecycle.md](references/state-and-lifecycle.md) |
| Any change about to be planned; plan output, drift, hardcoded IDs, version pins | [references/plan-safety-and-drift.md](references/plan-safety-and-drift.md) |
| IAM policies, roles, trust relationships, permission boundaries, service accounts, federation | [references/iam-and-access.md](references/iam-and-access.md) |
| Security groups, firewalls, load balancers, CIDR ranges, subnets, peering, DNS | [references/networking-and-exposure.md](references/networking-and-exposure.md) |
| Secrets, KMS keys, encryption settings, buckets, snapshots, anything holding data | [references/secrets-and-data-protection.md](references/secrets-and-data-protection.md) |
| Any new resource; tags, budgets, instance sizes, anything with a monthly bill | [references/cost-and-tagging.md](references/cost-and-tagging.md) |
| Clusters, databases, managed services, availability zones, backups, quotas, new accounts | [references/resilience-and-provisioning.md](references/resilience-and-provisioning.md) |
| Health checks, alarms, log sinks, apply-failure legibility, monitoring of provisioned resources | [references/failure-visibility.md](references/failure-visibility.md) |

Most real changes fire two or three rows (a typical provisioning brief fires at least plan-safety-and-drift, iam-and-access, and cost-and-tagging).
Read all of them; skip the rest.

## How each reference is structured

- **Failure modes to rule out**: concrete ways the change breaks in production, each with a `Check:` you can actually perform against the diff.
- **Escalation triggers**: conditions that are decisions, not implementation details; report `needs-decision` with a recommendation.
- **What good looks like**: the positive pattern, for calibration.

The checks are stack-agnostic on purpose: IaC-tool- and cloud-provider-specific guidance belongs to the stack skills the caller has installed, not here.
