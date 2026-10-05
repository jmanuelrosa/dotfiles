# CI security and secrets

When to read: the brief or diff touches workflow input from PRs, issues, or forks; token permissions; third-party step refs; or secret handling.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Untrusted input in a shell.** A template expression expanding PR titles, branch names, issue bodies, or commit messages inside a run block executes attacker-chosen shell (script injection).
  Check: untrusted event fields reach scripts only through environment variables, quoted at the point of use; no expression expands directly inside shell text, and untrusted values never feed the runner's cross-step environment or path propagation files.
- **Privileged trigger running PR code.** A trigger that runs with secrets and a write token while checking out or executing PR head code hands your secrets to any external contributor.
  Check: privileged workflows never check out or execute untrusted code; if they must read it, they treat it as data, or the work splits into an unprivileged build plus a privileged step that runs none of it.
- **Default token permissions.** The ambient CI token often defaults to write, and every step, including third-party ones, inherits it.
  Check: permissions are declared explicitly at the narrowest scope, read-only by default, elevated per job only where used.
- **Mutable third-party refs.** A step referenced by tag or branch re-resolves later; a compromised or moved tag runs someone else's code with your secrets.
  Check: third-party steps are pinned to an immutable ref (commit SHA or digest) with a human-readable version comment, and the ref verifiably belongs to the named upstream (a fork's commit or a typosquatted name passes a naive pin); upgrades are deliberate diffs.
- **Secrets in logs and artifacts.** Secrets echoed by debug output, dumped environments, or verbose tools escape masking, and values derived from a secret are not masked at all.
  Check: nothing prints the environment wholesale; artifact contents are explicit allowlists; masking is never the only line of defense.
- **Secrets handed to jobs that do not need them.** Passing whole secret sets to jobs or reusable workflows that use one value widens every compromise to all of them.
  Check: each job receives exactly the secrets it uses, by name; deploy-grade secrets are bound to the platform's environment scoping where it exists.
- **Privilege gated on a spoofable identity.** A condition granting privileged behavior because of who appears to have triggered the event trusts a display name an attacker can imitate.
  Check: privilege decisions key on authenticated event properties, not actor or bot display names; bot allowances verify the event type, not just the name.
- **Credentials persisted into the workspace.** Checkout credentials or build-time tokens left in the work tree get captured by whole-workspace artifact uploads and later steps.
  Check: checkout does not persist credentials it does not need; uploaded paths are enumerated, never the whole workspace.
- **Untrusted code on self-hosted runners.** A forked PR executing on a self-hosted runner runs arbitrary code inside your network with the runner's reach.
  Check: untrusted events run only on ephemeral, isolated runners; anything else is an escalation, not a default.
- **Standing credentials for automation.** A bot or coding agent wired into CI with a long-lived token and broad write access is a permanent compromise in waiting, and it acts faster than a human can notice.
  Check: automation identities get short-lived, narrowly scoped credentials (workload identity over static tokens), and merges or writes stay behind human approval unless the brief explicitly grants otherwise.

## Escalation triggers (`needs-decision`)

- Adding a new third-party action, orb, plugin, or base image (also an ask-first boundary in the agent).
- A change that needs a new secret (also an ask-first boundary in the agent).
- Any workflow that must combine secret access with processing of untrusted input.

## What good looks like

- Every workflow declares least-privilege permissions; a reader can tell at a glance which jobs can write.
- Third-party code in CI is pinned, reviewed, and minimal; secrets flow to exactly the steps that need them.
- The pipeline treats every PR-controlled field as attacker-supplied data, because it is.
