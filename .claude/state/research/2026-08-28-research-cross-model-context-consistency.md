# Research: Cross-model context consistency in Pi

| | |
|---|---|
| Date | 2026-08-28 |
| Mode | feasibility |
| Question | How can Pi track one conversation consistently when the user switches between models with different providers, capabilities, tokenizers, and context windows? |
| Repos examined | dotfiles; installed pi-coding-agent 0.84.3 package |
| Requested by / source | direct ask |

## TL;DR

**Verdict: Feasible with caveats** (confidence: high).
Pi already preserves one common session history and records model switches, so it does not need a second transcript.
The missing abstraction is a distinction between the model-independent logical context and each model's effective projected context.
Implement a local extension for provenance, capability-loss warnings, and honest UI state, then fix Pi core so usage and compaction never reuse token usage from a different model.
Exact semantic or token equivalence across providers is impossible because Pi intentionally adapts reasoning blocks, images, tool protocol, system instructions, and context size to the selected model.

## Context

A Pi conversation may move between models without starting a new session.
The requirement is not that every provider receive byte-identical payloads, which their APIs cannot accept, but that Pi preserve the same conversational facts, expose any lossy projection, and never present a prior model's token measurement as if it described the current model.

## Current state

Pi stores a versioned JSONL session tree whose message entries retain assistant provider, API, model, usage, tool calls, and results.
A model switch appends a `model_change` entry and changes the active model without rewriting earlier entries (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/docs/session-format.md:174-219`, `/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:1195-1279`).

Before a provider call, Pi projects that common history into a model-compatible view.
Cross-model replay may drop opaque reasoning, convert visible thinking to text, remove thought signatures, normalize tool-call IDs, synthesize missing tool results, and replace images when the target lacks vision (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/api/transform-messages.js:1-185`).

The local configuration enables automatic compaction with 10,000 recent tokens and an 8,192-token reserve, while selectable model windows range from 200k to 500k and include provider-defined models (`roles/ai/files/pi/settings.json:3-28`, `roles/ai/files/pi/models.json:2-29`).
The custom footer currently reports `ctx.getContextUsage()` and deliberately shows an unknown value only after compaction (`roles/ai/files/pi/extensions/footer.ts:182-204`).

Pi's current estimator is not model-aware.
After a switch, it can take the previous model's last assistant usage and divide it by the newly selected model's context window (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/compaction/compaction.js:119-155`, `/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:2632-2670`).
The same stale measurement can influence the pre-turn automatic compaction check (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:864-869,1567-1651`).

## Findings

### What should remain stable across models?

- **Answer:** Treat the active session branch as the canonical conversation ledger, but call it a common internal transcript rather than a model-neutral transcript because it retains provider-bound metadata and opaque reasoning. Give each logical context a stable identity derived from the session ID, active leaf ID, latest compaction ID, system-prompt hash, and active-tool-schema hash. A model switch changes the projection, not that logical identity.
- **Evidence:** Session entries are append-only children with stable IDs and parent IDs, and model changes are explicit entries (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/docs/session-format.md:174-219`). Existing messages are not rewritten during a switch (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:1201-1217`).
- **Confidence:** high
- **Assumptions:** A hash is used for identity and diagnostics only, never as a substitute for the underlying session entries.

### What must be tracked per model?

- **Answer:** Record an effective-context view containing model provider/API/ID, context window, logical-context ID, measurement quality (`exact`, `estimated`, or `unknown`), and degradation flags for reasoning, images, tool protocol, compaction, and provider-added instructions. Never carry an `exact` usage value across a model change. Until the selected model returns usage, show a model-specific estimate or unknown state.
- **Evidence:** Exact replay depends on provider, API, and model equality, while unsupported content is transformed conditionally (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/api/transform-messages.js:20-35,68-120`). The current usage estimator finds the latest assistant usage without comparing its originating model (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/compaction/compaction.js:119-155`).
- **Confidence:** high
- **Assumptions:** Provider-reported usage remains the best exact measurement after a successful response, even though it arrives after the request.

### Can this be implemented as a local extension?

- **Answer:** Visibility and continuity tracking can. A local extension can observe `model_select`, inspect or non-destructively modify pre-call messages through `context`, inspect provider payloads through `before_provider_request`, and persist metadata as non-context custom entries. It should persist only hashes, counts, source entry IDs, and degradation flags, not raw prompts or provider payloads. A full compaction fix cannot be cleanly implemented there because `session_before_compact` runs after Pi has already made its threshold decision.
- **Evidence:** Pi documents the relevant hooks and persistence API (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md:657-700,722-735,1453-1469`). The compaction extension hook can cancel or replace compaction content but does not replace the internal threshold estimate (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:1650-1689`). This repo already auto-discovers symlinked local extensions (`roles/ai/tasks/main.yml:323-334`).
- **Confidence:** high
- **Assumptions:** The extension remains provider-agnostic and does not import Pi's private adapter internals.

### Is a generated handoff required on every switch?

- **Answer:** No. The full active branch remains available, so automatic re-summarization on every switch adds cost and summary drift. Add an optional structured continuity capsule only at a genuinely lossy boundary, such as compaction or a switch to a model that cannot consume prior images or opaque reasoning. The capsule should list task goal, constraints, decisions, pending work, relevant files, unresolved questions, and source entry IDs.
- **Evidence:** Pi rebuilds active context from the session branch and retains pre-compaction history in the JSONL tree (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/session-manager.js:124-236`; `/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/README.md:272-280`). Cross-model loss is conditional rather than universal (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/api/transform-messages.js:20-35,68-120`).
- **Confidence:** high
- **Assumptions:** A capsule is marked as derived state and linked to source entries so it can be regenerated or challenged.

## Contradictions

The installed session-format documentation says newer compactions include a self-contained `retainedTail` (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/docs/session-format.md:229-248`), but Pi 0.84.3's coding-session path appends only the summary, first kept entry, token data, usage, and details (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/session-manager.js:802-817`).
Any continuity implementation should test the installed behavior rather than rely on the newer-format statement.

## Proposed approach

1. **Define two layers.** Keep Pi's session branch as the canonical ledger. Add an effective-context record keyed by logical-context ID and model identity. Do not create parallel transcripts.
2. **Build `context-continuity.ts` locally.** On `model_select`, mark usage stale, compare source and target capabilities, persist a small custom entry, and show one warning only when content will degrade. On `session_start`, reconstruct its state from custom entries.
3. **Make the footer honest.** After a model change, render `?/<new window>` or `estimated` until an assistant response from the selected provider/API/model supplies matching usage. Extend existing footer tests for small-to-large, large-to-small, resume, compaction, and repeated switches.
4. **Patch Pi core upstream.** Make `estimateContextTokens` accept the active model and reuse assistant usage only when provider/API/model match. Otherwise estimate the current messages and expose provenance. Use that result in both `getContextUsage()` and pre-turn compaction checks.
5. **Add loss-boundary capsules later.** Generate a structured, source-linked capsule only for compaction or detected capability loss. Keep it visible and auditable rather than silently replacing transcript content.

Rejected alternatives:

- **One global context percentage:** rejected because tokenization and context windows are model-specific.
- **Rewrite history for the target provider:** rejected because it destroys provenance and provider-bound replay data.
- **Summarize on every switch:** rejected because it adds latency, cost, and model-generated drift when no loss occurred.
- **Normalize everything in the extension `context` hook:** rejected because Pi's provider adaptation occurs later and duplicating private adapter logic would be brittle.

## Risks and open questions

- Pi does not expose a public provider-independent tokenization API, so pre-response counts remain estimates.
- `before_provider_request` payloads are provider-specific and later extensions can still replace them. Store metrics or hashes only, never payload content.
- A smaller-window target may require compaction before its first successful response. The core patch needs a conservative estimated path rather than simply suppressing compaction.
- Live system prompts and active tool schemas can change independently of the transcript. Hashing them makes the change visible but does not make provider instruction precedence identical.
- Decide whether the upstream fix belongs in `earendil-works/pi-mono` or remains a local patch after a minimal reproduction demonstrates the stale-usage bug.

## Rough effort

- Local tracker, footer behavior, and focused tests: 1 to 2 engineering days.
- Pi core estimator and compaction fix with upstream tests: 2 to 4 engineering days.
- Optional structured loss-boundary capsule: 2 to 4 additional days, mainly for schema design and adversarial tests.

A robust baseline is therefore about 3 to 6 engineering days. Exact cross-provider semantic equivalence is not an achievable acceptance criterion.

## Verification notes

- **Common transcript claim:** challenged as too model-neutral. **Partially held.** Pi preserves one internal transcript, but assistant entries contain provider-bound metadata and signed or opaque reasoning.
- **Cross-model semantic divergence:** challenged because several transforms preserve equivalence. **Partially held.** Tool-ID mapping and native system channels are safeguards, but reasoning loss, unsupported images, synthetic tool results, and provider-added instructions prevent a guarantee of equivalence.
- **Stale usage after model switch:** challenged against all compaction paths. **Held.** No model check invalidates prior usage before the new model responds, and threshold compaction can consume the stale value.
- **Extension-only implementation:** challenged for hidden APIs and workarounds. **Partially held.** An extension can implement diagnostics and state, but it cannot replace the core pre-compaction threshold calculation cleanly.

## Sources

- Direct ask (2026-08-28)
- Dotfiles repository: `roles/ai/files/pi/`, `roles/ai/tasks/main.yml`, `docs/internals/pi-harness.md`, `docs/internals/context-hygiene.md`, and related tests
- Installed Pi 0.84.3 documentation: `/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/README.md` and `docs/`
- Installed Pi 0.84.3 implementation: `/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/`
- Installed pi-ai implementation: `/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/`
- Pi project: https://github.com/earendil-works/pi-mono
- Anthropic TypeScript SDK message types: https://github.com/anthropics/anthropic-sdk-typescript/blob/main/src/resources/messages/messages.ts
- Google Gen AI JavaScript types: https://github.com/googleapis/js-genai/blob/main/src/types.ts

## Next steps

Approve a small implementation spike with two acceptance tests first: switching to a smaller model must not reuse the previous model's exact usage, and a switch to a model without vision must surface a capability-loss warning while preserving the original session entries.
Use the spike to decide whether to submit the estimator fix upstream before adding optional semantic capsules.
