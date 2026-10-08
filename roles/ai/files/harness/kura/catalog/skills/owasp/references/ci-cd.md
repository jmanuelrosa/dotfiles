# CI/CD Pipelines

When to read: the brief, diff, or assessed surface touches CI/CD pipeline definitions (`.github/workflows/`, GitLab CI, Jenkinsfiles and similar), workflow triggers, `GITHUB_TOKEN` or job permissions, pipeline secrets or OIDC federation, third-party actions, reusable workflows or CI plugins, runners or build agents, build caches, release, publish or deploy jobs, branch protection, rulesets, merge rules or other SCM settings, or AI assistants running inside a pipeline.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [CI/CD Security](https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html), [GitHub Actions Security](https://cheatsheetseries.owasp.org/cheatsheets/GitHub_Actions_Security_Cheat_Sheet.html), [Software Supply Chain Security](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html)

## Contents

- Untrusted code in privileged workflows
- Pipeline credentials and token scope
- Third-party actions, plugins and integrations
- Runners and build environment
- Caches, artifacts and integrity
- SCM and merge controls
- Deployment gates
- Security scanning in the pipeline
- CI/CD identity lifecycle
- Logging, monitoring and incident response

## Untrusted code in privileged workflows

- **`pull_request_target` runs pull request code.** This trigger runs in the base repository's context with a write-capable `GITHUB_TOKEN` and secrets, so checking out (via checkout action or CLI) and running untrusted PR code there gives an attacker code execution with those privileges; avoid the trigger, and never check out and run untrusted code under it.
  Check: workflows using `pull_request_target` do not check out the PR head or run its scripts, builds or tests; prefer `pull_request`. Owner: `platform`. Source: GitHub Actions.
- **`workflow_run` chains escalate privilege.** A `workflow_run` workflow can hold a write token and secrets while being triggered by a workflow an attacker modifies through a PR, and it may consume poisoned artifacts from that run without verification; chain workflows with `workflow_call` reusable workflows instead.
  Check: no privileged workflow is triggered by `workflow_run`, or it neither trusts nor executes artifacts from the triggering run. Owner: `platform`. Source: GitHub Actions.
- **`issue_comment` trigger without actor and commit binding.** Comment-triggered workflows can bypass PR approval and suffer a time-of-check to time-of-use race where the PR changes after approval; they verify the triggering actor is authorized (for example a trusted org member) and check out only a full commit SHA supplied in the approving comment (such as `/ok-to-test(<sha>)`). Label-based `pull_request` triggers are an alternative: verify the labeling actor is authorized (label permission does not mean the code was reviewed), check out exactly `github.event.pull_request.head.sha`, and never treat the label as approval for later commits.
  Check: comment- or label-triggered workflows check the actor's authorization and check out a pinned SHA, not the PR's moving head. Owner: `platform`. Source: GitHub Actions.
- **Code checked out by a mutable reference.** Checking out by pull request number or branch name runs whatever is there at execution time; always use an immutable full commit SHA.
  Check: checkout steps in privileged or approval-gated workflows reference a full SHA. Owner: `platform`. Source: GitHub Actions.
- **Event context interpolated into a shell step.** Attacker-controlled context (PR title, branch name, issue body) expanded directly into `run:` or similar execution blocks enables script injection; always pass any context through an intermediate environment variable, even for contexts that look safe.
  Check: no `${{ github.event.* }}` or other context expression appears inside a `run:` script; it is mapped through `env:` and referenced as a shell variable. Owner: `platform`. Source: GitHub Actions.
- **Fork pull requests run workflows automatically.** Enable "Require approval for all external contributors"; "first-time contributors" only is unsafe, because an attacker can land a harmless PR first and later PRs then run without approval.
  Check: repository or organization Actions settings require approval for all outside contributors. Owner: `platform`. Source: GitHub Actions.
- **AI assistant in CI with broad capabilities.** An AI reviewer or triager reading untrusted issues or PRs is a prompt-injection target; if it can be triggered by any account and holds secrets or a write token, it can exfiltrate or act; enable only the minimum tools and actions it needs.
  Check: AI-assistant workflows run with a read-only token, no unneeded secrets, and an explicit minimal tool allowlist. Owner: `platform`. Source: GitHub Actions.

## Pipeline credentials and token scope

- **Workflow token permissions not minimized.** Set `permissions: {}` at workflow level and grant only the specific permissions each job needs at job level; restrict the repository default `GITHUB_TOKEN` permission to read for contents and packages, since older repositories default to read-write.
  Check: every workflow declares `permissions: {}` at top level with job-level grants, and repository settings default the token to read. Owner: `platform`. Source: GitHub Actions.
- **Static long-lived credentials in workflows.** Personal access tokens and static cloud keys are replaced by OIDC-based short-lived credentials (trusted publishing, cloud federation); where static credentials remain, prefer temporary credentials or OTPs and add IP-based or other restrictions so a stolen valid credential still fails.
  Check: deploy and publish jobs authenticate via OIDC (`id-token: write`) rather than stored keys; see `tokens-and-federation.md` for the federation trust conditions. Owner: `platform`. Source: GitHub Actions, CI/CD.
- **Secrets hardcoded in the repository or pipeline config.** Secrets are never hardcoded in code repositories or CI/CD configuration files, are removed from other artifacts such as images and compiled binaries, and are kept in a secrets store encrypted at rest.
  Check: workflow files and CI config reference secrets only through the platform's secret store; no literal credentials. Owner: `platform`. Source: CI/CD, GitHub Actions, Software Supply Chain.
- **Secrets broader than the step that uses them.** Remaining static secrets are passed at step level rather than job level, preferably as environment-level secrets only available to jobs targeting that environment, and rotated regularly.
  Check: `secrets.*` references sit in the `env:` or `with:` of the step that needs them, not at job or workflow level. Owner: `platform`. Source: GitHub Actions.
- **`secrets: inherit` on reusable workflow calls.** Inheriting passes every caller secret including ones the callee does not need; pass only the required secrets explicitly, and review any `environment` the called workflow's jobs select, since that environment's secrets apply there and can override the caller's map.
  Check: no `secrets: inherit`; called workflows' environments are reviewed for what they expose. Owner: `platform`. Source: GitHub Actions.
- **Checkout persists git credentials.** Unless later steps need git operations, the checkout step uses `persist-credentials: false` so the token is not left in the workspace for a compromised step to read.
  Check: checkout steps set `persist-credentials: false` unless a later step pushes. Owner: `platform`. Source: GitHub Actions.
- **Secrets printed, logged or left in history.** Secrets must not be printed to the console, logged, or stored in shell history files; sensitive values that are not platform secrets are masked (for example `::add-mask::`).
  Check: steps do not echo, `set -x` around, or write secrets to files or logs, and derived sensitive values are masked. Owner: `platform`. Source: CI/CD, GitHub Actions.
- **Pipeline identity with more than it needs.** Identities used in pipelines get only the operations on the specific resources they require (deny by default, access justified, not assumed); pipelines and steps are limited in what other platform resources they can reach; secrets are not shared across pipelines, especially of different sensitivity; the OS account running the pipeline has no root or equivalent privilege.
  Check: cloud roles assumed by CI are scoped to the job's resources and actions, secret scopes are per pipeline, and runner jobs do not run as root. Owner: `platform`. Source: CI/CD.

## Third-party actions, plugins and integrations

- **Action or reusable workflow referenced by tag or branch.** Every action and reusable workflow is pinned to a full commit SHA, and the SHA is checked to belong to the named repository, because the platform resolves a SHA from any fork (impostor commits).
  Check: every `uses:` references a 40-character SHA from the stated owner and repo (an impostor-commit audit can automate this). Owner: `platform`. Source: GitHub Actions.
- **Third-party action adopted without vetting.** Third-party actions are minimized (call the platform API directly where possible) and, when used, come from a trusted, active author with several active contributors, stable and safe code, and no unnecessary permission requirements.
  Check: a new third-party `uses:` comes from a vetted publisher and the job grants it only needed permissions. Owner: `platform`. Source: GitHub Actions.
- **Action pins never updated or updated instantly.** Automated update tools (Dependabot, Renovate) keep actions current, with a release-age delay of a few days (Dependabot `cooldown`, Renovate `minimumReleaseAge`) so compromised releases can be caught first.
  Check: update-bot config covers the actions ecosystem and sets a cooldown or minimum release age. Owner: `platform`. Source: GitHub Actions.
- **CI plugin or integration installed ungoverned.** Only a small set of users may extend the CI/CD platform; each plugin or integration is vetted like any software acquisition (vendor reputation and security history, popularity, active maintenance, whether it requires security-reducing changes such as exposing ports, and whether the team can configure and maintain it), then brought under configuration management, patched, and removed when no longer needed.
  Check: plugin or integration additions go through an approval record and appear in managed configuration. Owner: `platform`. Source: CI/CD.
- **Each repository writes its own pipeline security.** Organizations with several repositories maintain a central repository of curated, security-reviewed workflows and actions and reuse it.
  Check: repositories call shared reviewed workflows for common jobs (scanning, release) instead of copies. Owner: `platform`. Source: GitHub Actions.
- See `supply-chain-and-dependencies.md` for lockfile enforcement, version pinning, hash verification, private feeds and dependency-confusion defenses applied in CI.

## Runners and build environment

- **Self-hosted runner on a public repository.** Self-hosted runners execute arbitrary code by design, often reach internal networks and cache credentials, so they are never used with public repositories. Where unavoidable: apply secure development practice (threat modeling, review, testing, patching, hardening), require approval for all external contributors and manually approve each run, use ephemeral runners destroyed after each job, store no sensitive data on the machine, and restrict its network access away from sensitive infrastructure.
  Check: public repositories' workflows target hosted runners; any self-hosted runner is ephemeral, network-restricted and approval-gated. Owner: `platform`. Source: GitHub Actions.
- **High- and low-privilege jobs share runners.** Runner groups and labels separate privileged runners (image builds, restricted-network access) from low-privilege ones (lint, static analysis), with each group limited to the repositories and workflows that need it.
  Check: privileged jobs target a dedicated runner group restricted to specific repositories. Owner: `platform`. Source: GitHub Actions.
- **Runner egress unrestricted.** Egress from hosted runners is monitored and restricted to prevent secret exfiltration.
  Check: workflows that handle secrets run an egress-control step or the runners sit behind an egress allowlist. Owner: `platform`. Source: GitHub Actions.
- **Builds share or reuse environments.** Builds run in isolated nodes and in ephemeral environments (VMs or containers destroyed immediately after the build), so a shared environment cannot be used for cache poisoning or code injection across builds.
  Check: build agents are ephemeral and not reused across jobs or projects. Owner: `platform`. Source: CI/CD, Software Supply Chain.
- **Pipeline step container runs `--privileged`.** Pipeline steps executed in Docker images avoid the `--privileged` flag.
  Check: CI job definitions and runner config do not enable privileged containers. Owner: `platform`. Source: CI/CD.
- **Build infrastructure not hardened.** Build tools sit in appropriately segregated networks with DLP or similar exfiltration controls, unused services are disabled, and the OS, images and servers running CI/CD are patched, inventoried with versions, and hardened to standards such as CIS Benchmarks or STIGs; default vendor settings are never relied on blindly, and configuration changes go through change management rather than ad hoc edits.
  Check: CI infrastructure is defined as code with hardening baselines and network segmentation, and changes are reviewed. Owner: `platform`. Source: CI/CD, Software Supply Chain.
- **Build tools not inventoried or monitored.** An inventory of all build tools with versions and plugins is collected automatically and maintained, and vulnerability databases and vendor advisories are monitored for them.
  Check: the build toolchain and plugin versions are declared in versioned config and covered by advisory monitoring. Owner: `platform`. Source: Software Supply Chain.
- **User-controllable build parameters.** Parameters that users can change to alter how a build is performed let anyone with that permission compromise the build; they are minimized or eliminated.
  Check: release and build workflows expose no free-form inputs that change build commands, sources or targets. Owner: `platform`. Source: Software Supply Chain.
- **CI platform reachable from anywhere or over weak transport.** Communication between SCM and CI/CD uses TLS 1.2 or higher, and access to CI/CD environments is restricted by IP where possible.
  Check: webhook and agent endpoints use TLS 1.2+ and CI access is network-restricted. Owner: `platform`. Source: CI/CD.

## Caches, artifacts and integrity

- **Caching enabled in release or publish workflows.** A poisoned cache restored in a privileged release job can tamper with published artifacts or steal production secrets; disable all forms of caching in release and publishing workflows.
  Check: release, publish and deploy workflows contain no cache restore (including setup actions' built-in caching). Owner: `platform`. Source: GitHub Actions.
- **Pipeline step inputs and outputs not integrity-checked.** Integrity is verified across the pipeline: signed commits required before merge, package hashes verified, artifacts code-signed, and frameworks such as in-toto used to link steps; the signing process itself is secured, since signing is not an absolute guarantee.
  Check: release jobs sign outputs and downstream jobs verify them before use; see `supply-chain-and-dependencies.md` for signature and provenance verification. Owner: `platform`. Source: CI/CD.

## SCM and merge controls

- **Merges possible without enforced review.** Pull requests require review before merge and the requirement cannot be bypassed; protected branches require reviews, passing status checks, signed commits and `CODEOWNERS` approval; auto-merge rules are avoided; rulesets enforce organization-level required workflows before merge.
  Check: branch protection or rulesets on default and release branches require reviews, code-owner approval, signed commits and required checks, with no bypass for regular users and auto-merge disabled. Owner: `platform`. Source: CI/CD, GitHub Actions, Software Supply Chain.
- **Pipeline config changeable without review.** Pipeline configuration is version-controlled so reviews and merge rules apply to it; ideally the CI config lives outside the repository it builds, and if it lives alongside the code it is reviewed before any merge request is approved.
  Check: CI config paths are covered by `CODEOWNERS` or a required reviewer. Owner: `platform`. Source: CI/CD, Software Supply Chain.
- **SCM permissions loose by default.** MFA is enforced; users and roles get no default permissions on SCM assets; external and ephemeral contributors are limited in number and permission; forking of private or internal repositories is restricted; and the ability to make a repository public is limited.
  Check: organization settings require MFA, set base permission to none or read, disable private forking and restrict visibility changes. Owner: `platform`. Source: CI/CD, Software Supply Chain.
- **Review done by people without the context to catch malice.** Reviews happen before merge, by peers experienced in the technology and in secure coding, look for both unintentional flaws and intentionally malicious code, and are documented for later review.
  Check: review policy names qualified reviewers for each area and reviews are retained. Owner: `security`. Source: Software Supply Chain.

## Deployment gates

- **Production deploy runs without human approval.** Production and other critical deployments or publications require manual approval and review before they run, enforced through deployment environments with required reviewers drawn from a defined list.
  Check: deploy and publish jobs target an environment with required reviewers. Owner: `platform`. Source: CI/CD, GitHub Actions.

## Security scanning in the pipeline

- **No workflow static analysis gating merges.** Workflow files are scanned (CodeQL `actions` language plus Zizmor for depth) on every relevant pull request as required status checks that at minimum block high and critical findings; full scans also run on a schedule (for example daily) with findings tracked to remediation, the tools are upgraded periodically for new rules, and multi-repository setups use a centralized reusable scanning workflow.
  Check: a workflow-scanning job runs on PRs, is a required check, and has a scheduled trigger. Owner: `platform`. Source: GitHub Actions.
- **Pipeline lacks code and IaC scanning.** Language-appropriate SAST, DAST and IaC vulnerability scanning are incorporated into the pipeline.
  Check: CI runs SAST and IaC scanning on changes. Owner: `platform`. Source: CI/CD, Software Supply Chain.
- **Secrets only detected after merge.** Secret scanning runs in pull requests and automatically fails the check on a potential secret, with ongoing monitoring for deviations.
  Check: a secret-scanning job is a required PR check. Owner: `platform`. Source: GitHub Actions, CI/CD.
- **No local secret scanning before commit.** Secret scanning also runs locally (pre-commit hooks) so secrets are caught before they are committed.
  Check: the repository's pre-commit configuration includes a secret scanner. Owner: `dx`. Source: GitHub Actions, CI/CD.

## CI/CD identity lifecycle

- **Local, shared or self-provisioned CI identities.** CI/CD access comes from a centralized IdP rather than local accounts; shared accounts and self-provisioning are disallowed, and only email domains the organization controls are allowed.
  Check: SCM and CI platforms are SSO-bound with local accounts disabled. Owner: `platform`. Source: CI/CD.
- **No identity inventory.** An up-to-date inventory of CI/CD identities records owner, identity provider, last used, last updated, granted permissions and permissions actually used, so over-privileged and forgotten identities are found and deprovisioned.
  Check: an inventory or access review process exists and stale identities are removed. Owner: `platform`. Source: CI/CD.

## Logging, monitoring and incident response

- **Pipeline and SCM events not logged or not watched.** All supply-chain systems (VCS, build tools, delivery mechanisms, artifact repositories, runtime hosts) log authentication attempts, configuration changes and other anomaly-relevant events in a parseable format (JSON, syslog) per the organization's log policy, without plaintext passwords, tokens or API keys; logs flow to a central log system or preferably a SIEM whose alerts are tuned and refined, while accepting it will not catch everything.
  Check: CI/CD and SCM audit logs are forwarded to central logging with alert rules defined. Owner: `sre`. Source: CI/CD, Software Supply Chain.
- **No incident response plan for pipeline compromise.** Assume breach: incident response procedures for CI/CD define roles, communication and escalation paths, and are improved from public post-mortems of other incidents.
  Check: a runbook covers CI/CD compromise (credential revocation, artifact recall, workflow lockdown). Owner: `sre`. Source: GitHub Actions.
- **Pipeline treated as less critical than application code.** Pipelines hold sensitive credentials, so they get the same secure development practice as production code (threat modeling, secure code review, security validation, penetration testing), and teams understand a tool before using it for security-sensitive operations such as deployment.
  Check: pipeline changes go through the same review and threat-model gates as application changes. Owner: `security`. Source: GitHub Actions, CI/CD.
