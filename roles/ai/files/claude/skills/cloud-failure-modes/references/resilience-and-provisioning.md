# Resilience and provisioning

When to read: the brief or diff touches clusters, databases, managed services, availability zones, backups, quotas, or new accounts.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Single point of failure behind an availability claim.** One zone, one instance, one gateway on the only path: the topology contradicts the availability the service is supposed to offer, and nothing fails until the zone does.
  Check: stated availability maps to the topology (instances spread across zones, data replicated, no single network chokepoint); a deliberate single-zone choice is stated with its risk.
- **No backup, or no restore path.** A data store without backups and retention converts any bad day into data loss, and an untested backup is a hope, not a control.
  Check: stateful services carry automated backups with explicit retention, point-in-time recovery where offered, and the report names the restore path.
- **Managed service on raw defaults.** Provider defaults optimize for first-run convenience: audit logging off, upgrades surprising, maintenance windows random.
  Check: audit and access logging, upgrade policy, and maintenance windows are set deliberately on every managed service; a default kept is named, not assumed.
- **Version at the end of its life.** Provisioning an engine or runtime version near end of support mints an unplanned migration with a deadline someone else discovers.
  Check: new managed services pin a version with support runway, and the upgrade policy states who moves it forward.
- **Cluster provisioned without an operational story.** A cluster with one node pool in one zone, control-plane logs off, and no upgrade policy is an outage and a forensic dead end in one resource.
  Check: node pools spread across zones, control-plane logging on, an upgrade channel or version policy stated; what runs inside the cluster stays the platform seat's.
- **Quota wall at apply time.** Plans do not check service quotas; the human applying hits the wall mid-apply and the change lands half-created.
  Check: changes that add significant count or size are compared against account quotas; anything close is flagged in the report for the applier.
- **Foundations hand-rolled past the landing zone.** Organizations with a landing zone or account factory encode identity, logging, network, and guardrail baselines; an account or project built beside it forks the foundation.
  Check: new accounts, subscriptions, or projects inherit the landing-zone baseline through its vending process; a deviation is escalated, not improvised.
- **Recovery settings without recovery objectives.** Replication, failover, and cross-region copies chosen without stated objectives are cost without a promise.
  Check: replication and failover choices trace to recovery objectives from the brief or project docs; absent objectives, the gap goes in the report rather than being invented.

## Escalation triggers (`needs-decision`)

- Provisioning a new account, subscription, or project, or deviating from the landing-zone baseline (also an ask-first boundary in the agent).
- Sizing or availability topology with no stated basis; sizing and failover derived from SLOs belong to the SRE seat, hand it across.

## What good looks like

- The topology matches the promise: availability, recovery, and quotas verified against what the service claims to offer.
- Managed services arrive with their operational story: logs, backups, upgrades, windows.
- A new account looks like every other account, because the landing zone built it.
