# Transformation layering

When to read: the brief or diff adds models, moves logic between layers, or touches staging, intermediate, or mart boundaries and cross-model references.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Mart reading raw sources.** A mart or metric model that reaches past staging binds business logic to raw-source quirks; every upstream change breaks the serving layer directly.
  Check: only staging models read sources; every downstream layer references models, never raw tables.
- **Re-deriving what a mart provides.** New logic recomputes joins or business rules an existing mart already serves, creating a second truth to maintain.
  Check: search the existing marts and intermediates before building; extend or consume what exists instead of paralleling it.
- **Staging doing business logic.** Aggregations or business rules in staging make the cleaned layer opinionated, so every consumer inherits decisions they cannot see.
  Check: staging renames, casts, and cleans one source one-to-one; joins and business logic live in intermediate or mart layers.
- **Circular or sideways references.** A model referencing its own downstream, or marts reaching sideways into marts, makes build order and lineage unreadable.
  Check: references flow one direction through the layers; the DAG has no cycles and no mart-to-mart shortcuts the project's conventions do not already allow.
- **Grain undeclared.** A model without a stated grain invites every consumer to guess what a row means, and each join compounds the guesses.
  Check: every new or changed model states its grain, and a uniqueness test asserts it.
- **Duplicate staging of one source.** Two staging models cleaning the same source differently, or one concept modeled twice under different names.
  Check: one source, one staging model; a second model for an existing concept consolidates with it or is escalated.
- **Lineage bypassed by hard-coded names.** A raw `schema.table` literal instead of the framework's reference idiom hides the edge from lineage, selectors, and consumer discovery.
  Check: models reference upstreams through the framework's ref and source idiom, never raw table names.
- **Naming outside conventions.** A model named against the project's layer prefixes or folder layout breaks selectors, docs generation, and the next engineer's search.
  Check: names and locations follow the detected conventions exactly; deviations are escalated, not improvised.

## Escalation triggers (`needs-decision`)

- Restructuring layers or moving models across layers beyond what the brief asked for.
- A concept that genuinely needs two models (a performance fork, a security split): propose it, never duplicate silently.
- Consolidating existing duplicates other work may depend on.

## What good looks like

- Sources are read once and cleaned once, and every downstream question has one obvious model to ask.
- Lineage reads top to bottom: staging cleans, intermediate joins, marts serve.
- A new engineer can predict where logic lives from the name alone.
