# Networking and exposure

When to read: the brief or diff touches security groups, firewalls, load balancers, CIDR ranges, subnets, peering, or DNS.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Ingress from everywhere.** A rule open to 0.0.0.0/0 (or ::/0), above all on management ports, is the most-scanned misconfiguration on the internet, and "temporary for testing" is how it ships.
  Check: every ingress rule names the narrowest source that works (a known CIDR, a security group, the load balancer); management ports are never internet-open, use the platform's session or bastion path instead.
- **Egress left wide open.** All-ports egress to everywhere on every workload is a data-exfiltration path nobody chose; only deliberate egress points need it.
  Check: egress is scoped to what the workload talks to; a workload that genuinely needs broad egress states it.
- **Default security group doing work.** The default group allows what nobody reviewed; resources that fall into it inherit unaudited reachability.
  Check: the default group is locked down and unused; every workload attaches purpose-built groups.
- **Public by default.** Data stores and internal services land on public subnets or with public endpoints enabled because that is the shortest path to "it connects".
  Check: databases, caches, and internal services sit on private subnets with private endpoints; public reachability is an escalation, never a convenience.
- **Plaintext on the wire.** A listener terminating HTTP, or a legacy TLS policy, exposes in transit what the storage layer carefully encrypts at rest.
  Check: public listeners redirect to TLS with a current policy; internal hops follow the project's in-transit convention deliberately.
- **Peering that assumes connectivity.** A peering connection is not reachability: route tables and security rules still gate it, and peering does not transit to third networks.
  Check: both sides carry routes and rules for the intended flows and nothing more; anything needing transitive reach goes through the project's hub, escalated if none exists.
- **Overlapping or exhausted address space.** A CIDR that overlaps a peer, even partially, makes peering and transit routing impossible later, and a range packed tight leaves no room to grow; both are one-way doors.
  Check: new ranges are checked against every network they may ever connect to, come from the project's address plan where one exists, and leave deliberate headroom (providers also reserve addresses per subnet).
- **Dangling DNS.** A record pointing at a released address or a deprovisioned resource is a subdomain takeover waiting for whoever claims the target next.
  Check: records are created and destroyed with the resource they point at; touched zones are scanned for records whose targets no longer exist.
- **No flow visibility.** A network segment without flow logs cannot support incident forensics or reachability debugging after the fact.
  Check: new networks and subnets follow the project's flow-log convention; if the project has none, flag it as a missing gate.

## Escalation triggers (`needs-decision`)

- Opening ingress or making a private resource publicly reachable (also an ask-first boundary in the agent).
- CIDR allocation, peering, transit, or DNS topology changes (also an ask-first boundary in the agent).

## What good looks like

- Reachability is enumerable: a reviewer can list what can reach each resource and why.
- Address space is planned like a namespace: non-overlapping, registered, with headroom.
- Nothing is public that does not serve the public.
