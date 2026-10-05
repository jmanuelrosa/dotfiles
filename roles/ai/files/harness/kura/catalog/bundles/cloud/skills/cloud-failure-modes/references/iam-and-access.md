# IAM and access

When to read: the brief or diff touches IAM policies, roles, trust relationships, permission boundaries, service accounts, or federation.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Wildcard scope "temporarily".** A `*` action or resource grows silently as the provider adds new actions, and temporary wildcards are never narrowed once things work.
  Check: actions and resources are explicit lists scoped to what the workload does today; any wildcard that remains carries a written justification in the report.
- **Trust policy anyone can assume.** A wildcard principal lets anything that learns the role identifier assume it (role ARNs are not secrets), and trusting an entire account root delegates the decision to every principal that account's admins ever authorize.
  Check: trust policies name exact principals; a wildcard principal exists only when paired with a condition that bounds it (organization, source account, source resource).
- **Third-party trust without an external ID.** A vendor-facing role missing its external-id condition is the confused deputy: another customer of the same vendor can point the vendor's systems at your role.
  Check: cross-account roles for third parties require the vendor-supplied external id in the trust condition; service principals carry source-account or source-resource conditions.
- **Static keys where federation fits.** A long-lived access key for automation is a standing compromise in waiting, and CI runners are where keys leak.
  Check: automation authenticates through OIDC federation or workload identity, scoped by repository, branch, or environment claims; a new static credential is an escalation, not a default.
- **Policy attached to a user.** Permissions granted directly to users scatter access outside group and role governance and survive team changes invisibly.
  Check: permissions attach to roles or groups; a direct user attachment is a finding.
- **Privilege that mints privilege.** A role that can create or attach policies, or pass a more privileged role to a service, is an administrator with extra steps; escalation paths hide in innocuous-looking grants.
  Check: policy-management and role-passing permissions are scoped to named resources and paths; a grant that can broaden itself is treated as admin and escalated.
- **Guessed-broad instead of derived-minimal.** When the minimal policy is unknown, the pressure move is granting broad and promising to narrow later.
  Check: derive needed actions from what the workload actually calls (access analysis tooling, the provider's action reference for the exact operations); if genuinely unknowable now, grant narrow, expect denials, and say so in the report.
- **Permission boundary or org policy ignored.** In organizations using boundaries or org-level ceilings, a role authored outside them either fails at runtime or silently exceeds the intended maximum.
  Check: new roles follow the boundary idiom visible in existing roles; policies are authored inside the ceiling the organization enforces.

## Escalation triggers (`needs-decision`)

- Broadening IAM: a new admin-level policy, a wildcard, a widened trust relationship (also an ask-first boundary in the agent).
- Cross-account access grants (also an ask-first boundary in the agent).
- A brief that requires a long-lived static credential; recommend the federated alternative in the escalation.

## What good looks like

- Every policy names exact actions on exact resources, and a reviewer can say which workload needs each one.
- Trust policies read as sentences: who, from where, under which condition.
- Humans and automation both hold short-lived credentials; a static key is the documented exception.
