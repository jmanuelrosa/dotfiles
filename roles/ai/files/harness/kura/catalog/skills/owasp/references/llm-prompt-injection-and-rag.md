# LLM Prompt Injection, RAG and Model Operations

When to read: the brief, diff, or assessed surface touches LLM prompt assembly, model output handling, guardrail or classifier models, RAG ingestion, embeddings or vector stores, response caches in front of a model, model training, model registries, artifacts or inference endpoints, or AI decisions in ad serving (consent-gated profiling, outcome callbacks, generative creatives).
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [LLM Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html), [Retrieval-Augmented Generation (RAG) Security](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html), [Secure AI/ML Model Ops](https://cheatsheetseries.owasp.org/cheatsheets/Secure_AI_Model_Ops_Cheat_Sheet.html), [AI-Powered Advertising Systems Security](https://cheatsheetseries.owasp.org/cheatsheets/AI-Powered_Advertising_Systems_Security_Cheat_Sheet.html)

## Contents

- Retrieval authorization and tenant isolation
- Response and inference caches
- Prompt boundary and untrusted context
- Model output handling
- Fail-closed pipeline
- Corpus integrity and ingestion
- Vector store and index integrity
- Embedding privacy and manipulation
- Deletion and retention
- Source attribution
- Model artifacts and AI supply chain
- Training and inference runtime isolation
- Inference endpoints, cost and extraction
- Consent gates on AI decisions
- Outcome callbacks and event integrity
- Generative output provenance and creative review
- Logging, monitoring and incident response
- Testing and evaluation

## Retrieval authorization and tenant isolation

- **Access control metadata dropped at chunking.** Classification, owner, permitted roles and permitted tenants must be stored on every vector chunk, not only on the source document; document-level permissions do not carry over to chunks on their own, so an unauthorized query retrieves a restricted chunk.
  Check: the chunking and embedding code copies permission and tenant fields onto each chunk record; a chunk schema without them is the finding. Owner: `data`. Source: RAG Security.
- **Permissions checked at ingestion only.** Enforce access control at retrieval time against the querying identity's current permissions, because permissions change after ingestion, and re-evaluate stored chunks when source permissions change.
  Check: the retrieval path filters on the caller's live permissions, and a source permission change updates chunk metadata; add the retrieval-time filter if absent. Owner: `backend`. Source: RAG Security.
- **Model trusted to enforce access control or business rules.** Access control and policy must be enforced in code before content reaches the model; the model generates text and does not enforce policy, and system-prompt secrecy is not a boundary.
  Check: no authorization, threshold, or policy decision exists only as a system-prompt instruction; move it to a deterministic check (for thresholds, a post-processor keyed off the model's structured output). Owner: `backend`. Source: RAG Security, AI Advertising.
- **Post-retrieval filtering only.** Apply query-time filtering that enforces the caller's access boundaries before similarity search results are returned; retrieve-then-filter exposes the similarity scores of restricted documents.
  Check: the tenant or permission filter is passed into the vector query itself, not applied to its results. Owner: `backend`. Source: RAG Security.
- **One flat vector namespace for all tenants.** Use separate namespaces, collections, or indices per tenant or classification level; never share a single store across tenants without per-chunk enforcement.
  Check: vector store provisioning and the namespace chosen per request derive from the tenant or classification, not a constant. Owner: `database`. Source: RAG Security.
- **Regulated chunks encrypted under a shared key.** Encrypt chunks at rest with per-tenant or per-classification keys where regulatory requirements demand it.
  Check: vector store encryption config for regulated tenants references distinct keys. Owner: `database`. Source: RAG Security.
- **Tenant-specific embedding model reused across tenants.** Do not reuse tenant-specific fine-tuned embedding models across tenants where training or adaptation data could leak between them.
  Check: embedding model selection is keyed by tenant for fine-tuned models. Owner: `data`. Source: RAG Security.
- **Similarity scores returned to the caller.** Do not return similarity scores to users or agents (they map corpus structure through differential analysis); restrict top-k and apply relevance thresholds.
  Check: retrieval API responses omit raw scores and cap result count. Owner: `backend`. Source: RAG Security.
- **Retrieval queries passed raw and unthrottled.** Normalize and inspect queries for abuse patterns before retrieval, and rate limit queries per user or agent identity; never rely on sanitization alone, enforce access boundaries independently.
  Check: the query path normalizes input, applies a per-identity rate limit, and still runs the access filter. Owner: `backend`. Source: RAG Security, LLM Prompt Injection.

## Response and inference caches

- **Cache key not scoped to permissions.** Scope response caches by user, tenant, and permission level, and isolate every model-side cache off tenant ID: KV cache (paged-attention serving stacks), RAG index namespace, plan cache, adapter pool.
  Check: every cache key in front of or inside the model includes tenant and permission scope; a shared key is the finding. Owner: `backend`. Source: RAG Security, AI Advertising.
- **Cache survives revocation or poisoning.** Invalidate cache entries when source documents are updated, deleted, or re-permissioned; set a maximum TTL by sensitivity; never cache restricted, classified, or PII-bearing responses (highly sensitive data not at all).
  Check: document update, delete and permission events trigger cache invalidation, and TTLs exist; add invalidation hooks. Owner: `backend`. Source: RAG Security.
- **Stale cache served when lookup fails.** On cache lookup failure, generate a fresh response; never fall back to a stale or possibly compromised cached response.
  Check: the cache error path calls the live pipeline. Owner: `backend`. Source: RAG Security.

## Prompt boundary and untrusted context

- **Untrusted content concatenated with instructions.** Identify untrusted content from every channel (user input, retrieved documents, tool results, conversation history) and keep it separate from trusted instructions with structured prompt templates; labels, delimiters, and prompt wording do not enforce that boundary.
  Check: prompt assembly tags each untrusted source and does not rely on delimiter text as the only control; permissions are enforced at the tool boundary. Owner: `backend`. Source: LLM Prompt Injection, AI Model Ops.
- **Retrieved content without delimiters or reinforcement.** Wrap retrieved content in delimiters the model is told to treat as untrusted data, and reinforce system instructions after it; positioning must be tested per model because attention patterns differ.
  Check: the RAG prompt template has begin and end markers around retrieved content and a reinforcement after it, with a per-model test. Owner: `backend`. Source: RAG Security.
- **Retrieved context unbounded.** Limit the number and total size of retrieved chunks to prevent context flooding; the published default is 3 to 5 chunks totaling 2,000 to 4,000 tokens.
  Check: retrieval config sets a chunk count and token budget. Owner: `backend`. Source: RAG Security.
- **External content enters context unscreened.** Validate and sanitize all inputs (user input, external content, encoded data) before they reach the model: scan retrieved chunks and fetched content for injection markers ("SYSTEM:", "INSTRUCTION:", "ignore previous", "you are now"), sanitize code comments and documentation, filter suspicious markup, and decode suspicious encodings for inspection.
  Check: a screening step runs on every external content channel before prompt assembly, not only on the user message. Owner: `backend`. Source: LLM Prompt Injection, RAG Security.
- **Input filter without normalization or length cap.** Normalize obfuscation (collapse whitespace, character repetition), detect encodings, and limit input length and comparison work before pattern or fuzzy matching; choose any fuzzy metric and threshold by measuring missed variants and false positives on benign and adversarial inputs.
  Check: the filter caps length before matching and its threshold is backed by a test set. Owner: `backend`. Source: LLM Prompt Injection.
- **Pattern filters as the only injection screen.** Regex filters do not reliably catch indirect injection; screen user prompts and retrieved or fetched context with a classifier, screen outputs against policy, and screen proposed tool calls against user intent, alongside the deterministic controls.
  Check: input, output and action screening placements exist for high-risk paths; tool permissions are still enforced separately. Owner: `backend`. Source: LLM Prompt Injection.
- **Guardrail model shares the primary model's attack surface.** A guardrail is one defense-in-depth layer, never a replacement for input validation, structured prompts, least-privilege tools, or human approval; prefer a purpose-trained classifier over a same-family chat model, and reserve heavier checks for tool invocations, external content ingestion, and sensitive output.
  Check: the guardrail model differs in family or training from the primary model, and destructive actions still require approval. Owner: `backend`. Source: LLM Prompt Injection.
- **Model-level defenses treated as robustness.** Rate limiting only restricts attempt budgets; safety training, content filters, and temperature zero do not stop repeated-attempt (Best-of-N) jailbreaks; keep authorization and least privilege outside the model.
  Check: no design note or code path relies on temperature, safety training, or a blocked example as the control for a privileged action. Owner: `architect`. Source: LLM Prompt Injection.
- **Privileged model reads untrusted text.** For attacker-controlled text inputs, use a dual-LLM handoff: a quarantined model with zero tool access parses untrusted data into a fixed schema, and the privileged planner reads only the schema and never the untrusted document; treat the CaMeL release as a research artifact, not a supported component.
  Check: the model instance that can call tools never receives raw untrusted content. Owner: `architect`. Source: LLM Prompt Injection, AI Advertising.
- **Participant text indexed without Unicode normalization.** Normalize participant-supplied text (Unicode NFC, strip zero-width, strip bidi-control) before classifier or retrieval indexing.
  Check: the ingestion or classifier pre-step applies NFC and strips zero-width and bidi characters. Owner: `data`. Source: AI Advertising, RAG Security.
- **System prompt without role and security constraints.** Design system prompts with clear role definitions and security constraints, and update them based on discovered vulnerabilities; never place a real secret in a prompt.
  Check: system prompt files contain no credentials and define role and constraints. Owner: `backend`. Source: LLM Prompt Injection.
- See `ai-agents-and-mcp.md` for tool-call authorization, approval binding for consequential actions, and recursion, retry and cost limits in agentic flows.

## Model output handling

- **Model output executed or rendered raw.** Treat model output as untrusted at every downstream use and apply the destination's own control (safe HTML rendering, parameterized queries); output keyword filtering is not sufficient, and benign inputs can still combine into harmful output.
  Check: no model output reaches eval, a shell, a query string, or an HTML sink without the sink-specific control. Owner: `backend`. Source: LLM Prompt Injection, RAG Security.
- **Markdown or HTML from the model rendered unsanitized.** Deploy HTML and Markdown sanitization for output rendering, since rendered links and hidden image tags exfiltrate data.
  Check: the client renders model output through a sanitizer that strips external image tags and raw HTML. Owner: `frontend`. Source: LLM Prompt Injection.
- **Free-form output drives automation.** Use structured outputs with JSON schema validation in automated workflows, and validate raw output against expected schemas in high-risk workflows (payments, data access, automation); validate any generated tool call against an allowlist of actions and parameters.
  Check: automated consumers parse model output through a schema validator and reject on failure. Owner: `backend`. Source: RAG Security.
- **Sensitive data leaks through responses.** Apply policy filters that detect and redact PII, secrets, credentials, and regulated data, redact fields dynamically by the caller's access level, and screen for system-prompt leakage before output is returned or passed to a tool.
  Check: an output redaction step exists and receives the caller's access level. Owner: `backend`. Source: RAG Security, LLM Prompt Injection.

## Fail-closed pipeline

- **Retrieval failure falls back to model memory.** When retrieval fails, return an error that the knowledge base is unavailable; answering from the model alone bypasses every RAG control.
  Check: the retrieval error path returns an error, not an un-grounded generation. Owner: `backend`. Source: RAG Security.
- **Failed access check returns a filtered subset.** When an access control check fails, return nothing.
  Check: exceptions in the permission filter propagate to a deny. Owner: `backend`. Source: RAG Security.
- **Integrity or attribution failure ignored.** Exclude a document whose hash verification fails and alert; block a response whose source attribution cannot be generated where attribution is required.
  Check: hash mismatch and attribution failure branches deny and raise an alert. Owner: `backend`. Source: RAG Security.
- **Silent degradation.** Implement fail-closed behavior at every stage, return errors naming the failed stage, never silently degrade, and treat failed retrieval or access checks as security events with alerts on repeats.
  Check: pipeline stages emit a security event on failure, not only a performance metric. Owner: `backend`. Source: RAG Security.

## Corpus integrity and ingestion

- **Document digest stored beside the document.** Record a SHA-256 digest of each approved document in a separately controlled manifest protected by a signature or MAC whose keys sit outside the document store's write permissions; verify the manifest and digest before retrieval, reject failures, and authorize baseline updates separately. Signing dataset manifests and RAG chunks with an offline key (in-toto attestation in a DSSE envelope) is the ad-tech form. A matching digest proves consistency, not safety.
  Check: digests live in a store the ingestion writer cannot modify, and retrieval verifies them. Owner: `data`. Source: RAG Security, AI Advertising.
- **No provenance on ingested content.** Record who uploaded each document, when, from what source, and with what approval; tag every training row and RAG chunk with a participant-provenance tag so scoped rollback is answerable without re-hashing.
  Check: the chunk and training-row schemas carry provenance fields. Owner: `data`. Source: RAG Security, AI Advertising.
- **Unknown sources ingested.** Maintain an allowlist of trusted document sources, reject unapproved ones, require approval workflows for new sources and bulk uploads, and never trust content by file extension or MIME type alone.
  Check: ingestion rejects sources absent from a configured allowlist. Owner: `data`. Source: RAG Security.
- **Ingested documents unscanned.** Scan ingested documents and external API responses for injection markers, hidden instructions, invisible Unicode, and zero-width characters, and verify integrity and content type before ingestion.
  Check: a scan step precedes embedding for every source. Owner: `data`. Source: RAG Security.
- **External sources auto-synced straight into the index.** Put a staging or review step between ingestion and availability in the vector store.
  Check: connector sync writes to staging, not directly to the serving index. Owner: `data`. Source: RAG Security.
- **Ingestion connectors over-privileged or unvetted.** Grant connectors least privilege (read access to specific folders, not admin on the whole drive), vet each connector's security posture and update cadence, and keep an inventory of sources and connectors with credentials, update schedules, and owners.
  Check: connector OAuth scopes are read-only and folder-scoped, and an inventory file exists. Owner: `data`. Source: RAG Security.
- **Embedding model and ingestion libraries unpinned.** Pin versions of embedding models and ingestion libraries; an uncontrolled embedding update changes retrieval across the corpus.
  Check: model identifiers and ingestion dependencies are pinned to exact versions. Owner: `data`. Source: RAG Security.
- **Training data unvalidated or untraceable.** Validate and sanitize training data, use version-controlled auditable training pipelines in reproducible environments, and apply differential privacy or anonymization when training on sensitive data.
  Check: training pipelines are versioned and include a validation stage. Owner: `data`. Source: AI Model Ops.
- **Outcome events admitted to training before adjudication.** Quarantine outcome and reward events for a documented adjudication window based on observed verdict latency and partner terms, remove rows later flagged as SIVT, and cap the maximum policy shift per epoch.
  Check: the training admission job enforces a delay and a reversal path. Owner: `data`. Source: AI Advertising.
- **Restricted-category retrieval trusted without anchors.** Pin canonical policy chunks per restricted category and require at least k of n anchors per query (published example k=3 of n=5); when fewer return, route to the non-LLM rules baseline, which is the real last line of defense. Prefer diversity-sampled retrieval such as MMR over similarity top-k alone as defense-in-depth.
  Check: restricted-category retrieval counts anchors and has a rules-baseline fallback. Owner: `backend`. Source: AI Advertising.

## Vector store and index integrity

- **Vector database without authentication.** Enable authentication, network isolation, and strong credentials before production; never deploy with default credentials, and never skip access control because the database is internal.
  Check: vector DB deployment config sets auth and network restrictions and contains no default credentials. Owner: `database`. Source: RAG Security.
- **Application or agent code can write the index.** Restrict index write access to authorized ingestion pipelines only.
  Check: the credentials used by request-serving or agent code are read-only on the index. Owner: `database`. Source: RAG Security.
- **Index changes unaudited and unrecoverable.** Log every insert, update, and delete with timestamp and modifier identity, verify index integrity with periodic checksums, keep snapshots for rollback, and alert on unexpected size changes.
  Check: index write paths emit audit records and a snapshot job exists. Owner: `database`. Source: RAG Security.

## Embedding privacy and manipulation

- **Embeddings treated as anonymized.** Embeddings leak source content through inversion and membership inference; apply the source documents' access controls to them, encrypt them at rest (always where regulated data is handled), and consider calibrated noise for high-risk datasets.
  Check: embedding storage inherits source permissions and has encryption at rest. Owner: `database`. Source: RAG Security.
- **Embedding API exposed.** Do not expose embedding generation APIs publicly or to untrusted agents or users without strict access control and rate limiting.
  Check: the embedding endpoint requires auth and has a rate limit. Owner: `backend`. Source: RAG Security.
- **Adversarial embeddings unmonitored (high-security).** Monitor embedding distribution statistics, detect drift on re-embedding, log the embedding model version per document, and cross-validate retrieval across multiple embedding models in high-security applications.
  Check: documents record their embedding model version and a distribution monitor exists. Owner: `data`. Source: RAG Security.

## Deletion and retention

- **Source deletion does not cascade.** Removing, de-permissioning, or expiring a source document must remove its chunks, embeddings, derived indexes, and cached responses; deletion must be propagated explicitly, and nothing derived may outlive the source's retention period. Handle audit logs per legal retention and erasure requirements.
  Check: the delete handler for a source reaches the vector store and caches. Owner: `data`. Source: RAG Security.
- **No deletion evidence.** Keep a deletion log for regulatory compliance and periodically audit the vector store for orphaned chunks.
  Check: a deletion log and an orphan-scan job exist. Owner: `data`. Source: RAG Security.

## Source attribution

- **Responses without signed attribution.** Return the retrieved documents, used chunks, and provenance metadata with every response, sign the attribution so it cannot change after generation, include document hashes, and offer a verification endpoint for cited documents.
  Check: the response payload carries signed attribution with hashes. Owner: `backend`. Source: RAG Security.
- **Upstream attribution trusted unverified.** Never trust source attribution from upstream services without cryptographic verification.
  Check: consumers verify attribution signatures before use. Owner: `backend`. Source: RAG Security.

## Model artifacts and AI supply chain

- **Model or adapter loaded without signature verification.** Sign model binaries (OpenSSF Model Signing), block deploy on signature failure, refuse to load any unsigned fine-tune adapter, and bind adapter signatures to CycloneDX ML-BOM entries tied to the participant-provenance tag.
  Check: the deploy and load paths verify signatures and abort on failure. Owner: `platform`. Source: AI Model Ops, AI Advertising.
- **Signature treated as proof of a clean model.** Provenance bounds who can ship a model, not what it learned; trigger-scan every refreshed or externally sourced model as defense-in-depth, gate promotion on a held-out trigger corpus built from your own policy taxonomy, and use staged rollout with per-supplier champion/challenger on a clean holdout.
  Check: the promotion pipeline has a behavioral gate beyond signature checks. Owner: `data`. Source: AI Advertising.
- **Third-party pre-trained model unvalidated.** Validate third-party or pre-trained models for integrity and safe behavior before production.
  Check: external model intake has a validation stage before registry promotion. Owner: `platform`. Source: AI Model Ops.
- **Model registry or artifact store open.** Store models in access-controlled registries, encrypt weights and datasets at rest, and restrict access to training logs and intermediate outputs.
  Check: registry and bucket IaC set access policies and encryption. Owner: `cloud`. Source: AI Model Ops.
- **Feature-store write credentials broad and long-lived.** Purpose-scope feature-store namespaces and rotate materialization-write credentials on the production-secrets cadence.
  Check: feature-store credentials are per namespace with a rotation policy. Owner: `data`. Source: AI Advertising.
- **Secrets hardcoded in notebooks or training code.** Never hardcode secrets in source or notebooks; use a secret manager, environment variables, or CI secret injection.
  Check: notebooks and training scripts contain no literal API keys or tokens. Owner: `data`. Source: AI Model Ops.
- **ML containers and pipelines unhardened.** Harden containers and limit capabilities (distroless images, AppArmor), include security scanning in CI/CD, grant training and inference jobs least privilege, and isolate development, staging, and production environments.
  Check: model-serving images are minimal with dropped capabilities and CI runs a scan. Owner: `platform`. Source: AI Model Ops.
- **No rollback or freeze path for models.** Implement rollback for model deployments, use shadow deployments and canary releases with rapid rollback, and be able to freeze the generation model version from the control plane during an incident.
  Check: deployment config supports canary and a pinned-version rollback. Owner: `platform`. Source: AI Model Ops, AI Advertising.

## Training and inference runtime isolation

- **Untrusted model jobs share trusted infrastructure.** Separate training, evaluation, and production inference by trust boundary; run untrusted evaluation, fine-tuning, and conversion jobs in sandboxes or isolated workers with restricted egress; use microVMs, gVisor, Kata Containers, confidential compute, or dedicated nodes for high-sensitivity models and data.
  Check: job specs for untrusted model work use an isolated runtime class and egress policy. Owner: `platform`. Source: AI Model Ops.
- **Accelerators shared between untrusted tenants.** Avoid sharing GPU or accelerator devices between mutually untrusted tenants unless hardware-backed partitioning and memory isolation exist, and clear inputs, outputs, temp files, caches, and accelerator memory between jobs where supported.
  Check: scheduling config pins untrusted tenants to dedicated or partitioned devices. Owner: `platform`. Source: AI Model Ops.
- **Model-serving container reaches host and metadata.** Disable access to host paths, container sockets, cloud metadata services, and unnecessary device mounts, and set per-workload CPU, memory, GPU, disk, process, and network limits.
  Check: serving manifests have no hostPath or socket mounts, block metadata, and set limits. Owner: `platform`. Source: AI Model Ops.
- **Teardown leaves artifacts behind.** Validate that job teardown removes temporary artifacts, local checkpoints, prompt logs, and cached embeddings.
  Check: teardown steps delete these paths. Owner: `platform`. Source: AI Model Ops.
- **Broad platform credentials in serving.** Scope model-serving credentials to the specific model, endpoint, and environment.
  Check: serving identities have per-endpoint IAM policies. Owner: `cloud`. Source: AI Model Ops.

## Inference endpoints, cost and extraction

- **Inference endpoint without authentication.** Apply authentication and authorization (OAuth, API tokens), validate and sanitize inputs, and use rate limiting and abuse detection.
  Check: inference routes require auth and have rate limits. Owner: `backend`. Source: AI Model Ops, LLM Prompt Injection.
- **No per-tenant spend limits.** Set per-tenant token, request, concurrency, and spend limits to reduce denial-of-wallet, and cap inference cost per call budgeted in dollars per minute.
  Check: limits exist per tenant and per call in config. Owner: `backend`. Source: AI Model Ops, AI Advertising.
- **Partner-visible raw scores.** Return tier labels, not raw scores, on partner-visible outputs; keep protocol money fields precise but guard them with technically enforced contractual query budgets and probing detection; reject, never coerce, out-of-domain feature values.
  Check: partner API responses expose labels, and query budgets are enforced in code. Owner: `backend`. Source: AI Advertising.

## Consent gates on AI decisions

- **Consent treated as a model feature.** Treat consent as an authorization check: gate the identifier write and the model call separately, because storage or access needs consent even when no model runs, and contextual review becomes profiling the moment its output joins a user identifier.
  Check: the serving path checks consent before the model call and before writing identifiers, as two gates. Owner: `backend`. Source: AI Advertising.
- **Child-directed traffic reaches profiling models.** Refuse the model call on child-directed traffic based on a platform-controlled classification; treat sender-declared OpenRTB `regs.coppa` only as a signal that raises the bar, and fail closed (treat as child-directed) when the classification is unavailable.
  Check: the gate reads a platform-owned flag and defaults to child-directed when missing. Owner: `backend`. Source: AI Advertising.
- **Opt-outs not honored at feature fetch.** Honor real-time opt-outs (Sec-GPC, `regs.gpp`, ATT, Android Ad ID reset) at the feature-fetch step, and invalidate downstream materializations (segments, lookalike scores, KV caches, adapter warm-pools) on opt-out.
  Check: feature fetch reads opt-out signals and an opt-out event triggers invalidation. Owner: `backend`. Source: AI Advertising.
- **Training corpus not consent-scoped.** Consent-scope the training corpus per IAB Europe TCF, treating TC strings as personal data.
  Check: training admission filters on a consent-reason code per row. Owner: `data`. Source: AI Advertising.
- **Sensitive inference and regulated verticals unguarded.** Test for special-category inference from generic inputs with a disparate-impact audit on each refresh, and route employment, housing, and credit ads through a stricter path.
  Check: the refresh pipeline runs the audit, and vertical routing exists. Owner: `data`. Source: AI Advertising.

## Outcome callbacks and event integrity

- **Callback signature omits event type or value.** Sign every outcome callback over `key_id`, `event_type`, event ID, timestamp, monetary value, and receiving endpoint, using HMAC-SHA256 over length-prefixed serialization or RFC 9421 HTTP Message Signatures with receiver-enforced required covered components.
  Check: the verifier rejects signatures missing any of these components. Owner: `backend`. Source: AI Advertising.
- **Signed headers but unsigned body.** Require an RFC 9530 `Content-Digest` as a covered component and revalidate it against the received bytes; no field outside the covered set may influence a monetary amount or a training label.
  Check: the receiver recomputes the body digest before parsing fields. Owner: `backend`. Source: AI Advertising.
- **Payload read before verification.** Verify the HMAC before any payload field influences a control-flow decision.
  Check: verification is the first operation in the callback handler. Owner: `backend`. Source: AI Advertising.
- **Replay window not covered by deduplication.** Deduplicate on event ID, never on (event_id, timestamp); retain dedup records for the full signature-acceptance period including clock skew and any agreed retry period, derived from the delivery contract rather than a fixed 24-hour default; reject expired callbacks.
  Check: the dedup key is the event ID and its retention derives from the acceptance window. Owner: `backend`. Source: AI Advertising.
- **Partner identified by issuer or Common Name.** Pin the certificate identity to a specific `partner_id` via a typed SAN entry or SPKI hash, never the Common Name or a trusted issuer alone.
  Check: mTLS partner mapping uses SAN or SPKI, not CN. Owner: `backend`. Source: AI Advertising.
- **Settlement and labels share one path.** Separate financial settlement from training-label materialization.
  Check: callbacks feed settlement and label stores through distinct pipelines. Owner: `data`. Source: AI Advertising.
- **Credential incident handled as auth-only.** On partner-credential compromise, rotate credentials, mark exposure-window rows suspect, invalidate per-partner weights, and invalidate model artifacts.
  Check: the incident runbook includes the three data-side actions. Owner: `sre`. Source: AI Advertising.
- **No non-agent fallback.** Keep a warm, pre-deployed rules-based fallback (for bidding) reachable with a single control-plane flip while an agent is quarantined.
  Check: a kill switch config routes traffic to the rules path. Owner: `backend`. Source: AI Advertising.

## Generative output provenance and creative review

- **Generated assets egress without marking.** A provider of a generative endpoint carries the EU AI Act Art. 50(2) machine-readable marking duty; emit a C2PA 2.4 manifest with a hard binding over the output bytes at egress, re-sign per rendition, and never rely on soft binding.
  Check: every generator egress path signs a manifest per rendition. Owner: `backend`. Source: AI Advertising.
- **Real-person likeness generated without authorization.** Require a likeness or voice-use authorization artifact before the generator accepts a brief asserting a real person; use voice-clone and AI-content detectors only to prioritize review, measure their false positives and negatives, and hold ambiguous or high-risk submissions for human review.
  Check: brief intake requires an authorization reference, and detector output never acts as approval. Owner: `backend`. Source: AI Advertising.
- **Single-model creative verdicts.** Cross-check every monetization-changing boolean verdict against a non-LLM rules baseline; run two VLMs with different backbones on submitted images as defense-in-depth, and route disagreement and high-risk tags (minors, celebrity likeness, trademark) to human review.
  Check: verdict code consults the rules baseline and routes disagreements. Owner: `backend`. Source: AI Advertising.
- **Legacy executable creatives accepted.** Reject VPAID creatives outright in video-programmatic and CTV; sandboxing VPAID is not viable.
  Check: creative ingest rejects VPAID. Owner: `backend`. Source: AI Advertising.
- **Participant provenance unverified.** Verify participant provenance per mode: ads.txt and the OpenRTB SupplyChain object, seller-ID authorization on catalog uploads, advertiser-domain ownership, ads.cert 2.0 or device attestation.
  Check: ingest paths verify the provenance mechanism for their mode. Owner: `backend`. Source: AI Advertising.
- **On-device model delegated to ad iframes.** Never add `allow="language-model"` to an ad slot iframe; treat every model output as untrusted at the DOM boundary, since CSP does not inherit into a cross-origin ad iframe.
  Check: ad slot markup carries no `language-model` permission. Owner: `frontend`. Source: AI Advertising.

## Logging, monitoring and incident response

- **Raw prompts and responses logged.** Trace requests with correlation IDs, retrieved document IDs, authorization decisions, model versions, and tool outcomes; exclude credentials, raw queries, retrieved content, model inputs and outputs, and tool arguments by default; capture content for investigations only as redacted fields in a restricted, retention-limited evidence store.
  Check: LLM logging calls record identifiers and decisions, not prompt or response bodies. Owner: `sre`. Source: RAG Security, LLM Prompt Injection, AI Model Ops.
- **Retrievals not attributable.** Log every retrieval (and cache hit) with the caller's identity and the access metadata of returned chunks.
  Check: the retrieval and cache layers emit audit records with identity. Owner: `backend`. Source: RAG Security.
- **No alerting on LLM abuse signals.** Alert on repeated injection attempts, encoding attempts and HTML injection, access control violations, unusual retrieval patterns or retrieval-distribution shifts, scraping, and sudden token, request, or spend changes; monitor input distribution, output entropy, latency, and drift.
  Check: alert rules exist for these signals. Owner: `sre`. Source: LLM Prompt Injection, RAG Security, AI Model Ops.
- **Guardrail decisions unlogged.** Log every guardrail decision and watch for drift in approval rate or refusal-reason distribution, which often precedes a working bypass.
  Check: guardrail verdicts are emitted as structured events with a drift monitor. Owner: `sre`. Source: LLM Prompt Injection.
- **No RAG or model incident runbook.** Define and rehearse procedures to quarantine a poisoned document, invalidate affected cache entries, and identify users who received tainted responses; define escalation for model abuse or drift, and keep emergency controls and kill switches.
  Check: a runbook covers these steps and a kill switch exists in config. Owner: `sre`. Source: RAG Security, AI Model Ops, LLM Prompt Injection.

## Testing and evaluation

- **No RAG red-team cases in CI.** Every deployment runs at minimum: poisoned document retrieval, indirect prompt injection, cross-tenant retrieval, stale permission, cache leakage, unauthorized tool invocation, attribution tampering, and deletion verification.
  Check: the CI suite contains all eight cases. Owner: `qa`. Source: RAG Security.
- **Injection tests only through the user channel.** Test direct and indirect injection with harmless data and instrumented tool substitutes, place indirect payloads in the external content channel under test, include attempts with none of the filter's keywords, and test repeated attempts within a defined budget.
  Check: injection tests feed retrieved or tool content, not only chat input, and use instrumented tools. Owner: `qa`. Source: LLM Prompt Injection.
- **Injection outcomes graded by response text.** Grade each security objective with its own observable (a dummy marker for disclosure, instrumented tool calls and dummy state for unauthorized actions, an instrumented destination for exfiltration); count missing telemetry and errors as inconclusive, never as blocked; validate the grader first.
  Check: the test harness asserts on tool instrumentation, not refusal phrases. Owner: `qa`. Source: LLM Prompt Injection.
- **False-positive rate hidden.** Record benign-request policy decisions separately from task completion, include model-generated refusals, and report false-positive rate, pending reviews, and completion rate together, by objective, with numerators, denominators, versions, and repeat count; do not claim population rates or equivalence from a hand-picked smoke test.
  Check: evaluation reports carry per-objective counts and versions. Owner: `qa`. Source: LLM Prompt Injection.
- **No adversarial robustness testing.** Include adversarial examples in testing, use robust training techniques, and monitor confidence thresholds for out-of-distribution inputs.
  Check: the evaluation suite includes adversarial inputs. Owner: `data`. Source: AI Model Ops.
- **Defenses not revisited.** Conduct regular security testing with known and new attack patterns, review security logs, train users on safe LLM interaction, and map threats to OWASP ASVS or Proactive Controls for AI/ML.
  Check: a recurring review and threat mapping are recorded. Owner: `security`. Source: LLM Prompt Injection, AI Model Ops.
