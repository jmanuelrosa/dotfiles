/**
 * velocity.ts - how much this session has changed, in pi's footer.
 *
 * The pi half of the `⚡ +120/-30` segment Claude Code's statusline.sh prints, and the only
 * segment of that status line worth porting. Pi's own footer already shows the model, the
 * provider, the thinking level, the context percentage against the window, the cache hit rate,
 * the cwd with its git branch and the session cost, so a second display of any of those would
 * spend footer width restating what is already two columns to the left. Edit velocity is the
 * one thing Claude shows that pi has no equivalent of.
 *
 * The counts come from the patch pi itself applied, never from a diff computed here:
 * `EditToolDetails.patch` is a standard unified patch, so counting its `+` and `-` lines is
 * counting what actually landed on disk. That matters because each entry in an `edits` array is
 * matched against the original file rather than against the result of the entries before it, so
 * measuring the two halves of those entries is not the same number and would drift from what
 * `git diff` reports for the same session.
 *
 * A `write` is counted as added lines only, and that is a known understatement rather than an
 * oversight: the event fires after the file is written, so the content it replaced is already
 * gone and no removal count can be recovered without having read the file first. Overwriting a
 * long file therefore reads as pure growth. The segment is a sense of scale to glance at, not
 * an audit, and a `git diff --stat` is one command away when the real figure matters.
 *
 * Nothing here throws. A `tool_result` handler is not the gate a `tool_call` handler is, so a
 * failure would cost a footer segment rather than a blocked call, but the extension directory
 * is shared with guardrails.ts and one convention for both is easier to keep than two.
 */

import {
  type ExtensionAPI,
  type ExtensionContext,
  isEditToolResult,
  isWriteToolResult,
  type ToolResultEvent,
} from "@earendil-works/pi-coding-agent";

// Namespaces the footer slot. Pi keys statuses by string and last writer wins, so a name no
// other extension would pick is what keeps two of them from erasing each other.
const STATUS_KEY = "dotfiles-velocity";

interface Tally {
  added: number;
  removed: number;
  files: Set<string>;
}

function empty(): Tally {
  return { added: 0, removed: 0, files: new Set() };
}

function lines(text: unknown): number {
  if (typeof text !== "string" || text === "") return 0;
  // A trailing newline terminates the last line rather than starting another, which is the
  // same count `wc -l` gives and the one a unified patch would have produced.
  const body = text.endsWith("\n") ? text.slice(0, -1) : text;
  return body.split("\n").length;
}

/**
 * The added and removed line counts of a unified patch.
 *
 * `+++` and `---` are the file headers rather than changed lines, and a `\` line is the
 * no-trailing-newline marker. Everything else beginning with `+` or `-` is a real line.
 */
function countPatch(patch: unknown): { added: number; removed: number } {
  let added = 0;
  let removed = 0;
  if (typeof patch !== "string") return { added, removed };
  for (const line of patch.split("\n")) {
    if (line.startsWith("+++") || line.startsWith("---")) continue;
    if (line.startsWith("+")) added += 1;
    else if (line.startsWith("-")) removed += 1;
  }
  return { added, removed };
}

function record(tally: Tally, event: ToolResultEvent): void {
  const path = event.input?.path;
  if (typeof path === "string" && path !== "") tally.files.add(path);

  if (isEditToolResult(event)) {
    const { added, removed } = countPatch(event.details?.patch);
    tally.added += added;
    tally.removed += removed;
    return;
  }
  tally.added += lines(event.input?.content);
}

function render(tally: Tally, ctx: ExtensionContext): string {
  const theme = ctx.ui.theme;
  const count = tally.files.size;
  const files = `${count} file${count === 1 ? "" : "s"}`;
  // The theme's own diff colours rather than success and error, so the segment agrees with the
  // diffs pi renders above it instead of reading as a pass and a failure.
  return [
    theme.fg("dim", "⚡ "),
    theme.fg("toolDiffAdded", `+${tally.added}`),
    theme.fg("dim", "/"),
    theme.fg("toolDiffRemoved", `-${tally.removed}`),
    theme.fg("dim", ` ${files}`),
  ].join("");
}

// The reasons that make the running total somebody else's number. `startup` is already zero and
// `reload` is the same session read again, so resetting on either would be the one case where a
// count is lost rather than handed over.
const FRESH = new Set(["new", "resume", "fork"]);

export default function (pi: ExtensionAPI) {
  let tally = empty();

  pi.on("session_start", async (event, ctx) => {
    try {
      if (!FRESH.has(event.reason)) return;
      tally = empty();
      // Cleared rather than rendered as `+0/-0`, so a fresh session shows no segment at all
      // until it changes something.
      ctx.ui.setStatus(STATUS_KEY, undefined);
    } catch {
      // As below: a footer segment is never worth interrupting a session for.
    }
  });

  pi.on("tool_result", async (event, ctx) => {
    try {
      // A refused or failed call changed nothing, and a gate the guardrails extension blocked
      // never reaches a result at all.
      if (event.isError) return;
      if (!isEditToolResult(event) && !isWriteToolResult(event)) return;
      record(tally, event);
      ctx.ui.setStatus(STATUS_KEY, render(tally, ctx));
    } catch {
      // A footer segment is never worth interrupting a session for.
    }
  });
}
