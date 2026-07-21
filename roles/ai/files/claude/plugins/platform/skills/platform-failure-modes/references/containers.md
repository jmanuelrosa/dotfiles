# Containers

When to read: the brief or diff touches Dockerfiles, base images, compose files, `.dockerignore`, or dev containers.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Floating base image.** A base on `latest` or a major-only tag re-resolves at every build; two builds of the same commit produce different images.
  Check: bases are pinned to a digest, or at minimum a full version tag, and upgrades are explicit diffs.
- **Toolchain shipped to production.** A single-stage build carries compilers, package managers, and source into the runtime image: attack surface and size nobody ordered.
  Check: builds are multi-stage; the final stage copies only runtime artifacts.
- **Root by default.** A container running as root turns any process compromise plus one runtime bug into a host compromise.
  Check: the final stage sets a non-root user; paths that must be writable are made so explicitly.
- **Unpinned packages inside the image.** OS or language packages installed without versions re-resolve per build, breaking reproducibility invisibly.
  Check: packages are version-pinned or resolved from a lockfile committed to the repo.
- **Layer order fighting the cache.** Copying the whole tree before installing dependencies invalidates the dependency layer on every source change.
  Check: dependency manifests are copied and installed before source; the expensive layers change least often.
- **Context leaking into the image.** A missing or stale `.dockerignore` ships VCS metadata, env files, and local artifacts into the build context: slow builds and accidental secrets.
  Check: the context is enumerated; secrets, VCS metadata, and build output are excluded.
- **Build secrets baked into layers.** A secret passed as a build argument or environment variable, or copied then deleted, persists in layer history for anyone who pulls the image.
  Check: secrets enter builds only through the builder's secret mechanism and appear in no layer.
- **Masked failures in build steps.** A piped command in a build step reports only the last command's status; a failed download piped onward builds a broken image marked success.
  Check: build steps that pipe set explicit pipefail semantics or drop the pipe; remote scripts are never piped straight into a shell.
- **Entrypoint that swallows signals.** Wrapping the process in a shell means termination signals never reach it; every shutdown becomes a timeout and a kill.
  Check: the entrypoint runs the process directly (exec form, or a script that execs it) so it receives signals and exits cleanly.
- **Compose drifting from CI.** A dev compose setup running different images, versions, or environment than the pipeline builds produces works-locally-fails-in-CI, and the reverse.
  Check: compose references the same Dockerfile and pinned bases the pipeline builds; every deliberate difference is written down.

## Escalation triggers (`needs-decision`)

- Adding a new base image or switching to a different one (also an ask-first boundary in the agent); pinned-version upgrades of the same base stay implementation.
- An image change that alters the runtime user, exposed ports, or entrypoint contract consumers depend on.

## What good looks like

- Same commit, same image: every input pinned, every build reproducible.
- The final image is minimal, non-root, and holds nothing but the runtime.
- Dev compose mirrors what CI builds closely enough that "works locally" means something.
