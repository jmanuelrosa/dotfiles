# Constraints and integrity

When to read: the brief or diff touches foreign keys, unique constraints, NOT NULL, check constraints, cascade rules, or invariants currently enforced in application code.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Constraint added over violating rows.** Existing data that violates a new NOT NULL, unique, or foreign key constraint fails the migration mid-apply, often after locks are already taken.
  Check: a query in the plan proves existing rows satisfy the constraint, and the fate of violators (fix, backfill, exclude) is decided before the DDL ships.
- **Validation under full lock.** Validating a new constraint scans the whole table while blocking writes.
  Check: on engines that support it, add the constraint unvalidated (NOT VALID) and validate in a separate step under the weaker lock; on Postgres, NOT NULL can ride a validated check constraint, and a unique constraint attaches to an index built with the online path (`USING INDEX`).
- **Invariant living in application hope.** Uniqueness or referential rules enforced only in code fail under concurrency: two requests both pass the read check and both write.
  Check: invariants the database can express live in the database; where the diff adds app-side enforcement of a schema-expressible rule, surface the schema constraint as a finding, with the violation path handled in code.
- **Uniqueness scoped wrong.** A unique constraint missing a tenant or soft-delete dimension enforces uniqueness across rows that should not compete, or fails to enforce it where they should.
  Check: unique constraints state their scope explicitly; multi-tenant tables include the tenant column, and soft-deleted rows are excluded via a partial or filtered index where the engine supports it.
- **Cascade surprise.** ON DELETE CASCADE or SET NULL reaching further than intended turns one delete into a mass mutation.
  Check: every cascade in the diff enumerates what it can reach; changing existing cascade or foreign key semantics escalates.
- **Foreign key without a supporting index.** On engines that do not index the referencing columns automatically (Postgres), parent deletes and updates scan the child table.
  Check: every foreign key's referencing columns have a supporting index or a stated reason not to.
- **Constraint dropped to unblock a feature.** A constraint that fails a new write path gets dropped instead of the data model being fixed.
  Check: dropping or loosening a constraint escalates, with the violating case named and the integrity question answered.

## Escalation triggers (`needs-decision`)

- Dropping, loosening, or changing the semantics of an existing constraint or cascade rule.
- A constraint add requiring cleanup of violating rows first (that cleanup is a backfill, also an ask-first boundary in the agent).
- Constraints on tables other services write to (also an ask-first boundary in the agent).

## What good looks like

- Invariants live in constraints; application code handles the violation path instead of simulating enforcement.
- Large-table constraint adds are two-phase: add unvalidated, validate separately.
- Every cascade is intentional, and its blast radius is enumerable.
