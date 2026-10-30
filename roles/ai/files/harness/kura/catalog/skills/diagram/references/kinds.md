# Kinds

Four kinds are the Diátaxis quadrants; `use-case` is the one a product conversation needs before any of them.
Each kind answers a different reader's question, so each gets a different picture, read from different places.

## What each kind draws

| Kind | Reader's question | What the picture shows | Mermaid type | Read first |
|---|---|---|---|---|
| `use-case` | What can an actor do with this, and where does the system end? | Actors outside a `subgraph` system boundary, the goals they reach inside it, and the external systems the goals depend on | `flowchart LR` | Entry points: routes, commands, handlers, jobs, UI screens; auth and tenancy checks that split actors |
| `explanation` | How does this work and why is it shaped like this? | The parts, who calls whom, and the data crossing each edge; or the lifecycle of one thing | `flowchart TD` with subgraphs; `sequenceDiagram` for a request; `stateDiagram-v2` for a lifecycle | The module boundaries, the public functions of each, the call graph between them |
| `reference` | What exactly exists and how does it relate? | Types, tables, modules or states, complete for the scope, with the fields or edges a user of the API needs | `classDiagram`, `erDiagram`, `stateDiagram-v2`, or a `flowchart` dependency map | Schemas, type definitions, enums, migrations, exported surface |
| `how-to` | Which steps get me from here to the goal, and where does it branch? | The decisions and steps a person takes, in order, with the branch at each decision | `flowchart TD` with decision diamonds; `sequenceDiagram` when the steps are calls to services | The command or workflow the reader runs, the config it reads, the failure paths |
| `tutorial` | What happens as I follow along? | A series: the same picture redrawn with one more part each time, so the reader watches the system assemble | `sequenceDiagram` or `flowchart`, two to four blocks | The path the tutorial's first run takes end to end |

A kind asked for with a subject that fits another kind better gets drawn as asked and the better kind named in the report.

## Where the page goes

Resolve in this order and stop at the first match:

1. `--into <doc.md>`: that page. Create it when absent.
2. A page already holding a marker with the same `name`: that page, in place.
3. The repo has a Diátaxis layout: `docs/tutorials/`, `docs/how-to/` (or `howto`, `guides`), `docs/reference/`, `docs/explanation/` (or `concepts`, `architecture`): the matching directory, `<slug>.md`. A `use-case` goes to `docs/explanation/` or its equivalent.
4. Otherwise `docs/diagrams/<slug>.md`, with a one-paragraph lead that names the subject and the kind.

Add a link from the nearest index (`docs/README.md`, `docs/index.md`, or the repo README's docs section) only when one already lists pages of that directory.
Never create the Diátaxis directories: that is a repo structure decision for the user.

## Anchoring

`paths` lists what the picture would change with, not everything read on the way:

- An `explanation` of a request path anchors the handlers and modules on that path.
- A `reference` of a schema anchors the schema file and its migrations directory.
- A `use-case` anchors the entry points (routes, commands) and the auth layer.
- A `how-to` anchors the command, workflow or config it walks through.

Prefer a directory glob (`src/auth/**`) over a long file list when the directory is the unit, and a file when it is.
Too wide a `paths` makes every scan stale; too narrow lets a real change slip. When unsure, anchor one level wider than the files drawn.
