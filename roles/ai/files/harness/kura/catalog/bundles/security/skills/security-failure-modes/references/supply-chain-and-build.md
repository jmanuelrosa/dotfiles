# Supply chain and build

When to read: the assessed surface includes dependency manifests and lockfiles, install scripts, CI workflows, base images, or release pipelines; fires in any whole-repo assessment.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **The CVE asserted from memory.** Training data is stale; naming a vulnerability the lockfile already patched destroys the report's credibility (also a hard rule).
  Check: every vulnerability claim is checked against the exact version the lockfile resolves, and the advisory itself is fetched when the version matters; a claim you could not verify is not a finding.
- **Auditing the manifest instead of the lockfile.** Version ranges describe intent; the lockfile describes what installs.
  Check: reasoning and scanner runs target lockfile-resolved versions; a missing lockfile, or one drifted from the manifest, is itself a finding.
- **Install-time code unreviewed.** Dependency lifecycle scripts run arbitrary code on every developer machine and CI runner at install time; recent worm campaigns spread exactly this way.
  Check: enumerate lifecycle scripts across the dependency tree from the lockfile and metadata, note whether installs run with scripts disabled, and treat unreviewed install scripts in direct dependencies as findings.
- **Mutable references in the build.** CI steps pinned to tags, base images on floating tags, and curl-piped installers re-resolve to whatever the upstream says today (the OpenSSF Scorecard Pinned-Dependencies check, unmet).
  Check: read the CI and container files: every third-party reference resolves to an immutable identifier (commit SHA, digest); list each mutable one.
- **Typosquat adjacency unexamined.** Lookalike names and near-forks of popular packages arrive through one hurried install.
  Check: scan direct dependency names for lookalikes of well-known packages and for low-adoption packages holding privileged positions; verify the intended upstream (repository link, publisher) for anything odd.
- **The dev-dependency blind spot.** Compromise arrives through dev tooling and CI as easily as through production dependencies, with the same reach into secrets and artifacts.
  Check: the install-script and pinning checks above cover dev dependencies and CI tooling, not just the production tree.
- **Releases without provenance.** Artifacts nobody can trace to source and build instructions cannot be trusted or recalled (the gap SLSA build levels describe).
  Check: read the release pipeline: whether artifacts are built on a hosted builder from tagged source and signed or attested; gaps are hardening findings routed to the platform seat.
- **Abandonware in a sensitive position.** An unmaintained or single-maintainer package doing auth, crypto, or parsing is a patch that will never come.
  Check: for dependencies on security-critical paths, read the maintenance signals already available (archived status, last release in the lockfile metadata, deprecation notices) and flag sensitive-position abandonware.
- **Vendored code invisible to scanners.** Copied-in libraries and snippets receive no advisories and no updates.
  Check: locate vendored or copied third-party code and confirm its provenance and update story are recorded; absence is a finding.

## Escalation triggers (report immediately)

- A dependency at a version named in a known, active supply-chain compromise, verified against the advisory rather than memory: treat the environment as potentially compromised now; lead the report with it.
- A lifecycle script in the tree that fetches and executes remote code at install time: same treatment.

## What good looks like

- The lockfile is authoritative, installs run with scripts disabled or reviewed, and every third-party reference in build and CI is pinned to an immutable identifier.
- Releases carry provenance someone outside the team could verify.
- Every dependency claim in the report names the installed version and the advisory it was checked against.
