# Internal CLIs and scaffolding

When to read: the brief or diff touches internal developer CLIs, code generators, project or package scaffolds, or one-command setup entrypoints.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **A second way to do an existing thing.** A new script or generator that overlaps an existing one splits muscle memory and docs, and the two drift apart.
  Check: the tool extends or replaces the existing path, it does not sit beside it; there is one blessed way to do the task.
- **No discoverability.** A CLI with no help output, no listing of subcommands, and undocumented flags is found only by reading its source, so it goes unused or misused.
  Check: every command self-documents (help text, listed subcommands, examples); the entrypoint is one discoverable command that resolves for teammates through the workspace (its `bin` wired, its entry portable), not a folder of scripts to memorize on the author's machine.
- **Silent or unactionable failure.** An internal tool that exits zero on partial failure, or dies with a stack trace and no next step, erodes trust and hides breakage.
  Check: tools exit non-zero on any failure and print an actionable message (what failed, what to do); success and failure are unambiguous.
- **Non-idempotent scaffold.** A generator that fails or duplicates on re-run, or overwrites local edits without warning, trains people to avoid it.
  Check: scaffolds are safe to re-run: they converge, skip or clearly prompt on existing files, and never silently clobber.
- **Scaffold output starts non-conforming.** A scaffold that emits code failing the repo's own lint, typecheck, or test gates ships debt from the first line.
  Check: freshly scaffolded output passes lint, typecheck, and the gates unmodified.
- **Scaffold drifts from the real standard.** A template frozen at authoring time diverges from how packages are actually built now, so new code is born legacy.
  Check: the scaffold tracks the current standard, ideally derived from a real reference package, and a check flags when it drifts.
- **Interactive-only or automation-hostile.** A tool that assumes a terminal hangs in automation, while one with no prompts is unusable interactively.
  Check: tools detect non-interactive execution and accept a flag for every prompt; automation never hangs on a hidden question.
- **Destructive convenience unguarded.** A clean, reset, or regenerate command that removes paths built from unset variables or wide globs will one day delete the wrong thing.
  Check: destructive operations validate their targets, fail on unset variables, and confirm anything not explicitly scoped.
- **Agent-facing surface unscoped or unlabeled.** An internal tool exposed to coding agents (via MCP or similar) that grants broad filesystem or destructive access with no reversibility signal lets an agent do damage it cannot foresee.
  Check: a tool exposed to agents is scoped to the project, deterministic, and annotates destructive or irreversible operations, and its read-only and mutating paths are distinct so the caller knows reversibility before invoking.

## Escalation triggers (`needs-decision`)

- Introducing a new internal-CLI framework or a new scaffold or generator standard (also an ask-first boundary in the agent).
- A tool that mutates shared developer state (global config, shared caches) on other machines.

## What good looks like

- One discoverable entrypoint; every command self-documents and fails loudly with a next step.
- Scaffolds are idempotent and their output passes every gate on the first run.
- The template reflects today's standard, not the day it was written.
