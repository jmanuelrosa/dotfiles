# The `product-team` OpenSpec schema

OpenSpec's stock `spec-driven` workflow, plus the three stages it lacks.

## Why it exists

Both workflows were run on the same real initiative from the same idea document, scored against a rubric written before either ran ([openspec-arm-rubric.md](../../../../../../docs/research/openspec-arm-rubric.md)).

Stock `spec-driven` produced 13 of 18 requirements and settled 5 of 7 genuinely-open decisions, in 18 minutes for $7.33, against the product-team pipeline's $100.83 over 3 days and 6 human decision points. It also settled two decisions at spec time that the pipeline did not reach until implementation.

Every miss fell inside a stage `spec-driven` does not have, and none fell in the four it shares. So this schema keeps the four stock artifacts unchanged and adds the three missing stages around them:

| Added artifact | Closes |
|---|---|
| `research` | evidence discipline, and requirements that let the product measure its own objectives |
| `ux-spec` | states, and the design-system pieces that do not exist yet |
| `red-team` | enforcement gaps, unexamined security and privacy defaults, reversibility |

## The graph

```
research → proposal → specs → ux-spec → design → red-team → tasks → apply
```

`ux-spec` sits before `design` because states drive the data contract: a paginated empty state changes the API sketch, and discovering that after the contract is written is how a contract ships that one of its own states cannot render.

`red-team` sits after `design` rather than after the proposal, which is where the product-team pipeline puts it. That is a deliberate improvement rather than a copy: the pipeline's stage-3 placement means it never sees the design, and the measured run shows the pipeline missing design-level defects (where validation runs relative to deploy, whether the deployed artifact is publicly readable) until implementation.

## Install into a project

```
cp -R <dotfiles>/roles/ai/files/openspec/schemas/product-team <project>/openspec/schemas/
```

Then make it the default in `<project>/openspec/config.yaml`:

```yaml
schema: product-team
```

Per change instead of by default: `openspec new change <name> --schema product-team`.

Verify with `openspec schema validate product-team` and `openspec status --change <name> --json`, which should show `research` ready and every other artifact blocked.

## Delegation, and what happens without it

Three artifacts ask to be produced by an agent, because fresh context is the point: an agent that has not read the idea document cannot inherit its assumptions.

| Artifact | Agent | From |
|---|---|---|
| `research` | `product-team:competitive-researcher`, `product-team:user-evidence-researcher` | the `product-team` plugin |
| `ux-spec` | `ux-shaper` | `claude-kit add ux-shaper --type agent --global` |
| `red-team` | `product-team:pm-red-team` | the `product-team` plugin |

None is required. Every one of those instructions carries the full method inline and tells the model to say in the output that it was not delegated, so the schema works in a project with neither the plugin nor the agent installed. It is weaker that way, most of all for `red-team`, where reviewing your own design in the same context reliably produces agreement.

**Untested:** whether `/opsx:propose` can dispatch an agent at all. Its skill declares `allowed-tools: Bash(openspec:*)`, while its body twice instructs the model to invoke a named skill or command when an `instruction` field asks for one. Those may conflict. The inline fallback is why that question does not block using this schema, but it is worth checking on the first real run and recording the answer here.

## Keeping up with upstream

`proposal`, `specs`, `design` and `tasks` carry upstream's instruction text with a short paragraph appended where a new artifact has to be read, and their four templates are byte-identical to the fork. That is deliberate: `openspec schema fork spec-driven <tmp>` on a newer OpenSpec produces a file this one can be diffed against.
