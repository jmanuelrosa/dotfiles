# Authorization and tenancy

When to read: the assessed surface includes roles, permissions, object ownership, tenancy, or admin surfaces.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **Guard parity assumed from middleware existence.** Middleware being defined is not middleware being applied; one route registered outside the guarded router ships open.
  Check: route by route, confirm the guard chain is actually applied by reading the router registrations and any exclusion or skip lists, never the middleware file alone.
- **Authentication mistaken for authorization (IDOR).** A logged-in caller using an object ID from the request without an ownership check reads any ID it can guess.
  Check: for each handler taking an ID from path, query, or body, trace the query it feeds: an ownership or tenant filter enforced server-side, on reads as well as writes, batch and nested lookups included.
- **Tenancy by convention.** Tenant filters remembered per query instead of enforced by mechanism mean the breach is one forgotten clause away.
  Check: identify the tenancy mechanism (row-level security, default scopes, repository filters); where scoping is a per-query convention, sample queries for misses and report the class with the enforced mechanism as the paved path.
- **Privilege escalation through the request body.** Binding request bodies wholesale to models lets a caller set role, admin, or tenant fields on themselves.
  Check: read the write paths for privilege- and ownership-bearing fields; anything not behind an explicit allowlist is a finding.
- **Admin surfaces on their own weaker rules.** Admin panels, internal tools, and support endpoints grown outside the main authorization layer collect bespoke, weaker checks.
  Check: locate every admin-capable surface and confirm it uses the same enforced authorization layer as the rest of the app, not its own.
- **Fail-open decisions.** An authorization check that allows when the permission lookup errors converts every outage into privilege escalation.
  Check: read the catch and error branches of each authorization decision point; every error path denies.
- **Client-side enforcement counted as a control.** Hidden buttons and front-end route guards protect nothing; the API is the boundary.
  Check: for each privileged action visible in the client, confirm the corresponding API enforces the same permission independently.
- **Horizontal moves through aggregate endpoints.** Search, export, reporting, and bulk endpoints assemble data across objects and are where single-object checks get bypassed.
  Check: trace aggregate and export queries for the same ownership and tenant scoping the single-object paths carry.
- **Non-ID references acting as capabilities.** Filenames, storage keys, and signed URLs fetched on the caller's behalf skip the object-level check the ID path has.
  Check: trace file and object-storage access for authorization on the referenced object itself, not just on the route that serves it.

## Escalation triggers (report immediately)

- A confirmed cross-tenant or cross-user access path traced end to end on an internet-facing surface: an actively exploitable P0; lead the report with it.
- The brief asking you to confirm access with requests against a live tenant: network calls against targets are out (also a hard rule); the evidence is the traced code path.

## What good looks like

- Authorization decisions live in one enforced layer, and routes inherit guards by construction.
- Every query touching tenant data is scoped by mechanism, not memory.
- Denied attempts are observable events with actor and resource, ready for detection-and-evidence.
