# PII and retention

When to read: the brief or diff touches sensitive fields, new sinks for existing data, masking, retention, or deletion.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Sensitive fields into a new sink.** Copying a dataset that contains PII into a new table, topic, export, vendor, or vector store multiplies the compliance surface silently.
  Check: enumerate the sensitive fields in any data the change moves; every new location for them is explicit in the brief or escalated, and embedding free text counts as a sink (vectors can memorize and leak PII).
- **Values in logs and errors.** Row-level logging, failed-record dumps, and exception context capture raw values from sensitive columns.
  Check: logs and error paths reference keys and metadata, never raw sensitive values; quarantined records containing PII get the same protection as their source.
- **Masking at the wrong layer.** Protection applied in a consumer view while the underlying table stays raw and broadly readable.
  Check: masking, tokenization, or column-level access applies where the data lands, and each downstream layer's exposure is stated.
- **Retention declared, propagation missing.** A retention policy on the source that its derived copies ignore: deletes never reach downstream tables, snapshots, or quarantine.
  Check: retention and deletion obligations propagate to every location the pipeline writes, including time-travel snapshots and dead-letter stores.
- **Deletion request meets immutable raw.** Right-to-be-forgotten arrives and the append-only raw layer has no designed path to honor it.
  Check: the project's existing deletion mechanism (crypto-shredding, rewrite jobs, exclusion lists) is followed; inventing one is an escalation, not an improvisation.
- **Backfills resurrect deleted data.** Reprocessing from raw re-materializes rows that were deleted downstream for compliance.
  Check: replay and backfill paths honor deletion or exclusion state, not just the original raw bytes.
- **Production PII in dev fixtures.** Sample data for local verification pulled from production with sensitive columns intact.
  Check: fixtures are synthetic or anonymized; production PII never lands on a laptop or in a dev bucket.
- **New fields unclassified.** A source adds fields (free text, nested payloads) whose sensitivity nobody assessed before they land.
  Check: newly landed fields are reviewed for sensitivity, and free-text or blob columns are treated as sensitive until shown otherwise.

## Escalation triggers (`needs-decision`)

- Retention, deletion, or archival changes (also an ask-first boundary in the agent).
- Landing sensitive fields somewhere they do not already live; if the destination is a new external sink or vendor, that is also an ask-first boundary in the agent.
- A deletion obligation with no existing mechanism to honor it.

## What good looks like

- Sensitive fields are enumerated, classified, and protected where they land, not where someone remembers.
- Deletion propagates everywhere the pipeline copied the data, including snapshots and quarantine.
- Local verification never needs production PII.
