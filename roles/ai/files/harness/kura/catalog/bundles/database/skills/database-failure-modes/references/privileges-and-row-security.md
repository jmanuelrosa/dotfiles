# Privileges and row security

When to read: the brief or diff touches roles, grants, object ownership, row-level security policies, stored routine bodies, or the accounts application or agent code connects as.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Application connects with owner or admin power.** A request-path role that owns its tables or holds superuser, `ALL`, or DDL rights turns any injection or leaked credential into full control of data and schema.
  Check: grants for the application role list explicit verbs on explicit objects, with no ownership, superuser, `ALL`, or DDL; routine-only access is `EXECUTE` on the routines it calls, never an owner role to get execute; migrations run under a separate role from the request path.
- **One account for every service and duty.** A role shared across services, or across application, migration, backup, and admin work, makes every consumer as powerful as the most privileged one and leaves nothing revocable on its own.
  Check: each service gets its own role, application connections never use the migration, backup, or admin role, and where the engine scopes accounts by host, the role admits only the hosts that use it.
- **Request role that bypasses row security.** On engines with row-level security (Postgres among them), superusers and roles with the bypass attribute skip every policy even when forced, and a table owner skips them unless forced, so tenant isolation exists only on paper.
  Check: each tenant-scoped table enables and forces row security with a tenant isolation policy; the request role is neither superuser, bypass-row-security, nor table owner; a policy reading the tenant from session state errors when it is unset instead of comparing against null; privileged migration and admin jobs constrain their own tenant set, because row security will not.
- **Read path holding write grants.** Request-serving or agent code that only reads but connects with write rights lets an injected query or a manipulated model rewrite the data it serves, retrieval indexes included.
  Check: credentials used by request-serving and agent code are read-only on the stores they only read; writes to a vector or retrieval index come only from the ingestion role; the store requires authentication even on an internal network.
- **Dynamic SQL inside a routine.** A procedure or function that concatenates its arguments into a statement is as injectable as application string-building, and one running with its definer's rights hands every caller the definer's power.
  Check: dynamic SQL in routine bodies binds inputs through the engine's parameterized execute form and takes identifiers only from a fixed allowlist; definer-rights routines pin their schema search path so callers cannot shadow the objects they reference.

## Escalation triggers (`needs-decision`)

- Granting superuser, bypass-row-security, ownership, or admin rights to any role a service connects as.
- Grant or policy changes on tables other services or teams consume or write to (also an ask-first boundary in the agent).
- Disabling, loosening, or dropping a row-security policy on a table that already holds tenant data.
- A brief that needs a login password or connection string: credentials stay out of this seat's reach, so ship the role definition and name the secret as a cross-slice dependency.

## What good looks like

- Every role reads as a sentence: which service, which objects, which verbs.
- The request path is the least privileged connection in the system; migration and admin roles never serve traffic.
- Tenant isolation holds even when application code forgets the filter.
- Read paths cannot write, and retrieval indexes change only through ingestion.
