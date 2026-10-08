# Containers and Kubernetes

When to read: the brief, diff, or assessed surface touches Dockerfiles, `.dockerignore`, Compose files, container run flags, image builds, base images or registries, Kubernetes manifests, Helm charts or Kustomize overlays, `securityContext`, Pod Security admission labels, RBAC, ServiceAccounts, NetworkPolicy, Secrets or etcd encryption, ResourceQuota or LimitRange, admission controllers, kubelet, API server or dashboard configuration, or container runtime detection.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html), [NodeJS Docker](https://cheatsheetseries.owasp.org/cheatsheets/NodeJS_Docker_Cheat_Sheet.html), [Kubernetes Security](https://cheatsheetseries.owasp.org/cheatsheets/Kubernetes_Security_Cheat_Sheet.html)

## Contents

- Container daemon and host
- Container privileges and isolation
- Kubernetes control plane access
- Pod security admission and policy
- Network exposure and segmentation
- Secrets in images, containers and clusters
- Image build hygiene
- Image supply chain and admission
- Resource limits
- Runtime detection and response
- Audit logging and update cadence
- Process lifecycle in containers

## Container daemon and host

- **Docker socket mounted into a container.** Access to `/var/run/docker.sock` is unrestricted root on the host; it is never mounted into containers, and mounting it read-only does not make the API read-only, because any process that connects can still create or modify containers (filesystem flags do not replace API authorization).
  Check: no Compose `volumes:`, run flag or Kubernetes `hostPath` mounts `docker.sock` or another runtime socket; fix by removing it. Owner: `platform`. Source: Docker Security.
- **Docker daemon listening on TCP.** Running the daemon with `-H tcp://...` exposes unencrypted, unauthenticated control of the host (to the internet if the host is connected); do not enable it, and if unavoidable, secure it per the vendor's TLS guidance.
  Check: daemon flags and `daemon.json` contain no unauthenticated TCP host. Owner: `platform`. Source: Docker Security.
- **Host kernel or container engine out of date.** Containers share the host kernel, so a vulnerable kernel or runtime allows container escape to host root regardless of container hardening; keep the host kernel and the container engine updated, and harden host OSes with patch and configuration management and firewall rules.
  Check: node images or host provisioning pin a maintained kernel and engine version and have an update process. Owner: `platform`. Source: Docker Security, Kubernetes Security.
- **Daemon runs as host root where rootless is feasible.** Rootless mode runs the daemon and containers without host root, limiting the impact of a daemon or runtime compromise (unlike `userns-remap`, which leaves the daemon as root); it is strongly recommended where its limitations are acceptable, does not protect against kernel exploits, and daemonless rootless engines such as Podman are an alternative.
  Check: the platform design records whether rootless or daemonless runtime was evaluated and chosen. Owner: `platform`. Source: Docker Security.

## Container privileges and isolation

- **Container runs as root.** Containers run as an unprivileged user (Dockerfile `USER`, run-time `-u`, or user-namespace remapping), and in Kubernetes `runAsNonRoot: true` (pod and container) with a numeric `runAsUser`; copied application files are owned by that user (`COPY --chown`), since `USER` alone leaves root-owned files.
  Check: the final Dockerfile stage sets a non-root `USER` and manifests set `runAsNonRoot: true`; fix by adding both. Owner: `platform`. Source: Docker Security, NodeJS Docker, Kubernetes Security.
- **Privileged container or broad capabilities.** Never run with `--privileged` or `privileged: true`, which grants all kernel capabilities; drop all capabilities and add back only those required (`--cap-drop all --cap-add ...`, or `capabilities.drop: [ALL]` with a minimal `add`).
  Check: no privileged flag in run commands, Compose or manifests; every container drops `ALL`. Owner: `platform`. Source: Docker Security, Kubernetes Security.
- **Privilege escalation through setuid binaries allowed.** Containers run with `--security-opt=no-new-privileges`, or `allowPrivilegeEscalation: false` in Kubernetes, so setuid and setgid binaries cannot raise privileges.
  Check: every container sets `allowPrivilegeEscalation: false` (or the run flag). Owner: `platform`. Source: Docker Security, Kubernetes Security.
- **Default security profile disabled.** Never disable the default seccomp, AppArmor or SELinux profile; start from the runtime's default profile, restrict syscalls to the workload's minimum with a per-workload seccomp profile, apply per-container AppArmor profiles, run SELinux on the host with correctly labeled containers (SELinux options for finer control), and configure these profiles in the pod security context.
  Check: no `seccomp=unconfined`, `apparmor=unconfined` or `Unconfined` profile type; pods set a `RuntimeDefault` or custom seccomp profile. Owner: `platform`. Source: Docker Security, Kubernetes Security.
- **Writable root filesystem.** Containers run with a read-only root filesystem (`--read-only`, Compose `read_only: true`, `readOnlyRootFilesystem: true`), adding a tmpfs or emptyDir for paths that need temporary writes; volumes used only for reading are mounted read-only. A read-only root does not make other mounts read-only or stop attacks that need no writes.
  Check: containers set `readOnlyRootFilesystem: true` and read-only volume mounts use `:ro` or `readOnly: true`. Owner: `platform`. Source: Docker Security, Kubernetes Security.
- **Pod shares host namespaces or unmasks `/proc`.** Pods avoid sharing the host network, PID or IPC namespace, use the default masked `/proc` mount, and avoid sensitive `hostPath` mounts; NetworkPolicy enforcement for `hostNetwork` pods depends on the network plugin and must be verified, not assumed.
  Check: manifests contain no `hostNetwork`, `hostPID`, `hostIPC`, `procMount: Unmasked` or sensitive `hostPath` outside explicitly privileged system namespaces. Owner: `platform`. Source: Kubernetes Security.
- **Containers can trigger loading of unused kernel modules.** Unprivileged processes can cause network-protocol modules to load just by opening a socket; nodes uninstall or blocklist unneeded modules (for example DCCP and SCTP via a modprobe blacklist file), or use an LSM such as SELinux to deny `module_request` to containers.
  Check: node provisioning includes a module blocklist or LSM rule denying module loading for containers. Owner: `platform`. Source: Kubernetes Security.
- **Untrusted or multi-tenant workloads on the shared kernel.** Highly untrusted or multi-tenant clusters add a sandbox layer between containers and the host kernel (gVisor, Kata Containers, Firecracker) to contain breakout and kernel exploits.
  Check: workloads running untrusted code use a sandboxed RuntimeClass. Owner: `platform`. Source: Kubernetes Security.

## Kubernetes control plane access

- **etcd reachable beyond the API servers.** Write access to etcd is root on the cluster and read access readily escalates, bypassing admission; API servers authenticate to etcd with strong credentials (mutual TLS client certificates), etcd sits behind a firewall that only API servers can cross, and other components use separate etcd instances or ACLs limited to a keyspace subset.
  Check: etcd flags require client certificate auth, and network rules allow etcd ports only from API servers. Owner: `platform`. Source: Kubernetes Security.
- **Cluster users authenticated with built-in mechanisms.** Production clusters use external API authentication (OIDC with short-lived tokens and central groups, the managed provider's IAM, or impersonation through an authenticating proxy) with MFA for all user access; static token files, X.509 client certificates (not revocable without rotating the CA) and ServiceAccount tokens are not used to authenticate people.
  Check: kubeconfigs and API server flags use OIDC or provider IAM for humans; no `--token-auth-file` and no long-lived user client certificates. Owner: `platform`. Source: Kubernetes Security.
- **Authorization not RBAC-based.** The API server authorizes with the Node and RBAC authorizers together with the NodeRestriction admission plugin, deny by default, granting each user and service the least privilege its role needs.
  Check: `--authorization-mode` includes `Node,RBAC`, NodeRestriction is enabled, and RBAC grants avoid wildcards and cluster-admin for workloads. Owner: `platform`. Source: Kubernetes Security.
- **Kubelet API allows anonymous access.** Kubelet HTTPS endpoints give powerful control over the node and its containers and allow unauthenticated access by default; production clusters enable kubelet authentication and authorization.
  Check: kubelet config disables anonymous auth and uses webhook authorization. Owner: `platform`. Source: Kubernetes Security.
- **Control plane and node ports open to the network.** Authentication and authorization are configured on the cluster and nodes, network rules block access to Kubernetes ports (API server 6443, etcd 2379-2380, kubelet 10250, read-only kubelet 10255, scheduler 10259, controller manager 10257, kubelet healthz 10248, kube-proxy 10249 and 10256, NodePorts 30000-32767), and the API server is limited to trusted networks.
  Check: security groups or firewall rules expose none of these ports publicly and restrict the API endpoint to trusted CIDRs. Owner: `cloud`. Source: Kubernetes Security.
- **Dashboard exposed or over-privileged.** The Kubernetes dashboard is never exposed publicly without additional authentication, runs behind an authenticating reverse proxy with MFA using the user's own credentials (OIDC tokens or impersonation) rather than a privileged ServiceAccount, its ServiceAccount has no high privileges and no leftover `cluster-admin` binding, permissions are per user, and network policies can block it even from internal pods.
  Check: the dashboard Service is not a public LoadBalancer or Ingress without auth, and its ServiceAccount binding is minimal. Owner: `platform`. Source: Kubernetes Security.

## Pod security admission and policy

- **Namespaces without Pod Security enforcement.** Pod Security admission enforces at least `baseline` for all pods and strives for `restricted`; namespaces carry the lowest-privilege level that supports their risk (`pod-security.kubernetes.io/enforce`, with `audit` and `warn` to trial a stricter level), and `privileged` is allowed only where absolutely required, such as critical system services needing host access. Pod Security Policies are removed (v1.25) and not relied on.
  Check: every application namespace sets `pod-security.kubernetes.io/enforce` to `baseline` or `restricted`; any `privileged` namespace is justified. Owner: `platform`. Source: Kubernetes Security, Docker Security.
- **No granular policy beyond the built-in levels.** Where finer control is needed, an admission policy engine (Validating Admission Policy, OPA Gatekeeper, Kyverno) enforces rules such as images only from trusted sources, no root, encrypted and retained storage, and limited internet access, and the same policies run early in CI or on developer machines.
  Check: cluster admission policies cover image source, non-root and other org rules, and CI evaluates manifests against them. Owner: `platform`. Source: Kubernetes Security, Docker Security.
- **Shared or auto-mounted ServiceAccount credentials.** Each application has its own ServiceAccount, and containers that do not call the Kubernetes API do not mount ServiceAccount credentials.
  Check: workloads set a dedicated `serviceAccountName` and `automountServiceAccountToken: false` unless they use the API. Owner: `platform`. Source: Kubernetes Security.
- **Container privileges never reassessed.** Capabilities, role bindings and privileges given to containers are continuously assessed against least privilege, and before deployment the system can report what is deployed (image components and vulnerabilities), where (cluster, namespace, node), how (privileged, reachable peers, security context), what it can access (secrets, volumes, host, API) and whether it complies with policy.
  Check: manifests or tooling expose these attributes per workload and policy reports are reviewed. Owner: `platform`. Source: Kubernetes Security.
- **Resources not separated by namespace.** Namespaces partition resources and limit the scope of user permissions.
  Check: workloads of different teams or trust levels live in separate namespaces with namespace-scoped RBAC. Owner: `platform`. Source: Kubernetes Security.

## Network exposure and segmentation

- **Published port bypasses the host firewall.** Docker writes its own iptables or nftables rules that open published ports on all interfaces ahead of host firewall DENY rules (UFW and similar tools are bypassed); bind published ports to `127.0.0.1` when only local access is needed, or use an integration that makes the firewall govern Docker networks, and verify other iptables-based firewalls behave correctly.
  Check: `-p` mappings and Compose `ports:` bind to `127.0.0.1:` unless public exposure is intended. Owner: `platform`. Source: Docker Security.
- **All containers share the default bridge.** Inter-container communication is on by default; define custom networks and attach only the containers that need to talk (more granular than disabling `icc` entirely).
  Check: Compose files define purpose-specific networks rather than relying on the default bridge. Owner: `platform`. Source: Docker Security.
- **Pods not isolated by NetworkPolicy.** Pods are non-isolated for ingress and egress by default, so a compromised application can attack its neighbors; `networking.k8s.io/v1` NetworkPolicies restrict each direction that needs it (an ingress policy does not restrict egress), policies are additive and same-node traffic stays allowed, and the cluster's network plugin must enforce NetworkPolicy or the resources have no effect. Prefer these native controls over third-party proxies or shims.
  Check: each namespace has default-deny ingress and egress policies plus explicit allows, and the CNI supports NetworkPolicy. Owner: `platform`. Source: Kubernetes Security, Docker Security.
- **Allowed traffic never compared with observed traffic.** Active network traffic is observed and compared with what policies allow, and superfluous allowed connections are removed to shrink the attack surface.
  Check: a periodic review tightens NetworkPolicies based on observed flows. Owner: `platform`. Source: Kubernetes Security.
- **Service-to-service traffic unencrypted and unauthenticated.** A service mesh can provide mTLS between services, identity-based authentication and authorization per service, ingress and egress control, and alerts when mTLS status changes, at the cost of added complexity and expertise.
  Check: the platform design states how in-cluster traffic is encrypted and authenticated. Owner: `architect`. Source: Kubernetes Security.

## Secrets in images, containers and clusters

- **Secret passed via `ENV` or `ARG` at build time.** Build arguments and environment values persist in image history and layers, deleting a file in a later layer leaves it in an earlier one, and a secret in the Dockerfile makes the Dockerfile itself secret; build-time secrets (such as a registry `.npmrc`) use build secret mounts (`RUN --mount=type=secret`) in a build stage, and multi-stage builds keep build credentials out of the final image.
  Check: no `ARG` or `ENV` carries a token, password or key, and private-registry auth uses a secret mount in a non-final stage. Owner: `platform`. Source: NodeJS Docker.
- **Build context includes secrets or local artifacts.** A `.dockerignore` excludes credentials and local config (`.env`, cloud credential files, `.npmrc`), `.git`, and local `node_modules` (which may contain modified code), because a wildcard `COPY .` copies everything in the context.
  Check: `.dockerignore` exists and lists these paths whenever the Dockerfile uses `COPY .`. Owner: `platform`. Source: NodeJS Docker.
- **Kubernetes Secret exposed as an environment variable.** Secrets are mounted as read-only volumes rather than environment variables, and kept separate from the image and pod definition so access to the image does not grant the secret.
  Check: manifests mount Secrets as read-only volumes rather than `env.valueFrom.secretKeyRef`, and no secret is baked into the image. Owner: `platform`. Source: Kubernetes Security.
- **Secrets stored unencrypted in etcd.** The API server stores resources unencrypted by default; configure a non-`identity` encryption provider first for Secrets and rewrite existing Secrets so earlier data is encrypted, encrypt etcd backups with a well-reviewed solution, and consider full disk encryption; this does not help if the decryption keys are also obtained.
  Check: the encryption configuration lists a non-identity provider first for `secrets`, with a re-encryption step recorded. Owner: `platform`. Source: Kubernetes Security.
- **Cluster secrets managed only as Kubernetes Secrets.** An external secrets manager can store secrets instead, controlling and rotating them centrally across clusters and clouds; Docker or Swarm secrets are not the recommended pattern for Kubernetes.
  Check: the design states which secret store backs workloads and how rotation happens. Owner: `platform`. Source: Kubernetes Security, Docker Security.
- **Compose file-backed secrets assumed encrypted.** Compose file-backed secrets are bind mounts of host files, so the source files need restrictive permissions and storage encryption; Swarm-managed secrets are transported over mutual TLS and stored in an encrypted Raft log. Secrets are delivered this way rather than through images or run-time command arguments.
  Check: Compose secret source files are outside the repository with restrictive permissions. Owner: `platform`. Source: Docker Security.
- **Secret material in container filesystems unreviewed.** Secret material present in containers is reviewed against least privilege and its compromise risk assessed, and container filesystems and images are scanned for tokens, passwords and keys, which are readable by anyone with access during build, in the registry or backups, or at runtime.
  Check: the image pipeline includes a secret scan of the built image. Owner: `platform`. Source: Kubernetes Security, Docker Security.

## Image build hygiene

- **Base image referenced by mutable tag.** Base images are pinned by digest (keeping the readable tag alongside, `image:tag@sha256:...`) so builds are deterministic, never by bare name or `latest`.
  Check: every `FROM` line carries an `@sha256:` digest. Owner: `platform`. Source: NodeJS Docker, Docker Security.
- **Full OS base image with shells and package managers.** Images are minimal (small official variants, distroless, or `scratch` for static binaries); if those are impossible, OS package managers and shells are not left in the image (remove the package manager in a later build step); images are built from approved, secure base images that are scanned and monitored regularly.
  Check: the final stage uses a minimal or distroless base and contains no package manager or shell where avoidable. Owner: `platform`. Source: Kubernetes Security, NodeJS Docker.
- **Single-stage build ships toolchain and dev dependencies.** Multi-stage builds install and compile in a build stage and copy only runtime artifacts into a small final image; production images install only production dependencies deterministically (for npm, `npm ci --omit=dev`) and set the runtime to production mode (for Node.js, `NODE_ENV=production`), which some frameworks need to enable security and performance settings.
  Check: the Dockerfile is multi-stage, the final install omits dev dependencies, and the production environment flag is set. Owner: `platform`. Source: NodeJS Docker.
- **Dockerfile anti-patterns unlinted.** A Dockerfile linter in CI checks for a `USER` directive, pinned base image and OS package versions, `COPY` instead of `ADD`, and no `curl | bash` in `RUN`.
  Check: CI runs a Dockerfile linter and the Dockerfile pins OS package versions and avoids `ADD` and piped remote scripts. Owner: `platform`. Source: Docker Security.
- **Images and bundled tools left stale.** Images and the third-party tools they include are kept up to date with current component versions.
  Check: base image digests and bundled tool versions are refreshed by automated updates. Owner: `platform`. Source: Kubernetes Security.

## Image supply chain and admission

- **Images pushed and deployed without a scan gate.** A CI pipeline scans every built image for vulnerabilities, secrets and misconfigurations; a failed assessment fails the pipeline, and only images that pass are pushed to the private registry and deployed.
  Check: the image job runs a scanner before push and blocks on findings above the agreed threshold. Owner: `platform`. Source: Kubernetes Security, Docker Security.
- **Images pulled from arbitrary registries.** Only images adhering to organization policy run: approved images are stored in a private registry with strict access controls and metadata, and admission (ImagePolicyWebhook or a policy engine) rejects images not recently scanned, built on a base image not explicitly allowed, or from insecure registries.
  Check: an admission policy restricts image registries and base images, and manifests reference only the private registry. Owner: `platform`. Source: Kubernetes Security, Docker Security.
- **Images unsigned, without SBOM or provenance.** Images are signed and signatures verified at deployment (Notary, Cosign), each image has an SBOM and documented provenance, and these are stored with the image in a trusted registry; secure deployment policies validate images before they run.
  Check: the image pipeline signs images and attaches SBOM and provenance, and admission verifies signatures. Owner: `platform`. Source: Docker Security, Kubernetes Security.
- **Running images not rescanned.** First-party and third-party images in production are scanned regularly for newly disclosed CVEs, and base images and dependencies are monitored continuously.
  Check: a scheduled scan covers images currently deployed, not only new builds. Owner: `platform`. Source: Kubernetes Security.
- **Running containers patched in place.** When a running container is vulnerable, the source image is updated and redeployed (for example through rolling updates) rather than updating the running container, which breaks the image-container relationship.
  Check: remediation goes through image rebuild and redeploy; no runbook step patches live containers. Owner: `platform`. Source: Kubernetes Security.
- See `supply-chain-and-dependencies.md` for SBOM content, attestation binding and provenance verification rules, and `ci-cd.md` for pipeline hardening.

## Resource limits

- **Container without resource limits.** Limiting resources is the main container-level DoS defense: memory, CPU, a maximum restart count (`--restart=on-failure:<n>`), file descriptors (`--ulimit nofile`) and processes (`--ulimit nproc`), and in Kubernetes memory and CPU requests and limits on every container.
  Check: every container spec sets memory and CPU limits; run and Compose configs set restart and ulimit bounds. Owner: `platform`. Source: Docker Security.
- **Namespace without quotas or defaults.** A `ResourceQuota` caps aggregate requests, limits and object counts per namespace to contain cross-tenant exhaustion, and a `LimitRange` supplies per-pod and per-container defaults and minimum and maximum allocations, which quotas do not provide.
  Check: each application namespace has both a ResourceQuota and a LimitRange. Owner: `platform`. Source: Kubernetes Security.

## Runtime detection and response

- **No runtime threat detection.** Runtime monitoring (syscall- or eBPF-based) watches process activity and network communications between services and with external endpoints, alerting on a shell run inside a container, a sensitive host path such as `/proc` mounted, unexpected reads of files such as `/etc/shadow`, unexpected exec calls, privilege escalation attempts and new outbound connections.
  Check: a runtime detection agent is deployed cluster-wide with rules for these events. Owner: `sre`. Source: Kubernetes Security, Docker Security.
- **Replica divergence and alert routing missing.** Replicas of a deployment should behave nearly identically, so significant deviation is investigated; security tooling integrates with paging, chat and SIEM and uses deployment labels or annotations to route alerts to the owning team, and remediation is prioritized with Kubernetes context (a severe vulnerability in an internet-exposed privileged deployment outranks one in a non-critical test environment).
  Check: workloads carry ownership labels used by alert routing. Owner: `sre`. Source: Kubernetes Security.
- **No containment step for a breached pod.** A breach is contained with native controls: scale suspicious pods to zero, or kill and restart breached instances.
  Check: the incident runbook includes scale-to-zero and restart steps. Owner: `sre`. Source: Kubernetes Security.
- **Long-lived infrastructure credentials.** Certificates have short lifetimes with automated rotation, the authentication provider issues short-lived tokens, ServiceAccount tokens used in external integrations are rotated frequently, and bootstrap tokens are revoked or de-authorized once node bootstrap completes.
  Check: no non-expiring ServiceAccount token Secrets exist for integrations and bootstrap tokens have expiry. Owner: `platform`. Source: Kubernetes Security.

## Audit logging and update cadence

- **API audit logging disabled.** Audit logging is enabled with an `--audit-policy-file` containing at least one rule (without the flag nothing is logged; an empty rule list is invalid), audit files are archived on a secure server, and monitoring alerts on anomalous or unwanted API calls, especially authorization failures (`Forbidden`), which may indicate stolen credentials.
  Check: API server flags set an audit policy and log destination, and an alert exists on Forbidden responses. Owner: `platform`. Source: Kubernetes Security.
- **Docker daemon at debug log level.** Keep the daemon at log level `info` (the default) so security-relevant events are captured, and do not run it at `debug` unless required.
  Check: `daemon.json` `log-level` and daemon flags are `info` or unset. Owner: `platform`. Source: Docker Security.
- **Cluster on an unsupported Kubernetes version.** Run the latest stable Kubernetes within the three most recent minor releases that receive security backports, follow the version skew policy, upgrade with rolling updates or node-pool migration, and subscribe to the security announcement list.
  Check: cluster version config pins a currently supported minor release. Owner: `platform`. Source: Kubernetes Security.
- **Security started late in the container lifecycle.** Security is integrated as early as possible in the container lifecycle with goals shared between security and DevOps teams.
  Check: image and manifest policies run in CI, not only at admission. Owner: `platform`. Source: Kubernetes Security.

## Process lifecycle in containers

- **Application started through a wrapper or shell form.** Package-manager wrappers (`npm start`) and shell-form `CMD` do not forward signals, so the application never receives `SIGTERM`; start the runtime directly with exec-form `CMD [...]`, and because some runtimes (Node.js) mishandle signals as PID 1, run a minimal init (for example `dumb-init`) as PID 1 that proxies signals.
  Check: the final `CMD` or `ENTRYPOINT` is exec-form, invokes the runtime directly, and is wrapped by a minimal init where the runtime needs one. Owner: `platform`. Source: NodeJS Docker.
- **No graceful shutdown on termination signals.** The application handles `SIGINT` and `SIGTERM` by stopping new connections (responding `503`), finishing in-flight requests and closing resources such as database connections before exiting, so orchestrated scale-downs do not cut off users.
  Check: the server entry point registers termination handlers that close the server and dependencies. Owner: `backend`. Source: NodeJS Docker.
