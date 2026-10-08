# AI Agents, MCP and AI-Assisted Coding

When to read: the brief, diff, or assessed surface touches an LLM agent that calls tools, tool authorization or human approval of agent actions, agent memory, multi-agent or sub-agent messaging, an MCP server, client, or its configuration, coding-agent sandboxes, rules files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules` and similar), AI review bots in CI, agent-generated changes to dependencies, tests, or build files, or execution records supplied by a third-party agent or MCP server.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [AI Agent Security](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html), [MCP Security](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html), [Verifying Third-Party Agent Execution Evidence](https://cheatsheetseries.owasp.org/cheatsheets/Verifying_Third_Party_Agent_Execution_Evidence_Cheat_Sheet.html), [Secure Coding with AI](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html), with merged items from [LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), [RAG Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html), [Secure AI/ML Model Ops](https://cheatsheetseries.owasp.org/cheatsheets/Secure_AI_Model_Ops_Cheat_Sheet.html), [AI-Powered Advertising Systems Security](https://cheatsheetseries.owasp.org/cheatsheets/AI-Powered_Advertising_Systems_Security_Cheat_Sheet.html)

## Contents

- Tool authorization and least privilege
- High-impact action approval
- Untrusted context: tool results, memory and other agents
- MCP server authentication and transport
- MCP tool definitions, installation and isolation
- Coding-agent runtime and context exposure
- Agent-authored changes: rules files, build paths, tests and dependencies
- CI/CD agents
- Loop, cost and rate limits
- Logging and monitoring
- Verifying third-party execution evidence
- Agent testing and release gates

## Tool authorization and least privilege

- **Authorization decided by the model.** Enforce tool authorization in an execution component outside the agent's context, validating each call against the user's permissions and session context; the model choosing a tool is not the user being authorized for it, and an authorized retrieval does not authorize the resulting tool call.
  Check: the tool dispatcher checks the end user's permission for the specific tool and target before executing, independent of model output. Owner: `backend`. Source: AI Agent, LLM Prompt Injection, RAG Security, MCP.
- **Wildcard or unscoped tool grants.** Grant agents and MCP servers the minimum tools for the task, scope each tool (read-only vs write, specific resources, allowed paths), keep separate tool sets per trust level, and allowlist tools per context (a support agent gets no payment tools); never `*` permissions or unrestricted shell.
  Check: tool configs list explicit operations and paths, and no tool accepts arbitrary commands. Owner: `backend`. Source: AI Agent, MCP, RAG Security, LLM Prompt Injection, Coding with AI.
- **Unknown tools fail open.** Fail closed for unknown tools or tools with no approval requirement defined; unmapped tools default to requiring review.
  Check: the risk lookup defaults to a non-low tier and the dispatcher denies unregistered tools. Owner: `backend`. Source: AI Agent.
- **Tool arguments unvalidated.** Validate every tool input as untrusted LLM output: strict JSON Schema with `additionalProperties: false` and `pattern` on strings, sanitization against SQL, OS command, and path-traversal injection, and avoid raw shell commands or unsanitized file paths.
  Check: each tool's parameter schema disallows extra properties and the handler uses parameterized calls. Owner: `backend`. Source: MCP, LLM Prompt Injection, Coding with AI.
- **URL-fetching tool without an allowlist.** Never fetch arbitrary URLs supplied by the model without strict allowlist validation; injected prompts steer fetch tools at internal services and cloud metadata endpoints. See `ssrf.md` for the full control set.
  Check: fetch tools validate destinations against an allowlist before connecting. Owner: `backend`. Source: MCP.
- **Model holds direct access to sensitive APIs.** The model requests actions through a controlled interface instead of executing them; each call in a chain is independently authorized, and retrieved content never drives tool execution without an intermediate validation step.
  Check: no tool wrapper chains a second privileged call from model output without re-authorization. Owner: `architect`. Source: RAG Security.
- **LLM application holds write credentials it does not need.** Grant LLM applications minimal permissions: read-only database accounts where possible, restricted API scopes and system privileges.
  Check: the agent's DB role and API tokens are read-only unless a write tool requires otherwise. Owner: `database`. Source: LLM Prompt Injection.
- **Agent data unclassified.** Minimize sensitive data in agent context, classify data and apply handling rules per operation (context, log, output), encrypt at rest and in transit, and enforce retention and deletion.
  Check: context building applies a classification-driven redaction step. Owner: `backend`. Source: AI Agent.

## High-impact action approval

- **Approval is a boolean flag.** Bind each approval to actor, tool, target resource, normalized parameters, timestamp, and expiry; check and consume it in one atomic step immediately before execution so it cannot be replayed, and require new approval when target or parameters change. Use short-lived authorization artifacts with replay protection for irreversible operations.
  Check: the approval record stores the full tuple and the executor compares and consumes it atomically; a `user_confirmed` boolean is the finding. Owner: `backend`. Source: AI Agent, AI Advertising, LLM Prompt Injection.
- **Proposal and execution in one component.** Separate decision-making from execution: the agent proposes, and a policy service or execution component independently validates scope, privilege, and approval state.
  Check: the component that executes destructive actions does not trust the agent's own claim of approval. Owner: `architect`. Source: AI Agent.
- **Risk judged from prompt wording.** Base approval on the proposed operation, target, arguments, and caller authority, not on keywords in the prompt; tier every tool by risk and set autonomy boundaries per tier; a prompt asking for human review does not stop execution, so configure every sensitive tool in the framework's approval hook, persist interrupted state, and resume only after a decision on the actual action and arguments.
  Check: the approval gate is configured per tool in code, not described in a prompt. Owner: `backend`. Source: LLM Prompt Injection, AI Agent, AI Advertising.
- **Confirmation UI shows a summary or can be bypassed.** Show action previews with full tool-call parameters, never auto-approve tool calls (especially across multiple servers), and make sure model-crafted responses cannot bypass the confirmation UI.
  Check: the approval view renders the full argument set and its approve action is not reachable from model output. Owner: `frontend`. Source: MCP, AI Agent.
- **No step-up for critical actions.** Require step-up authentication for account recovery, payment initiation, privilege changes, bulk deletion, or production deployment. See `mfa-passkeys-and-transaction-signing.md` for transaction authorization.
  Check: critical tools require a fresh authentication factor. Owner: `backend`. Source: AI Agent.
- **High-impact actions repeat on retry.** Make high-impact actions idempotent where possible, and require explicit duplicate confirmation when not.
  Check: destructive or financial tools accept an idempotency key. Owner: `backend`. Source: AI Agent.
- **Approval path fails open.** Fail closed when risk classification, approval validation, policy lookup, or audit logging fails.
  Check: exceptions in these steps deny the action. Owner: `backend`. Source: AI Agent.
- **No interrupt or rollback.** Let users interrupt and roll back agent operations, keep a clear audit trail of decisions and actions, and keep emergency kill switches.
  Check: a cancel path and kill switch exist for running agent tasks. Owner: `backend`. Source: AI Agent, LLM Prompt Injection.

## Untrusted context: tool results, memory and other agents

- **Tool responses trusted as instructions.** Treat every tool response as untrusted, including from approved servers: label it as data in context, use tag stripping and instruction-pattern detection only as extra filtering, sanitize outputs before they feed other tools (downstream SSRF or command injection), and extract structured fields instead of raw HTML from scraping tools.
  Check: tool results pass through a labeling and sanitizing step, and subsequent calls are authorized in code. Owner: `backend`. Source: MCP, AI Agent.
- See `llm-prompt-injection-and-rag.md` for screening, delimiting, and guardrail models on external content entering agent context.
- **Exfiltration through tool arguments.** Detect sensitive data in tool parameters (credentials, file contents, environment variables), encoded data in URLs, and unusually large payloads to HTTP or webhook tools, and filter sensitive data from outputs.
  Check: an output validator inspects tool-call parameters for secrets and size before dispatch. Owner: `backend`. Source: AI Agent, MCP, Coding with AI.
- **Agent memory shared across users.** Isolate memory between users and sessions, and set expiration and size limits.
  Check: memory reads and writes are keyed by user and session with TTL and size caps. Owner: `backend`. Source: AI Agent.
- **Memory persisted unvalidated.** Validate and sanitize data before storing it in memory, audit for and redact sensitive data before persistence (never store it unencrypted or unredacted), and protect long-term memory with cryptographic integrity checks.
  Check: the memory write path redacts and scans, and stored entries carry a keyed integrity value verified on read. Owner: `backend`. Source: AI Agent.
- **Inter-agent messages trusted by origin.** Treat output from one agent as untrusted input to the next; authenticate communicating agents and enforce the sender's permissions at the receiver, since a valid signature does not grant permission; do not pass full history or raw tool responses between agents without sanitization.
  Check: the receiving agent re-authorizes requested actions and sanitizes inbound context. Owner: `backend`. Source: AI Agent, Coding with AI.
- **Inter-agent signatures replayable.** Use a maintained protocol that signs sender, intended recipient, message type, payload, creation and expiry times, and a unique message ID; enforce a bounded validity window, atomically check and record IDs for the full window plus clock skew in state shared across all receivers, reject when that state is unavailable, and keep transport encryption.
  Check: the receiver has a shared replay store keyed by message ID and rejects on store failure. Owner: `backend`. Source: AI Agent.
- **Sub-agents inherit the parent's full privileges.** Restrict sub-agent permissions and credentials to their scope, validate their actions stay within the parent task, prevent escalation through agent chains, isolate agent execution environments, and apply circuit breakers against cascading failure.
  Check: sub-agent spawn code passes a reduced tool set and credentials. Owner: `architect`. Source: Coding with AI, AI Agent.

## MCP server authentication and transport

- **Remote MCP server without authentication.** Require authentication on remote endpoints exposing non-public tools or data, and validate authorization on every protected request; with legacy session-based revisions, use random session IDs bound to the authenticated user and never treat an ID as authentication.
  Check: every MCP HTTP handler runs auth and authorization per request. Owner: `backend`. Source: MCP.
- **Token audience unchecked or token passed upstream.** Follow the MCP OAuth 2.1 profile: clients send the `resource` parameter naming the server, the server validates the token's audience is itself, rejects invalid tokens, and never forwards an MCP access token to an upstream API.
  Check: token validation asserts audience, and upstream calls use separately obtained credentials. Owner: `backend`. Source: MCP.
- **Local HTTP server exposed or Origin unchecked.** Bind local Streamable HTTP servers to localhost unless network access is needed; validate `Origin` and reject a present but invalid value with HTTP 403 (do not reject solely for a missing Origin from non-browser clients); validate `Host` against expected names; use TLS for remote connections.
  Check: the listener address, Origin and Host checks are in the server setup. Owner: `backend`. Source: MCP.
- **Shared or broad MCP credentials.** Use scoped per-server credentials and never share tokens across servers; request narrow OAuth scopes (for example `mail.readonly`, not `mail.modify` or full access); prefer ephemeral short-lived tokens over long-lived PATs.
  Check: each server config has its own credential with minimal scopes. Owner: `backend`. Source: MCP.
- **OAuth tokens in plaintext MCP config.** Store OAuth access and refresh tokens in OS-native secure storage (macOS Keychain, Windows Credential Manager, Linux Secret Service), never in MCP config files, application settings, source, or logs.
  Check: MCP config files contain no token values. Owner: `dx`. Source: MCP.
- **Remote server identity unverified.** Verify remote server identity by certificate pinning or cryptographic server verification, and never accept server public keys from an unverified first-contact response.
  Check: client config pins the server identity. Owner: `backend`. Source: MCP.
- **No per-session resource controls.** Apply rate limits, quotas, and timeouts per session or tenant.
  Check: the MCP server sets these limits. Owner: `backend`. Source: MCP.
- **Optional message signing misused.** Integrity after TLS termination is an optional, threat-model-driven control: if needed, choose a reviewed mechanism both endpoints support and define key trust, signed content, replay rejection, and failure behavior; do not present it as a core MCP requirement.
  Check: any message-signing design documents these four decisions. Owner: `architect`. Source: MCP.

## MCP tool definitions, installation and isolation

- **Tool definitions not pinned (rug pull).** Inspect every tool description, parameter name, type, and return schema before approval, treating the whole schema as an injection surface; pin reviewed definitions by cryptographic hash, verify before each execution, and re-prompt for consent when they change. Pinning detects metadata changes only, and tool annotations are hints, not enforcement.
  Check: the client or gateway stores definition hashes and blocks on change. Owner: `dx`. Source: MCP, Coding with AI.
- **Cross-server shadowing.** Treat each MCP server as an independent untrusted domain, prevent one server's descriptions from referencing or altering another's tools, watch for duplicate tool names, and use an MCP proxy or gateway to enforce isolation.
  Check: the gateway config namespaces tools per server and flags name collisions. Owner: `architect`. Source: MCP, Coding with AI.
- **Local MCP server with full host access.** Run local servers in a sandbox with minimal privileges (a bare `chroot` is not a sandbox), restrict file system access to required directories, disable network unless needed, and separate sensitive servers (payment, auth, PII) from general ones; `stdio` avoids a listening endpoint but restricts nothing else.
  Check: the server launch config wraps it in a sandbox with path and network limits. Owner: `dx`. Source: MCP, Coding with AI.
- **MCP server installed unreviewed.** Install only from trusted sources after reviewing source and tool definitions, verify integrity by checksum or signature, check package names for typosquatting, scan dependencies, use scanning tooling (such as `mcp-scan`) for poisoned descriptions and post-install changes, and keep an allowlist of approved servers and tools.
  Check: MCP server entries reference allowlisted, version-pinned packages. Owner: `dx`. Source: MCP, Coding with AI.
- **Silent server connection.** Show a consent dialog before connecting any new server, with the exact untruncated local command and the source and publisher; never let web content or untrusted data trigger installation, and never let agents discover and connect servers automatically.
  Check: the client has no auto-connect or install-from-content path. Owner: `dx`. Source: MCP, Coding with AI.

## Coding-agent runtime and context exposure

- **Coding agent runs with full developer credentials.** Run coding agents in sandboxes (dev containers, restricted shells, VMs, ephemeral workspaces) with command allowlists, block credential stores, SSH keys, and cloud CLI configs, use ephemeral task-scoped credentials, and keep production credentials, deploy keys, and org secrets out of reach; arbitrary code execution happens only sandboxed.
  Check: agent sandbox config denies reads of credential paths and no long-lived production credential is exposed. Owner: `dx`. Source: Coding with AI, AI Agent.
- **Agent egress unrestricted.** Apply egress controls on the agent runtime and block outbound network when the task does not need it; do not allow unrestricted browsing or URL fetching.
  Check: the sandbox network policy is allowlist-based. Owner: `dx`. Source: Coding with AI.
- **Auto-accept on unfamiliar code.** Evaluate the risk of permission-skipping or auto-accept modes and never enable them on untrusted or unfamiliar codebases.
  Check: shared agent settings do not enable permission bypass by default. Owner: `dx`. Source: Coding with AI.
- **Agent runtime without resource limits.** Set CPU, memory, disk, and process-count limits on agent execution environments.
  Check: container or VM config sets these limits. Owner: `dx`. Source: Coding with AI.
- **Secrets readable as agent context.** Add `.env`, `.env.*`, `*.pem`, `*.key`, `credentials.json`, `serviceAccountKey.json` and similar to the AI tool's context exclusion list (`.gitignore` does not apply to AI tools), keep secrets in environment variables or vaults rather than the project tree, and do not open secret files or paste credentials while AI tools with editor or terminal context are active.
  Check: the AI tool's ignore or exclusion file covers secret patterns, and no secrets sit in the tree. Owner: `dx`. Source: Coding with AI.
- **Unknown context sent to the provider.** Review what context the assistant sends, audit it via controlled request inspection with credentials and personal data redacted from captures, restrict agent context to the minimum files needed, and use self-hosted or air-gapped tools (or approval) for classified, regulated, or highly sensitive code.
  Check: a documented decision exists for sensitive repositories. Owner: `dx`. Source: Coding with AI.

## Agent-authored changes: rules files, build paths, tests and dependencies

- **Rules files change without review.** Treat `.cursorrules`, `.cursor/rules/`, `CLAUDE.md`, `.claude/`, `AGENTS.md`, `.github/copilot-instructions.md`, `.windsurfrules`, `.aider.conf.yml`, and custom system prompt files as security-critical: require explicit approval for changes, flag them in every PR via hooks or CI, block external contributors and the agent itself from modifying them without review.
  Check: CODEOWNERS or a CI check covers these paths. Owner: `platform`. Source: Coding with AI.
- **Rules files weaken controls.** Audit existing rules files for instructions that weaken security controls, disable safety features, or tell the agent to ignore file types or patterns.
  Check: read rules files for such directives. Owner: `dx`. Source: Coding with AI.
- **Repository content treated as instructions.** Treat issues, PR descriptions and comments, READMEs, changelogs, error traces, and fetched pages as untrusted when an agent processes them; review and audit the agent's resulting actions after it processes external or public content, and flag injection patterns beforehand.
  Check: workflows that feed contributor content to agents include a review step on the agent's resulting changes. Owner: `dx`. Source: Coding with AI.
- **Out-of-scope edits pass review.** Flag unexpected modifications in CI (lockfiles, CI/CD config, tests, files outside the requested scope), review every file of an agent PR individually rather than its summary, require CODEOWNERS for CI configs, Dockerfiles, deployment scripts, and rules files, and limit the agent's file scope where supported.
  Check: CI has a scope-diff check and CODEOWNERS covers sensitive paths. Owner: `platform`. Source: Coding with AI.
- **Agent changes to auto-executing build files.** Review with heightened scrutiny changes to `package.json` scripts (postinstall, preinstall, prepare, prebuild), `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Dockerfile`, `docker-compose.yml`, `Makefile`, `Rakefile`, `Taskfile`, `setup.py`, `pyproject.toml`, `go generate` directives, and any file run during build, install, test, or deploy; flag added network access, downloads, or shell execution, require explicit approval for pipeline changes, and pin third-party actions to a commit SHA, never a tag.
  Check: CI diffs build configuration and requires approval; workflow `uses:` references are SHA-pinned. Owner: `platform`. Source: Coding with AI.
- **Agent rewrites or deletes tests.** Require human review of AI test modifications (deleted tests, weakened assertions, new mocks replacing the dependency under test, assertions of generated rather than correct behavior), flag test deletions and assertion-count drops in CI, and never let the agent write both security-critical code and its tests without independent verification.
  Check: a CI rule flags test deletions and assertion reductions in agent PRs. Owner: `qa`. Source: Coding with AI.
- **Security tests written by the generating agent.** Write security-critical tests (authentication, authorization, input validation, cryptography) by hand and add adversarial cases the AI did not generate: invalid inputs, expired tokens, malformed payloads, boundaries, concurrent access; never treat a green AI-generated suite as security evidence.
  Check: security-critical modules have human-authored negative tests. Owner: `qa`. Source: Coding with AI.
- **Hallucinated package installed.** Verify every AI-suggested package exists and check its page, downloads, maintainer history, and creation date; treat packages under 30 days old, with very low downloads, or a lone maintainer as suspicious; block installs below a minimum age with a pre-install hook or CI check; keep an internal package allowlist.
  Check: a minimum-age or allowlist gate runs before install. Owner: `dx`. Source: Coding with AI.
- **AI-suggested versions carry known CVEs.** Audit every AI-generated dependency list, fail CI on known vulnerabilities regardless of authorship, cross-reference NVD, GitHub Advisory Database, or OSV, and pin and update versions through the normal dependency process, never by AI suggestion.
  Check: CI runs a dependency audit that fails the build. Owner: `dx`. Source: Coding with AI.
- **Invisible Unicode in code, commits and agent output.** Detect and flag bidi overrides (U+202A through U+202E, U+2066 through U+2069) and zero-width characters (U+200B, U+200C, U+200D, U+FEFF), scan PRs for homoglyphs, and review agent-generated commit messages and PR descriptions for content aimed at future agent runs.
  Check: CI runs an invisible-character and homoglyph scan. Owner: `platform`. Source: Coding with AI.
- **Agent output rendered with live Markdown.** Sanitize agent output before rendering in IDE chat panes or PR comments: strip or escape Markdown image tags, hidden links, and HTML entities, since external image URLs exfiltrate context through parameters.
  Check: the rendering surface sanitizes images and links. Owner: `frontend`. Source: Coding with AI.
- **AI change without an accountable human.** Assign a human owner to every AI-generated change, require explicit developer approval before merge, never accept AI review as a substitute for human review, and keep an audit trail of approver, AI tool, and model version.
  Check: branch protection requires human approval on agent PRs. Owner: `platform`. Source: Coding with AI.

## CI/CD agents

- **CI agent holds org secrets or deploy keys.** Scope CI agent credentials to the minimum (review bots get no deploy keys or secret write access) and run them isolated from production secrets beyond the job's needs.
  Check: the agent workflow's `permissions` and secrets are read-only and job-scoped. Owner: `platform`. Source: Coding with AI.
- **PR content fed raw to the CI agent.** Filter and sanitize PR title, body, comments, and diff before passing them as context, sandbox processing of external contributors' PRs, and do not trust the agent's comments or fixes without checking for manipulation.
  Check: the workflow sanitizes PR fields and gates external-fork runs. Owner: `platform`. Source: Coding with AI.
- **CI agent pushes without a gate.** Require approval gates before CI agents push commits, modify workflows, or access sensitive resources.
  Check: the agent token cannot push to protected branches or edit workflows unapproved. Owner: `platform`. Source: Coding with AI.

## Loop, cost and rate limits

- **Unbounded agent loops (denial of wallet).** Enforce recursion, retry, chain-depth, token, and cost limits; track token use and cost per session and user; rate limit and scope-limit output actions; and trip circuit breakers or kill switches on abnormal cost, latency, or tool-call spikes, or calls to never-used endpoints.
  Check: the agent loop has max-iteration, retry, and budget caps and a breaker. Owner: `backend`. Source: AI Agent, AI Model Ops, RAG Security.

## Logging and monitoring

- **Tool invocations unlogged.** Log agent decisions, tool calls, and outcomes with user context and timestamps, tracing which query led to which retrieval, output, and tool call; redact secrets and PII, and exclude sensitive prompt, tool-argument, and response content by default (MCP's full-parameter logging still requires that redaction).
  Check: the dispatcher emits a structured, redacted event per call with a correlation ID. Owner: `sre`. Source: AI Agent, MCP, RAG Security, Coding with AI.
- **High-risk actions lack decision metadata.** Log action classification, risk score when applicable, authorization outcome, approval identifier, execution result, and policy version for each high-risk action.
  Check: the executor logs these fields. Owner: `backend`. Source: AI Agent.
- **No anomaly detection on agent behavior.** Feed agent and MCP logs into a SIEM and alert on approval-behavior drift, repeated bypass attempts, elevated privilege use, new tools being called, admin-level queries, abnormal tool frequency, rising high-risk actions, cross-server data flows, cross-agent instruction propagation, and anomalous reasoning patterns.
  Check: alert rules exist for these signals. Owner: `sre`. Source: AI Agent, MCP, Coding with AI, LLM Prompt Injection.
- **CI agent actions unmonitored.** Log CI agent action metadata, correlation IDs, authorization decisions, and outcomes without secrets or sensitive content, and monitor for unexpected file changes, network calls, or secret access.
  Check: the CI agent job emits these records. Owner: `sre`. Source: Coding with AI.

## Verifying third-party execution evidence

- **Supplier record treated as independent proof.** List who could write or alter a record (component, host, recorder, operator, signing-key holder) and count independent parties, not processes; a signature shows who asserted something, not that it is true; without independent observation classify the record as a supplier assertion and never use it alone to settle an incident or dispute involving that supplier.
  Check: decisions resting on vendor traces name the evidence class (independently re-checkable, supplier assertion, or no information). Owner: `security`. Source: Agent Evidence.
- **No independent observer.** Obtain event data from an observer independent of the component (such as a gateway or boundary you control), store it where the component and supplier cannot rewrite it, and corroborate supplier records against it, remembering it covers only what crosses that boundary.
  Check: a boundary recorder exists with storage outside the supplier's write access. Owner: `sre`. Source: Agent Evidence.
- **Supplier timestamp accepted as freshness.** Send a fresh unpredictable nonce, require it signed together with the execution claims, and compare it; a nonce bounds signing time, not capture time, and a trusted timestamp shows existence, not truth, so record which timing property was checked.
  Check: the verifier issues and checks a nonce. Owner: `backend`. Source: Agent Evidence.
- **Record not bound to the intended artifact and run.** Recompute the digest of an independently obtained expected artifact and compare it with the signed subject, separately match the signed execution identifier or challenge, and check which inputs (tool definitions, configuration, prompts, model version, policy) the record covers; a stable artifact digest is not an execution identifier.
  Check: the verifier compares both digest and run ID against values obtained outside the record. Owner: `backend`. Source: Agent Evidence.
- **Omitted events undetectable.** Reconcile records against an expected-event list or per-execution sequence the supplier cannot redefine; for transparency logs verify inclusion and consistency proofs and detect split views by comparing signed log states across independent observers; a log entry count or one spot-check is not completeness.
  Check: reconciliation uses an observer-owned expected-event list. Owner: `sre`. Source: Agent Evidence.
- **Recording-failure behavior unknown.** Determine whether the component drops, buffers, or stops on recording failure (including buffer overflow), exercise the failure in an environment you control, preserve independently observed delivery failures, choose drop or stop by action risk, and make evidence loss visible; an empty report from a lossy recorder is not a clean run.
  Check: a test or exercised outage documents the failure behavior. Owner: `sre`. Source: Agent Evidence.
- **Verifier trusts a key shipped with the record.** Use a maintained verifier with signer identities, keys or roots, and permitted algorithms configured independently of the record, validate certificate paths and revocation, and keep verification policy and expected values outside the evidence; a shared MAC key cannot attribute authorship among its holders, and asking the supplier's service to validate its own record leaves it a supplier assertion.
  Check: trust anchors come from local config, not the record. Owner: `backend`. Source: Agent Evidence.
- **Verification results without stated limits.** State the exact property checked (signer, artifact, execution binding, timing, or coverage) and record the trust assumptions and limits with each result.
  Check: verification output names the property and assumptions. Owner: `security`. Source: Agent Evidence.

## Agent testing and release gates

- **No agent abuse-case suite.** Keep repeatable tests for prompt override, tool misuse, privilege escalation, memory poisoning, data exfiltration, recursive tool abuse, approval bypass, and multi-agent chaining, run before production and after material changes to prompts, tools, memory, retrieval, policies, or model providers.
  Check: the test suite contains all eight cases. Owner: `qa`. Source: AI Agent.
- **Policy changes ship without updated tests.** Run adversarial suites in CI for agent templates, tool policies, and prompt changes, keep regression tests for previously observed failures, block releases when high-risk tool policies, approval logic, or credential scopes change without updated tests, and scrutinize test changes in the same PR.
  Check: CI requires test changes alongside policy or scope changes. Owner: `qa`. Source: AI Agent.
- **Red-team fixtures hold live data.** Version-control red-team prompts and expected denials without secrets or live customer data.
  Check: fixtures contain no real credentials or customer records. Owner: `qa`. Source: AI Agent.
- **No retained validation evidence.** For production agents retain the tested agent version, model provider, tool policy, retrieval configuration, abuse cases with expected and observed results (approval, denial, timeout, circuit breaker), and accepted residual risk with its compensating control.
  Check: a release artifact records these fields. Owner: `qa`. Source: AI Agent.
- **MCP setup never attacked.** Conduct regular security audits and simulated attacks against MCP setups.
  Check: a recurring MCP assessment is scheduled. Owner: `security`. Source: MCP.
