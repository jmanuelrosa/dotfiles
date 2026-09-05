# Cross-Model Context Consistency - Design Doc

**Status:** Draft
**Author:** José Manuel Rosa Moncayo
**Date:** 2026-08-28
**Scope:** Pi session context visibility, model-switch continuity, context usage estimation, and automatic compaction

## Summary

Pi will continue to use its existing session branch as the authoritative conversation history while adding an explicit per-model projection state.
A local extension and footer change will make model switches, capability loss, and stale usage visible without rewriting conversation content.
A separate upstream Pi change will prevent token usage from one model from driving another model's context percentage or automatic compaction.

## Motivation

Pi supports changing providers and models inside one conversation.
A switch appends a `model_change` entry and preserves earlier messages, so the underlying conversation remains available (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/docs/session-format.md:174-219`, `/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:1195-1279`).

The effective context is not identical after every switch.
Pi may drop opaque reasoning, convert visible thinking to text, remove thought signatures, normalize tool-call IDs, synthesize missing tool results, or replace images when the target model lacks vision (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/api/transform-messages.js:1-185`).
These adaptations are required for provider compatibility, but Pi does not currently present them as a change in the effective context.

Context usage is also misleading immediately after a model switch.
`estimateContextTokens()` selects the latest assistant usage without checking which model produced it, and `getContextUsage()` divides that value by the active model's context window (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/compaction/compaction.js:119-155`, `/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:2632-2670`).
The same value can influence the pre-turn automatic compaction decision (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:864-869,1567-1651`).
Switching to a smaller window may therefore trigger unnecessary compaction, while switching to a larger window may understate pressure.

The local footer currently treats usage as unknown only after compaction (`roles/ai/files/pi/extensions/statusline.ts:182-204`).
The model-switch boundary needs the same honesty until the selected model has supplied relevant usage.

## Non-goals

- Guarantee byte-identical provider payloads across models.
- Guarantee identical token counts across tokenizers or providers.
- Rewrite persisted session messages into a target model's native format.
- Reveal or preserve hidden model reasoning that a provider marks opaque.
- Generate a new summary on every model switch.
- Log raw prompts, provider payloads, tool arguments, images, or reasoning blocks.
- Maintain a private fork of Pi while an upstream correction is reviewed.
- Change Pi's compaction summary format in the first release.

## Background

### Pi session history today

Pi stores a versioned JSONL tree.
Each entry has an ID and parent ID, while assistant messages retain their originating provider, API, model, usage, and content metadata (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/docs/session-format.md:174-219`).

A switch changes the active model and appends a model-change entry.
It does not rewrite existing messages (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:1201-1217`).
This common internal transcript is the authority for conversational facts, but it is not fully model-neutral because it can contain provider-bound signatures and opaque data.

### Provider projection today

Pi transforms the active message list before provider serialization.
An exact same-model replay requires provider, API, and model ID equality (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/api/transform-messages.js:68-70`).
Cross-model transformations preserve references where possible, such as rewriting matching tool-call and result IDs together, but semantic equivalence is not guaranteed (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/api/transform-messages.js:40-64,100-185`).

### Local extension surface

Pi exposes the hooks needed for local visibility.
`model_select` reports the old model, new model, and switch source.
`context` receives a deep copy of the messages before each model call.
`appendEntry()` persists extension state without adding it to LLM context (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/docs/extensions.md:657-665,722-735,1453-1469`).

The extension context exposes the selected model, session manager, current context usage, and system prompt.
The extension API exposes the active tools (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts:219-256,968-978`).
Local extension files are already installed through the role's extension glob, so a new top-level extension requires no additional Ansible task (`roles/ai/tasks/main.yml:323-334`).

### Compaction boundary

The local extension can observe or cancel a requested compaction, but `session_before_compact` runs after Pi has made its threshold decision (`/opt/homebrew/Cellar/pi-coding-agent/0.84.3/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js:1650-1689`).
Cancelling compaction after a switch could trade a false positive for a provider overflow.
The local implementation must not use that unsafe workaround.

## Design rules

- The active Pi session branch remains the only authoritative conversation ledger.
- A model switch changes the effective projection, not the logical conversation identity.
- Usage produced before the current model epoch is never labeled exact for the active model.
- The model epoch begins at the latest model-change entry on the active branch.
- Capability loss is reported only when the active context contains affected content.
- Local tracking records metadata, hashes, counts, and entry IDs only.
- The first release observes context but does not modify messages in the `context` hook.
- Automatic compaction remains enabled and is corrected in Pi core rather than bypassed locally.
- Custom-entry payloads are versioned and reconstructable after resume.
- Notifications are emitted once per model epoch, not once per provider request.
- The continuity tracker is a deep module: event handlers provide a narrow input surface while session traversal, freshness checks, and degradation detection remain internal.

## Design

### 1. Logical context identity

The logical context identifies the model-independent conversational state being projected.
It excludes model-change, thinking-level, and continuity-tracker entries so switching models does not create a new logical conversation version by itself.

```typescript
interface LogicalContextIdentity {
  sessionId: string;
  contextEntryId: string | null;
  compactionEntryId: string | null;
  systemPromptHash: string;
  activeToolsHash: string;
}
```

`contextEntryId` is the latest active-branch entry that can affect LLM context, including a message, compaction, or branch summary.
`compactionEntryId` identifies the summary boundary independently so two projections cannot silently disagree about whether detailed history or a compacted summary is active.
The hashes use a fixed algorithm and canonical ordering, but the original prompt and tool schemas are not persisted by this feature.

### 2. Model projection state

Each model epoch has one projection state.
The state is persisted as a custom entry with custom type `context-continuity`.

```typescript
type UsageQuality = "exact" | "estimated" | "unknown";

type Degradation =
  | "images-unsupported"
  | "opaque-reasoning-unavailable"
  | "orphaned-tool-result-synthesized"
  | "smaller-context-window";

interface ContextProjectionEntryV1 {
  version: 1;
  event: "model-switch";
  source: "set" | "cycle";
  logicalContext: LogicalContextIdentity;
  previousModel: ModelIdentity | null;
  activeModel: ModelIdentity;
  usageQuality: "unknown";
  degradations: Degradation[];
}

interface ModelIdentity {
  provider: string;
  api: string;
  id: string;
  contextWindow: number;
}
```

The extension does not append a duplicate entry when `model_select` has source `restore`.
On restore, it rebuilds state from the active branch and displays the current projection status.
Only explicit set and cycle operations persist model-switch records.

`smaller-context-window` is informational and is emitted only when the target window is smaller than the previous window.
It does not claim that compaction is required because the pre-response token estimate may be uncertain.

### 3. Continuity extension

Create `roles/ai/files/pi/extensions/context-continuity.ts`.
The extension owns model-epoch reconstruction, degradation detection, persistence, and one-time notifications.

```typescript
export default function contextContinuity(pi: ExtensionAPI): void {
  pi.on("session_start", (_event, ctx) => {
    restoreProjectionState(ctx.sessionManager.getBranch());
  });

  pi.on("model_select", (event, ctx) => {
    const projection = buildProjection(event, ctx, pi.getActiveTools());
    if (event.source !== "restore") {
      pi.appendEntry("context-continuity", projection);
    }
    notifyDegradationsOnce(projection, ctx);
  });

  pi.on("context", (event, ctx) => {
    observeEffectiveMessages(event.messages, ctx.model);
  });
}
```

The `context` handler inspects only the messages Pi has selected after session and compaction processing.
It does not return replacement messages in version 1.
This avoids duplicating Pi's provider adapters or changing the conversation while still allowing warnings to reflect the actual active context.

The extension uses public Pi types and APIs only.
It does not import `dist/` implementation modules such as `transform-messages.js` or `compaction.js` because those paths are not stable extension contracts.

### 4. Degradation detection

The local detector reports observable capability boundaries without attempting to duplicate every provider transform.

| Condition in active context | Target condition | Reported degradation |
|---|---|---|
| User or tool content contains an image | `model.input` lacks `image` | `images-unsupported` |
| Assistant content contains redacted thinking or a thought signature from another model | Provider/API/model differs | `opaque-reasoning-unavailable` |
| Tool call has no matching result in the selected active context | Any target model | `orphaned-tool-result-synthesized` |
| Target context window is smaller than previous window | Window decreases | `smaller-context-window` |

Tool-call ID normalization is not reported because Pi preserves call-result linkage where possible.
Provider-native system instruction encoding is not reported because differing transport syntax alone does not establish semantic loss.

Notifications state what changes, not what hidden reasoning contained.
For example: `Context projection changed: 2 images are unavailable to cursor/composer-2-5.`

### 5. Honest footer usage

Modify `roles/ai/files/pi/extensions/statusline.ts` so `contextSegment()` checks whether usage belongs to the current model epoch before rendering a percentage.

The freshness helper traverses the active branch and finds the latest of:

- a model-change entry,
- a compaction entry,
- a valid assistant response matching the current provider, API, and model.

Usage is stale when no matching valid assistant response exists after both the latest model change and latest compaction.
In that state the footer renders `?/<context-window>` and may append a short `model changed` status through the existing extension-status surface.

After a matching assistant response, the footer resumes Pi's normal token and percentage display.
The local footer does not invent an estimated token number because Pi exposes no public provider-independent tokenizer.

```typescript
interface UsageFreshness {
  quality: "exact" | "unknown";
  reason?: "model-changed" | "compacted";
}
```

This local behavior corrects the display but not Pi's internal compaction decision.
The footer must not imply that internal compaction is safe until the upstream change is installed.

### 6. Upstream model-aware usage estimation

Submit a Pi upstream change that introduces a model epoch boundary into context estimation.
The installed implementation seams are `dist/core/compaction/compaction.js:119-160` and `dist/core/agent-session.js:1567-1651,2632-2670`; the contribution will modify their source equivalents in `earendil-works/pi-mono`.

The estimator will follow these rules:

1. Find the latest model-change and compaction boundaries on the active branch.
2. Reuse provider usage only from a valid assistant response after both boundaries.
3. Require provider, API, and model ID to match the active model.
4. If no eligible usage exists, estimate all active messages using Pi's generic estimator.
5. Return measurement provenance with the count.
6. Use the same result for footer context usage, pre-turn threshold checks, post-turn checks, and `tokensBefore` compaction metadata.

```typescript
type ContextEstimate = {
  tokens: number | null;
  quality: "exact" | "estimated" | "unknown";
  usageMessageIndex: number | null;
};
```

Adding `quality` to the internal estimate is required.
Exposing it through `getContextUsage()` should be an additive optional field so existing extensions remain compatible.
If upstream maintainers reject the public field, the core correctness change can still land while the local footer retains its branch-based freshness check.

### 7. Delivery sequence

1. Add failing local footer tests for model-switch freshness.
2. Add the continuity extension and its event-level tests.
3. Update the footer to render unknown usage after a switch.
4. Prepare an upstream Pi reproduction for stale cross-model usage and premature compaction.
5. Add failing upstream tests for switch direction, restore, compaction boundary, and switch-back epochs.
6. Implement the model-aware estimator upstream.
7. Upgrade the Homebrew `pi-coding-agent` formula after the upstream release is available.
8. Verify the local extension against the released API and remove any temporary compatibility wording from the warning.

The local extension and honest footer can ship before the upstream release.
The feature is not considered fully complete until the installed Pi version contains the compaction correction.

## Runtime behaviour matrix

| Scenario | Logical context | Footer usage | Warning | Automatic compaction |
|---|---|---|---|---|
| Start and respond with the default model | Advances with messages | Normal after response | None | Existing behavior, then model-aware after upstream release |
| Switch to a model with the same capabilities | Unchanged at switch | Unknown until matching response | None | Generic estimate until matching response after upstream release |
| Switch to a smaller context window | Unchanged at switch | Unknown until matching response | Smaller-window notice once | Generic estimate against target window after upstream release |
| Switch from vision to text-only with images in active context | Unchanged at switch | Unknown until matching response | Image-loss warning once | Based on target projection after upstream release |
| Switch across providers with opaque reasoning | Unchanged at switch | Unknown until matching response | Reasoning-metadata warning once | Generic estimate until matching response after upstream release |
| Switch away and then back to an earlier model | Unchanged at each switch | Unknown again after returning | Only current capability losses | Old usage is not reused across the new epoch |
| Resume with the model restored | Reconstructed from branch | Normal only if matching usage follows latest boundaries | Existing unresolved loss status only | Model-aware branch reconstruction after upstream release |
| Compact current context | Advances to compaction boundary | Unknown until next valid response | None unless projection loses capabilities | Uses compacted context only |
| New model returns an error with no usage | Unchanged | Remains unknown | Existing projection warning only | Generic estimate, never prior-model exact usage |

## Alternatives considered

- **One global percentage across models:** Rejected because context windows, tokenizers, message transforms, and provider accounting differ.
- **Rewrite stored history on every switch:** Rejected because it would destroy source provenance and provider-bound replay data.
- **Generate a summary on every switch:** Rejected because it adds latency, cost, and model-generated drift when the active history is already usable.
- **Cancel automatic compaction locally after switches:** Rejected because it can turn a false-positive compaction into a provider context overflow.
- **Import Pi's private transform and estimator modules:** Rejected because extensions would become coupled to installed `dist/` paths and internal signatures.
- **Maintain a private Pi fork:** Rejected because the defect is narrow enough for an upstream correction and the local package is managed through Homebrew.
- **Inspect and persist final provider payloads:** Rejected because payloads are provider-specific, may be changed by later extensions, and contain sensitive conversation data.

## Testing Decisions

Tests assert observable state and rendering rather than private implementation structure.

### Local extension tests

Create `lib/python/tests/test_pi_context_continuity.py` using the existing extension execution pattern in `lib/python/tests/test_pi_velocity.py:146-163,268-271`.
Cover:

- explicit model selection appends one versioned custom entry,
- restore reconstructs state without appending a duplicate,
- repeated provider calls do not repeat notifications,
- text-only targets detect images in user and tool content,
- same-model replay does not report opaque-reasoning loss,
- cross-model replay reports opaque or signed reasoning loss without exposing content,
- orphaned tool calls are detected,
- no raw message or prompt content appears in persisted projection data.

### Footer tests

Extend `lib/python/tests/test_pi_statusline.py`, which already covers context thresholds and post-compaction unknown rendering (`lib/python/tests/test_pi_statusline.py:309-349`).
Cover:

- small-to-large switch,
- large-to-small switch,
- switch away and back,
- resume after model change,
- matching assistant response after switch,
- aborted and error responses,
- compaction followed by model switch,
- current context window displayed while usage is unknown.

### Repository verification

Run `make test` because it is the repository's unattended verification target.
Run the focused Python suites first, then the full target.
The Ansible extension glob already installs new extension files, so no task-level test is added unless implementation changes that glob.

### Upstream tests

The installed npm artifact does not include its upstream test sources, so test paths will be resolved in `earendil-works/pi-mono` before implementation.
Behavioral coverage must include:

- no reuse of pre-switch usage,
- provider/API/model equality,
- model epoch reset when switching back,
- generic estimation before the first target-model response,
- threshold compaction against the target window,
- error and zero-usage responses,
- compaction and model-change boundary ordering,
- additive compatibility of any public `quality` field.

## Open questions

- Will Pi upstream accept an additive `quality` field on `ContextUsage`, or should measurement provenance remain internal?
- Should the smaller-window notice remain informational, or include the generic estimate once the upstream API exposes measurement quality?
- Should structured continuity capsules become a separate follow-up design after real capability-loss cases demonstrate that warnings alone are insufficient?

## Appendix - affected files

### Local files to create

- `roles/ai/files/pi/extensions/context-continuity.ts`
- `lib/python/tests/test_pi_context_continuity.py`

### Local files to modify

- `roles/ai/files/pi/extensions/statusline.ts`
- `lib/python/tests/test_pi_statusline.py`

### Local files read for integration and verification

- `roles/ai/files/pi/settings.json`
- `roles/ai/files/pi/models.json`
- `roles/ai/tasks/main.yml`
- `docs/internals/pi-harness.md`
- `docs/internals/context-hygiene.md`
- `lib/python/tests/test_pi_velocity.py`

### Upstream components to modify after cloning `earendil-works/pi-mono`

- Source equivalent of `pi-coding-agent/dist/core/compaction/compaction.js`
- Source equivalent of `pi-coding-agent/dist/core/agent-session.js`
- Context-estimation and compaction test suites
- Public extension context types if measurement quality is exposed
