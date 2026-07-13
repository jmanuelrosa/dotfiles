# Templates and reuse

When to read: the brief or diff touches shared workflows, composite actions, golden-path templates, or scaffolding.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Breaking an invisible consumer.** Shared workflows, composite actions, and templates are consumed by repos you cannot enumerate; a renamed input or output breaks them at their next run, not in your PR.
  Check: inputs and outputs evolve additively with defaults; removals go through deprecation; search for consumers where the platform allows, and assume more exist than you found.
- **Renaming a check consumers gate on.** A renamed job or check detaches every branch protection wired to the old name: merges block forever on a check that never reports, or proceed ungated where the gate counts only what reported.
  Check: check names are contracts; a rename is coordinated with the protection rules that reference it, which is an escalation, not a refactor.
- **Unversioned template evolution.** Consumers referencing a shared workflow by branch receive every change immediately, including the broken ones.
  Check: shared workflows and templates offer versioned refs; breaking changes land behind a new major ref while the old one keeps working.
- **Copy-paste divergence.** Fixing one copy of a pasted pipeline while its siblings rot forks the golden path into five muddy trails.
  Check: repeated logic is extracted into a reusable unit as part of the change, or the divergence is stated and justified in the report.
- **Golden path without an escape hatch.** A template that cannot be extended forces teams to eject entirely, and then nobody is on the paved road.
  Check: templates expose extension points (inputs, hooks, override files) for the variations that already exist among consumers.
- **Defaults that surprise.** A template default (permissions, triggers, environments) that is wrong for a consumer becomes that consumer's silent configuration, and an unsafe default multiplies into every repo scaffolded from it.
  Check: defaults are the safest choice, not the most convenient one; risky behavior is opt-in per consumer.
- **Contract mismatch at the call site.** A reusable unit invoked with mistyped inputs or missing required inputs and secrets fails opaquely at run time, not review time.
  Check: caller arguments match the callee's declared contract (names, types, required secrets), validated with the CI system's linter where one exists.
- **Scaffolding that rots.** A golden-path scaffold generating code that no longer matches current conventions mints new debt with every use.
  Check: scaffold output passes the lint and CI of a freshly generated project; the template is exercised as part of the change, not assumed.

## Escalation triggers (`needs-decision`)

- Breaking changes to shared workflows, templates, or contracts other repos consume (also an ask-first boundary in the agent).
- Deprecating or removing a template or shared workflow others build on (also an ask-first boundary in the agent).

## What good looks like

- One paved road: the shared unit is easier to use than copy-paste and safe to upgrade.
- Template changes are tested like code: a consumer exercised, or a scaffold generated and built.
- Every contract surface (inputs, outputs, check names, refs) is documented and versioned.
