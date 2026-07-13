# Events, queues, and async processing

When to read: the brief or diff touches message consumers or producers, queues, topics, background jobs, schedulers, or webhooks.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Redelivery treated as exception.** Every mainstream broker is at-least-once; exactly-once at the application level is a myth, and redelivery is normal operation (consumer crash, visibility timeout, rebalance).
  Check: the handler is idempotent, via a processed-message store, natural key, or state guard; processing the same message twice produces one effect.
- **Ordering assumed where none exists.** Ordering holds only per partition or per key, and only with one in-flight consumer; cross-key or cross-topic ordering assumptions break silently under scale or retry.
  Check: if the handler depends on order, the partition key guarantees it; otherwise the handler tolerates out-of-order arrival.
- **Poison message blocks the queue.** A message that always throws is redelivered forever, stalling its partition and starving everything behind it.
  Check: bounded retries per message, then dead-letter with the error attached, and an alert on DLQ depth; a DLQ nobody watches is a black hole.
- **Publish and commit torn apart.** Publishing before the DB commit emits phantom events for rolled-back work; publishing after can silently lose the event if the process dies between the two.
  Check: use the project's outbox or transactional-messaging pattern; if none exists, flag the gap instead of hand-rolling a best-effort publish.
- **Event schema breaks old consumers.** During deploys, consumers read events produced by both old and new code, and replays surface messages from months ago.
  Check: additive schema changes only; removed or retyped fields are a `needs-decision`; the handler tolerates unknown fields.
- **Job retry without design.** Default retry policies (immediate, unbounded, no jitter) turn one failure into a self-inflicted load spike, and a partially completed job that retries re-executes its completed side effects.
  Check: exponential backoff with jitter and a retry cap; each side effect inside the job is individually idempotent or guarded.
- **Visibility timeout shorter than processing.** A job still running when its lease expires gets delivered to a second worker; both complete, effects double.
  Check: lease or visibility timeout comfortably exceeds worst-case processing time, or the job heartbeats to extend it.
- **Unbounded queue growth.** A producer faster than its consumer grows the queue until latency or storage fails; nobody notices without a depth signal.
  Check: queue depth and consumer lag are visible in metrics with an alert threshold; sustained imbalance is a capacity `needs-decision`, not something to hide.
- **Event fan-out loops.** Handlers that publish events which trigger other handlers can form cycles or amplification cascades nobody designed.
  Check: trace the full event chain the change participates in before adding a new edge to it.
- **Compensation that fails or goes silent.** In a saga or multi-step workflow, a compensation handler that can itself fail, or that skips publishing its outcome when the underlying operation was already rolled back, leaves the workflow stuck half-compensated forever.
  Check: compensation steps are idempotent, retry to success, and always emit their result event; each step has its own timeout rather than one global one; a partially executed step still gets compensated.

## Escalation triggers (`needs-decision`)

- Creating a new topic, queue, or scheduled job (also an ask-first boundary in the agent).
- Changing a partition key, consumer group, or delivery semantics on an existing flow.
- Any handler whose correct behavior under redelivery the brief does not pin down.

## What good looks like

- Every consumer is safe to replay from the beginning of the topic.
- Failure of a handler is visible (DLQ alert, lag metric) before a user reports it.
- The event catalog stays additive; consumers never need lockstep deploys with producers.
