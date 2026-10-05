# Streaming

When to read: the brief or diff touches streaming jobs or pipeline-level consumers, offsets, checkpoints, reprocessing, or lag.
App-side producers, consumers inside services, and handler idempotency belong to backend-failure-modes' events-and-async reference; this file covers streams as pipeline input and output, at partition scale.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Offsets committed before processing.** Committing position and then processing means a crash between the two loses the batch: at-most-once by accident (Kafka's documented delivery-semantics contract: advance position only after the effect is durable).
  Check: offsets or checkpoints advance only after the batch's output is durably written; a crash between write and commit yields a duplicate, and the sink dedupes it (see idempotency-and-replay).
- **Checkpoint and output torn apart.** A job whose state checkpoint and sink commit are separate operations replays or loses the delta between them on recovery.
  Check: the sink is transactional with the checkpoint or idempotent by batch or offset key, and the recovery contract after a hard kill is stated; an exactly-once claim names its mechanism (transactional producer with read-committed consumers, or a transactional sink), otherwise design for at-least-once plus an idempotent sink.
- **Poison message stalls the partition.** One malformed record retried forever blocks everything behind it; lag on that partition grows without bound.
  Check: bounded retries per record, then dead-letter or quarantine with the error attached, and a metric on quarantine depth someone watches.
- **Lag invisible.** Consumer lag is the freshness promise in disguise; without a lag signal the pipeline runs late for days before a user notices.
  Check: lag or watermark delay is exported and alertable; sustained growth is a capacity `needs-decision`, not something to absorb quietly.
- **Reprocessing breaks the sink.** Replaying from an earlier offset re-emits everything; sinks and downstream pipelines built for append-only forward progress double-count.
  Check: reprocessing is designed, not improvised: sinks are idempotent by key or partition, or the replay writes to a new output cut over deliberately.
- **Ordering assumed across partitions.** Order holds per partition or key only; a repartition, rekey, or parallelism change silently breaks cross-record assumptions.
  Check: changing partition count or keys on an existing stream is escalated, and any order-dependent pipeline logic names the key that guarantees it.
- **Schema evolution mid-stream.** Old and new events coexist during deploys, and replays surface records from months ago.
  Check: the job reads both old and new schema versions (registry compatibility mode or tolerant reader); removing or retyping a field escalates.
- **Streaming and batch logic drift.** The same transformation implemented twice, once streaming and once batch, drifts until the two disagree about the same output.
  Check: shared logic is factored once, or an explicit reconciliation compares the two paths on a schedule.

## Escalation triggers (`needs-decision`)

- Reprocessing an existing stream from earlier offsets: it is a backfill, propose the exact command and window for a human (also an ask-first boundary in the agent).
- Schema changes to a topic other pipelines or teams consume (also an ask-first boundary in the agent).
- Changing partition count, keys, or delivery semantics on an existing stream.

## What good looks like

- The job can be killed at any moment and resumes without loss or unmerged duplicates.
- Lag is a dashboard number with an alert, not a vibe.
- Replaying from any offset is a designed operation, not an emergency experiment.
