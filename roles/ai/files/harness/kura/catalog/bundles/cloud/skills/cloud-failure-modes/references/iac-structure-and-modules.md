# IaC structure and modules

When to read: the brief or diff touches module interfaces, variables and outputs, module sources, environment layout, or root-module structure.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Module interface changed in place.** A module's variables and outputs are consumed by root modules and repos you cannot enumerate; renaming or removing one breaks them at their next plan, not in your diff.
  Check: inputs and outputs evolve additively with defaults; removals go through deprecation and a version bump, never an in-place edit.
- **Output that passes an input straight through.** An output wired to a variable instead of a resource attribute severs the dependency graph; consumers read the value before the resource exists.
  Check: outputs reference resource attributes so the graph orders creation; any passthrough is deliberate and stated.
- **Variable added "for flexibility".** Every exposed variable is a contract the module must keep; a knob nobody asked for can never be removed without a breaking change.
  Check: each new variable has a caller that needs it today; everything else stays a local.
- **Unpinned module source.** A registry module without an exact version, or a git source on a branch or mutable tag, re-resolves to unreviewed code; module refs carry no lockfile checksum the way providers do.
  Check: registry modules pin an exact version; git sources pin a commit SHA; sources come only from namespaces the project already trusts.
- **Registry namespace confusable.** A module source one character off the intended namespace, or a fork of it, passes review and installs someone else's code; module ecosystems have demonstrated hijackable names.
  Check: the source path verifiably belongs to the intended organization or registry namespace; a new namespace is a supply-chain escalation, not a convenience.
- **Provider configured inside a shared module.** A reusable module that configures its own provider or hardcodes a region cannot be instantiated twice or reused across accounts, and it fights the caller's provider aliases.
  Check: shared modules declare required providers but never configure them; region and account context flow in from the root.
- **Environment forked by copy-paste.** A module copied and hand-edited per environment turns one fix into N fixes and lets environments drift apart invisibly.
  Check: every environment consumes the same versioned module; differences ride through variable files or per-environment maps, never edited copies.
- **Variable files that diverge structurally.** Per-environment variable files with different shapes let a key renamed in one environment silently keep a stale default in another.
  Check: environment files share one structure and differ only in values; a new or renamed key lands in every environment or is defaulted deliberately.
- **Monolith or confetti.** One root module deploying everything gives every change the whole system as blast radius; dozens of tiny stacks wired by remote-state reads make every change a distributed refactor.
  Check: layers split by change frequency and blast radius (network, IAM, data, compute); cross-stack reads go through published outputs and stay few.
- **Cross-stack dependency the tool cannot see.** Stacks that consume each other's resources without a declared output edge, or that form a cycle, apply in whatever order the runner picks: green today, deadlock tomorrow.
  Check: every consumer reads a declared output of its producer; the stack graph is acyclic, with an ordering a newcomer could state.

## Escalation triggers (`needs-decision`)

- Breaking changes to module inputs, outputs, or remote-state outputs other stacks consume (also an ask-first boundary in the agent).
- Adding a module from a registry or source the project does not already use (also an ask-first boundary in the agent).
- Re-layering root modules or splitting state: it moves resource addresses, so it rides on the state-and-lifecycle reference and its migration boundary.

## What good looks like

- Modules version like libraries: consumers upgrade deliberately, and nothing breaks them silently.
- Environments differ in data, not code: one module, one variable shape, values per environment.
- The dependency graph is explicit end to end; nothing relies on apply-order luck.
