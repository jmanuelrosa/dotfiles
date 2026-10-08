# Secrets Management

When to read: the brief, diff, or assessed surface touches API keys, database credentials, tokens, certificates, or other secrets in code, config, container images, environment variables, CI/CD variables, a secrets manager or vault, Kubernetes secrets, secret rotation or revocation, IAM access to secrets, secret scanning, or a leaked-secret incident.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

## Contents

- Secrets in code, images, and runtime injection
- Access control and IAM
- CI/CD handling of secrets
- Lifecycle: creation, rotation, expiration, revocation
- Auditing and monitoring
- Detection and incident response
- Availability, backup, and break-glass
- Secrets in memory and encryption of secrets
- Program and platform choices

## Secrets in code, images, and runtime injection

- **Secret baked into a container image or definition.** Secrets are never hard-coded with Docker `ENV` or `ARG` or built into an image; build-time injection is not recommended, and secret files are mounted by the orchestrator at runtime rather than built in.
  Check: read Dockerfiles and build args for secret-looking values or `COPY` of credential files; move them to orchestrator-mounted secrets. Owner: `platform`. Source: Secrets Management.
- **Secrets passed as environment variables when better options exist.** Environment variables are visible to all processes and may land in logs or dumps, so they are not recommended unless file mounts or in-memory fetch from the secret store are impossible; when used, the orchestrator injects the real value and nothing is hard-coded.
  Check: in deployment manifests, prefer volume-mounted or sidecar-fetched secrets over env vars and flag literal secret values in env blocks. Owner: `platform`. Source: Secrets Management.
- **Secret exposed through a mechanism shared across deployments.** Secrets are exposed only through mechanisms between the container and its deployment unit (for example a Pod), never through external mechanisms shared among deployments or orchestrators such as a shared volume.
  Check: flag secret volumes shared across workloads or namespaces; prefer in-memory volumes scoped to one Pod. Owner: `platform`. Source: Secrets Management.
- **Orchestrator secret storage not encrypted.** When the orchestrator stores secrets (for example Kubernetes Secrets), its storage backend is encrypted and the keys are well managed.
  Check: confirm encryption at rest is configured for the cluster's secret store with a managed key. Owner: `cloud`. Source: Secrets Management.
- **Encrypted secrets in git decryptable by developers or across environments.** A git-stored secret is encrypted so developers cannot decrypt it, is different per environment (DTAP) and encrypted with a different key per environment, and only the designated consumer in that environment can decrypt it.
  Check: read the encrypted-secrets config (recipients, key ids); flag developer keys among recipients or one key shared across environments. Owner: `platform`. Source: Secrets Management.
- **Pipeline-generated secrets with weak generation.** Scripts or binaries that create secrets use secure randomness and adequate length, driven by well-defined metadata kept in git or elsewhere.
  Check: read the generation script; flag non-CSPRNG sources and short lengths. Owner: `platform`. Source: Secrets Management.
- **Secrets transmitted in plaintext.** Secrets are never transmitted over plaintext channels; TLS is used everywhere.
  Check: flag `http://`, unencrypted database or broker URLs, and disabled TLS on any connection that carries credentials. Owner: `backend`. Source: Secrets Management.
- See `cryptography-and-keys.md` for keeping encryption keys out of source, version control, and environment variables.
- See `logging-and-error-handling.md` for keeping secrets, tokens, and keys out of logs.

## Access control and IAM

- **Engineers or services can read every secret.** Least privilege applies to secrets: the secrets system supports fine-grained, per-object access controls, policies limit which entities can read or write each secret, and engineers do not have access to all secrets.
  Check: read vault policies or cloud IAM for secret access; flag wildcard resources on secret read actions and human roles with read on production secrets. Owner: `cloud`. Source: Secrets Management.
- **Production and development secrets share one access boundary.** If access within one solution cannot be reduced enough, production and development secrets are separated into separate secret management solutions with tighter access to production; in Azure Key Vault, the RBAC permission model is used with least-privilege roles and separate vaults per application and environment as the primary boundary.
  Check: confirm production secrets live in a separate vault, project, or account from non-production ones. Owner: `cloud`. Source: Secrets Management.
- **IAM escalation paths reach the secrets.** The full IAM setup is hardened: no open "pass role" privileges or unrestricted IAM creation, tight control over what can impersonate a service account, and every cloud component's IAM in the threat model; only the specific roles that need secrets can access them, and those accounts are monitored.
  Check: flag `iam:PassRole` or equivalent on `*`, broad role-creation permissions, and service-account impersonation grants to workloads that do not need them. Owner: `cloud`. Source: Secrets Management.
- **Custom rotation function role assumable by others.** If a custom function rotates secrets, its role can be assumed only by that function, and the cloud provider's built-in rotation is preferred because misconfiguration risk is lower.
  Check: read the rotation role's trust policy; flag principals other than the function. Owner: `cloud`. Source: Secrets Management.
- **Root credentials of the secrets manager stored inside it.** The primary or root credentials of a secrets management solution are kept in a secondary secrets management solution.
  Check: confirm where the vault's root, unseal, or cloud management credentials are stored. Owner: `cloud`. Source: Secrets Management.

## CI/CD handling of secrets

- **Pipeline output or debugging exposes secrets.** Pipeline output does not leak secrets, production pipelines cannot be listened in on with debugging tools, and nobody can exec into CI/CD runners or workers.
  Check: flag `set -x`, echoing of secret variables, debug-mode toggles on production pipelines, and runner configs that allow interactive access. Owner: `platform`. Source: Secrets Management.
- **CI/CD tooling not treated as production.** CI/CD tooling is hardened and patched like production, has security event monitoring and proper authentication, authorization, and accounting, gives developers only the functions they need (administration via configuration-as-code in a separate repository), and creates pipelines only through an approved, security-reviewed MR/PR process.
  Check: confirm pipeline definitions change only via reviewed PRs and that project admin rights are limited. Owner: `platform`. Source: Secrets Management.
- **High-value long-lived secrets stored in CI tooling.** Secrets stored in CI/CD tooling are not long-term, wide-blast-radius, or high-value; shared secrets are limited (never one password for all admins), the set of people who can view or alter them is known and small, they are rotated regularly, forks or copied job definitions do not carry them, and each stored secret is documented with its reason.
  Check: list CI secret variables; flag cloud admin keys or static long-lived credentials, and confirm secrets are not exposed to fork-triggered workflows. Owner: `platform`. Source: Secrets Management.
- **CI credentials to the secrets manager are broad, long-lived, or unattributable.** Credentials CI uses to reach the secrets manager are rotated frequently and expire when the job completes, are scoped to only the secrets and services the job needs, and remain attributable to the person or service that triggered the job (through the certificate identity, token principal, or correlated request parameters); CI uses designated service accounts and this is re-verified periodically.
  Check: prefer short-lived federated job credentials over static tokens; confirm the role is scoped per pipeline and carries the triggering principal. Owner: `platform`. Source: Secrets Management.
- **CI delivers secrets the consumer could fetch itself.** It is better for the consumer to retrieve its own secret using a scheduled service account, so the pipeline holds orchestration credentials but never the secrets.
  Check: flag pipelines that read secrets only to pass them into deployments; switch to runtime retrieval by the workload identity. Owner: `platform`. Source: Secrets Management.
- **CI/CD actions not logged or alerted.** Every action in a CI/CD tool is logged, alert rules fire on any non-standard manipulation of the pipeline or its admin interface (including secret extraction via encoding or encryption), and logs are queryable for at least 90 days and kept longer in cold storage.
  Check: confirm CI audit logs are shipped to central logging with a 90-day queryable retention and alert rules exist. Owner: `sre`. Source: Secrets Management.

## Lifecycle: creation, rotation, expiration, revocation

- **Static secrets used where dynamic ones are possible.** Dynamic secrets are used where possible, with a short lease and revocation when no longer needed; restarting or stopping the consumer does not revoke stolen credentials, so invalidation is tied to lease expiry or explicit revocation.
  Check: for database and cloud credentials, confirm lease or TTL settings and a revocation step on decommission. Owner: `backend`. Source: Secrets Management.
- **Static secrets rotated manually or not at all.** Static secrets are rotated regularly and preferably automatically, with rotation of encryption keys planned for re-encryption impact; user credentials are excluded from scheduled rotation and rotated only on suspected or evidenced compromise.
  Check: confirm a rotation schedule or automation for each static machine secret, and that no forced periodic rotation is applied to user passwords. Owner: `cloud`. Source: Secrets Management.
- **Rotation function can be redirected to another resource.** An automated rotation function confirms rotation is enabled and the request token identifies a known secret version, returns safely if that version is already current, otherwise requires the pending stage, validates the current credential and that the pending version targets the intended database and user, reads the pending credential from the version named by the request token (not from state of an earlier invocation), and tests the pending credential before promotion (AWS: `ClientRequestToken`, `AWSPENDING`, `AWSCURRENT`).
  Check: read the rotation handler for each of these checks, starting from the provider's rotation templates. Owner: `cloud`. Source: Secrets Management.
- **Secrets never expire or are trusted without a status check.** Secrets expire after a defined time where possible, enforced by the consumer or by the secrets manager triggering rotation, policies limit availability to a period suited to the credential type, and applications verify a secret is still active before trusting it.
  Check: confirm expiry or TTL on issued secrets and an active-status check where the application validates presented secrets. Owner: `backend`. Source: Secrets Management.
- **Secrets not revocable or revocation not checked.** Secrets no longer needed or possibly compromised are revoked (including certificate revocation for TLS), revocation status is identifiable, and attempts to use revoked secrets are logged.
  Check: confirm a revocation API or procedure exists for each secret type and that use of a revoked secret produces a log event. Owner: `backend`. Source: Secrets Management.
- **New secrets weak or over-privileged.** Secrets are generated cryptographically robust for their purpose with the minimum privileges for their role, and credentials are provisioned over a secure channel rather than sending the password together with the username.
  Check: confirm generated credentials use a CSPRNG and the associated role is least-privilege; flag onboarding flows that send username and password in one message. Owner: `backend`. Source: Secrets Management.

## Auditing and monitoring

- **Secret access not audited or audit log tamperable.** Auditing is tamper- and deletion-resistant and covers at least who requested a secret for what system and role, approval or rejection, when and by whom it was used, expiry, attempts to reuse expired secrets, authentication and authorization errors, updates, and administrative actions on the supporting stack; timestamps are reliable via time sync, with monitoring for clock skew and manual time changes.
  Check: confirm audit logging is enabled on the secrets manager, shipped to a write-protected store, and that hosts run time sync. Owner: `sre`. Source: Secrets Management.
- **Anomalous secret use not alerted.** Monitoring records who or what accesses each secret, from which IP and by what method; CI credentials used from an IP other than the CI system, or a consumer arriving from an unexpected IP or user agent, raise an alert and the secret is treated as compromised.
  Check: confirm alert rules on secrets-manager access by source IP or identity anomalies. Owner: `sre`. Source: Secrets Management.
- **Secret metadata not recorded.** The secrets solution stores, per secret, when and by whom or what it was created, consumed, archived, rotated, or deleted, the contact for questions, its purpose and intended consumers, its type (AES key, HMAC key, RSA private key), and the manual rotation date if any.
  Check: confirm secret definitions carry owner, purpose, and type tags or descriptions. Owner: `cloud`. Source: Secrets Management.
- **Multi-cloud secrets audited and governed inconsistently.** Across multiple clouds, a centralized or standardized secrets solution enforces consistent rotation, access control, and auditing policies, with logs aggregated in central monitoring.
  Check: confirm each cloud's secret access logs reach the same central logging and that rotation policy is defined once. Owner: `cloud`. Source: Secrets Management.

## Detection and incident response

- **No pre-commit or PR secret detection.** Secret detection runs at the developer level (IDE, pre-commit hook, or PR), standard test secrets are used organization-wide to cut false positives, detection tools and signatures are evaluated often, more than one tool may be correlated, and signatures cover connection strings, API keys, passwords, 2FA keys, private keys, session tokens, config files, hard-to-rotate tokens, and platform-specific credential formats.
  Check: confirm a secret-scanning step exists in pre-commit config or CI on every PR. Owner: `dx`. Source: Secrets Management.
- **Secret handling and exposure response undocumented.** Documentation, updated especially after incidents, covers per secret who has access, how it is rotated, dependencies broken by rotation, the incident contact, and the impact of exposure, plus how to test for secrets, whom to alert, containment steps, and what to log during the event.
  Check: confirm a secrets runbook exists and names these elements. Owner: `security`. Source: Secrets Management.
- **Exposed secret not contained in order.** On exposure, the secret is revoked immediately, a replacement is created and deployed quickly (preferably automated and not human-readable), and the revoked secret is removed from the exposed system including code and logs (history rewrites with their consequences planned, log removal preserving log integrity); IR teams can see who had access, when it was used, and when it was last rotated, from a single logging location.
  Check: in a leak-fix diff, confirm the secret was rotated at the issuer, not only deleted from the file. Owner: `security`. Source: Secrets Management.
- **Secret-usage logging never validated.** Purple team exercises compare what should have been logged with what was logged and whether alerts fired, and logging follows a standardized vocabulary.
  Check: confirm detection tests or exercises reference secret-access events. Owner: `sre`. Source: Secrets Management.

## Availability, backup, and break-glass

- **Secrets backups untested or exposed.** Backups of the secrets system run automatically at a frequency matched to the number and lifecycle of secrets, restores are tested frequently, and backups are encrypted, stored with reduced access, and monitored for unauthorized access; secrets critical to product operations, especially encryption keys, are also backed up to separate (cold) storage.
  Check: confirm backup schedule, encryption, and restricted access on the backup location in IaC or runbooks. Owner: `cloud`. Source: Secrets Management.
- **No break-glass path when the secrets service is down.** Emergency break-glass credentials are backed up securely in a secondary secrets system and tested routinely, the secrets service is highly available for users and applications, and maintenance windows are chosen from metrics and audit logs.
  Check: confirm a documented and tested break-glass procedure exists. Owner: `sre`. Source: Secrets Management.
- **Secrets or KMS API quotas can take the service down.** Per-account or per-project API limits can cause self-inflicted DoS, so workloads are spread to limit blast radius and data key caching is used where supported.
  Check: for high-volume encryption or secret reads, confirm caching or batching and quota headroom. Owner: `cloud`. Source: Secrets Management.

## Secrets in memory and encryption of secrets

- **Secrets held in immutable strings in garbage-collected runtimes.** In .NET and Java, secrets are kept in byte or char arrays rather than Strings, memory is zeroed after use, and the plaintext window is minimized; whether to invest in memory protection is decided by threat model, and is recommended for untrusted environments or high-security needs.
  Check: flag secrets converted to String in sensitive paths and confirm buffers are cleared after use. Owner: `backend`. Source: Secrets Management.
- **High-assurance secrets processed on ordinary hosts.** For highly sensitive secrets, hardware or OS memory encryption, attested enclaves (secrets provisioned only after cryptographic attestation), confidential computing, or dedicated HSMs can isolate them.
  Check: where the threat model requires it, confirm secrets are released only to attested environments. Owner: `cloud`. Source: Secrets Management.
- **Convergent encryption enables guessing.** If convergent encryption is used to detect secret reuse, the scheme imposes sufficient resource cost during encryption and secrets are long enough to hamper guessing.
  Check: flag deterministic encryption of short secrets without a costly KDF. Owner: `backend`. Source: Secrets Management.
- **Self-managed key material imported without need.** Bring-your-own-key import is not recommended unless the threat model and policy require it; with cheaper stores such as AWS Parameter Store, encryption must be specified explicitly.
  Check: confirm parameter-store secrets use an encrypted type with a specified key. Owner: `cloud`. Source: Secrets Management.

## Program and platform choices

- **Secrets scattered across unmanaged stores.** A designated secrets management solution is used in every environment, standardized and centralized (possibly several solutions with standardized interaction) including lifecycle, authentication, authorization, and accounting; it is immediately apparent what each secret is for and where it lives; and an organization-wide policy sets password complexity and approved algorithms.
  Check: flag new secrets stored outside the organization's designated solution. Owner: `architect`. Source: Secrets Management.
- **Secrets tooling too hard to adopt.** The solution has clear documentation, SDKs, a CLI, CI/CD and IaC integrations, self-service workflows, clear error messages, and support channels, so developers do not fall back to insecure practices.
  Check: confirm a documented, supported path to obtain a secret exists for the service being built. Owner: `dx`. Source: Secrets Management.
- See `tokens-and-federation.md` for protecting OIDC and OAuth tokens and client credentials, and `mfa-passkeys-and-transaction-signing.md` for phishing-resistant authentication at the IdP.
