# Data types and semantics

When to read: the brief or diff chooses or changes column types, stores time, money, text, or identifiers, or touches charsets and collations.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Silent narrowing.** Shrinking a text length, casting to a smaller integer, or reducing numeric precision truncates or rejects exactly the rows that do not fit, discovered at write time.
  Check: type changes widen by default; any narrowing enumerates existing out-of-range values first and escalates as lossy.
- **Naive timestamps.** A timestamp without timezone changes meaning with server or session timezone; mixing naive and aware columns corrupts comparisons.
  Check: time is stored as UTC instants in the engine's timezone-aware type, following the project's existing convention; deviations in the diff are flagged, not copied.
- **Money in floats.** Binary floating point cannot represent decimal amounts; sums drift silently.
  Check: money uses integer minor units or a decimal type with explicit precision and scale, matching the project's existing pattern.
- **Key exhaustion or fragmentation.** A 32-bit key on a growing table exhausts, and the fix is a locked rewrite of it and every referencing column; fully random IDs fragment write locality on clustered or write-heavy tables.
  Check: new keys state their growth and locality assumptions (bigint sequences, time-ordered UUIDs, or the project's pattern); a key type near exhaustion on a referenced table escalates.
- **Charset or collation mismatch.** Joining or comparing text columns with different charsets or collations forces conversions that defeat indexes and can error outright.
  Check: new text columns match the charset and collation of the columns they join or compare against; on MySQL that means utf8mb4, never the legacy utf8 alias.
- **Native enum lock-in.** A native enum type turns every added or removed value into a DDL event, on some engines a table rewrite.
  Check: follow the project's existing pattern for enumerations (lookup table, check constraint, or native enum); changing a native enum's values on a large table gets a lock check.
- **JSON as a schema escape hatch.** Fields queried relationally but stored in a JSON blob dodge constraints and defeat indexing.
  Check: fields with relational access patterns get real columns; JSON columns name what queries them and carry expression indexes where those queries filter.

## Escalation triggers (`needs-decision`)

- Any narrowing or otherwise lossy type change (also an ask-first boundary in the agent).
- Changing the type or strategy of a key other tables reference.
- A charset, collation, or time-handling convention change reaching beyond the tables in the brief.

## What good looks like

- Types encode the domain: range, precision, and encoding chosen for the data's real shape, not the ORM default.
- Time is one convention, timezone-aware, everywhere.
- Every key has a stated growth story; nothing exhausts or fragments by surprise.
