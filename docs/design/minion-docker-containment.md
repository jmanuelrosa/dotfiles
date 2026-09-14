# Docker containment for Minion, Design Doc

**Status:** Superseded for V1 by [the trusted-session specification](../specs/minion.md); retained as the rejected stronger-containment alternative

The user reconsidered this design after returning to the Theo workflow that motivated Minion.
V1 now accepts the same trust and residual process risk as a manually run Pi session, so none of the Docker image or containment work below is scheduled for implementation.
**Author:** José Manuel Rosa Moncayo
**Date:** 2026-09-13
**Scope:** Minion worker tools, Docker lifecycle, candidate transfer, recovery, and publication boundaries

## Summary

Minion V1 will preserve the approved cancellation guarantee by putting every mission-controlled filesystem operation and command process inside one Docker container per mission.
The Pi SDK model session and durable supervisor remain on the host, but the session receives only Minion-owned tool implementations whose effects are brokered into that container.
The worker container never receives the Docker socket, model credentials, host agent directories, Git credentials, or a writable mount of the human checkout.

The clean human checkout is the approved source and eventual publication target.
It is mounted read-only only long enough to seed a mission workspace held in a Docker volume.
A candidate returns to the host only after the container is stopped, Docker confirms it is not running, and the supervisor validates a complete filesystem manifest against the recorded baseline.

This changes the original direct-current-checkout execution design.
The checkout still has an exclusive mission lease and supplies the exact base, but autonomous writes happen in the isolated workspace and are imported at quiescent checkpoints.
No Git worktree is introduced.

V1 initially supports Linux-compatible missions whose declared checks can run without container network access.
A mission requiring macOS behavior, direct hardware access, private dependency credentials, SSH, Docker-in-Docker, or unrestricted network access is refused.

## Decision context

The guarded-runtime diagnostics established two independent failures:

- SDK abort and prompt settlement stop same-process-group work but do not stop a writer that detached into another process group.
- A normal writable project directory allowed an agent to modify or create `.pi/sandbox.json` until a Minion-only `denyWrite` covered the project `.pi` path.

The second failure now has a positive candidate boundary for the tested operations.
All seven normal-terminal project-policy cases completed their positive controls, denied the policy attempt, and left the target unchanged.
The first failure cannot be repaired by another process-group signal.
The installed `launchd.plist` documentation states that launchd cleanup kills remaining processes with the job's process group ID, which is the boundary the detached diagnostic escaped.

The user chose Docker-contained V1 rather than weakening cancellation semantics or adding a macOS VM dependency.
Docker, Colima, and Lima CLIs are present on this machine; that is local implementation evidence, not a portable prerequisite guarantee.

## Goals

- Make every process that can alter mission work a member of one destroyable Docker container.
- Keep model and publication credentials on the host and out of the worker container.
- Prevent mission work from writing the human checkout, project `.pi`, Pi agent files, or durable mission authority until a stopped candidate is validated and imported.
- Preserve exact candidate identity across container verification, host import, commit, and PR creation.
- Reconcile supervisor crashes and Docker uncertainty without starting duplicate containers or repeating publication.
- Refuse unsupported environments and permissions rather than silently falling back to host execution.

## Non-goals

- Running macOS-only builds or tests in a Linux container.
- Mounting the human checkout read-write into the worker container.
- Giving the container Docker, Git forge, cloud, SSH, or model-provider credentials.
- Supporting package downloads or arbitrary egress in the first contained slice.
- Docker-in-Docker, privileged containers, host PID or IPC namespaces, device passthrough, or a mounted Docker socket.
- Replacing the host's existing commit and PR skills.
- Claiming that containers eliminate kernel or hypervisor vulnerabilities.
- Automatically restarting a mission after a host reboot, Docker daemon restart, or Colima restart.

## Architecture

### Host control plane

The detached delivery supervisor remains the mission authority on the host.
It owns durable records, approval, budgets, the checkout lease, the Pi SDK sessions, Docker lifecycle, candidate validation, evaluation, and publication.
The authoritative mission directory remains outside the repository and is never mounted into a container.

Provider calls remain on the host so model credentials do not cross the container boundary.
Only an untouched Pi built-in provider path is eligible.
The existing diagnostic continues to refuse `cursor-sdk`, config-registered providers, complete native extension providers, model fallback, and provider changes during startup.

The host session starts with Pi built-ins disabled and project extensions undiscovered.
It activates only Minion-owned `read`, `write`, `edit`, `bash`, `grep`, `find`, and `ls` implementations after verifying each tool's source provenance.
Those implementations preserve Pi's normal tool names so the sandbox, permission system, and guardrail hooks still receive `tool_call` events.
They invoke Docker with an argument array, never by interpolating model input into a host shell command.

No worker-controlled input can select a container name, Docker context, mount, image, entrypoint, user, capability, network, label, or resource limit.
Those values come from the approved mission and supervisor state.

### Worker data plane

One container and one workspace volume belong to one mission.
Their names are deterministic from the stable mission ID, and reverse-DNS labels record the mission ID, operation ID, approved mission hash, and supervisor schema version.
The durable launch intent is written before `docker create`.
The returned container ID and inspected configuration are durably recorded before `docker start`.

The container runs a trusted, immutable command broker as its long-lived process.
The broker accepts only supervisor-authenticated local requests through Docker exec and launches all requested commands inside the container.
It also owns an independent cumulative active-time deadline so a dead host supervisor cannot leave a mission running beyond its approved time.
The broker and deadline code come from the approved image, not from the writable workspace.

Every file helper and shell command runs inside the same container and workspace.
A shell command may create a new session or process group, but it remains inside the container's PID and mount namespaces.
Cancellation is not complete until Docker reports the container stopped.
The adversarial validation must prove that a detached writer cannot produce another workspace write after that confirmation.

### Filesystem layout

The human checkout is never mounted read-write.
The container receives:

| Container path | Source | Access |
|---|---|---|
| `/source` | Canonical clean host checkout | Read-only during workspace seeding |
| `/workspace` | Mission-owned Docker volume | Read-write |
| `/mission` | Non-secret approved work packet | Read-only |
| `/tmp` and required runtime scratch paths | Container tmpfs | Read-write, bounded |
| Image root filesystem | Approved image | Read-only |

No home directory, Pi agent directory, Docker configuration, Docker socket, SSH directory, Git credential store, cloud credential store, or host temporary directory is mounted.
The work packet contains the approved mission hash, criteria, non-goals, allowed relative paths, declared checks, and resource limits, but no durable authority record or credential.

Workspace seeding copies the clean source tree into the volume without trusting container Git metadata as authority.
The host records a baseline manifest before launch.
That manifest includes normalized relative path, file type, executable bit, byte length, and content digest for every admitted entry.
It rejects absolute paths, parent traversal, case-colliding paths, device nodes, sockets, FIFOs, escaping symlinks, and repository entries the V1 importer cannot reproduce safely.

`.git`, `.pi`, and Minion control paths are not candidate output surfaces.
The worker may read the approved source representation it needs, but the importer refuses any candidate entry under those paths.
A mission whose acceptance criteria require changing them is unsupported by this V1 boundary.

### Container hardening contract

The created container must satisfy all of these properties before it can start:

- The image is named by an explicitly approved immutable digest.
- The image build inputs and package versions are pinned and contain no checkout, credential, or build secret.
- The runtime user is non-root and matches the workspace ownership contract.
- The root filesystem is read-only, with explicit bounded tmpfs mounts for scratch paths.
- All Linux capabilities are dropped.
- New privileges are disabled.
- Privileged mode, devices, host PID, host IPC, and host networking are absent.
- The Docker socket and every other daemon control socket are absent.
- PID, memory, CPU, file-descriptor, and writable-scratch limits equal the approved mission values.
- Init and an exec-form entrypoint preserve signal delivery and reap children.
- Restart policy is `no`.
- Automatic removal is disabled so crash recovery can inspect the same container and logs.
- Container network access is disabled for the first contained slice.

The supervisor verifies the effective values through Docker inspect after creation.
A requested flag and an observed container setting are separate evidence.
Any mismatch causes deletion of the never-started container and a launch refusal.

The approved Docker direction authorizes Docker as the containment dependency.
The user separately approved official `node:26.8.2-bookworm-slim` with no added OS packages for the containment-validation image.
Its exact Linux arm64 digest must be resolved and recorded before any build or run.
Later mission toolchain images remain separate ask-first dependency decisions.

### Tool execution contract

The host-side tool broker maps one Pi tool call to one Docker operation and one journal operation ID.
File-tool arguments remain structured through the boundary.
Only the `bash` tool passes a command string to a shell, and that shell exists inside the container.

The broker records tool name, normalized input identity, container ID, exec identity when available, start and finish times, exit status, output hash, truncation metadata, and cancellation result.
Tool output follows Pi's existing line and byte limits, with the complete output stored in non-authoritative mission evidence outside the model context.

The active-tool preflight requires:

- The exact approved tool-name set, with no additional built-in, extension, MCP, subagent, or provider-host tool.
- Minion-owned source provenance for each active implementation.
- Successful sandbox, permission, and guardrail startup.
- A provider-path classification eligible for Pi-mediated tools.
- No project extension discovery and no dynamic provider registration.

A tool-set change, extension reload, provider change, or model fallback invalidates the session and blocks further work.

### Network and credentials

Model-provider traffic stays in the host Pi SDK session and uses its existing credential resolution.
Credential values are never written into mission records, Docker labels, image layers, container environment, workspace files, or tool output.

The worker container starts with no network.
The first implementation slice therefore supports only repositories whose source, toolchain, dependencies, and mandatory checks are already present in the approved image or workspace inputs.
A missing dependency is a blocker, not permission to mount host caches or enable egress.

Future public dependency access requires a separate approved egress design with domain enforcement and no direct route around it.
Private registries, SSH, cloud credentials, browser sessions, and Docker socket access remain out of scope unless separately specified and approved.

### Candidate quiescence and transfer

Docker pause is not a quiescence boundary.
The supervisor quiesces a candidate by stopping the container, escalating to kill after the approved grace period, waiting for Docker completion, and inspecting the container state as not running.
If the daemon is unavailable or the state cannot be confirmed, the mission remains visibly `stopping` or `interrupted` and no candidate is imported.

Only a confirmed-stopped container can be exported.
The supervisor reads the workspace through a daemon-mediated copy from the stopped container and validates a complete candidate manifest before touching the human checkout.
It does not execute candidate code during import.

The importer compares the candidate with the recorded baseline and enforces:

- Every changed, added, and deleted path is normalized and inside the approved mission scope.
- No protected or unsupported path appears.
- File types, modes, sizes, counts, symlinks, and digests are representable and within approved limits.
- The leased host checkout still matches its launch identity and baseline.
- The exported manifest hash matches the bytes applied to the host.

Import uses direct host filesystem operations without invoking repository hooks or candidate scripts.
After import, the supervisor recomputes the host candidate identity.
Container verification evidence remains applicable only when its input manifest equals the imported host manifest and its declared Linux environment satisfies the mission check.
Any host difference invalidates that evidence.

A later repair increment starts from a newly recorded baseline or reseeds a fresh contained workspace from the exact imported candidate.
A stopped container is never restarted after its candidate has been imported without a new operation and identity check.

### Cancellation and deadlines

Cancellation performs these steps:

1. Stop admitting work and durably record the cancellation intent.
2. Abort the host Pi session so it cannot issue another tool call.
3. Request graceful container stop with the approved timeout.
4. If still running, issue Docker kill.
5. Wait and inspect until Docker reports the container not running.
6. Preserve the stopped container, volume, candidate metadata, and logs for inspection.
7. Record `cancelled` only after the stopped-state evidence is durable.

A Docker command failure is not proof that the requested state change failed or succeeded.
The supervisor reconciles by deterministic name, recorded ID, labels, and inspect state before retrying.
More than one matching container, changed labels, or an unexpected image or mount set is a blocker.

The internal broker deadline is independent of the host supervisor.
Its expiry terminates the container process, after which recovery confirms the stopped state.
Cumulative time accounting conservatively charges any interval whose end was not durably recorded until Docker evidence establishes the container stopped.

### Supervisor death and recovery

Restart policy `no` prevents Docker from treating Minion as a service to restart automatically.
The container may continue after an unexpected host-supervisor crash, but it can write only its mission volume and remains discoverable by deterministic identity and labels.
The independent broker deadline bounds that interval.

On supervisor restart:

1. Load the durable launch or execution intent.
2. Query the configured local Docker daemon by exact container name and mission labels.
3. Reject zero, duplicate, or mismatched identities as an interrupted-state reconciliation problem.
4. Inspect running state, image digest, mounts, security settings, and workspace volume identity.
5. Stop admission and either reattach supervision within the original budget or stop the container according to the recorded recovery policy.
6. Recompute cumulative active time and candidate identity before any resume.

A Docker daemon or Colima restart never resumes mission work automatically.
Explicit `/minion resume` is still required after reconciliation.

### Publication

Worker tools cannot commit, push, create a PR, or reach forge credentials.
The supervisor imports the stopped, verified candidate into the clean leased host checkout and checks byte-for-byte identity first.

Commit and PR creation then run on the host through the existing required skills.
Publication receives the accepted candidate hash and refuses if the host checkout changes.
The container remains stopped throughout publication.
A publication crash is reconciled from Git and forge state as already required by the main Minion specification.

## Preflight refusal conditions

Launch refuses when any of these is true:

- Docker is missing, the daemon is unavailable, or the selected context does not resolve to an approved local Unix socket.
- The effective daemon is remote, uses an unapproved platform, or cannot report the required security settings.
- The approved image digest is absent and pulling or building it was not explicitly authorized.
- Image provenance, runtime user, entrypoint, or pinned inputs do not match the approved image record.
- The repository is dirty, has an unresolved Git operation, changed since approval, or cannot acquire its exclusive lease.
- The source tree contains path or file types the importer cannot represent safely.
- The mission or a mandatory check requires macOS, hardware, GUI, private credentials, SSH, Docker, or network access inside the worker.
- Provider path, model identity, tool provenance, guard startup, or active tools do not match the approval.
- A container or volume with the deterministic identity exists but cannot be reconciled exactly.
- Requested resource limits cannot be represented and verified by the daemon.
- A protected path, authority store, credential path, Docker socket, or writable host checkout would be mounted.

## Failure states

| Observation | Mission state |
|---|---|
| Create outcome uncertain | `interrupted`, reconcile deterministic name and labels |
| Start outcome uncertain | `interrupted`, inspect before any retry |
| Docker unavailable during work | `interrupted`, no host fallback |
| Stop or kill unconfirmed | `stopping`, never `cancelled` |
| Container stopped with nonzero command | Worker failure evidence, not containment failure by itself |
| Container identity or config drift | `blocked` |
| Candidate manifest invalid | `blocked`, preserve volume and evidence |
| Host checkout changed before import | `blocked`, do not overwrite |
| Mandatory check requires unsupported environment | `blocked` |
| Budget expires | Stop container, confirm stopped, then `budget-exhausted` |

## Validation sequence

No delivery-loop implementation begins until the first four slices pass.

### Slice 1: Docker capability and identity probe

Owner: platform staff engineer.

- Resolve the approved local Docker endpoint without reading broad Docker credentials into model context.
- Create a labelled, restart-disabled disposable container from the approved image digest.
- Inspect and compare every hardening property before start.
- Prove create/start/inspect/wait/stop/kill reconciliation with fake mission records.

Gate: no started container may have an unverified image, mount, namespace, capability, user, network, restart, or resource setting.

### Slice 2: Detached descendant containment

Owner: platform staff engineer.

- Launch ordinary and detached writers inside the same mission container.
- Kill the host-side Docker CLI and the synthetic supervisor separately.
- Exercise graceful stop, forced kill, internal deadline expiry, and daemon-command uncertainty.
- Confirm Docker reports stopped and prove no subsequent workspace writes occur.
- Preserve raw timing, container state, and cleanup evidence separately.

Gate: all writer modes stop at the container boundary, including after supervisor death, or Docker containment is rejected.

### Slice 3: Filesystem and authority boundary

Owner: platform staff engineer.

- Prove the host checkout and source mount remain unchanged under file, shell, rename, symlink, hard-link, and directory-replacement attempts.
- Prove `.git`, `.pi`, mission authority, credentials, Docker socket, and host temporary paths are absent or read-only as specified.
- Prove the mission volume is writable and survives a stopped container for inspection.
- Verify rootfs and tmpfs behavior under the non-root runtime user.

Gate: candidate work can change only the mission volume.

### Slice 4: Tool mediation

Owner: platform staff engineer.

- Register only Minion-owned tool implementations and assert source provenance from Pi's tool registry.
- Drive deterministic model tool calls through `session.prompt()` into Docker.
- Reject hidden built-ins, extra tools, project extensions, provider changes, custom providers, and host-tool providers.
- Abort during every tool kind and reconcile its container operation.

Gate: no model-selected operation can execute directly on the host.

### Slice 5: Candidate export and import

Owner: DX staff engineer.

- Build baseline and candidate manifests with adversarial path and file-type fixtures.
- Export only from a confirmed-stopped container.
- Reject traversal, case collisions, protected paths, escaping links, special files, oversized candidates, and host drift.
- Apply accepted bytes to a disposable host checkout and prove exact manifest identity.

Gate: untrusted container output cannot select or alter a host path outside the approved candidate.

### Slice 6: Durable recovery and budgets

Owner: DX staff engineer.

- Journal Docker intents and results around every uncertain operation.
- Reconcile supervisor crash points before and after create, start, exec, stop, kill, export, import, and removal.
- Preserve cumulative time and usage without reset.
- Require explicit resume after daemon or machine interruption.

Gate: restart neither duplicates work nor loses a running container identity.

### Slice 7: One contained delivery increment

Owners: DX staff engineer for the delivery loop, platform staff engineer for the container adapter, parent session for integration.

- Seed one approved Linux-compatible mission.
- Run one worker increment, contained verification, candidate evaluation, stop, export, and exact host import.
- Keep publication disabled.
- Reject stale or fabricated evidence and any candidate mismatch.

Gate: the imported candidate and its evidence are exact, while no process remains able to alter either.

Publication, bounded delegation, Pi controls, and representative missions remain later increments from the main specification.

## Required adversarial tests

- A writer that calls `setsid`, ignores termination, closes inherited descriptors, and continues writing cannot write after confirmed container stop.
- Killing the supervisor before it records create/start/stop results leaves one reconcilable labelled container, never an untracked host writer.
- Killing the Docker CLI does not cause an operation to be blindly repeated.
- A workspace payload cannot reach the Docker socket, host checkout, mission authority, agent configuration, credentials, or host network.
- A candidate tar entry cannot escape through absolute paths, parent traversal, Unicode or case collision, symlink, hard link, device, FIFO, or socket.
- A project `.pi` override cannot disable the host guards or become candidate output.
- A provider alias or custom provider cannot restore host tools.
- A tool override with the expected name but wrong source provenance refuses startup.
- Container pause, a settled prompt, a dead Docker CLI, and a successful stop command are not accepted as stopped-state evidence.
- No publication begins while the container is running or while host and container candidate manifests differ.

## Alternatives considered

### Writable host checkout bind mount

Rejected.
A detached writer would retain direct access to the human checkout until Docker stop completed, and a mount mistake could expose `.git` or `.pi` despite the policy layer.
A mission volume plus validated import gives the container no host path to corrupt.

### Model session inside the container

Rejected for V1.
It would require moving provider credentials, Pi runtime state, skills, and enforcement configuration into the data plane whose compromise the boundary is meant to contain.
Keeping reasoning on the host and brokering only tools minimizes secrets and image complexity.

### Host-native launchd supervision

Rejected.
The documented cleanup boundary is the job's process group, while the diagnostic writer survived in a different process group.

### macOS VM

Deferred.
It can preserve macOS execution fidelity but adds an uninstalled runtime, image lifecycle, heavier provisioning, and a larger synchronization surface.
Docker V1 refuses missions that need that fidelity.

### Weaker quarantine semantics

Rejected by the user.
The approved cancellation contract remains strict: cancellation is not complete while mission work can still write.

## Open decisions and implementation blockers

- Resolve and record the exact Linux arm64 digest for the approved `node:26.8.2-bookworm-slim` tag.
- Define later mission toolchain images without turning them into an unpinned general workstation; the containment-validation image adds no OS packages.
- Validate Docker Desktop and Colima behavior for stopped-container export, init, resource limits, read-only mounts, and whole-container termination.
- Decide retention and explicit cleanup policy for stopped containers, volumes, and full logs after success, cancellation, and blockers.
- Design public dependency egress separately if offline-only missions are too narrow after the containment slices pass.

Until these decisions and validation gates pass, the existing runtime probe remains diagnostic-only and Minion cannot launch autonomous work.

## Sources and checklist decisions

Docker's current documentation supports read-only root filesystems, tmpfs scratch, non-root users, dropped capabilities, no-new-privileges, PID and memory limits, and forced `SIGKILL` after a bounded stop timeout.
It also warns that bind mounts write directly to the host and that recursive read-only behavior depends on engine and kernel support, which is why this design avoids a writable checkout bind and requires inspect plus runtime tests rather than trusting requested flags.

The platform container checklist asks for a pinned base, non-root final runtime, pinned packages, a small build context, no baked secrets, and an exec-form entrypoint.
The Docker direction and Node 26 slim validation base are approved, but the checklist's immutable-digest gate remains unsatisfied until the Linux arm64 manifest is verified and recorded.
