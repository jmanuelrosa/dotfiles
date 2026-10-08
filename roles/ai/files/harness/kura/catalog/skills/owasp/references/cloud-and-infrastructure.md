# Cloud and Infrastructure

When to read: the brief, diff, or assessed surface touches IAM policies or roles, VPCs, subnets or security groups, object storage buckets or signed URLs, DNS records or custom domains, serverless functions and their triggers, Terraform/Pulumi/CDK or other IaC, WAF or DDoS config, or relational database servers, accounts, grants and connection settings.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Cloud Architecture Security](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Cloud_Architecture_Cheat_Sheet.html), [Infrastructure as Code Security](https://cheatsheetseries.owasp.org/cheatsheets/Infrastructure_as_Code_Security_Cheat_Sheet.html), [Serverless / FaaS Security](https://cheatsheetseries.owasp.org/cheatsheets/Serverless_FaaS_Security_Cheat_Sheet.html), [Subdomain Takeover Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Subdomain_Takeover_Prevention_Cheat_Sheet.html), [Database Security](https://cheatsheetseries.owasp.org/cheatsheets/Database_Security_Cheat_Sheet.html)

## Contents

- Identity and least privilege
- Trust boundaries and network exposure
- Object storage exposure
- DNS and subdomain takeover
- Database hardening
- Serverless functions
- IaC pipeline, inventory and runtime
- Edge protection, logging and monitoring
- Shared responsibility and patching

## Identity and least privilege

- **Wildcard IAM action or resource on a workload role.** Each function or workload gets its own role limited to the exact actions and resources it needs, and database or API keys it holds are scoped to the smallest set of actions; an `*` action or resource, or one high-privilege role shared across functions, lets a single compromised function reach everything the role can.
  Check: IaC policy documents attached to functions and workloads contain no `*` in action or resource and no role is shared by functions with different needs; replace with named actions on named resources. Owner: `cloud`. Source: Serverless/FaaS, IaC Security.
- **Persistent access key embedded in a service instead of a workload identity.** Services that reach object storage or other cloud APIs authenticate with a workload identity or federated role that yields short-lived credentials, limited to the required storage operations and resources; a persistent key can be hardcoded and, when stolen, exposes every resource it permits. IAM-mediated access is acceptable for sensitive user data only when it follows rigorous coding and cloud practice.
  Check: no long-lived cloud access keys in code, environment variables, or IaC for workloads; roles are attached through instance profiles, workload identity, or STS-style federation. Owner: `cloud`. Source: Cloud Architecture, Serverless/FaaS.
- **IaC execution rights not restricted.** Define who may create, update, run, and delete IaC scripts and inventory, limit authorized IaC users to what their task needs, and have the scripts grant created resources only what they require to work.
  Check: the deploy role, state backend, and pipeline that applies IaC are restricted to named principals with scoped permissions, and resource policies emitted by the IaC are minimal. Owner: `cloud`. Source: IaC Security.

## Trust boundaries and network exposure

- **Internal caller trusted because of network location or ownership.** Access is never granted merely because a component is internal or owned by the same organization; per NIST SP 800-207, protected resources require explicit authentication and authorization, and trust checks are identified between cloud components as well as at connections to end users and vendors. The full-trust configuration, where user input reaches a critical component with no auth or identity check, is not used unless there is no sensitive content, and user input is never trusted even in low-risk applications.
  Check: service-to-service endpoints authenticate the caller and authorize the operation, with no "request came from the VPC, so allow" branch. Owner: `architect`. Source: Cloud Architecture.
- **Service reachable around the gateway that authenticates for it.** A gateway can perform shared authentication, but the service behind it authenticates the calling gateway, validates propagated user context, enforces permissions that need resource or business context, and blocks direct access that bypasses the gateway; it reaches storage with its own least-privileged identity, because an authenticated user does not authorize every storage operation.
  Check: the service verifies the gateway's identity and the user context instead of trusting forwarded headers, and network rules or ingress config prevent reaching it except through the gateway. Owner: `backend`. Source: Cloud Architecture.
- **Datastore or backend server in a public subnet.** Databases, backend servers and their file systems, and anything too sensitive for direct internet access sit in private subnets reached only through public entry points (gateways, load balancers, public front ends); VPCs separate whole applications, large components, and per-customer duplicates. Bastions in public subnets are very insecure when engineered incorrectly.
  Check: IaC places datastores and backends in subnets without a route to an internet gateway and without public IPs, and security groups admit them only from the tier in front. Owner: `cloud`. Source: Cloud Architecture, Database Security.
- **Function with unrestricted network egress.** Default network access, including outbound internet, is disabled unless required; functions sit in private subnets with controlled egress, sensitive functions (payment, auth) are isolated from general-purpose ones, and production and staging are separated by strict boundaries.
  Check: function network config names private subnets and security groups that restrict outbound traffic, and sensitive functions do not share subnets, roles, or accounts with general ones. Owner: `cloud`. Source: Serverless/FaaS.

## Object storage exposure

- **Sensitive data in public object storage.** Public object storage is not an advisable distribution method and is used only for public, non-sensitive, generic resources; anything stored with public access for any period must be treated as leaked, and public buckets also give attackers reconnaissance into the environment.
  Check: bucket policies and ACLs grant no anonymous read or list on buckets holding user or internal data, and account-level public-access blocks are on. Owner: `cloud`. Source: Cloud Architecture.
- **Signed URL used for sensitive data or built from injectable input.** Signed URLs are used only for user data that is not very sensitive, because anyone holding the URL has anonymous access; their expiry is decided deliberately, and custom or dynamic URL generation must not be injectable.
  Check: signed URLs carry a short expiry, are generated by the provider SDK for an object key the server derives and authorizes, and are not used for highly sensitive files. Owner: `backend`. Source: Cloud Architecture.

## DNS and subdomain takeover

- **Cloud resource deleted before its DNS record.** Decommission in this order: serve a maintenance page or redirect, update or remove the DNS record, wait at least the TTL (typically 300 to 3600 seconds), then delete the resource; deleting the resource first opens a takeover window that lasts until someone notices.
  Check: teardown diffs remove or repoint every associated record (CNAME, A, MX, NS, TXT) in the same or an earlier change than the resource deletion, and teardown pipelines verify DNS removal before marking decommissioning complete. Owner: `cloud`. Source: Subdomain Takeover.
- **NS, MX, or A record pointing at a released target.** NS delegation to a deleted hosted zone or closed DNS-provider account lets anyone claim every record under the subdomain; MX to a deprovisioned mail service lets an attacker receive mail and pass CA email domain validation; A records to released elastic IPs can be reassigned.
  Check: every NS, MX, A, and CNAME record in the zone config targets a resource that still exists and is owned by the organization, ideally managed in the same IaC codebase. Owner: `cloud`. Source: Subdomain Takeover.
- **DNS records with no linked owning resource.** Keep an inventory mapping each CNAME, A, or NS record to its target resource, owning team, project, creation and expected decommission date, and business justification, consulted and updated on every infrastructure change; manage DNS in version control so additions and removals are reviewed, approved, and logged.
  Check: DNS records live in IaC or a DNS-as-code tool alongside the resources they point to, changed through reviewed diffs, not by console edits. Owner: `cloud`. Source: Subdomain Takeover.
- **No automated dangling-record detection.** Scan all DNS records on a schedule (daily or weekly, fingerprint scans at least weekly) to verify targets resolve and return expected content rather than provider error pages, alert on new CNAMEs and on targets returning 404, NXDOMAIN, or default error pages, and monitor Certificate Transparency logs for unexpected certificates.
  Check: a scheduled job or pipeline step performs dangling-record scanning and a CT-log monitor is configured for the organization's domains. Owner: `sre`. Source: Subdomain Takeover.
- **Provider domain verification not used or removed on teardown.** Where the provider offers custom-domain verification (Azure App Service `asuid` TXT, Google Cloud TXT or Search Console, Cloudflare for SaaS custom hostname verification, GitHub Pages verified domains, CloudFront certificate-backed alternate names), use it and keep the verification record even after decommissioning; where none exists, prompt DNS removal is the only control.
  Check: custom-domain bindings have their verification TXT records in the zone config and teardown diffs do not delete them. Owner: `cloud`. Source: Subdomain Takeover.
- **Wildcard DNS record at the apex.** Avoid wildcard records unless absolutely necessary; when required, scope them narrowly (`*.staging.example.com`, not `*.example.com`), front them with a proxy that allowlists valid hostnames and errors on others, and monitor CT logs for matching certificates.
  Check: no apex-level wildcard record in zone config; any wildcard has a hostname allowlist at the proxy. Owner: `cloud`. Source: Subdomain Takeover.
- **Security controls trust every subdomain.** Limit takeover blast radius: session cookies are not scoped to the parent domain unless necessary (prefer the exact host and the `__Host-` prefix), CSP lists trusted subdomains explicitly instead of `*.example.com`, CORS validates against an explicit origin allowlist, OAuth/SSO uses exact-match redirect URIs, and SPF mechanisms do not match addresses a taken-over subdomain could control.
  Check: cookie `Domain` attributes, CSP source lists, CORS origin checks, and redirect-URI allowlists contain no wildcard subdomain patterns. Owner: `backend`. Source: Subdomain Takeover.
- **Decommissioned subdomain still referenced by trust configuration.** Decommissioning also removes the subdomain from OAuth redirect allowlists, CSP directives, and CORS configuration, revokes or lets expire its TLS certificates, updates the DNS inventory, and confirms the name no longer resolves and is not claimable.
  Check: the teardown change removes the hostname from redirect, CSP, and CORS allowlists in the same release. Owner: `backend`. Source: Subdomain Takeover.
- **Takeover response not runbooked.** On discovery: remove the record immediately (or repoint it to a target you control), revoke certificates issued during the takeover found via CT logs, assess cookie, phishing, OAuth/SSO, and email exposure, notify affected users when sensitive data, credentials, or cookies were exposed, fix the process gap, scan every zone for other dangling records, and document the timeline and corrective actions.
  Check: the incident-response runbook contains these steps. Owner: `sre`. Source: Subdomain Takeover.

## Database hardening

- **Thick client connecting directly to the database.** An application running on an untrusted system always connects through an API that enforces access control; direct connections from a thick client to the backend database are never made.
  Check: desktop or mobile client code contains no database driver, connection string, or database credential. Owner: `desktop`. Source: Database Security.
- **Database reachable beyond the application hosts.** The database is isolated and talks to as few hosts as possible: local socket or named pipe instead of TCP where feasible, bind to localhost, firewall the port to specific hosts, or place it on a dedicated internal segment; web management tools (phpMyAdmin, pgAdmin) are protected with authentication, HTTPS, and network restrictions.
  Check: server config binds narrowly and network rules admit the database port only from application hosts; any admin UI sits behind auth and network allowlists. Owner: `database`. Source: Database Security.
- **Unencrypted database connections.** The database accepts only encrypted connections using a trusted certificate, and clients connect with TLS 1.2 or later with modern ciphers (AES-GCM or ChaCha20) and verify the server certificate; without this, traffic after the initial authentication crosses the network in clear text.
  Check: server config requires TLS for all connections and client connection settings enable certificate and hostname verification rather than disabling it. Owner: `database`. Source: Database Security.
- **Shared or over-privileged database account.** Authentication is always required, including local connections; each account has a strong unique password, serves a single application, never uses built-in `root`, `sa`, or `SYS`, holds no administrative rights over the instance, connects only from allowed hosts, reaches only its databases, and is not the database owner (ownership enables privilege escalation). Dev, UAT, and production use separate databases and accounts.
  Check: migrations and grant scripts create a dedicated per-application role with host restrictions and no ownership or admin grants. Owner: `database`. Source: Database Security.
- **Grants broader than the application's queries.** Grant only the permissions the application needs (the sheet notes most applications need only `SELECT`, `UPDATE`, and `DELETE`); avoid database links or linked servers, and when required give them an account limited to the minimum databases, tables, and system privileges. Security-critical applications apply table-, column-, or row-level permissions, or block the underlying tables and require access through restricted views.
  Check: grant statements list explicit privileges on explicit objects, with no `ALL` grants and no linked-server account broader than its use. Owner: `database`. Source: Database Security.
- **Database credentials in application source.** Credentials are never stored in source code; they live in a configuration file outside the web root, readable only by the required users, not committed, and encrypted with built-in protection where possible; integrated authentication (Windows authentication for SQL Server, the native Windows plugins for MySQL) removes stored credentials entirely.
  Check: no connection string with an embedded password in the repository. Owner: `backend`. Source: Database Security. See `secrets-management.md` for secret storage and rotation.
- **Database accounts never reviewed.** Review accounts and permissions regularly, remove accounts when an application is decommissioned, and change passwords when staff leave or compromise is suspected.
  Check: decommissioning changes drop the application's database role, and a documented review cadence exists. Owner: `database`. Source: Database Security.
- **Database server not hardened.** Base the host OS on a secure baseline (CIS Benchmarks or Microsoft Security Baselines), install security updates, run the database service as a low-privileged user, remove default accounts and databases, store transaction logs on a separate disk from the data files, and take regular backups protected with appropriate permissions and ideally encrypted.
  Check: provisioning code applies the baseline, sets a non-root service user, and configures encrypted, access-restricted backups. Owner: `database`. Source: Database Security.
- **Dangerous engine features left enabled.** On SQL Server, disable `xp_cmdshell`, `xp_dirtree` and other unneeded stored procedures, CLR execution, the SQL Browser service, and Mixed Mode Authentication unless required, and remove the Northwind and AdventureWorks samples; on MySQL or MariaDB, run `mysql_secure_installation` to remove default databases and accounts and withhold the `FILE` privilege from all users.
  Check: server configuration and grant scripts show these features disabled and no account holds `FILE`. Owner: `database`. Source: Database Security.

## Serverless functions

- **Function trigger without authentication.** Every trigger (API gateway, pub/sub, storage events, IoT) enforces authentication and authorization, function-to-function calls are validated with signed tokens or workload identities, and invocations are rate limited and throttled against DoS and abuse.
  Check: each trigger in the function config has an authorizer or source restriction, and internal invocations carry a verified identity. Owner: `cloud`. Source: Serverless/FaaS.
- **Event payload trusted as input.** All event payloads are untrusted: validate length, type, and format, defend against SQL, XSS, JSON injection, and deserialization attacks, and strip unnecessary fields and metadata before processing.
  Check: handlers parse events through a schema or explicit validators before use and never trust an event source blindly. Owner: `backend`. Source: Serverless/FaaS.
- **Secret or sensitive data persisted across invocations.** The runtime is not assumed clean between invocations: secrets and sensitive temporary data are not kept in global or static variables or left in `/tmp`, timing side channels are considered, and sensitive workloads use single-use execution environments where the platform supports them.
  Check: no secret or per-request sensitive value assigned at module scope, and handlers delete temp files they create. Owner: `backend`. Source: Serverless/FaaS.
- **Secrets in function environment configuration.** Secrets are fetched at runtime from a vault or caching extension, not from platform-level function configuration such as environment variables, and are never hardcoded; use ephemeral credentials (STS, workload identity federation) and rotate secrets automatically.
  Check: function definitions in IaC carry no secret values in environment blocks, and code obtains them from the secret store. Owner: `cloud`. Source: Serverless/FaaS. See `secrets-management.md` for secret lifecycle controls.
- **Unsigned deployment package or artifact.** Sign artifacts at build time and verify signatures against an approved publisher before deployment or use; a checksum alone does not authenticate the publisher. For AWS Lambda, use code signing configurations with allowed signing profiles and `UntrustedArtifactOnDeployment` set to `Enforce` (the default `Warn` admits packages failing expiry, publisher, or revocation checks), and sign layers with an allowed profile too. Keep deployment packages minimal and scan their dependencies.
  Check: function IaC attaches a code signing config set to enforce, and the pipeline signs and verifies packages and layers. Owner: `cloud`. Source: Serverless/FaaS, IaC Security.

## IaC pipeline, inventory and runtime

- **IaC changes not security-checked in CI/CD.** Run IaC static analysis, open-source dependency checks, and container image scans in the CI/CD pipeline on every change with consolidated reporting and compliance history, plus dynamic analysis of the environments the infrastructure interoperates with; security plugins in the IDE catch issues earlier.
  Check: the pipeline has IaC misconfiguration scanning, dependency, and image scanning steps that run on IaC changes and gate merges. Owner: `platform`. Source: IaC Security.
- **Secrets committed with IaC.** Secrets such as tokens, passwords, and SSH keys are not kept in plain text files or source control, and secret detection runs on the repository.
  Check: no credentials in IaC variables files or state committed to the repo, and a secret scanner runs in CI. Owner: `platform`. Source: IaC Security. See `secrets-management.md` for storage and rotation.
- **Infrastructure change shipped apart from its feature.** All IaC changes are tracked in version control with enough information to revert, and a feature's infrastructure lands in the same branch or merge request as the feature.
  Check: infrastructure for a feature appears in the feature's PR, not in an out-of-band console change. Owner: `cloud`. Source: IaC Security.
- **Untagged or orphaned cloud resources.** Every deployed resource is labeled, tracked, and logged in inventory; untagged assets become ghost resources that drift the security posture, so monitor for them. Decommissioning erases configuration, securely deletes data, and removes the resource from runtime and inventory.
  Check: IaC applies mandatory tags to every resource (via default tags or policy), and teardown includes data deletion. Owner: `cloud`. Source: IaC Security.
- **Infrastructure patched in place instead of replaced.** Build infrastructure to an exact specification with no deviation; a required change provisions new infrastructure and retires the old.
  Check: changes are applied by redeploying from IaC, with no manual mutation steps in runbooks. Owner: `cloud`. Source: IaC Security.
- See `secure-sdlc.md` for threat modeling and attack surface analysis before designing a cloud architecture or IaC.

## Edge protection, logging and monitoring

- **Entry point without a WAF.** Attach a WAF to entry points such as load balancers and API gateways as a first line of defense, start from the provider's managed rule sets, and add custom rules: restrict routes to acceptable endpoints, protect chosen technologies and key endpoints, and rate limit sensitive APIs; attach monitoring or alerting to the WAF. Choose DDoS protection by risk and business criticality, from WAF rate limits and route blocking up to managed DDoS services.
  Check: IaC associates a WAF with every public entry point, with managed rules plus rate-limit rules on sensitive routes. Owner: `cloud`. Source: Cloud Architecture.
- **Request logs capture credentials or whole headers and bodies.** Log HTTP outcomes through an allow-listed event schema (method, route template, status, correlation ID, non-secret actor identifier), exclude credentials, session cookies, access tokens, and sensitive content before collection, never capture all headers or bodies by default, and keep SSNs, health data, and other PII out of logs; log internal actions with actor and permission information and propagate trace IDs through the whole request lifecycle.
  Check: logging middleware writes named fields rather than the raw request, and redaction runs before the log sink. Owner: `backend`. Source: Cloud Architecture, Serverless/FaaS. See `logging-and-error-handling.md` for the logging vocabulary.
- **Security and audit logging off at provisioning.** Enable security and audit logs when provisioning infrastructure and ship them to centralized logging; legal and compliance set retention times.
  Check: IaC enables audit and flow logging for accounts, networks, and managed services, with a defined retention. Owner: `cloud`. Source: IaC Security, Cloud Architecture, Serverless/FaaS.
- **No anomaly or runtime threat alerting.** Alert on deviations from an environment-specific baseline: 4xx and 5xx rates, CPU, memory, and storage, database reads and writes, and serverless invocations; alert on failed health checks, deployment errors, container on/off cycling, and cost limits; run continuous monitoring and runtime threat detection.
  Check: alert rules for these signals exist in the monitoring config with thresholds derived from a baseline. Owner: `sre`. Source: Cloud Architecture, IaC Security, Serverless/FaaS.

## Shared responsibility and patching

- **Security assumed to be the provider's under the chosen service model.** Know, per service, which layers are yours: on managed services authentication and authorization, logging and monitoring, code security, and third-party library patching remain the developer's; on IaaS nearly everything from network access control and OS vulnerabilities upward is. For SaaS, request attestation records and compliance evidence such as ISO 27001.
  Check: the design records the responsibility split for each chosen service and assigns an owner to each customer-side control. Owner: `architect`. Source: Cloud Architecture.
- **Self-managed images and services left stale.** Automate regular minor-version and image updates (golden images) and schedule time to refresh stale resources and handle end-of-life migrations.
  Check: an automated image or patch pipeline exists for self-managed compute, and base images are not pinned to outdated versions without an update job. Owner: `cloud`. Source: Cloud Architecture.
