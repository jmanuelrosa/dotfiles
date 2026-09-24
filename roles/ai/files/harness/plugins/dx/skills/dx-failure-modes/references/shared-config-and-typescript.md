# Shared config and TypeScript

When to read: the brief or diff touches shared eslint/biome/prettier/tsconfig packages, TypeScript project references, incremental typecheck, or editor config.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Config copied, not shared.** Per-package copies of eslint/tsconfig/prettier drift, so the same code lints differently in two packages and a rule fix lands in one place only.
  Check: shared config lives in one internal package the others extend; per-package files only override, never restate.
- **Project references incomplete.** A composite TypeScript build missing a reference edge type-checks against a sibling's stale declarations, so a break in one package is invisible in another until a clean build.
  Check: every cross-package import has a matching project reference, every referenced project is itself composite, and cross-package resolution uses real workspace links rather than path aliases pointing at a sibling's source while the runtime resolves its build output; no reference edge closes a cycle (the project build fails on a circular reference graph); a clean project build surfaces the same errors the editor does.
- **Plain typecheck in a referenced project.** Running the type-checker without its build/graph mode ignores project references and either rebuilds everything or checks stale outputs.
  Check: typecheck runs in the mode that respects references (incremental build), so the graph is honored and results are current.
- **Incremental build info stale.** Build-info keyed on the wrong inputs, or committed to the repo, serves stale results so typecheck passes over code it never re-checked.
  Check: build-info is local, ignored by git, and keyed on the real input set, and no two projects share a build-info file or overlap an output directory; a clean typecheck and an incremental one agree.
- **Editor and CI disagree.** A different type-checker, linter, or formatter version (or config resolution) between the editor and CI produces pass-locally-fail-in-CI.
  Check: editor, hooks, and CI resolve the same config from the same pinned tool versions; formatting is idempotent across them.
- **Formatter fighting the linter.** A formatter and a lint rule that disagree on the same concern loop on autofix and churn diffs.
  Check: formatting and lint concerns are partitioned (formatter owns layout, linter owns correctness); no rule re-formats what the formatter owns.
- **Autofix that changes behavior.** A lint autofix or codemod applied in bulk can silently change semantics under the guise of a no-op refactor.
  Check: behavior-changing fixes are reviewed as code, not bulk-applied; only provably safe fixes run unattended.
- **A second config system.** Adding a new linter or formatter beside the existing one splits the ruleset and doubles maintenance.
  Check: extend the config toolchain the repo already has; a replacement is a migration, not an addition.

## Escalation triggers (`needs-decision`)

- Adding or replacing a linter, formatter, or type-checker, or a repo-wide rule change that reformats or re-lints the whole tree (also an ask-first boundary in the agent).
- Raising the shared TypeScript or lint baseline in a way that newly fails existing packages.

## What good looks like

- One shared config package; per-package files are thin overrides.
- A clean project build and the editor report the same type errors; incremental never lies.
- Editor, hooks, and CI enforce an identical ruleset at identical versions.
