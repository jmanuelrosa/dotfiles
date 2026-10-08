# Supply Chain and Dependencies

When to read: the brief, diff, or assessed surface touches dependency manifests or lockfiles, `.npmrc` or other package-manager config, registries, mirrors or private feeds, install scripts, adding or upgrading a dependency, package publishing or registry tokens, SBOM, provenance, signing or attestation of release artifacts, vulnerability scanning results, CVE triage, suppressions, backports or patched forks of a dependency.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Software Supply Chain Security](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html), [Vulnerable Dependency Management](https://cheatsheetseries.owasp.org/cheatsheets/Vulnerable_Dependency_Management_Cheat_Sheet.html), [Dependency Graph and SBOM](https://cheatsheetseries.owasp.org/cheatsheets/Dependency_Graph_SBOM_Cheat_Sheet.html), [NPM Security](https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html), [CI/CD Security](https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html)

## Contents

- Dependency resolution and integrity
- Install-time code execution
- Choosing and adopting dependencies
- Publishing packages
- Signing, provenance and release evidence
- SBOM and dependency graph
- Vulnerability detection and monitoring
- Remediating a vulnerable dependency
- Source and developer environment

## Dependency resolution and integrity

- **Lockfile not enforced at install.** When the manifest and lockfile disagree, a plain install silently resolves different versions than were recorded; builds and production installs use the lockfile-enforcing mode (`npm ci`, `yarn install --frozen-lockfile`) so any inconsistency aborts the install.
  Check: CI, Dockerfiles and deploy scripts use the frozen-lockfile install command, never a plain `install`; fix by switching the command. Owner: `platform`. Source: NPM Security, CI/CD.
- **Dependency versions not pinned or not hash-verified.** Dependency references are immutable: versions are pinned to ones verified as legitimate and secure, and every downloaded package is checked against a known-good hash, normally through the lockfile, so a compromised or vulnerable version is not pulled in unnoticed.
  Check: a lockfile with integrity hashes is committed and changes with every manifest change; a manifest change without the lockfile is rejected. Owner: `dx`. Source: Software Supply Chain, CI/CD.
- **Internal package names resolvable from the public registry.** Dependency confusion lets a public package with an internal name and a higher version win resolution; internal packages use scoped names (`@org/name`, NuGet ID prefixes or the platform equivalent), the scope is mapped to the private registry in the package-manager config (for example `@org:registry=<private URL>` in `.npmrc`), the package manager uses a single private feed where possible, and internal names are reserved on the public registry with an empty placeholder.
  Check: every internal dependency is scoped, the scope-to-registry mapping is in a committed config file available to CI, and no unscoped internal names exist. Owner: `dx`. Source: NPM Security, CI/CD.
- **Package-manager config not committed.** The file controlling registry and integrity settings (such as `.npmrc`) is committed to source control and present in the CI environment, so CI resolves the same way developers do.
  Check: the registry config file is tracked and not ignored. Owner: `dx`. Source: CI/CD.
- **Dependencies fetched straight from public registries.** Builds resolve through an access-controlled private repository, proxy or vetted mirror (with retention and immutability policies where available) that all dependencies are proxied through; artifacts are reviewed before entering it, and its use cannot be bypassed.
  Check: CI and build config point at the private registry or proxy and no step overrides it with a public URL. Owner: `platform`. Source: Software Supply Chain, NPM Security, CI/CD.

## Install-time code execution

- **Third-party lifecycle scripts run at install.** Malicious packages execute arbitrary commands (token harvesting) through install hooks such as `postinstall`; installs run with scripts disabled (`--ignore-scripts`, or `ignore-scripts=true` in the project or global `.npmrc`), and packages that legitimately need scripts are allowed individually through an allowlist.
  Check: the project `.npmrc` sets `ignore-scripts=true` (or CI installs pass `--ignore-scripts`) and any exceptions are listed in an explicit allowlist. Owner: `dx`. Source: NPM Security.

## Choosing and adopting dependencies

- **Dependency adopted without assessing the supplier.** Before a third-party component, product or service enters the supply chain, both vendor and offering are assessed in proportion to criticality: maturity, security history and response to past vulnerabilities, and (for larger vendors) third-party certifications, which are a data point but never relied on alone. Open-source components are checked for active maintenance, popularity, maturity, release (not alpha or beta) status, enough maintainers, updated dependencies, test coverage including security rules, documentation with secure-usage guidance, a documented vulnerability reporting process with timely fixes, and a license consistent with intended use.
  Check: a diff adding a dependency names a released version of a maintained, adequately staffed project whose license fits; flag single-maintainer, pre-release or abandoned packages. Owner: `dx`. Source: Software Supply Chain, NPM Security.
- **Typosquatted or hallucinated package name.** Attackers publish look-alike names and names that AI assistants hallucinate; before installing, confirm the package exists and is the intended one on both the source repository and the registry (metadata, contributors, latest versions), with real download counts, a genuine repository with commits and contributors, and release history; be suspicious of very recently created packages, never install AI-suggested packages without independent verification, and in teams add a registry existence check to CI for newly added dependencies.
  Check: each newly added package name matches a well-established project and is not a near-miss of a popular name; CI verifies new dependencies before they reach production. Owner: `dx`. Source: NPM Security.
- **New versions adopted immediately.** Upgrades wait for new versions to circulate before adoption (configure a release-age delay in update tooling) and are applied after reviewing changelogs, release notes and code changes and testing them; staying out of date for long is also a risk, so freshness is reviewed regularly.
  Check: dependency update automation configures a minimum release age, and upgrade PRs are reviewed rather than auto-merged. Owner: `dx`. Source: NPM Security.
- **Documentation example copied into production.** README and official examples sometimes demonstrate patterns weaker than the library's own defaults (MD5 single-iteration key derivation, re-adding auth headers on redirect after the library stripped them, unanchored regex for origin or audience matching, `Math.random()` for file names); examples get a security review, the library's internal secure defaults are preferred, security-sensitive parameters are validated (anchored regex, authenticated encryption, HTTPS-only credentials), and insecure documentation is reported upstream.
  Check: code using a library's crypto, redirect, regex-matching or randomness options matches the library's secure defaults rather than a weaker README pattern. Owner: `dx`. Source: NPM Security.

## Publishing packages

- **Secrets or unintended files in a published package.** When both `.gitignore` and `.npmignore` exist, only `.npmignore` applies, so files hidden from git can still ship; use the `files` allowlist in `package.json` (it takes precedence over ignore files), keep secrets out of the working directory being published, and review the tarball with `--dry-run` before publishing.
  Check: published packages declare a `files` allowlist and the publish step runs a dry-run review; an exposed token is revoked. Owner: `dx`. Source: NPM Security.
- **Long-lived publish token where trusted publishing is available.** CI publishing uses trusted publishing with OIDC, which issues short-lived, workflow-specific credentials and generates provenance attestations automatically; classic tokens are revoked. Where a token is unavoidable it is a granular token limited to the needed packages, organizations and permissions, read-only for installs, with the shortest practical expiry, restricted source IP ranges where stable, 2FA bypass only for non-interactive workflows that cannot use trusted publishing, stored in the CI secret store and never committed.
  Check: publish workflows authenticate through OIDC trusted publishing; any remaining token is granular, scoped, expiring and read from the CI secret store. Owner: `platform`. Source: NPM Security.
- **Publisher and CI tokens never reviewed.** CI and publisher tokens are restricted, scoped, bound to workflows or IP ranges, rotated, reviewed regularly, and unnecessary or exposed tokens are revoked immediately.
  Check: a token inventory or rotation procedure exists for registry tokens. Owner: `platform`. Source: NPM Security.
- **Registry account without 2FA.** Publishing accounts enable 2FA for authorization and writes; interactive publishing requires 2FA and token-based publishing is disallowed where practical; developers stay logged out of the registry in daily work so their credentials are not the weak spot.
  Check: package or organization settings require 2FA for publishing and settings changes. Owner: `dx`. Source: NPM Security.
- **No monitoring or playbook for a compromised publish.** Unusual publishes, token usage and dependency changes raise alerts, and a documented remediation playbook covers revoking tokens, deprecating or yanking compromised versions, publishing fixes and notifying consumers.
  Check: alerting and a written playbook exist for the published packages. Owner: `sre`. Source: NPM Security.

## Signing, provenance and release evidence

- **Unsigned components accepted.** Consumers accept only digitally signed components and validate the signature before use; producers sign artifacts and build provenance (for example with Sigstore) and harden the code-signing infrastructure, since its compromise extends to every consumer.
  Check: deploy or install steps verify signatures before use, and release workflows sign artifacts. Owner: `platform`. Source: Software Supply Chain, NPM Security, CI/CD.
- **Provenance generated locally or easy to forge.** Provenance (where, when and how an artifact was produced) is generated by the build platform, not a developer machine, is hard for attackers to forge, and contains everything needed to link the result back to the builder.
  Check: provenance is produced in the CI release job by the build platform's generator, not by a script developers can run locally. Owner: `platform`. Source: Software Supply Chain.
- **Release evidence not verified before deployment.** Before installation or deployment, verification checks signatures, allowed signer identities, the artifact digest and expected attestation type, and for build provenance also the expected builder identity, source repository, build type and parameters; missing, invalid or unexpected evidence is rejected when the trust policy requires it. Signer identity patterns are regular expressions, so they are anchored and literal dots escaped, and the policy is never derived from the untrusted bundle itself. Valid signatures authenticate claims; they do not prove the SBOM is complete, the software safe, or the builder uncompromised.
  Check: the verification step pins issuer and an anchored identity pattern from trusted config and checks digest and builder fields. Owner: `platform`. Source: Dependency Graph and SBOM, NPM Security.

## SBOM and dependency graph

- **No SBOM per release.** Each release has an automatically generated SBOM in a standard machine-readable format (CycloneDX or SPDX), produced in CI after dependency resolution.
  Check: the release pipeline generates and stores an SBOM for every release. Owner: `platform`. Source: Dependency Graph and SBOM, Software Supply Chain, NPM Security.
- **SBOM missing relationships or metadata.** The SBOM captures component names, versions, suppliers, package identifiers and hashes where available, direct and transitive relationships, and the described product, SBOM author, generation time and generator identity and version; incomplete or unknown coverage is recorded explicitly, because absence from an SBOM is not evidence of absence.
  Check: generator config emits the dependency graph and metadata and declares completeness. Owner: `platform`. Source: Dependency Graph and SBOM.
- **SBOM built from manifests only.** The inventory is reconciled with the final package or container image, including bundled libraries and OS packages, and discrepancies are corrected; generation scope and known gaps are recorded.
  Check: SBOM generation runs against the built artifact or image, not just the manifest. Owner: `platform`. Source: Dependency Graph and SBOM.
- **SBOM not schema-validated.** The document is validated against its format's schema before publication or ingestion, with a separate check of metadata and relationships; passing does not establish completeness.
  Check: the pipeline runs a schema validation step on the SBOM. Owner: `platform`. Source: Dependency Graph and SBOM, NPM Security.
- **SBOM signed separately from the artifact.** The SBOM is bound to the final artifact's digest through a signed attestation identifying both; signing artifact and SBOM separately does not establish the relationship, and an SBOM attestation describes inventory while build provenance separately records how the artifact was made.
  Check: the release attaches an SBOM attestation referencing the artifact digest. Owner: `platform`. Source: Dependency Graph and SBOM.
- **Release evidence overwritten or overshared.** Each release's inventory stays distinct, original SBOMs and signed evidence are preserved alongside the release even when imported elsewhere, write access is restricted, and sharing of sensitive metadata is limited.
  Check: release storage keeps per-release SBOM and attestation files with restricted write permissions. Owner: `platform`. Source: Dependency Graph and SBOM.

## Vulnerability detection and monitoring

- **No automated dependency analysis from the start.** Automated analysis of dependencies runs from the birth of the project (adding it late creates a backlog that can block delivery), as SCA in CI alongside verification of signatures, provenance and SBOM; the deployed state is monitored continuously against vulnerability sources (NVD, OSV, CISA KEV) with alerts when new CVEs affect a stored manifest snapshot.
  Check: CI runs an SCA step on every change and a scheduled job or service monitors released manifests or SBOMs. Owner: `platform`. Source: Vulnerable Dependency Management, Software Supply Chain, NPM Security, CI/CD.
- **Scanner with a single data source and no false-positive handling.** Detection tools use several reliable input sources (CVE databases miss fully disclosed issues without a CVE) and support flagging a finding as a false positive; security tooling itself is maintained, secured and correctly configured, and is never treated as finding everything.
  Check: the chosen scanner config draws on multiple advisory sources and records suppressions explicitly. Owner: `platform`. Source: Vulnerable Dependency Management, Software Supply Chain.
- **Final build output assumed secure.** Binary composition analysis of the finished artifact detects exposed secrets and unauthorized components or content and verifies integrity; both suppliers and consumers perform it.
  Check: the release pipeline scans the built artifact or image, not only the source tree. Owner: `platform`. Source: Software Supply Chain.
- **SAST findings on dependencies accepted unverified.** SAST may be run on OSS components as well as internal code, but its results are manually verified and not read as a complete view of security.
  Check: SAST findings are triaged before action, not auto-accepted or auto-dismissed. Owner: `security`. Source: Software Supply Chain.
- **Deployed systems not mapped to release inventories.** Release SBOMs are mapped to deployed systems and components reassessed when advisories arrive; monitoring is holistic (code dependencies, container images, web servers, OS components) and insecure configuration changes are acted on; priority comes from exploitability, exposure and impact, not dependency depth, and the graph identifies which parent brings in an affected component.
  Check: an inventory links each deployment to its release SBOM, and triage notes record exploitability and exposure. Owner: `sre`. Source: Dependency Graph and SBOM, Software Supply Chain.
- **VEX "not affected" accepted on trust.** Before accepting a VEX claim, the issuer is authenticated, document integrity verified, and the justification assessed against the exact product version and deployment conditions, with risk reassessed over time.
  Check: VEX-based suppressions reference a verified issuer and a version-specific justification. Owner: `security`. Source: Dependency Graph and SBOM.

## Remediating a vulnerable dependency

- **Risk accepted by the development team alone.** Accepting the risk of a detected vulnerability is decided by the Chief Risk Officer (fallback: CISO) based on the team's technical analysis and the CVSS indicators.
  Check: each risk-accepted dependency finding records the accountable approver. Owner: `security`. Source: Vulnerable Dependency Management.
- **Transitive dependency patched in place.** When a transitive dependency is vulnerable, action is taken on the direct dependency that brings it in, because changing the transitive one directly often destabilizes the application.
  Check: remediation PRs upgrade the direct parent rather than forcing a transitive version, unless the backport path below applies. Owner: `dx`. Source: Vulnerable Dependency Management.
- **Patched release adopted without test evidence.** When a fixed version exists, it is updated in a test environment and the automated tests for features using the dependency must pass before production; failures from API changes are fixed in application code; runtime incompatibilities are raised with the provider while an interim mitigation is applied.
  Check: upgrade PRs run tests covering the dependent features. Owner: `dx`. Source: Vulnerable Dependency Management.
- **Wrapper mitigation assumed to cover every path.** While no fix exists, provider workarounds are applied and validated; reachable calls to affected functions and exploit conditions are identified, a wrapper is used only when its checks block those conditions on every affected call path, otherwise the functionality is disabled or isolated; the wrapper is temporary with the upgrade or replacement tracked. A provider exploit becomes a regression test, but blocking one payload does not prove safety, so alternate inputs and all reachable paths are tested and existing tests rerun.
  Check: interim mitigations cite the analyzed call paths, include a regression test, and link a tracked permanent fix. Owner: `backend`. Source: Vulnerable Dependency Management.
- **Scanner suppression broader than one CVE.** An ignore entry for a dependency covers only the specific CVE being handled (a dependency can carry several), and the README notes which CVE is handled and why the tool still alerts.
  Check: suppression entries name a single CVE id, not a whole package. Owner: `dx`. Source: Vulnerable Dependency Management.
- **In-house patch or backport treated as remediation without proof.** When no fix exists (patch yourself) or a fix exists but cannot be adopted (breaking major, transitive pin, unmaintained version line), the patch is derived from the CVE, upstream advisory, issue and fix (a vulnerability category alone does not say which change prevents exploitation); a backport first confirms the upgrade is really blocked and records the exact blocker, isolates only the security-relevant change and keeps it minimal. Before the vulnerability counts as handled: a reproducing test fails against the unpatched and passes against the patched dependency, the dependency's own tests and the application tests pass, and only then is the alert suppressed per CVE. Suppressing the alert or editing a version string records a fix without making one.
  Check: a patched or backported dependency ships with a reproducing test, passing upstream tests, a recorded blocker, and a per-CVE suppression added in the same change. Owner: `dx`. Source: Vulnerable Dependency Management.
- **Patched artifact committed per project.** A backported or patched build is published to the internal registry or proxy the build already trusts, with a version identifier traceable to its upstream version and recorded provenance (source commit, CVE, who produced it), not committed as a local file in each project.
  Check: the manifest resolves the patched version from the internal registry and provenance is recorded. Owner: `platform`. Source: Vulnerable Dependency Management.
- **Backport kept forever.** A backport is a standing commitment: every upstream release is re-patched and every new CVE adds a patch; the recurring cost is sized against acquiring maintained backports, OS-packaged dependencies use the distribution's patched builds, the recorded blocker is re-tested at each dependency review, and the backport is dropped as soon as the fixed version is adoptable. A backport provider is judged on ecosystem and version-line coverage with a published response time, published patches and provenance, delivery through the existing registry without manifest rewrites, and a documented exit.
  Check: each backport has an owner, a re-test date for its blocker, and an exit plan. Owner: `dx`. Source: Vulnerable Dependency Management.
- **Provider not told about a vulnerability you found.** A vulnerability found through a full-disclosure post or a penetration test is reported to the provider; for unresponsive or unwilling providers, an alternative component is evaluated and commercial providers are pressed through risk leadership, and for open-source dependencies an upstream fix is contributed where possible.
  Check: the remediation ticket records the upstream report. Owner: `security`. Source: Vulnerable Dependency Management.
- **Fix assumed complete because the inventory changed.** After rebuilding, the new SBOM is compared with the previous release and deployment mappings updated; an updated inventory does not prove the vulnerability is fixed or the mitigation works.
  Check: remediation includes a test or verification beyond the version bump. Owner: `platform`. Source: Dependency Graph and SBOM.

## Source and developer environment

- **Weak access control on source, build and registry accounts.** Development, version-control, build and registry environments apply least privilege and separation of duties, enforce MFA, rotate credentials, and never store or transmit credentials in clear text or commit them to source control.
  Check: SCM and registry organization settings require MFA, and secret scanning guards the repository. Owner: `platform`. Source: Software Supply Chain.
- **Development tools unvetted.** Developer machines run endpoint security and receive threat assessments; only trusted, well-vetted IDEs, plugins and extensions are used, and they are included in the system inventory.
  Check: a team-recommended extension or tool list exists and new tooling is vetted before use. Owner: `dx`. Source: Software Supply Chain.
- **Package-manager environment never health-checked.** The package-manager setup in development and CI is verified (registry reachable and the configured one expected, tool and runtime versions, folder and cache permissions, cache checksum integrity), for example with `npm doctor`.
  Check: CI or onboarding docs include the package-manager health check. Owner: `dx`. Source: NPM Security.
- See `secure-sdlc.md` for coordinated vulnerability disclosure.
- See `ci-cd.md` for peer review before merge, protected branches and other SCM settings, build environment hardening, ephemeral builds, build parameters, and supply-chain logging.
