# State and lifecycle

When to read: the brief or diff touches state backends, resource renames or moves, imports, lifecycle guards, or anything touching state.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Local or unlocked state.** State on a workstation or in a backend without locking lets two runs corrupt it, and state holds resource attributes and secrets in plaintext.
  Check: the backend is remote, encrypted at rest, access-controlled, and locking; local state anywhere beyond a disposable sandbox is a finding to report.
- **One state spanning unrelated components.** Network, IAM, data, and app resources in one state give a typo in any of them the whole file as blast radius, and one lock serializes every change.
  Check: state splits per environment and then per layer; a new resource lands in the state whose blast radius matches it.
- **Workspaces standing in for environments.** Workspaces share a backend, credentials, and blast radius; they isolate state names, not failure domains, and one compromised credential reaches every environment.
  Check: environment isolation follows the project's shape; where isolation is the goal, separate roots, backends, or accounts do the isolating, and workspaces stay a convenience layer.
- **Rename that plans as destroy and create.** The tool reads a changed resource address as delete-and-recreate; a "harmless" rename or refactor destroys the live resource and its data.
  Check: every address change carries a moved block or the tool's equivalent; the plan for a pure refactor shows zero destroys.
- **Hand-edited state.** State is a private API: hand edits and imperative removals break on tool upgrades and leave no reviewable trace.
  Check: state changes are expressed in code (moved, import, removed blocks) so they are planned and reviewed; imperative state commands are proposed for a human, never run.
- **Index-based identity.** Resources created with `count` over a list take their identity from position; removing one element renames or recreates every later resource, including ones the brief never mentioned.
  Check: collections where identity matters iterate a stable map key (`for_each`); positional counting is reserved for genuinely fungible copies.
- **Stateful resource without a guard.** A database, bucket, or volume with no destroy guard can be dropped by a stray refactor or an unread plan.
  Check: stateful resources carry a lifecycle guard (`prevent_destroy`) and provider-level deletion protection; every exception is stated.
- **Create-before-destroy where old and new cannot coexist.** Reversing replace order for zero downtime deadlocks on uniquely named resources and doubles cost on stateful ones during the overlap.
  Check: create-before-destroy pairs with generated or prefixed names, and the resource tolerates two instances existing at once.
- **Import that guesses.** Importing a live resource with config written from memory produces an immediate diff the next plan wants to "fix", possibly destructively.
  Check: imported config reproduces the live resource attribute for attribute; the first plan after an import is a no-op.

## Escalation triggers (`needs-decision`)

- Any state migration or restructuring: moves between states, imports, removals (also an ask-first boundary in the agent); propose the exact commands or code blocks for a human.
- Removing a lifecycle guard or deletion protection from a stateful resource (also an ask-first boundary in the agent).
- Any operation irreversible for the data a resource holds, however it is wrapped.

## What good looks like

- State is remote, locked, encrypted, and split so a mistake reaches one layer of one environment.
- Refactors plan as pure moves: zero destroys, zero surprises.
- The first plan after an import or migration shows no changes.
