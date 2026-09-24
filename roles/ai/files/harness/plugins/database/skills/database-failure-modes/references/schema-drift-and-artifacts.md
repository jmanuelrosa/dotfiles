# Schema drift and artifacts

When to read: the brief or diff touches ORM schema files, generated clients or types, migration state, or shows disagreement between schema sources.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Schema file and migration chain disagree.** The declarative schema says one thing, the migrations produce another; the next generated migration then "fixes" the drift with DDL nobody intended.
  Check: run the tool's own drift check (`prisma migrate diff`, `alembic check`, or equivalent); the generated migration contains all of, and only, the intended change.
- **Auto-sync reconciling by destruction.** Push or auto-sync modes reconcile a renamed field as drop-plus-add, destroying the column's data.
  Check: schema changes flow through generated migrations reviewed as SQL; auto-sync runs only against disposable local databases, and the generated SQL is read for drops the DSL hides.
- **Stale generated artifacts.** A client or type bundle not regenerated after a schema change compiles against yesterday's shape.
  Check: every generated artifact is regenerated with the project's own command and committed together with the schema change; none is hand-edited.
- **Multiple migration heads.** Parallel branches each add a migration; the graph now has two heads, or an ordering that different environments resolve differently.
  Check: the migration graph has a single head after the change, merged with the tool's own mechanism, and the resulting order is explicit rather than timestamp luck.
- **Checksum or history mutation.** Editing an applied migration breaks the tool's checksum record in every environment that ran it; repair commands hide the divergence without explaining it.
  Check: applied migrations stay byte-identical; a checksum failure is investigated as drift, never repaired away.
- **Out-of-band schema changes.** Hotfix DDL applied manually leaves a live environment ahead of the chain; the next migration fails or double-applies.
  Check: where drift against a live database is suspected, the plan gives a human the exact schema-diff command to run; drift is never resolved by editing history.
- **Seeds and fixtures left behind.** Seed data referencing removed or retyped columns breaks local verification quietly, and with it every future contributor's setup.
  Check: seeds, fixtures, and factory definitions still load after the change.

## Escalation triggers (`needs-decision`)

- Drift where the live database, not the migration chain, may hold the truth: a human decides which wins.
- Baseline, squash, or repair operations touching history others may have applied (the agent never rewrites applied history itself).
- Moving to a different migration workflow or tool (adding a dependency is also an ask-first boundary in the agent).

## What good looks like

- One source of truth: schema file, migration chain, and local database agree, and the tool proves it.
- Generated artifacts are regenerated, committed with the schema, never hand-edited.
- The migration graph is linear with a single head, and applied files are immutable.
