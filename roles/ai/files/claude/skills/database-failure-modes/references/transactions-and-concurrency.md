# Transactions and concurrency

When to read: the brief or diff wraps migrations in transactions, assumes an isolation level, takes locks in queries, or runs through a connection pooler.
Transaction semantics of business logic (outbox, idempotency, check-then-act) belong to the backend seat's data-safety reference; this file covers the transactional behavior of DDL, migrations, and the connection layer.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **DDL transactionality assumed.** Engines differ: Postgres rolls back most DDL; MySQL commits implicitly on DDL, so a multi-statement migration is not atomic there and a mid-way failure leaves half-applied state.
  Check: establish whether the detected engine can roll back the migration's DDL; where it cannot, each migration is a single statement or written to re-run safely from any midpoint.
- **Non-transactional statement inside a wrapped migration.** Some statements (Postgres `CREATE INDEX CONCURRENTLY` among them) refuse to run inside a transaction; tools that wrap by default need an explicit opt-out.
  Check: migrations containing such statements disable the wrapper explicitly, and the remaining statements in that file are safe unwrapped.
- **Long transaction as collateral damage.** A transaction held open across slow work blocks vacuum from reclaiming dead rows across the database on Postgres, grows undo on InnoDB, and can block DDL elsewhere.
  Check: no transaction in the diff spans unbounded data work or external waits; long work commits in batches.
- **Isolation assumed, not established.** Read-then-write logic assuming stronger isolation than the engine default (READ COMMITTED on Postgres, REPEATABLE READ on MySQL) admits anomalies the code never handles.
  Check: any logic in the diff that depends on an isolation guarantee names it, and either matches the default or sets the level explicitly.
- **Deadlock by inconsistent ordering.** Two paths locking the same rows in different orders deadlock under load; batch updates without a deterministic order acquire row locks in whatever order the plan visits them.
  Check: multi-row updates in the diff (backfill batches included) lock in a consistent indexed order, and multi-object DDL follows the ordering existing migrations use.
- **Pooler-incompatible session state.** Under transaction-mode pooling (PgBouncer and equivalents), session state does not survive between transactions: session advisory locks (including the ones migration tools take), prepared statements, SET without LOCAL, temp tables, LISTEN/NOTIFY.
  Check: detect the pooler and its mode; anything in the diff, or the migration tool itself, needing session affinity is verified to connect around the pooler or is flagged.

## Escalation triggers (`needs-decision`)

- Changing pooling or replication configuration (also an ask-first boundary in the agent).
- Logic that needs a stronger isolation level than the project's default.
- A migration that cannot be made atomic or safely re-runnable on the detected engine.

## What good looks like

- Every migration is atomic on the detected engine, or explicitly written to resume from any midpoint.
- Transaction scope matches work scope: short, batched, never holding locks across unbounded work.
- The connection layer's guarantees (pooler mode, session state) are a design input, not a postmortem finding.
