# Contracts and consumers

When to read: the brief or diff touches pipeline output schemas, contract files, freshness or SLA declarations, or output versioning.
This file covers declaring and evolving contracts for pipeline outputs; modeling on top of them (dbt, metrics, semantic layers) belongs to the analytics seat.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Output without a contract.** A new table or topic ships with no declared schema, freshness, or owner, so consumers bind to whatever the first run happened to produce.
  Check: new outputs declare schema, freshness expectation, and ownership in the project's contract idiom (contract file, registry entry, schema artifact) before consumers attach.
- **Contract and reality drift.** The declared schema and the produced data diverge because the contract artifact was not updated with the code, or nothing validates the two against each other.
  Check: the contract artifact changes in the same diff as the output, and a check ties them (contract test, registry compatibility check), or the missing gate is flagged.
- **Breaking change disguised as additive.** Retyping, renaming, or changing the meaning of an existing field (unit, timezone, nullability) while the field name survives.
  Check: existing fields keep name, type, and meaning; semantic changes ride a new field or a new version with a stated deprecation path for the old one.
- **Invisible consumers assumed absent.** "Nobody reads this yet": dashboards, ad-hoc queries, exports, and sibling teams bind to outputs without telling you.
  Check: search for consumers (lineage, warehouse query logs, code references) before any non-additive change; finding none is not evidence of none, escalate anyway.
- **Freshness promised nowhere.** Consumers assume the output is current while the pipeline knows only its schedule; when a run fails, nobody knows what staleness was acceptable.
  Check: the freshness expectation is declared where consumers can see it, and something compares actual to declared (or the gap is flagged).
- **Versioning by mutation.** A "v2" implemented by changing v1 in place hands replays and late consumers an incoherent mix of semantics.
  Check: versions are parallel outputs with a cutover plan, never in-place edits.
- **Null semantics unstated.** Null meaning unknown, not-applicable, or pipeline bug is undocumented, so every consumer guesses differently.
  Check: nullable contract fields state what null means, and columns consumers depend on carry not-null or null-rate expectations in the quality gates.
- **Sensitive fields unclassified in the contract.** PII flows through without classification, so downstream sinks cannot enforce policy on it.
  Check: contract or schema artifacts carry the project's sensitivity classification per field where the idiom supports it (see pii-and-retention).

## Escalation triggers (`needs-decision`)

- Schema changes to a table or topic other pipelines or teams consume (also an ask-first boundary in the agent).
- Declaring a freshness or SLA promise the current schedule and dependencies cannot meet.
- A consumer asking for semantics that belong in the analytics layer: hand it across, don't model it in the pipeline.

## What good looks like

- Every output a consumer can reach has a contract naming schema, freshness, and owner.
- Evolution is additive; breaking is a scheduled, versioned event consumers hear about in advance.
- The contract is enforced by a check, not a wiki page.
