# Cost and tagging

When to read: the brief or diff touches any new resource; tags, budgets, instance sizes, or anything with a monthly bill.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Untagged spend.** A resource without owner, environment, and cost-attribution tags cannot be budgeted, attributed, or safely cleaned up; it becomes permanent through anonymity.
  Check: every new resource carries the project's full tag scheme, through provider default tags where they exist plus resource-level additions; tag keys match the existing scheme exactly, case included.
- **Cost discovered at the bill.** The cheapest moment to question a resource is before it exists; a cost surprise a month later is an incident with no owner.
  Check: state the expected monthly cost delta at decision time (estimation tooling if installed, provider pricing knowledge otherwise) and put it in the report; an unknown cost is a finding, not a shrug.
- **Always-on where scales-to-zero fits.** An always-on resource bills for every hour including the idle ones; the equivalent serverless or scheduled shape bills for use.
  Check: every new always-on resource states why constant capacity is needed; spiky or scheduled usage prefers shapes that scale with it.
- **Cost that compounds with traffic.** Per-request, per-gigabyte, and cross-zone charges look free at development volume and compound at production volume.
  Check: name the dimensions each new resource meters on (requests, storage, egress, cross-zone traffic) and what happens to cost when traffic grows tenfold.
- **Oversized by guesswork.** Instance and cluster sizes picked to "be safe" ship large headroom that is never revisited.
  Check: sizing has a stated basis (existing workload data, the project's convention, the smallest tier that fits); a guess is labeled a guess, with a revisit note in the report.
- **Sizing with no guardrail.** Nothing but attention stops the next change from provisioning an outsized or disallowed shape, and attention is exactly what completion pressure spends.
  Check: where the project has policy-as-code, size and type limits are encoded there; where it does not, flag the missing gate in the report.
- **Non-production billed like production.** Development and staging sized like production and running around the clock quietly multiply the bill.
  Check: non-production environments justify production sizing, and always-on non-production resources carry a schedule or a stated reason.
- **Orphans by design.** Volumes that outlive instances, addresses that outlive gateways, snapshots that accumulate forever: resources whose end of life nobody wrote down.
  Check: everything created has a deletion story: it dies with its parent, a lifecycle policy ages it out, or the report names who owns removing it.

## Escalation triggers (`needs-decision`)

- A significant cost delta or a new always-on resource (also an ask-first boundary in the agent).
- Deviating from or extending the project's tag scheme: attribution is an organizational contract, not a local choice.

## What good looks like

- Every resource answers who owns it, what it is for, and what it costs, from tags alone.
- The report states the cost delta and its scaling dimensions before anyone pays it.
- Nothing accrues silently: every resource has a lifecycle end.
