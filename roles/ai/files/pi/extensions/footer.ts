/**
 * footer.ts - pi's footer, rebuilt to say what Claude Code's statusline.sh says.
 *
 * Pi's own footer already carries the numbers: cwd with branch, token totals, cache hit rate,
 * cost, context percentage, model, provider, thinking level. What it does not carry is any of
 * the *reading* Claude's status line does for those numbers. A context figure of `36.4%/200k`
 * is a fact; `context [▓▓▓░░░░░] 73k (36%) handoff` is the same fact with the wrap-up threshold
 * from docs/internals/context-hygiene.md applied to it, and that threshold is the whole reason
 * the gauge is worth footer width. The same goes for the toolchain: which node and which package
 * manager a session is about to shell out to is a thing pi never shows and Claude always does.
 *
 * So this replaces the built-in footer through `ctx.ui.setFooter` rather than adding another
 * `setStatus` segment beside it, which is the trade this file exists to record. Adding a segment
 * would have been cheaper and upgrade-proof, but it would have printed a second context reading
 * two columns from pi's own, and two disagreeing renderings of one number is worse than either.
 * The cost of owning the footer is real and is paid here: the token totals, the cache hit rate
 * and the cost split below are this file's arithmetic over pi's session entries, and a pi release
 * that changes what an entry carries changes these numbers silently. lib/python/tests/
 * test_pi_footer.py is the guard on that, checking every field read here against pi's own `.d.ts`.
 *
 * Two things the built-in footer shows are deliberately not rebuilt, because the extension API
 * does not reach them: the `(auto)` auto-compaction marker and the `(sub)` subscription marker
 * both read private session state. A cursor session backed by a subscription therefore shows its
 * token counts with no dollar figure rather than `$0.000 (sub)`, which is the honest rendering of
 * what an extension can actually see.
 *
 * Every other extension's status still appears. `getExtensionStatuses()` is rendered verbatim on
 * the second row, so velocity.ts, the rtk toggle and the cursor badge in guardrails.ts keep
 * working untouched, and so does any status set by the packages in settings.json. Replacing the
 * footer without rendering that map is how a custom footer silently deletes every other
 * extension's output.
 *
 * Nothing here throws into pi's render loop. `render` is called on every repaint, so a throw
 * would be a crash per frame rather than a wrong number; the whole body is guarded and an empty
 * footer is the failure state.
 */

import { existsSync, readFileSync, realpathSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type {
  ExtensionAPI,
  ExtensionContext,
  ReadonlyFooterDataProvider,
  SessionEntry,
  Theme,
} from "@earendil-works/pi-coding-agent";
import { type Component, truncateToWidth, type TUI, visibleWidth } from "@earendil-works/pi-tui";

const SEPARATOR = " │ ";

/**
 * Every value this footer shares with Claude Code's statusline.sh, read from one file.
 *
 * The threshold, the gauge cells, the lockfile table and the glyphs are rendered by two
 * harnesses in two languages, and a value typed into both is a value that drifts. The wrap-up
 * threshold is the one that matters most: it also drives Claude's context-nudge.sh, so three
 * files answer to it and a footer marking a handoff at a different percentage from the hook that
 * asks for one is worse than neither saying anything.
 *
 * Read as JSON by path rather than imported as a module, and that is not a style choice. Pi
 * loads this file through the symlink the ai role puts in ~/.pi/agent/extensions, and jiti
 * resolves a relative import from that symlink rather than from its realpath, so `../..`
 * anything is looked for inside the pi agent directory and is not found. Resolving the realpath
 * first is what guardrails.ts already does to reach the claude hooks it drives, and it is the
 * one resolution that works from here.
 *
 * Nothing is defaulted. The file is two directories above this one inside the same checkout, so
 * it can only be missing when the checkout is, and a copy of every value kept as a fallback
 * would be the duplication this exists to remove. Each reader below degrades on its own: no
 * glyph renders no glyph, no threshold renders no marker, no table renders no package manager.
 */
const VOCABULARY_PATH = join(
  dirname(realpathSync(fileURLToPath(import.meta.url))),
  "..",
  "..",
  "statusline.json",
);

interface Vocabulary {
  handoffPct?: number;
  bar?: { width?: number; filled?: string; empty?: string };
  glyphs?: Record<string, string>;
  labels?: Record<string, string>;
  packageManagers?: { lockfile: string; name: string }[];
}

function loadVocabulary(): Vocabulary {
  try {
    const parsed: unknown = JSON.parse(readFileSync(VOCABULARY_PATH, "utf8"));
    return typeof parsed === "object" && parsed !== null ? (parsed as Vocabulary) : {};
  } catch {
    return {};
  }
}

const VOCAB = loadVocabulary();
const HANDOFF_PCT = typeof VOCAB.handoffPct === "number" ? VOCAB.handoffPct : undefined;

/** `<emoji> `, or nothing at all when the vocabulary could not be read. */
function glyph(name: string): string {
  const mark = VOCAB.glyphs?.[name];
  return typeof mark === "string" && mark !== "" ? `${mark} ` : "";
}

function word(name: string): string {
  const found = VOCAB.labels?.[name];
  return typeof found === "string" ? found : "";
}

// Where the gauge stops being a warning and starts being a problem. Local rather than shared,
// because the two harnesses colour differently on purpose: statusline.sh interpolates truecolor
// Solarized stops, and this paints with pi ThemeColor names so a user-authored theme still
// governs. Pi's own footer reddens at 90; this reddens at 70 because by then a handoff was
// already due, and a colour that arrives once the window is nearly gone has nothing left to warn
// about.
const CRITICAL_PCT = 70;

// Below this the bar is dropped and the percentage carries the segment alone. A gauge squeezed
// into a narrow terminal costs the eight columns that the model name needs more.
const BAR_MIN_WIDTH = 80;

/**
 * What a segment is worth when the terminal is too narrow to hold the row.
 *
 * Admitted highest first, so what survives at 60 columns is the reading that cannot be recovered
 * from anywhere else: the context gauge and the model. A node version is one `node --version`
 * away, and a token total is in `/usage`.
 */
const KEEP = {
  toolchain: 10,
  spend: 30,
  statuses: 50,
  repo: 70,
  model: 90,
  context: 100,
} as const;

interface Segment {
  text: string;
  keep: number;
}

/** Pi's own footer number format, so a session that switches renderings sees the same figures. */
function formatTokens(count: number): string {
  if (count < 1000) return count.toString();
  if (count < 10_000) return `${(count / 1000).toFixed(1)}k`;
  if (count < 1_000_000) return `${Math.round(count / 1000)}k`;
  if (count < 10_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  return `${Math.round(count / 1_000_000)}M`;
}

/** The theme colour a percentage reads at. Named colours rather than the truecolor gradient
 * statusline.sh uses, because pi themes are user-authored (roles/ai/files/pi/themes) and a hard
 * RGB ramp would be the one part of the footer that ignored the theme it sits in. */
function tier(percent: number): "success" | "warning" | "error" {
  if (percent >= CRITICAL_PCT) return "error";
  if (HANDOFF_PCT !== undefined && percent >= HANDOFF_PCT) return "warning";
  return "success";
}

function gauge(percent: number, theme: Theme): string {
  const width = VOCAB.bar?.width ?? 0;
  const full = VOCAB.bar?.filled;
  const void_ = VOCAB.bar?.empty;
  // Nothing to draw with is the same degradation a narrow terminal gets below BAR_MIN_WIDTH:
  // the percentage beside it carries the reading on its own.
  if (width < 2 || typeof full !== "string" || typeof void_ !== "string") return "";
  const filled = Math.min(width, Math.round((percent * width) / 100));
  const cells = [];
  for (let cell = 0; cell < width; cell += 1) {
    // Each filled cell takes the colour of the percentage it stands for rather than of the
    // total, which is what makes the bar read as a ramp under a theme that has no gradient.
    cells.push(
      cell < filled ? theme.fg(tier(((cell + 1) * 100) / width), full) : theme.fg("dim", void_),
    );
  }
  return cells.join("");
}

/**
 * The context reading, and the only segment that is never dropped.
 *
 * `percent` is null in exactly one situation, the turn after a compaction, and pi renders that
 * as `?`. It is kept rather than smoothed over: a gauge that guessed there would be reporting a
 * window it cannot see.
 */
function contextSegment(ctx: ExtensionContext, theme: Theme, width: number): string {
  const usage = ctx.getContextUsage();
  if (!usage) return "";
  const label = theme.fg("dim", word("context"));
  const window = formatTokens(usage.contextWindow);
  if (usage.percent === null) {
    return `${label} ${theme.fg("dim", `?/${window}`)}`;
  }
  const percent = Math.max(0, Math.min(100, Math.round(usage.percent)));
  const cells = width >= BAR_MIN_WIDTH ? gauge(percent, theme) : "";
  const bar = cells ? `[${cells}] ` : "";
  const tokens = usage.tokens === null ? "" : `${theme.fg("dim", formatTokens(usage.tokens))} `;
  const reading = theme.fg(tier(percent), `(${percent}%)`);
  const due = HANDOFF_PCT !== undefined && percent >= HANDOFF_PCT;
  const mark = due ? ` ${theme.bold(theme.fg(tier(percent), word("handoff")))}` : "";
  return `${label} ${bar}${tokens}${reading}${mark}`;
}

/**
 * Where the session is, as Claude shows it: the directory name and the branch.
 *
 * The basename rather than pi's `~/path/to/here`, which is the one field this footer states more
 * briefly than pi does. The full path is a `pwd` away and the branch is the part that changes
 * under you; spending three columns on the parent directories buys nothing the title bar does
 * not already say.
 */
function repoSegment(ctx: ExtensionContext, data: ReadonlyFooterDataProvider, theme: Theme): string {
  const cwd = ctx.sessionManager.getCwd();
  const name = basename(cwd) || cwd;
  const branch = data.getGitBranch();
  const session = ctx.sessionManager.getSessionName();
  const parts = [`${glyph("repo")}${theme.bold(theme.fg("accent", name))}`];
  if (branch) parts.push(theme.fg("muted", `(${branch})`));
  if (session) parts.push(theme.fg("dim", `• ${session}`));
  return parts.join(" ");
}

// The thinking levels that every theme is required to define a colour for. `thinkingMax` and
// `searchMatchText` are optional in pi's theme schema, so painting with them would leave a
// user-authored theme rendering an unstyled word where every other level is coloured.
const THINKING_COLORS = {
  off: "thinkingOff",
  minimal: "thinkingMinimal",
  low: "thinkingLow",
  medium: "thinkingMedium",
  high: "thinkingHigh",
  xhigh: "thinkingXhigh",
} as const;

/**
 * Model, provider and thinking level.
 *
 * The provider is always named, where pi names it only when more than one is configured. This
 * footer is read on a machine whose default provider routes tool calls through Cursor's own host
 * tools (docs/internals/pi-harness.md), and which provider is answering decides whether the
 * guardrail gates run at all, so it is never the field to drop for width.
 */
function modelSegment(ctx: ExtensionContext, theme: Theme): string {
  const model = ctx.model;
  if (!model) return theme.fg("dim", `${glyph("model")}no model`);
  const parts = [
    `${glyph("model")}${theme.fg("accent", model.id)}`,
    theme.fg("dim", `(${model.provider})`),
  ];
  if (model.reasoning) {
    const level = ctx.thinkingLevel ?? "off";
    const colour = THINKING_COLORS[level as keyof typeof THINKING_COLORS];
    parts.push(colour ? theme.fg(colour, level) : theme.fg("dim", level));
  }
  return parts.join(" ");
}

interface Spend {
  input: number;
  output: number;
  cacheRead: number;
  cacheWrite: number;
  cost: number;
  /** Cost since the last user message, which is what a turn is from the footer's side. */
  turn: number;
  /** The last assistant message's cache read as a share of everything it sent. */
  cacheHit: number | undefined;
}

/**
 * What this session has spent, counted the way pi's own footer counts it.
 *
 * Every entry carrying usage is added, not just the assistant messages: a tool result can carry
 * its own usage, and a compaction or a branch summary is a model call the user paid for whose
 * cost would otherwise disappear from the total at the moment it happened.
 *
 * The turn figure is the running total reset at every user message, so it reads as "this turn"
 * while a turn is in flight and as "the last turn" while the session is idle. That is the split
 * pi's single dollar figure hides: a session at `$4.10` says nothing about whether the current
 * question is cheap or is the expensive one.
 */
function spend(entries: readonly SessionEntry[]): Spend {
  const totals: Spend = {
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    cost: 0,
    turn: 0,
    cacheHit: undefined,
  };
  for (const entry of entries) {
    if (entry.type === "message" && entry.message.role === "user") {
      totals.turn = 0;
      continue;
    }
    const usage =
      entry.type === "message"
        ? entry.message.role === "assistant" || entry.message.role === "toolResult"
          ? entry.message.usage
          : undefined
        : entry.type === "compaction" || entry.type === "branch_summary"
          ? entry.usage
          : undefined;
    if (!usage) continue;
    totals.input += usage.input;
    totals.output += usage.output;
    totals.cacheRead += usage.cacheRead;
    totals.cacheWrite += usage.cacheWrite;
    totals.cost += usage.cost.total;
    totals.turn += usage.cost.total;
    if (entry.type === "message" && entry.message.role === "assistant") {
      const prompt = usage.input + usage.cacheRead + usage.cacheWrite;
      totals.cacheHit = prompt > 0 ? (usage.cacheRead / prompt) * 100 : undefined;
    }
  }
  return totals;
}

function spendSegment(ctx: ExtensionContext, theme: Theme): string {
  const totals = spend(ctx.sessionManager.getEntries());
  const parts = [];
  if (totals.input) parts.push(`↑${formatTokens(totals.input)}`);
  if (totals.output) parts.push(`↓${formatTokens(totals.output)}`);
  if (totals.cacheRead) parts.push(`R${formatTokens(totals.cacheRead)}`);
  if (totals.cacheWrite) parts.push(`W${formatTokens(totals.cacheWrite)}`);
  if (totals.cacheHit !== undefined && (totals.cacheRead > 0 || totals.cacheWrite > 0)) {
    parts.push(`CH${totals.cacheHit.toFixed(0)}%`);
  }
  const dim = parts.length ? theme.fg("dim", parts.join(" ")) : "";
  if (!totals.cost) return dim;
  // The turn figure only earns its parentheses while it differs from the total; on the first
  // turn of a session the two are the same number printed twice.
  const turn =
    totals.turn > 0 && totals.turn < totals.cost
      ? ` ${theme.fg("muted", `(+$${totals.turn.toFixed(3)})`)}`
      : "";
  const cost = theme.fg("dim", `$${totals.cost.toFixed(3)}`);
  return dim ? `${dim} ${cost}${turn}` : `${cost}${turn}`;
}

// Lockfile → package manager, the same ordered table statusline.sh walks, from the same file.
// Order is the content here: specific before npm is what makes a bun repo carrying a
// package-lock.json read as bun, so the shared file keeps an array rather than an object.
const LOCKFILES: readonly (readonly [string, string])[] = (VOCAB.packageManagers ?? [])
  .filter((entry) => typeof entry?.lockfile === "string" && typeof entry?.name === "string")
  .map((entry) => [entry.lockfile, entry.name] as const);
const KNOWN_PMS = new Set(LOCKFILES.map(([, name]) => name));

/**
 * The package manager this project uses, walking up from cwd.
 *
 * Upward, because a monorepo keeps its lockfile at the root and its `package.json` files in the
 * packages, so a check that stopped at cwd would report nothing from exactly the repos where
 * knowing the manager matters most. `packageManager` is preferred over the lockfile because it
 * carries the version too, and reading it costs no child process.
 */
function detectPackageManager(cwd: string): { name: string; version?: string } | undefined {
  let directory = cwd;
  for (;;) {
    const declared = packageManagerField(directory);
    if (declared) return declared;
    for (const [file, name] of LOCKFILES) {
      if (existsSync(join(directory, file))) return { name };
    }
    const parent = dirname(directory);
    if (parent === directory) return undefined;
    directory = parent;
  }
}

function packageManagerField(directory: string): { name: string; version?: string } | undefined {
  try {
    const field = JSON.parse(readFileSync(join(directory, "package.json"), "utf8")).packageManager;
    if (typeof field !== "string" || !field.includes("@")) return undefined;
    const [name, declared] = [field.slice(0, field.indexOf("@")), field.slice(field.indexOf("@") + 1)];
    if (!KNOWN_PMS.has(name)) return undefined;
    // corepack appends a `+sha224.…` integrity hash that is not part of the version.
    return { name, version: declared.split("+")[0] || undefined };
  } catch {
    return undefined;
  }
}

interface Toolchain {
  cwd: string;
  node?: string;
  pm?: string;
}

/**
 * The node and package-manager versions, resolved once per directory and never on the render
 * path. Two child processes at most, which is affordable at a session start and would not be at
 * sixty frames of footer; statusline.sh caches to a temp file for the same reason, because it is
 * re-executed every turn where this extension is alive for the whole session.
 */
async function resolveToolchain(pi: ExtensionAPI, cwd: string): Promise<Toolchain> {
  const resolved: Toolchain = { cwd };
  const node = await version(pi, "node", []);
  if (node) resolved.node = node.replace(/^v/, "");
  const pm = detectPackageManager(cwd);
  if (pm) {
    const declared = pm.version ?? (await version(pi, pm.name, [], cwd));
    resolved.pm = declared ? `${pm.name} ${declared}` : pm.name;
  }
  return resolved;
}

async function version(pi: ExtensionAPI, command: string, args: string[], cwd?: string) {
  try {
    const done = await pi.exec(command, [...args, "--version"], { timeout: 2000, cwd });
    if (done.code !== 0) return undefined;
    return done.stdout.trim().split("\n")[0]?.trim() || undefined;
  } catch {
    // A missing binary is the common case, not an error: it means the segment has nothing to say.
    return undefined;
  }
}

function toolchainSegment(toolchain: Toolchain | undefined, theme: Theme): string {
  if (!toolchain) return "";
  const parts = [];
  if (toolchain.node) parts.push(`${glyph("node")}${theme.fg("success", `node ${toolchain.node}`)}`);
  if (toolchain.pm) parts.push(`${glyph("packageManager")}${theme.fg("accent", toolchain.pm)}`);
  return parts.join(SEPARATOR);
}

/** Pi's own rule for extension statuses: one line, no control characters, sorted by key so a
 * repaint never reorders them. */
function statusSegment(data: ReadonlyFooterDataProvider): string {
  return Array.from(data.getExtensionStatuses().entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, text]) => text.replace(/[\r\n\t]/g, " ").replace(/ +/g, " ").trim())
    .filter((text) => text !== "")
    .join("  ");
}

/**
 * A row, filled in priority order until the terminal runs out.
 *
 * Segments are admitted highest-`keep` first rather than the row being assembled and then
 * trimmed, because trimming drops a wide segment and leaves the columns it occupied empty: an
 * 80-column row would lose the whole toolchain to a spend figure it could not fit either. Here a
 * segment that does not fit is skipped and the next one is still offered the space, so the row is
 * as full as the width allows and what it holds is what it could least afford to lose.
 *
 * Whole segments, never a partial one, because a segment cut mid-word still reads like data.
 * Truncation is left for the single case it is right for: the first segment admitted is admitted
 * unconditionally, since a row emptied by a narrow terminal is indistinguishable from a footer
 * that failed to render.
 */
function fit(segments: Segment[], width: number, theme: Theme): string {
  const present = segments.filter((segment) => segment.text !== "");
  if (present.length === 0) return "";
  const separator = theme.fg("dim", SEPARATOR);
  const separatorWidth = visibleWidth(separator);
  const admitted = new Set<Segment>();
  let used = 0;
  for (const segment of [...present].sort((a, b) => b.keep - a.keep)) {
    const cost = visibleWidth(segment.text) + (admitted.size ? separatorWidth : 0);
    if (admitted.size && used + cost > width) continue;
    admitted.add(segment);
    used += cost;
  }
  const row = present
    .filter((segment) => admitted.has(segment))
    .map((segment) => segment.text)
    .join(separator);
  return truncateToWidth(row, width, theme.fg("dim", "…"));
}

class DotfilesFooter implements Component {
  // Assigned in the constructor body rather than declared as parameter properties, which pi
  // rejects at load: extensions are type-stripped rather than compiled, and a parameter property
  // is syntax that has to be emitted rather than erased.
  private readonly pi: ExtensionAPI;
  private readonly ctx: ExtensionContext;
  private readonly tui: TUI;
  private readonly theme: Theme;
  private readonly data: ReadonlyFooterDataProvider;
  private readonly unsubscribe: () => void;
  private toolchain: Toolchain | undefined;
  private resolving = false;

  constructor(
    pi: ExtensionAPI,
    ctx: ExtensionContext,
    tui: TUI,
    theme: Theme,
    data: ReadonlyFooterDataProvider,
  ) {
    this.pi = pi;
    this.ctx = ctx;
    this.tui = tui;
    this.theme = theme;
    this.data = data;
    this.unsubscribe = data.onBranchChange(() => tui.requestRender());
  }

  dispose(): void {
    this.unsubscribe();
  }

  /** Pi calls this on the built-in footer to drop its cached branch; there is nothing cached
   * here that a repaint does not read again. */
  invalidate(): void {}

  render(width: number): string[] {
    try {
      return this.rows(width);
    } catch {
      // A footer is never worth a crash in the render loop, and the loop runs per frame.
      return [];
    }
  }

  private rows(width: number): string[] {
    this.refreshToolchain();
    const { ctx, theme, data } = this;
    const identity: Segment[] = [
      { text: repoSegment(ctx, data, theme), keep: KEEP.repo },
      { text: contextSegment(ctx, theme, width), keep: KEEP.context },
      { text: modelSegment(ctx, theme), keep: KEEP.model },
    ];
    const machine: Segment[] = [
      { text: toolchainSegment(this.toolchain, theme), keep: KEEP.toolchain },
      { text: spendSegment(ctx, theme), keep: KEEP.spend },
      { text: statusSegment(data), keep: KEEP.statuses },
    ];
    return [fit(identity, width, theme), fit(machine, width, theme)].filter((row) => row !== "");
  }

  /**
   * Re-resolves node and the package manager when the session moves.
   *
   * Driven from render rather than from an event, because pi has no cwd-change event an
   * extension can hook and a session that switches projects would otherwise report the previous
   * project's package manager for the rest of its life. The comparison is a string compare per
   * frame; the work behind it happens at most once per directory.
   */
  private refreshToolchain(): void {
    const cwd = this.ctx.sessionManager.getCwd();
    if (this.resolving || this.toolchain?.cwd === cwd) return;
    this.resolving = true;
    resolveToolchain(this.pi, cwd)
      .then((resolved) => {
        this.toolchain = resolved;
        this.tui.requestRender();
      })
      .catch(() => {})
      .finally(() => {
        this.resolving = false;
      });
  }
}

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (_event, ctx) => {
    try {
      // setFooter is documented as a no-op outside the TUI, and `mode` is the guard pi's own
      // docs name for terminal-only UI. Registering anyway would be harmless and dishonest.
      if (ctx.mode !== "tui") return;
      // Re-registered on every session start rather than once per process, so the footer closes
      // over the context of the session it is describing after a switch, a resume or a fork.
      ctx.ui.setFooter(
        (tui, theme, data) => new DotfilesFooter(pi, ctx, tui, theme, data),
      );
    } catch {
      // As in the render guard: the footer is the least important thing in the session.
    }
  });
}
