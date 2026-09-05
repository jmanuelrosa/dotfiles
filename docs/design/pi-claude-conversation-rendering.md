# Pi Claude-Style Conversation Rendering - Design Doc

**Status:** Implemented
**Author:** José Manuel Rosa Moncayo
**Date:** 2026-09-02
**Scope:** Pi built-in tool rendering and thinking-duration rows

## Summary

Pi will keep the current Solarized conversation styling while replacing always-expanded built-in tool output with Claude-like semantic rows and bounded previews. The default view will show enough source, diff, command, and search output to remain useful; `Ctrl+O` will reveal the complete available detail. Native thinking stays hidden behind Pi's own inline `✻ Thinking…` label, which remains available through `Ctrl+T`. An earlier revision of this design instead produced a durable `Thought for Ns` row per completed thinking block; superseded in §4.

## Motivation

The current hierarchy successfully aligns built-in tool calls on `●` and nests results under `└`, but it forces both native call and result renderers into `expanded: true` (`roles/ai/files/pi/extensions/claude-ui.ts:219-256`). Large reads, writes, diffs, and command results therefore dominate the conversation and make assistant narration difficult to scan.

Claude Code uses a different information hierarchy: a semantic tool label, a short result summary, a bounded excerpt, and an explicit expansion path. Pi exposes only a boolean expanded state, but its public renderer API permits custom default previews and complete expanded output. Pi's own built-in-renderer example already uses bounded 15-, 20-, and 30-line excerpts (`/opt/homebrew/Cellar/pi-coding-agent/0.84.4/libexec/lib/node_modules/@earendil-works/pi-coding-agent/examples/extensions/built-in-tool-renderer.ts:32-249`).

Thinking has a separate limitation. Pi emits exact `thinking_start` and `thinking_end` events with a `contentIndex` (`/opt/homebrew/Cellar/pi-coding-agent/0.84.4/libexec/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/types.d.ts:400-452`), but its native hidden-thinking label is global and retroactively updates every assistant component. Per-block native labels are therefore not possible through Pi 0.84.4's public APIs. Durable custom entries provide the closest supported approximation without replacing assistant rendering or patching Pi internals.

## Non-goals

- Reproduce Claude's conversation UI pixel for pixel.
- Patch Pi internals or depend on files under `dist/modes` from repository code.
- Change the Solarized theme, startup header, footer, or velocity segment.
- Change package-tool renderers.
- Hide or alter tool results sent to the model; this design changes presentation only.
- Style ordinary assistant narration differently from final assistant prose.
- Place duration rows inside native assistant components with exact block-level ordering.

## Background

### Built-in tool rendering today

`claude-ui.ts` re-registers Pi's built-in tool definitions and wraps their native components with `HierarchyComponent` (`roles/ai/files/pi/extensions/claude-ui.ts:114-147,219-272`). The wrapper provides the desired sibling and child indentation, but both renderer calls override Pi's state with `expanded: true`. The existing semantic summary helpers at `roles/ai/files/pi/extensions/claude-ui.ts:149-217` are used only when a native renderer returns no lines.

Pi permits a same-name tool registration to replace rendering while preserving the original execution definition. Renderer context includes component reuse, errors, partial state, and a boolean `expanded` value (`/opt/homebrew/Cellar/pi-coding-agent/0.84.4/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts:307-377`). There is no third native display state, so the extension must define its own bounded default policy.

### Thinking rendering today

`hideThinkingBlock` is true (`roles/ai/files/pi/settings.json:34`), so native thinking is hidden by default. Pi's assistant component merges adjacent thinking blocks and uses one static label when thinking is hidden (`/opt/homebrew/Cellar/pi-coding-agent/0.84.4/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/modes/interactive/components/assistant-message.js:67-119`). `setHiddenThinkingLabel()` applies globally to existing and streaming assistant components (`/opt/homebrew/Cellar/pi-coding-agent/0.84.4/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/modes/interactive/interactive-mode.js:1694-1703`).

Pi's public API can append custom entries that do not participate in model context and can register a durable renderer for them (`/opt/homebrew/Cellar/pi-coding-agent/0.84.4/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts:860-875,947-969`). This is the supported persistence and rendering surface for duration rows.

## Design rules

- A collapsed tool result must provide a semantic summary and a bounded useful excerpt.
- `Ctrl+O` must reveal all detail available to the renderer.
- Errors remain fully visible without expansion.
- Tool labels describe completed operations with stable names; live activity remains present tense.
- All indentation belongs to one hierarchy component so wrapped lines stay aligned.
- Theme colors use semantic Pi tokens only.
- Thinking rows are durable display metadata and never enter model context.
- Native thinking is hidden by default but remains available through `Ctrl+T`.
- The extension uses public Pi APIs only.

The tool renderer remains a deep module: its public behavior is the existing built-in tool interface and two expansion states, while tool-specific summaries, clipping, indentation, and error policy remain internal.

## Design

### 1. Semantic tool rows

Add a tool-specific call formatter separate from the live `describeActivity()` formatter:

```text
⏺ Read(src/auth.ts)
⏺ Write(config/settings.json)
⏺ Update(roles/ai/tasks/main.yml)
⏺ Bash(make test)
⏺ Grep("token refresh", src)
⏺ Find(*.ts, roles/ai)
⏺ List(docs/design)
```

Long commands and arguments wrap within the supplied component width. Continuation lines align after the `⏺ ` prefix. The call row does not include full write content or an edit diff; those belong to the result child.

### 2. Balanced result previews

Replace forced native expansion with a result component that owns a summary, excerpt, and omission hint. The default limits are:

| Content | Default limit | Selection |
|---|---:|---|
| Read and write source | 10 lines | First lines |
| Grep, find, and list output | 10 lines | First rows |
| Bash and PowerShell output | 20 lines | Last lines |
| Edit diff | 30 lines | First diff lines |

The component renders:

```text
⏺ Read(src/auth.ts)
  ⎿  Read 42 lines
    import { ... }
    ...
    +32 lines (ctrl+o to expand)
```

The actual shortcut label comes from Pi's keybinding-aware `keyHint("app.tools.expand", ...)` helper instead of hard-coding `Ctrl+O`.

When expanded, the same component removes the preview limit and omission hint. It renders all text present in the tool result, all write content from the call arguments, or the complete edit diff from result details. Pi's execution-level truncation limits still apply; the UI cannot recover output the tool did not return.

### 3. Tool mapping

| Tool | Result summary | Preview source |
|---|---|---|
| Read | `Read N lines` or image metadata | Result text |
| Write | `Wrote N lines to path` | `args.content` |
| Update | `Updated N blocks in path` with `+A/-D` when available | `details.diff` |
| Bash / PowerShell | `Completed`, exit/failure state, and duration when available | Result output tail |
| Grep | `Found N matches` or `No matches found` | Result text |
| Find | `Found N files` or no-results message | Result text |
| List | `Listed N entries` or empty-directory message | Result text |

Partial results reuse the same component and update in place through `lastComponent`. Failed results render the semantic failure summary followed by the complete returned error text, regardless of expansion state.

### 4. Thinking-duration entries (superseded)

**Superseded by `docs/plans/2026-09-04-following-the-idea-to-cozy-feigenbaum.md`.** On a model that interleaves reasoning between every text block and tool call, a single turn appends ten to fifteen duration entries, and `interactive-mode.js:2920-2925` splices each one *before* the still-streaming assistant component - so every entry for a turn renders as a clump ahead of the prose that produced it, not beside it. This is the answer to the open question below: sibling ordering does not interleave, it clumps. The design was replaced by restoring Pi's own inline hidden-thinking label (§5), which already renders once per run of thinking blocks in the correct position; the fix was to stop blanking it, not to build a parallel display. This section is kept for the record of what was tried and why it failed.

Register an entry renderer with a repository-owned type such as `dotfiles-thinking-duration`:

```ts
interface ThinkingDurationEntry {
  durationMs: number;
  timestamp: number;
  contentIndex: number;
  responseId?: string;
}
```

`message_update` receives the cumulative assistant message and its stream event (`/opt/homebrew/Cellar/pi-coding-agent/0.84.4/libexec/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts:578-589`). The extension will:

1. Record `Date.now()` for each `thinking_start`, keyed by the active assistant lifecycle and `contentIndex`.
2. On the matching `thinking_end`, calculate elapsed milliseconds.
3. Append a custom entry through `pi.appendEntry()`.
4. Render the entry as muted `Thought for Ns` text.
5. Clear unfinished timers at the next assistant lifecycle, turn reset, or session shutdown.

Durations use rounded whole seconds with a minimum display of one second. A block without a matching end event does not produce a duration row, avoiding misleading results after cancellation or stream failure.

Custom entries are excluded from model context and survive normal session reloads. Older entries may disappear when they fall before a compaction checkpoint, matching Pi's existing session-history behavior.

### 5. Native thinking visibility (revised)

**Revised by `docs/plans/2026-09-04-following-the-idea-to-cozy-feigenbaum.md`.** `hideThinkingBlock` stays true, but the hidden label is now set to `"✻ Thinking…"` instead of the empty string, since §4's custom duration row no longer exists to duplicate. `assistant-message.js:85-115` already renders one hidden-thinking label per run of thinking blocks, inline between the surrounding text blocks - the correct position and granularity that §4's sibling entries could not reach. Reset the label on extension shutdown, unchanged from the original design.

`Ctrl+T` continues to reveal native thinking content, now in addition to the inline label rather than alongside a separate duration row.

### 6. Documentation and tests

The Pi harness documentation and AI role README describe bounded defaults, `Ctrl+O`, and `Ctrl+T`. Tests exercise renderers through the public extension API rather than importing Pi internals.

## Runtime behaviour matrix

| State | Tool display | Thinking display |
|---|---|---|
| Tool running | Semantic `⏺` call and live working indicator | Unchanged |
| Tool succeeds, default view | `⎿` summary plus bounded excerpt | Unchanged |
| Tool succeeds, `Ctrl+O` | Complete available result detail | Unchanged |
| Tool fails | Full returned error, even when collapsed | Unchanged |
| Thinking streams | Native block hidden; existing working UI continues | No duration row until completion |
| Thinking completes | Unchanged | Native inline `✻ Thinking…` label (see §4 supersession) |
| User presses `Ctrl+T` | Unchanged | Native thinking content becomes visible in addition to the duration row |
| Session reloads | Tool transcript renders from persisted calls/results | Duration entries render from session data |
| Session compacts | Pi's normal retained tool history | Pre-checkpoint duration entries may be omitted |

## Alternatives considered

- **Always-expanded native renderers:** Preserves detail but produces the current oversized conversation and makes `Ctrl+O` ineffective.
- **Native collapsed renderers only:** Too inconsistent. Successful reads may render no result, writes put content in the call, and edits do not honor expansion uniformly.
- **Summary-only rows:** Too little context and repeats the information-hiding problem that prompted the previous rollback.
- **Global hidden-thinking label:** Cannot preserve per-block durations because every assistant component receives the latest label.
- **Custom messages:** Can render durations but participate in model context, which wastes tokens and changes semantics.
- **Patch native assistant components:** Could achieve exact placement but is fragile across Pi upgrades and violates the public-API boundary.

## Testing Decisions

Tests assert external rendered behavior:

- semantic call labels and hierarchy indentation;
- each tool's summary and default preview limit;
- omission counts and keybinding-aware expansion hints;
- complete expanded content;
- full collapsed errors;
- partial-render component reuse;
- thinking start/end correlation and duration rounding;
- no entry for incomplete thinking;
- custom entries use a registered renderer and are excluded from message context by API choice;
- startup hides native thinking labels and shutdown restores the default;
- no imports from `dist/modes`.

The existing Node-driven extension fixture in `lib/python/tests/test_pi_claude_ui.py:22-218` remains the primary test pattern.

## Open questions

- Visual inspection may require adjusting preview limits or vertical spacing after `/reload`; these are presentation constants, not architectural changes.
- Pi's insertion point for multiple duration entries in one assistant message must be confirmed in a live session. The accepted boundary is sibling ordering, not exact inline placement.

## Appendix - affected files

- `roles/ai/files/pi/extensions/claude-ui.ts`
- `roles/ai/files/pi/settings.json`
- `lib/python/tests/test_pi_claude_ui.py`
- `docs/internals/pi-harness.md`
- `roles/ai/README.md`
- `docs/design/pi-claude-conversation-rendering.md`
