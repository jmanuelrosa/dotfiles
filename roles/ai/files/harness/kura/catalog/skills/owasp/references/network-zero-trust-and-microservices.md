# Network Segmentation, Zero Trust and Microservices

When to read: the brief, diff, or assessed surface touches service-to-service calls, an API gateway or service mesh, mTLS or internal tokens, firewall rules, security groups or network policies, network zones or VPN access, workforce identity and admin access, device trust, a microservice logging pipeline, legacy systems behind a proxy, or a microservice architecture inventory.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Network Segmentation](https://cheatsheetseries.owasp.org/cheatsheets/Network_Segmentation_Cheat_Sheet.html), [Zero Trust Architecture](https://cheatsheetseries.owasp.org/cheatsheets/Zero_Trust_Architecture_Cheat_Sheet.html), [Microservices Security](https://cheatsheetseries.owasp.org/cheatsheets/Microservices_Security_Cheat_Sheet.html), [Microservices based Security Arch Doc](https://cheatsheetseries.owasp.org/cheatsheets/Microservices_based_Security_Arch_Doc_Cheat_Sheet.html)

## Contents

- Service-to-service authentication and authorization
- Segmentation and network access
- Workforce identity and privileged access
- Devices and endpoints
- Data protection
- Logging pipeline and security monitoring
- Legacy systems
- Policy-as-code and rollout
- Architecture inventory for security analysis

## Service-to-service authentication and authorization

- **Downstream service relies on the gateway for authorization.** Gateway checks reject unauthorized ingress and direct access that bypasses them is prevented, but each service enforces access to its protected operations, including internal calls, with object, tenant, and business rules enforced at the service; gateway checks, identity-aware proxies, and WAF filtering complement this and never establish that a downstream operation is authorized. As the system grows, prefer shared, reviewed policies with service-level enforcement.
  Check: every handler of a protected operation performs its own authorization check, including handlers only reachable from other services, and no code path treats "came through the gateway" or "internal network" as permission. Owner: `backend`. Source: Microservices, Zero Trust. See `authorization.md` for policy placement and distribution.
- **Calling service not authenticated.** Each service authenticates the service that calls it, either with mTLS (every service holds its own key pair, backed by a PKI that handles provisioning, trust bootstrap, revocation, and rotation) or with a signed token obtained from a security token service using the caller's own identity and attached to every request over TLS.
  Check: internal endpoints require a client certificate or a validated service token, and service credentials are per-service rather than shared. Owner: `backend`. Source: Microservices.
- **User context forwarded in a form the receiver cannot validate.** Propagate authenticated user context in a form each receiving service can validate, and authenticate the calling service separately; a signature protects an assertion's integrity but does not itself grant access to the requested resource.
  Check: services do not read user identity from unsigned forwarded headers, and a valid user assertion is still followed by an authorization check. Owner: `backend`. Source: Microservices. See `tokens-and-federation.md` for forwarding, token exchange, and internal assertions.
- **Token validated by signature alone, or accepted when validation fails.** Local validation uses trusted issuer keys and the applicable token profile (RFC 9068 for JWT access tokens), since signature verification alone is insufficient, and it does not see server-side revocation before expiry, so pair it with token lifetimes or a revocation mechanism meeting the required response time; online introspection caches are bounded to the required freshness and never outlive token expiry. Requests are rejected when the required validation cannot be completed, and neither approach replaces service-level authorization.
  Check: token validation checks issuer, audience, expiry, and type in addition to signature, introspection cache TTL is capped below token expiry, and validator errors deny the request. Owner: `backend`. Source: Microservices.
- **Authorization for one resource reused for another.** Each resource session is authorized with least privilege and authorization for one resource never grants another; ongoing sessions are reevaluated per policy with reauthentication or reauthorization after a time limit, on a request for another resource, or on suspicious activity, and access is revoked when policy no longer permits it. Session expiry follows resource sensitivity, without requiring a new interactive login on every request.
  Check: tokens and sessions are scoped to a resource or audience, sensitive resources set shorter lifetimes, and a revocation path exists. Owner: `backend`. Source: Zero Trust. See `sessions-and-cookies.md` for expiration values.
- **API gateway that does not authenticate, validate, or throttle.** API security gateways authenticate every API call, validate request schemas, and enforce rate limits for microservice communication.
  Check: gateway route config attaches an authenticator, a request schema, and a rate limit to each route. Owner: `cloud`. Source: Zero Trust. See `rest-and-webhooks.md` for REST controls.
- **Internal traffic in plaintext.** Every connection is encrypted and authenticated regardless of network location (office to cloud, between internal systems, between clouds, between containers), using TLS 1.3 or better per the sheet; a service mesh can handle identity and encryption between containers.
  Check: internal service, database, broker, and cross-cloud connections are configured for TLS, and mesh or sidecar config enforces mTLS in strict rather than permissive mode. Owner: `platform`. Source: Zero Trust. See `http-headers-tls-and-caching.md` for TLS configuration.

## Segmentation and network access

- **Flat network without security zones.** A system consists by default of at least three security zones: FRONTEND (balancer, application-layer firewall, web server, web cache), MIDDLEWARE (applications, authorization, analytics, message queues, stream processing), and BACKEND (SQL databases, LDAP directory, cryptographic key storage, file servers); internet-facing services sit in an inbound DMZ protected by a WAF, and outbound-only services sit in a DMZ with no rules admitting traffic from external networks.
  Check: network IaC defines separate segments per zone with firewall rules between them, and nothing in BACKEND is reachable from the internet. Owner: `cloud`. Source: Network Segmentation.
- **Cross-system access bypassing the owning application.** FRONTEND and MIDDLEWARE segments of different information systems do not talk to each other, and a MIDDLEWARE segment never reaches another service's BACKEND segment (no access to a foreign database bypassing its application server).
  Check: firewall and security-group rules grant no path from one system's application tier to another system's data tier. Owner: `cloud`. Source: Network Segmentation.
- **Shared segment treated as segmented.** When many applications share a network behind one load balancer, segmentation no longer separates them and access control between applications happens at layer 7 in the balancer.
  Check: a shared segment exposes a single inbound port to the balancer, and the balancer config enforces per-application routing and access rules. Owner: `cloud`. Source: Network Segmentation.
- **No micro-segmentation or default-deny between workloads.** Give each application its own segment, block traffic unless specifically permitted, monitor internal (east-west) traffic, and encrypt all communication between systems; for containers, network policies control which workloads may talk.
  Check: Kubernetes namespaces carry a default-deny network policy with explicit allows, and cloud security groups have no broad internal allow rules. Owner: `platform`. Source: Zero Trust.
- **VPN admission treated as authorization.** Prefer access to specific resources (ZTNA) over broad network access; any VPN that remains during migration is restricted and monitored, a VPN connection alone never authorizes other resources, and authentication and resource authorization are tested before legacy paths are retired. Apply DNS and web filtering and analyze network connections. Zero Trust is identity-based, so network controls alone do not achieve it.
  Check: resources behind the VPN still authenticate and authorize each request rather than allowlisting the VPN address range. Owner: `cloud`. Source: Zero Trust.
- **No written network security policy.** The organization defines a policy describing firewall rules and basic allowed network access, presented concisely with diagrams and examples (CI/CD permissions, monitoring-system access) so teams know what access can be requested.
  Check: a network policy document exists and firewall changes reference it. Owner: `architect`. Source: Network Segmentation.

## Workforce identity and privileged access

- **Workforce MFA missing or phishable.** Require MFA for employees, contractors, and partners; the most secure options are FIDO2 hardware keys activated by PIN, biometric, or separate password, WebAuthn passkeys with required user verification, and smart or PIV cards; TOTP apps and backup codes are acceptable; SMS is avoided (SIM swapping, phishing). Biometrics alone are not MFA, and conditional access requires stronger authentication in high-risk situations.
  Check: identity provider or app MFA config disallows SMS as a factor and step-up policy exists for high-risk access. Owner: `backend`. Source: Zero Trust. See `mfa-passkeys-and-transaction-signing.md` for factor implementation.
- **Standing administrative privileges.** Grant least privilege, provide elevated access just in time for a specific task with automatic expiration, remove permanent admin rights, and put administrative accounts under privileged access management.
  Check: IAM config has no permanently assigned admin roles for humans; elevation goes through a time-bound grant. Owner: `cloud`. Source: Zero Trust.
- **Fragmented or unreviewed workforce accounts.** Use one identity system rather than multiple user databases (and the same login across all clouds), automate role-based account creation, review access every quarter, and use separate accounts for administration.
  Check: services federate to the central identity provider instead of keeping local user stores, and admin roles bind to dedicated admin identities. Owner: `cloud`. Source: Zero Trust.
- **Access decision ignores context.** Access policy is dynamic: it weighs identity, device, location, time, and normal behavior, applies risk-based step-up rather than flat allow or deny, and enforcement happens at every enforcement point, not only the network edge. Assets that fall out of compliance lose access.
  Check: the design names the policy engine, the signals it uses, and every enforcement point. Owner: `architect`. Source: Zero Trust.

## Devices and endpoints

- **Unregistered or unhealthy device granted access.** Register approved devices with unique PKI certificates, continuously assess health (antivirus, OS patches, security configuration), scan for vulnerabilities, and automatically remove access when a device is compromised or out of compliance; every endpoint has anti-malware, behavior monitoring, full disk encryption, and remote wipe. Unknown devices are routed to isolated access (for example a secure browser environment) rather than given network access.
  Check: access policy requires a device certificate and a compliance signal before granting access. Owner: `security`. Source: Zero Trust.

## Data protection

- **Sensitive data unclassified.** Label data by sensitivity, identify data assets with their protection level (PII, confidential), and map which storages hold each asset as golden source or cache, so every piece of sensitive data is identified and classified.
  Check: the design or data inventory lists each asset with a protection level and its storages. Owner: `architect`. Source: Zero Trust, Microservices Arch Doc.
- **Data access not logged or exfiltration unmonitored.** Encrypt data at rest and in transit, monitor and block unauthorized transfers, and record who accessed what data and when.
  Check: reads of sensitive records emit an audit event with actor, resource, and timestamp. Owner: `backend`. Source: Zero Trust. See `cryptography-and-keys.md` for encryption at rest.

## Logging pipeline and security monitoring

- **Secrets written to local logs before filtering.** Each service excludes secrets and unnecessary sensitive data before it emits a log entry, including to local files or standard output; agent-side filtering is an additional safeguard and cannot remove data already written locally.
  Check: redaction happens in the service's logger, not only in the shipping agent. Owner: `backend`. Source: Microservices. See `logging-and-error-handling.md` for data to exclude.
- **No correlation ID across a call chain.** Services generate a correlation ID that uniquely identifies every call chain, and the logging agent includes it in every message, publishes structured logs (JSON, CSV), and appends platform and runtime context (hostname, container name, class, file).
  Check: inbound middleware creates or propagates a correlation ID and outbound clients forward it. Owner: `backend`. Source: Microservices.
- **Log transport unauthenticated or broker unrestricted.** The logging agent and message broker use mutual authentication (for example TLS-based) to encrypt log messages and authenticate each other, and the broker enforces least-privilege access control.
  Check: agent-to-broker config enables mutual TLS and broker ACLs limit each producer and consumer. Owner: `sre`. Source: Microservices.
- **Log loss not planned for.** Buffer logs locally, run a dedicated logging agent on the same host, decouple collection from processing with a broker, define buffer limits and behavior when storage fills, monitor delivery failures, test recovery from outages, and have the agent report health and status; local files and brokers alone do not guarantee lossless delivery.
  Check: pipeline config sets buffer limits and overflow behavior, and an alert fires on agent unavailability or delivery failure. Owner: `sre`. Source: Microservices.
- **Logs modifiable from a compromised host.** Copy logs to a separate server in its own segment using an append-only mechanism such as syslog, so an attacker who compromises a system cannot alter its logs.
  Check: logs ship off-host to a dedicated log segment the source host cannot rewrite. Owner: `sre`. Source: Network Segmentation.
- **Security telemetry not centralized or acted on.** Collect logs from all systems and all clouds into a SIEM, hunt threats, analyze behavior against learned baselines, automate response (isolate accounts, quarantine devices), and track authentication success versus failure, policy violations, MTTD, and MTTR; collect identity, network, runtime, deployment, and vulnerability telemetry. Assess and mitigate the privacy risks of this monitoring and exclude sensitive data from what is collected.
  Check: every system's logs route to the central SIEM, with alert rules for authentication failures and policy violations. Owner: `sre`. Source: Zero Trust.

## Legacy systems

- **Legacy system exposed without modern authentication.** Put security proxies or wrappers (identity-aware proxy, application firewall, API gateway) in front of systems that cannot do strong authentication, MFA, or session management, use protocol-translation gateways to convert SAML or OAuth into what the system expects, isolate legacy systems in separate heavily monitored zones that require modern authentication to enter, and use network-based detection where the system cannot log.
  Check: no legacy endpoint is reachable except through the proxy, and its zone has restricted, monitored ingress. Owner: `architect`. Source: Zero Trust.

## Policy-as-code and rollout

- **Workload policy not version-controlled or verified at deploy.** Where policy-as-code is adopted, policies are version-controlled, tested in CI/CD, enforced automatically at deployment, and traceable through audit logs; continuous verification covers workload identity, image signature validation, SAST, IaC and image scanning gates, and RBAC and network-policy drift. Admission checks reject violating deployments but do not replace runtime resource authorization.
  Check: admission or org policies live in the repo with CI tests, and deployment fails on unsigned images or policy violations. Owner: `platform`. Source: Zero Trust.
- **Zero Trust rolled out without inventory or validation.** Migrate incrementally: first inventory users, devices, applications, and data flows, pilot changes on selected workflows, verify legitimate access still works, monitor policy decisions, then pick the next workflow by risk and dependencies; use risk-based authentication so low-risk activity stays seamless, test policies with real users, train staff, secure executive sponsorship, and prefer open standards over a single-vendor platform.
  Check: the migration plan names the inventory, pilot scope, and validation criteria before cutting over access paths. Owner: `architect`. Source: Zero Trust.

## Architecture inventory for security analysis

- **Microservice architecture undocumented for security.** Inventory each application service (ID, description, repository, owning team, API definition including the security scheme such as scopes or API keys per endpoint, architecture description, runbook), each infrastructure service (authentication, authorization, discovery, logging, monitoring, gateway) with its documentation, each data storage and message queue with its software, and each data asset with its protection level; render the result as a call graph or data flow diagram.
  Check: the architecture doc lists every service, storage, queue, and asset with these attributes. Owner: `architect`. Source: Microservices Arch Doc.
- **Inter-service relations not recorded.** Record service-to-storage relations with access type (read or read/write), synchronous service-to-service calls with protocol, purpose, and data passed, asynchronous publisher-subscriber relations with their queue, and asset-to-storage relations, and use them for data leakage analysis.
  Check: each new call, queue subscription, or datastore access in a diff has a matching entry in the relations inventory. Owner: `architect`. Source: Microservices Arch Doc.
- **Trust boundary crossings unjustified.** Feed the inventories into a system model, mark trust boundaries and flows that cross them, justify each crossing, and record endpoint identities, authentication and authorization enforcement points, and data-in-transit protection; then check those controls against deployed configuration, since the inventory alone does not verify enforcement. Use infrastructure-service inventory to confirm security controls are centralized, simple, vetted, and reusable rather than duplicated or missing.
  Check: the threat model maps each crossing to a named enforcement point that exists in code or config. Owner: `architect`. Source: Microservices Arch Doc.
- **Service permissions not derived from its relations.** Define the minimal scopes or API keys each service needs for other APIs and the minimal grants it needs on databases and queues from its API definition and recorded relations.
  Check: a service's credentials and grants match its recorded relations with nothing extra. Owner: `architect`. Source: Microservices Arch Doc.
- **Endpoints missing from security testing scope.** Enumerate the endpoints to test and threat-model from the API definitions and infrastructure-service documentation.
  Check: the security test suite or scope covers every endpoint in the API definitions. Owner: `qa`. Source: Microservices Arch Doc.
