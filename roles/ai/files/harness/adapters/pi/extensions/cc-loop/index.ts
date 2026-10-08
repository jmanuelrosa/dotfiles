import { randomUUID } from "node:crypto";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const COMMAND = "cc-loop";
const WAKEUP_TOOL = "schedule_wakeup";
const LIST_TOOL = "cron_list";
const DELETE_TOOL = "cron_delete";
const LOOP_TOOLS = [WAKEUP_TOOL, LIST_TOOL, DELETE_TOOL];
const STATE_ENTRY = "cc-loop-state";
const MESSAGE_TYPE = "cc-loop";

const SECOND_MS = 1000;
const MINUTE_MS = 60 * SECOND_MS;
const HOUR_MINUTES = 60;
const DAY_MINUTES = 24 * HOUR_MINUTES;
const DAY_MS = DAY_MINUTES * MINUTE_MS;

const RECURRING_MAX_AGE_MS = 7 * DAY_MS;
const EXPIRY_DAYS = RECURRING_MAX_AGE_MS / DAY_MS;
const MAX_JOBS = 50;
const RECURRING_JITTER_FRACTION = 0.1;
const RECURRING_JITTER_CAP_MS = 15 * MINUTE_MS;
const CACHE_TTL_MS = 5 * MINUTE_MS;
const CACHE_LEAD_MS = 15 * SECOND_MS;
const MIN_DELAY_SECONDS = 60;
const MAX_DELAY_SECONDS = 3600;
const KEEPALIVE_DELAY_SECONDS = 1200;
const KEEPALIVE_BUDGET = 1;
const LOOP_FILE_MAX_CHARS = 25000;
const LIST_PROMPT_CHARS = 80;
const JOB_ID_CHARS = 8;
const JITTER_SPACE = 2 ** 32;
const MAX_DAY_INTERVAL = 28;
const CRON_SEARCH_LIMIT_MS = 366 * DAY_MS;
const TURN_START_GRACE_MS = 5 * SECOND_MS;
const SINGLE_SHOT_MODES = new Set(["print", "json"]);

const UNIT_SECONDS: Record<string, number> = { s: 1, m: 60, h: 3600, d: 86400 };
const CLEAN_MINUTES = [1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30];
const CLEAN_HOURS = [1, 2, 3, 4, 6, 8, 12];

const AUTONOMOUS_SENTINEL = "<<autonomous-loop>>";
const AUTONOMOUS_DYNAMIC_SENTINEL = "<<autonomous-loop-dynamic>>";
const LOOP_FILE_SENTINEL = "<<loop.md>>";
const LOOP_FILE_DYNAMIC_SENTINEL = "<<loop.md-dynamic>>";
const AUTONOMOUS_DELIVERED = "__autonomous_preamble__";

const LEADING_INTERVAL = /^\d+[smhd]$/;
const UNIT_WORDS = "s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days";
const EVERY_ONLY = new RegExp(`^every\\s+(\\d+)\\s*(${UNIT_WORDS})\\s*$`, "i");
const TRAILING_EVERY = new RegExp(`^(.*\\S)\\s+every\\s+(\\d+)\\s*(${UNIT_WORDS})\\s*$`, "is");
const MINUTE_STEP_CRON = /^\*\/\d+ \* \* \* \*$/;

const USAGE = `Usage: /${COMMAND} [interval] <prompt>`;
const STOP_USAGE = `Usage: /${COMMAND} stop <id>`;
const NO_JOBS = "No scheduled jobs.";
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

const AUTONOMOUS_PREAMBLE = `# Autonomous loop check
You're being invoked on a timer while the user is away or occupied. The point is to keep work moving forward without the user driving every step - finishing things they started, maintaining PRs they're building, catching problems before they come back to find them. You're a steward, not an initiator. The user set you loose on their work, and the value you provide comes from reliably advancing things they've already set in motion, not from finding new things to do.
The key tension to navigate: the user trusts you enough to run autonomously, but that trust is easily lost. Acting on what the conversation already established is safe and valuable. Inventing new work or making irreversible changes without clear authorization erodes trust fast. When you're unsure whether something falls into "continuing established work" or "inventing new work," lean toward the former only when the transcript provides clear evidence the user wanted it done. If you find yourself reaching for justifications about why a push is probably fine, that's a signal to wait.
## What to act on
The current conversation is your highest-signal source - re-read the transcript above, since everything there is something the user was actively engaged with. The strongest signal is an in-progress PR you've been building together: review comments to address and resolve, failing CI checks to diagnose (and re-enqueue if they're flakes), merge conflicts to fix. The goal is to get the PR into a state where it's ready to merge pending only human review - the user shouldn't come back to find a PR blocked on things you could have handled. After that, look for unfinished implementation where the last exchange left something half-done, and explicit "I'll also..." or "next I'll..." commitments the conversation made and didn't honor. Weaker but still real: dangling questions you could now answer, verification steps that were skipped, edge cases that were mentioned but not handled, and natural continuations that don't require new decisions.
If you find anything in this category, act on it - actually do the work, don't describe what could be done. Run the tests, don't say "you could run the tests." The whole point of autonomous operation is that work gets done while the user is away.
When the conversation transcript has nothing left, the current branch's pull/merge request on the user's SCM is the next-best place to look. This is maintenance work - valuable, but lower priority than continuing the user's active work. Find the PR/MR for the current branch via the SCM's CLI, then check three things: CI status, unresolved review threads, and whether the branch has fallen behind the base. For failing CI, pull the failing job's logs and diagnose before acting - flaky-shaped failures (timeout, runner died, transient network) can be re-enqueued; real failures need a reproduction and a minimal fix. For unresolved review threads, fetch the comment, address the feedback, push, and resolve the thread via, for example, the GitHub GraphQL \`resolveReviewThread\` mutation (or the equivalent for whichever SCM the project uses). Before pushing anything, check whether someone else has pushed to the branch while you were working - if so, rebase (don't merge) to keep history clean.
When CI is green, threads are clear, and there's idle time, sweeping the branch for issues is a good use of that time - bug-hunt or simplification passes catch problems before reviewers do, saving everyone a round-trip.
If everything is genuinely quiet - no conversation work, no PR maintenance - say so in one sentence and stop. No summary of what you checked, no list of what you might do later. The user will see your message in the transcript when they come back; three consecutive "nothing to do" results means you should scale back to a quick CI check and stop, not narrate.
## Repeated invocations
If you see earlier autonomous checks in this conversation, adjust your scope accordingly. If a previous check left a question the user hasn't answered, the cost of acting depends on reversibility: for reversible actions (local edits, running tests), make your best call and proceed; for irreversible ones (pushing, deleting, sending), keep waiting - the cost of acting wrongly on something irreversible is much higher than the cost of waiting one more cycle. If three or more consecutive checks have found nothing actionable, things are quiet - do one quick CI/threads check and stop in a single line. Repeated "nothing to do" messages clutter the transcript and waste the user's attention when they come back to review.
Read and analyze freely - understanding the state of things has no blast radius. Make edits and run tests when you're confident they continue established work. Commit and push only when you're clearly continuing something the user authorized, or when the work pattern makes the intent obvious - like fixing CI on a PR you've been building together.
`;

const VISIBLE_UPDATE =
  "This must be ordinary visible response text - the user cannot see your thinking/reasoning, so an update written only there is invisible to them. Make it the last thing in the turn, then end the turn.";
const OUTCOME_UPDATE = "write the loop's outcome for the user as ordinary visible response text";
const POLL_INSTEAD_OF_MONITOR =
  "Pi has no background monitor that can wake this loop when an event lands, so poll for it instead: pick a `delaySeconds` matched to how fast that state actually changes.";
const NOOP_FIELD =
  '`noop`: `true` if this tick changed nothing ("still waiting", "quiet hold"); `false` if it did something worth keeping.';

export type Parsed =
  | { kind: "list" }
  | { kind: "stop"; id?: string }
  | { kind: "default"; interval?: string }
  | { kind: "fixed"; interval: string; prompt: string }
  | { kind: "dynamic"; prompt: string }
  | { kind: "usage" };

export interface CronPlan {
  cron: string;
  human: string;
  cadence: string;
  rounded: boolean;
}

export interface WakeupPlan {
  clamped: number;
  wasClamped: boolean;
  targetMs: number;
}

interface Job {
  id: string;
  cron: string;
  prompt: string;
  createdAt: number;
  final?: boolean;
}

interface Wakeup {
  id: string;
  prompt: string;
  targetMs: number;
  reason?: string;
  keepalive: boolean;
}

interface Chain {
  startedAt: number;
  lastScheduledFor: number;
  agedOut?: boolean;
}

interface Snapshot {
  jobs: Job[];
  wakeup: Wakeup | null;
  chains: Record<string, Chain>;
  keepalives: number;
}

interface LoopFile {
  path: string;
  content: string;
}

export interface Clock {
  now(): number;
  setTimer(callback: () => void, delayMs: number): unknown;
  clearTimer(handle: unknown): void;
}

const SYSTEM_CLOCK: Clock = {
  now: () => Date.now(),
  setTimer: (callback, delayMs) => {
    const handle = setTimeout(callback, Math.max(0, delayMs));
    handle.unref?.();
    return handle;
  },
  clearTimer: (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
};

function canonicalUnit(word: string): string {
  const unit = word.toLowerCase();
  if (unit.startsWith("s")) return "s";
  if (unit.startsWith("h")) return "h";
  if (unit.startsWith("d")) return "d";
  return "m";
}

export function parseInput(raw: string): Parsed {
  const input = raw.trim();
  if (input === "") return { kind: "default" };
  if (input === "list") return { kind: "list" };
  const stop = input.match(/^stop(?:\s+(\S+))?$/);
  if (stop) return { kind: "stop", id: stop[1] };
  if (LEADING_INTERVAL.test(input)) return { kind: "default", interval: input };
  const everyOnly = input.match(EVERY_ONLY);
  if (everyOnly) return { kind: "default", interval: `${everyOnly[1]}${canonicalUnit(everyOnly[2])}` };

  const first = input.split(/\s+/)[0];
  if (LEADING_INTERVAL.test(first)) {
    const prompt = input.slice(first.length).trim();
    return prompt ? { kind: "fixed", interval: first, prompt } : { kind: "usage" };
  }
  const trailing = input.match(TRAILING_EVERY);
  if (trailing) {
    const prompt = trailing[1].trim();
    const interval = `${trailing[2]}${canonicalUnit(trailing[3])}`;
    return prompt ? { kind: "fixed", interval, prompt } : { kind: "usage" };
  }
  return { kind: "dynamic", prompt: input };
}

function nearest(requested: number, candidates: number[]): number {
  return candidates.reduce((best, candidate) =>
    Math.abs(candidate - requested) < Math.abs(best - requested) ? candidate : best,
  );
}

export function intervalToCron(interval: string): CronPlan {
  const match = interval.match(/^(\d+)([smhd])$/);
  if (!match) throw new Error(`not an interval: ${interval}`);
  const amount = Number.parseInt(match[1], 10);
  const unit = match[2];
  const minutes = Math.max(
    1,
    unit === "s"
      ? Math.ceil(amount / UNIT_SECONDS.m)
      : unit === "m"
        ? amount
        : unit === "h"
          ? amount * HOUR_MINUTES
          : amount * DAY_MINUTES,
  );
  const candidates = [
    ...CLEAN_MINUTES,
    ...CLEAN_HOURS.map((hours) => hours * HOUR_MINUTES),
    ...Array.from({ length: MAX_DAY_INTERVAL }, (_, index) => (index + 1) * DAY_MINUTES),
  ];
  const chosen = nearest(minutes, candidates);
  let cron: string;
  let cadence: string;
  if (chosen < HOUR_MINUTES) {
    cron = chosen === 1 ? "* * * * *" : `*/${chosen} * * * *`;
    cadence = `${chosen}m`;
  } else if (chosen < DAY_MINUTES) {
    const hours = chosen / HOUR_MINUTES;
    cron = hours === 1 ? "0 * * * *" : `0 */${hours} * * *`;
    cadence = `${hours}h`;
  } else {
    const days = chosen / DAY_MINUTES;
    cron = days === 1 ? "0 0 * * *" : `0 0 */${days} * *`;
    cadence = `${days}d`;
  }
  const requestedSeconds = amount * UNIT_SECONDS[unit];
  return { cron, human: cronToHuman(cron), cadence, rounded: chosen * UNIT_SECONDS.m !== requestedSeconds };
}

function clockTime(minute: number, hour: number): string {
  return new Date(2000, 0, 1, hour, minute).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export function cronToHuman(cron: string): string {
  const fields = cron.trim().split(/\s+/);
  if (fields.length !== 5) return cron;
  const [minute, hour, dayOfMonth, month, dayOfWeek] = fields;
  const restWild = dayOfMonth === "*" && month === "*" && dayOfWeek === "*";
  if (hour === "*" && restWild) {
    if (minute === "*") return "Every minute";
    const step = minute.match(/^\*\/(\d+)$/);
    if (step) {
      const every = Number.parseInt(step[1], 10);
      return every === 1 ? "Every minute" : `Every ${every} minutes`;
    }
  }
  if (/^\d+$/.test(minute) && hour === "*" && restWild) {
    const at = Number.parseInt(minute, 10);
    return at === 0 ? "Every hour" : `Every hour at :${String(at).padStart(2, "0")}`;
  }
  const hourStep = hour.match(/^\*\/(\d+)$/);
  if (/^\d+$/.test(minute) && hourStep && restWild) {
    const every = Number.parseInt(hourStep[1], 10);
    const at = Number.parseInt(minute, 10);
    const suffix = at === 0 ? "" : ` at :${String(at).padStart(2, "0")}`;
    return every === 1 ? `Every hour${suffix}` : `Every ${every} hours${suffix}`;
  }
  if (!/^\d+$/.test(minute) || !/^\d+$/.test(hour)) return cron;
  const time = clockTime(Number.parseInt(minute, 10), Number.parseInt(hour, 10));
  if (restWild) return `Every day at ${time}`;
  if (dayOfMonth === "*" && month === "*" && /^\d$/.test(dayOfWeek)) {
    const name = WEEKDAYS[Number.parseInt(dayOfWeek, 10) % 7];
    if (name) return `Every ${name} at ${time}`;
  }
  if (dayOfMonth === "*" && month === "*" && dayOfWeek === "1-5") return `Weekdays at ${time}`;
  return cron;
}

type FieldMatcher = (value: number) => boolean;

function fieldMatcher(field: string): FieldMatcher {
  const parts = field.split(",").map((part) => {
    if (part === "*") return () => true;
    const step = part.match(/^(\*|\d+-\d+)\/(\d+)$/);
    if (step) {
      const every = Number.parseInt(step[2], 10);
      const [low, high] = step[1] === "*" ? [0, Number.POSITIVE_INFINITY] : step[1].split("-").map(Number);
      return (value: number) => value >= low && value <= high && (value - (step[1] === "*" ? 0 : low)) % every === 0;
    }
    const range = part.match(/^(\d+)-(\d+)$/);
    if (range) return (value: number) => value >= Number(range[1]) && value <= Number(range[2]);
    const exact = Number(part);
    return (value: number) => value === exact;
  });
  return (value) => parts.some((matches) => matches(value));
}

function dayOfMonthMatcher(field: string): FieldMatcher {
  if (field.startsWith("*/")) {
    const every = Number.parseInt(field.slice(2), 10);
    return (value) => (value - 1) % every === 0;
  }
  return fieldMatcher(field);
}

export function nextCronMatch(cron: string, fromMs: number): number | null {
  const fields = cron.trim().split(/\s+/);
  if (fields.length !== 5) return null;
  const [minute, hour, dayOfMonth, month, dayOfWeek] = fields;
  const minuteOk = fieldMatcher(minute);
  const hourOk = fieldMatcher(hour);
  const domOk = dayOfMonthMatcher(dayOfMonth);
  const monthOk = fieldMatcher(month);
  const dowOk = fieldMatcher(dayOfWeek);
  const domWild = dayOfMonth === "*";
  const dowWild = dayOfWeek === "*";
  const dayOk = (date: Date) => {
    const dom = domOk(date.getDate());
    const dow = dowOk(date.getDay()) || (dayOfWeek.includes("7") && date.getDay() === 0);
    if (domWild || dowWild) return dom && dow;
    return dom || dow;
  };

  const start = new Date(fromMs);
  start.setSeconds(0, 0);
  let cursor = start.getTime() + MINUTE_MS;
  const limit = fromMs + CRON_SEARCH_LIMIT_MS;
  while (cursor <= limit) {
    const date = new Date(cursor);
    if (!monthOk(date.getMonth() + 1) || !dayOk(date)) {
      date.setHours(24, 0, 0, 0);
      cursor = date.getTime();
      continue;
    }
    if (!hourOk(date.getHours())) {
      date.setHours(date.getHours() + 1, 0, 0, 0);
      cursor = date.getTime();
      continue;
    }
    if (minuteOk(date.getMinutes())) return cursor;
    cursor += MINUTE_MS;
  }
  return null;
}

export function jitterFraction(id: string): number {
  const fraction = Number.parseInt(id.slice(0, JOB_ID_CHARS), 16) / JITTER_SPACE;
  return Number.isFinite(fraction) ? fraction : 0;
}

export function nextRecurringFire(cron: string, fromMs: number, id: string): number | null {
  const first = nextCronMatch(cron, fromMs);
  if (first === null) return null;
  const second = nextCronMatch(cron, first);
  if (second === null) return first;
  const period = second - first;
  if (
    MINUTE_STEP_CRON.test(cron) &&
    CACHE_LEAD_MS < period &&
    period >= CACHE_TTL_MS &&
    period - CACHE_LEAD_MS < CACHE_TTL_MS
  ) {
    return fromMs + period - CACHE_LEAD_MS;
  }
  return first + Math.min(jitterFraction(id) * RECURRING_JITTER_FRACTION * period, RECURRING_JITTER_CAP_MS);
}

function ceilToMinute(ms: number): number {
  const date = new Date(ms);
  if (date.getSeconds() > 0 || date.getMilliseconds() > 0) date.setMinutes(date.getMinutes() + 1);
  date.setSeconds(0, 0);
  return date.getTime();
}

export function planWakeup(requested: number, now: number): WakeupPlan {
  let rounded: number;
  if (Number.isNaN(requested)) rounded = MIN_DELAY_SECONDS;
  else if (requested === Number.POSITIVE_INFINITY) rounded = MAX_DELAY_SECONDS;
  else if (requested === Number.NEGATIVE_INFINITY) rounded = MIN_DELAY_SECONDS;
  else rounded = Math.round(requested);
  const clamped = Math.max(MIN_DELAY_SECONDS, Math.min(MAX_DELAY_SECONDS, rounded));
  const wasClamped = !Number.isFinite(requested) || rounded !== clamped;
  let targetMs = ceilToMinute(now + clamped * SECOND_MS);
  if (clamped * SECOND_MS <= CACHE_TTL_MS) {
    const budget = CACHE_TTL_MS - CACHE_LEAD_MS;
    while (targetMs - now > budget && targetMs - MINUTE_MS >= now + MIN_DELAY_SECONDS * SECOND_MS) {
      targetMs -= MINUTE_MS;
    }
  }
  return { clamped, wasClamped, targetMs };
}

export function truncateLoopFile(text: string): string {
  if (text.length <= LOOP_FILE_MAX_CHARS) return text;
  const cut = text.lastIndexOf("\n", LOOP_FILE_MAX_CHARS);
  return `${text.slice(0, cut > 0 ? cut : LOOP_FILE_MAX_CHARS)}\n> WARNING: loop.md was truncated to ${LOOP_FILE_MAX_CHARS} bytes. Keep the task list concise.`;
}

export function loopFileCandidates(cwd: string, home: string): string[] {
  return [
    join(cwd, ".pi", "loop.md"),
    join(home, ".pi", "agent", "loop.md"),
    join(cwd, ".claude", "loop.md"),
    join(home, ".claude", "loop.md"),
  ];
}

export function readLoopFile(cwd: string, home: string = homedir()): LoopFile | null {
  for (const path of loopFileCandidates(cwd, home)) {
    let raw: string;
    try {
      raw = readFileSync(path, "utf8");
    } catch {
      continue;
    }
    const content = raw.trim();
    if (content) return { path, content: truncateLoopFile(content) };
  }
  return null;
}

function singleLine(text: string, width: number): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length <= width ? flat : `${flat.slice(0, width - 1)}…`;
}

function newId(): string {
  return randomUUID().slice(0, JOB_ID_CHARS);
}

function dynamicReminder(): string {
  return `\nAfter re-arming, write a brief status update for this tick. ${VISIBLE_UPDATE} To stop the loop, call ${WAKEUP_TOOL} with \`stop: true\`.`;
}

function rearmSentence(sentinel: string): string {
  return `You scheduled this tick via the ${WAKEUP_TOOL} tool (not a recurring cron). To keep the loop alive, call ${WAKEUP_TOOL} again this turn with \`prompt\` set to the literal sentinel \`${sentinel}\` and \`noop\` set to \`true\` if this tick changed nothing (or \`false\` if it did) - otherwise the loop ends after this tick.`;
}

function autonomousTick(): string {
  return `# Autonomous loop tick\nRun the autonomous check using the loop instructions established earlier in this conversation. If you cannot find them, treat this as a no-op tick. The recurring cron will fire the next tick automatically - do not call ${WAKEUP_TOOL} from this tick.`;
}

function autonomousDynamicTick(): string {
  return `# Autonomous loop tick (dynamic pacing)\nRun the autonomous check using the loop instructions established earlier in this conversation. If you cannot find them, treat this as a no-op tick.\n${rearmSentence(AUTONOMOUS_DYNAMIC_SENTINEL)}${dynamicReminder()}`;
}

function loopFileTick(): string {
  return `# /${COMMAND} tick - loop.md tasks\nWork the tasks from the loop.md contents established earlier in this conversation. If you cannot find them, treat this as a no-op tick. The recurring cron will fire the next tick automatically - do not call ${WAKEUP_TOOL} from this tick.`;
}

function loopFileDynamicTick(): string {
  return `# /${COMMAND} tick - loop.md tasks (dynamic pacing)\nWork the tasks from the loop.md contents established earlier in this conversation. If you cannot find them, treat this as a no-op tick.\n${rearmSentence(LOOP_FILE_DYNAMIC_SENTINEL)}${dynamicReminder()}`;
}

function loopFileAbsentDynamicTick(): string {
  return `# /${COMMAND} tick - loop.md absent (dynamic pacing)\nloop.md is not currently present. Run the autonomous check using the loop instructions established earlier in this conversation.\nYou scheduled this tick via the ${WAKEUP_TOOL} tool (not a recurring cron). To keep the loop alive - and to pick up loop.md if it is recreated - call ${WAKEUP_TOOL} again this turn with \`prompt\` set to the literal sentinel \`${LOOP_FILE_DYNAMIC_SENTINEL}\` and \`noop\` set to \`true\` if this tick changed nothing (or \`false\` if it did) - otherwise the loop ends after this tick.${dynamicReminder()}`;
}

export function isSentinel(prompt: string): boolean {
  return [AUTONOMOUS_SENTINEL, AUTONOMOUS_DYNAMIC_SENTINEL, LOOP_FILE_SENTINEL, LOOP_FILE_DYNAMIC_SENTINEL].includes(prompt);
}

export interface Delivery {
  lastLoopFileDelivered: string | null;
  autonomousPreambleDelivered: boolean;
}

export function resolveSentinel(delivery: Delivery, prompt: string, loopFile: () => LoopFile | null): string {
  if (prompt === AUTONOMOUS_SENTINEL || prompt === AUTONOMOUS_DYNAMIC_SENTINEL) {
    const reminder = prompt === AUTONOMOUS_DYNAMIC_SENTINEL ? autonomousDynamicTick() : autonomousTick();
    if (delivery.autonomousPreambleDelivered || delivery.lastLoopFileDelivered !== null) return reminder;
    delivery.autonomousPreambleDelivered = true;
    return `${AUTONOMOUS_PREAMBLE}\n${reminder}`;
  }
  const dynamic = prompt === LOOP_FILE_DYNAMIC_SENTINEL;
  const file = loopFile();
  if (file) {
    const reminder = dynamic ? loopFileDynamicTick() : loopFileTick();
    if (delivery.lastLoopFileDelivered === file.content) return reminder;
    delivery.lastLoopFileDelivered = file.content;
    return `# /${COMMAND} tick - tasks from ${file.path}\nThe user configured a loop-tasks file. Work through the tasks defined below; these are the instructions for this tick and every subsequent tick (the reminder on later fires refers back to this message).\n${file.content}\n${reminder}`;
  }
  const reminder = dynamic ? loopFileAbsentDynamicTick() : autonomousTick();
  if (delivery.lastLoopFileDelivered === AUTONOMOUS_DELIVERED || delivery.autonomousPreambleDelivered) return reminder;
  delivery.lastLoopFileDelivered = AUTONOMOUS_DELIVERED;
  delivery.autonomousPreambleDelivered = true;
  return `${AUTONOMOUS_PREAMBLE}\n${reminder}`;
}

export function dynamicInstructions(input: string, slash: boolean): string {
  const prompt = slash
    ? "It is the slash command in the next user message, already expanded; act on it directly."
    : "It is the next user message; act on it directly.";
  return `# /${COMMAND} - self-paced loop
The user invoked \`/${COMMAND}\` without an interval and wants you to self-pace. Decide what makes the next iteration worth running - a passage of time, or an observable event.
1. **Run the parsed prompt now.** ${prompt}
2. **If the next run is gated on an event** (CI finishing, a log line matching, a file changing, a PR comment): ${POLL_INSTEAD_OF_MONITOR}
3. **Decide whether the loop continues.** If the task needs another iteration, call ${WAKEUP_TOOL} with:
   - \`delaySeconds\`: the cadence - pick based on what you observed. Read the tool's own description for cache-aware delay guidance.
   - \`reason\`: one short sentence on why you picked that delay.
   - \`prompt\`: the full original /${COMMAND} input verbatim, prefixed with \`/${COMMAND} \` so the next firing re-enters this command and continues the loop. For example, if the user typed \`/${COMMAND} check the deploy\`, pass \`/${COMMAND} check the deploy\` as the prompt.
   - ${NOOP_FIELD}
   If it doesn't need another iteration, stop instead (step 5) - re-arming is a per-turn choice, not a default.
4. **After the wakeup is armed, briefly confirm**: that you're self-pacing, that you ran the task now, and what delay you picked. ${VISIBLE_UPDATE}
5. **To stop the loop** - the task is complete, further iterations can't make progress, or the user asked you to stop - call ${WAKEUP_TOOL} with \`stop: true\` (no other fields). Then ${OUTCOME_UPDATE} - a stopped loop has no next tick to surface it. Stopping is the loop's normal ending - the user can restart it anytime with /${COMMAND}.
## Input
${input}`;
}

export function defaultDynamicInstructions(file: LoopFile | null): string {
  const sentinel = file ? LOOP_FILE_DYNAMIC_SENTINEL : AUTONOMOUS_DYNAMIC_SENTINEL;
  const heading = file
    ? `# /${COMMAND} - loop.md tasks with dynamic pacing\nThe user invoked \`/${COMMAND}\` with no prompt and no interval and has a loop-tasks file at \`${file.path}\`. Run those tasks now, then self-pace the next iteration via ${WAKEUP_TOOL} - no cron.`
    : `# /${COMMAND} - autonomous default with dynamic pacing\nThe user invoked \`/${COMMAND}\` with no prompt and no interval. Run the autonomous check now, then self-pace the next iteration via ${WAKEUP_TOOL} - no cron.`;
  const subject = file ? "the loop.md tasks" : "the autonomous check";
  const confirm = file
    ? `that you're running tasks from \`${file.path}\` in dynamic-pacing mode, that you ran the first tick now`
    : "that this is the autonomous default in dynamic-pacing mode, that you ran the check now";
  const section = file
    ? `## Loop tasks (from ${file.path})\n${file.content}`
    : `## Autonomous-loop instructions (for the immediate execution and every fire)\n${AUTONOMOUS_PREAMBLE}`;
  return `${heading}
## Action
1. **Run ${subject} now**, following the instructions inlined below.
2. **If the next tick is gated on an event** (CI finishing, a PR comment, a log line): ${POLL_INSTEAD_OF_MONITOR}
3. **Decide whether the loop continues.** If the next check is worth running, call ${WAKEUP_TOOL} with:
   - \`delaySeconds\`: pick based on what you observed this turn - quiet branch? wait longer. Lots in flight? wait shorter. Read the tool's own description for cache-aware delay guidance.
   - \`reason\`: one short sentence on why you picked that delay.
   - \`prompt\`: the literal string \`${sentinel}\` - the dynamic-mode sentinel expands at fire time to the full instructions (first fire, or loop.md edited) or a dynamic-pacing-specific short reminder (subsequent fires). Do not pass the full instructions; that is handled automatically.
   - ${NOOP_FIELD}
   If it isn't, stop instead (step 5) - re-arming is a per-turn choice, not a default.
4. **After the wakeup is armed, briefly confirm**: ${confirm}, and what delay you picked. ${VISIBLE_UPDATE}
5. **To stop the loop** - the task is complete, further iterations can't make progress, or the user asked you to stop - call ${WAKEUP_TOOL} with \`stop: true\` (no other fields). Then ${OUTCOME_UPDATE} - a stopped loop has no next tick to surface it. Stopping is the loop's normal ending - the user can restart it anytime with /${COMMAND}.
${section}`;
}

export function defaultFixedInstructions(file: LoopFile | null, interval: string): string {
  const heading = file
    ? `# /${COMMAND} - loop.md tasks on a recurring job\nThe user invoked \`/${COMMAND}\` with no prompt (just the interval \`${interval}\`) and has a loop-tasks file at \`${file.path}\`. A recurring job now runs those tasks each tick; run the first tick immediately.`
    : `# /${COMMAND} - the autonomous default on a recurring job\nThe user invoked \`/${COMMAND}\` with no prompt (just the interval \`${interval}\`). A recurring job now runs the autonomous-loop default each tick; run the first autonomous check immediately.`;
  const subject = file ? "the loop.md tasks" : "the autonomous check";
  const section = file
    ? `## Loop tasks (from ${file.path})\n${file.content}`
    : `## Autonomous-loop instructions (for the immediate execution and every fire)\n${AUTONOMOUS_PREAMBLE}`;
  return `${heading}
## Action
**Run ${subject} now**, following the instructions inlined below. Don't wait for the first scheduled fire. Later ticks are delivered automatically, so do not call ${WAKEUP_TOOL} for this loop.
${section}`;
}

export function scheduledConfirmation(id: string, plan: CronPlan, interval: string, note?: string): string {
  const rounding = plan.rounded
    ? ` Rounded \`${interval}\` to \`${plan.cadence}\`, the nearest interval cron can express evenly.`
    : "";
  const extra = note ? ` ${note}` : "";
  return `Scheduled recurring job ${id} (${plan.human}, cron \`${plan.cron}\`).${rounding}${extra} Session-only (not written to disk; stops when this pi session ends). Auto-expires after ${EXPIRY_DAYS} days. Use \`/${COMMAND} stop ${id}\` to cancel sooner.`;
}

const WAKEUP_DESCRIPTION = `Schedule when to resume work in /${COMMAND} dynamic mode - the user invoked /${COMMAND} without an interval, asking you to self-pace iterations of a specific task.
${POLL_INSTEAD_OF_MONITOR} Schedule only as often as that state changes; for anything slow, a long wait (1200s+) keeps the loop alive without burning turns.
Pass the same /${COMMAND} prompt back via \`prompt\` each turn so the next firing repeats the task. For an autonomous /${COMMAND} (no user prompt), pass the literal sentinel \`${AUTONOMOUS_DYNAMIC_SENTINEL}\` as \`prompt\` instead - the runtime resolves it back to the autonomous-loop instructions at fire time. (There is a similar \`${AUTONOMOUS_SENTINEL}\` sentinel for cron-based autonomous loops; do not confuse the two - ${WAKEUP_TOOL} always uses the \`-dynamic\` variant.) To end the loop, call this tool with \`stop: true\` (omit every other field) - the loop ends immediately and no further wakeups fire.
Set \`noop: true\` if nothing changed - you checked and there's nothing to report ("no change", "still waiting", "quiet hold"). Set \`noop: false\` if something happened worth keeping - you edited a file, posted a message, advanced state, or surfaced a finding. Omit \`noop\` when stopping (\`stop: true\`).
## Picking delaySeconds
The provider's prompt cache decides how expensive a wake-up is: waking inside the cache TTL re-reads your conversation context cached (fast, cheap); waking past it re-reads everything uncached. Many providers default to a 5-minute TTL; some offer 1 hour.
In either regime: never schedule extra wakeups just to keep the cache warm - they cost more than the cache miss they avoid. Match the delay to what you're actually waiting for: when actively polling external state (a CI run, a deploy, a remote queue), pick the delay from how fast that state actually changes; for idle ticks with no specific signal to watch, default to **1200s-1800s** (20-30 min) - the user can always interrupt if they need you sooner.
On a 5-minute TTL only, two refinements: under 300s (60s-270s) the cache stays warm, so prefer 270s over 300s when actively polling (300s is the worst-of-both - you pay the miss without amortizing it); and commit to 1200s+ rather than repeated ~300s waits, so one cache miss buys a long wait.
The runtime clamps to [${MIN_DELAY_SECONDS}, ${MAX_DELAY_SECONDS}], so you don't need to clamp yourself.
## The reason field
One short sentence on what you chose and why. Shown back to the user. "watching CI run" beats "waiting." The user reads this to understand what you're doing without having to predict your cadence in advance - make it specific.`;

const WAKEUP_PARAMETERS = Type.Object({
  delaySeconds: Type.Optional(
    Type.Number({
      description: `Seconds from now to wake up. Clamped to [${MIN_DELAY_SECONDS}, ${MAX_DELAY_SECONDS}] by the runtime. Required unless \`stop\` is true.`,
    }),
  ),
  reason: Type.Optional(
    Type.String({
      description:
        "One short sentence explaining the chosen delay. Shown to the user. Be specific. Required unless `stop` is true.",
    }),
  ),
  prompt: Type.Optional(
    Type.String({
      description: `The /${COMMAND} input to fire on wake-up. Pass the same /${COMMAND} input verbatim each turn so the next firing re-enters the command and continues the loop. For autonomous /${COMMAND} (no user prompt), pass the literal sentinel \`${AUTONOMOUS_DYNAMIC_SENTINEL}\` (or \`${LOOP_FILE_DYNAMIC_SENTINEL}\` when running loop.md tasks) instead (the dynamic-pacing variant, not the cron-mode \`${AUTONOMOUS_SENTINEL}\`). Required unless \`stop\` is true.`,
    }),
  ),
  stop: Type.Optional(
    Type.Boolean({
      description:
        "Set to true to end the dynamic loop immediately instead of scheduling another wakeup. When true, all other fields are ignored and no further wakeups fire.",
    }),
  ),
  noop: Type.Optional(
    Type.Boolean({
      description:
        "true = nothing changed (you checked and there is nothing to report). false = something happened worth keeping (edited a file, posted a message, advanced state, surfaced a finding). Required unless `stop` is true.",
    }),
  ),
});

function text(content: string) {
  return { content: [{ type: "text" as const, text: content }], details: undefined };
}

export function createLoop(pi: ExtensionAPI, clock: Clock = SYSTEM_CLOCK, home: string = homedir()): void {
  const jobs = new Map<string, Job>();
  const timers = new Map<string, unknown>();
  let wakeup: Wakeup | null = null;
  let chains: Record<string, Chain> = {};
  let keepalives = 0;
  let tickInFlight: string | null = null;
  let pending: string[] = [];
  let dispatching = false;
  let dispatchGuard: unknown;
  let lastOutcome: string | undefined;
  let current: ExtensionContext | null = null;
  let startWaiters: Array<() => void> = [];
  let settleWaiters: Array<() => void> = [];
  const delivery: Delivery = { lastLoopFileDelivered: null, autonomousPreambleDelivered: false };

  const cwd = () => current?.cwd ?? process.cwd();
  const loopFile = () => readLoopFile(cwd(), home);

  function pruneChains(now: number): void {
    for (const [prompt, chain] of Object.entries(chains)) {
      const continuing = now <= chain.lastScheduledFor + MAX_DELAY_SECONDS * SECOND_MS;
      if (!continuing && wakeup?.prompt !== prompt) delete chains[prompt];
    }
  }

  function persist(): void {
    pruneChains(clock.now());
    const snapshot: Snapshot = {
      jobs: [...jobs.values()].map(({ final: _final, ...job }) => job),
      wakeup,
      chains,
      keepalives,
    };
    pi.appendEntry(STATE_ENTRY, snapshot);
  }

  function syncTools(): void {
    const looping = jobs.size > 0 || wakeup !== null || tickInFlight !== null;
    const active = new Set(pi.getActiveTools());
    if (LOOP_TOOLS.every((name) => active.has(name) === looping)) return;
    for (const name of LOOP_TOOLS) {
      if (looping) active.add(name);
      else active.delete(name);
    }
    pi.setActiveTools([...active]);
  }

  function clearTimer(id: string): void {
    const handle = timers.get(id);
    if (handle !== undefined) clock.clearTimer(handle);
    timers.delete(id);
  }

  function armJob(job: Job, fromMs: number): void {
    clearTimer(job.id);
    const at = nextRecurringFire(job.cron, fromMs, job.id);
    if (at === null) return;
    timers.set(job.id, clock.setTimer(() => fireJob(job.id), at - clock.now()));
  }

  function armWakeup(next: Wakeup): void {
    clearTimer(next.id);
    timers.set(next.id, clock.setTimer(() => due(next.id), next.targetMs - clock.now()));
  }

  function fireJob(id: string): void {
    timers.delete(id);
    const job = jobs.get(id);
    if (!job) return;
    const now = clock.now();
    if (now - job.createdAt >= RECURRING_MAX_AGE_MS) job.final = true;
    else armJob(job, now);
    due(id);
  }

  function due(id: string): void {
    timers.delete(id);
    if (!pending.includes(id)) pending.push(id);
    drain();
  }

  function slashCommand(prompt: string): string {
    const match = prompt.match(/^\/(\S+)(.*)$/s);
    if (!match) return prompt;
    const [, name, rest] = match;
    const commands = pi.getCommands();
    if (commands.some((command) => command.name === name)) return prompt;
    if (commands.some((command) => command.source === "skill" && command.name === `skill:${name}`)) {
      return `/skill:${name}${rest}`;
    }
    return prompt;
  }

  function endDispatch(): void {
    if (dispatchGuard !== undefined) clock.clearTimer(dispatchGuard);
    dispatchGuard = undefined;
    dispatching = false;
  }

  function send(content: string, expand: boolean): void {
    const busy = current !== null && !current.isIdle();
    if (!busy) {
      endDispatch();
      dispatching = true;
      dispatchGuard = clock.setTimer(() => {
        endDispatch();
        drain();
      }, TURN_START_GRACE_MS);
    }
    pi.sendUserMessage(content, busy ? { expandPromptTemplates: expand, deliverAs: "followUp" } : { expandPromptTemplates: expand });
  }

  function dispatch(prompt: string): void {
    if (isSentinel(prompt)) {
      send(resolveSentinel(delivery, prompt, loopFile), false);
      return;
    }
    send(slashCommand(prompt), true);
  }

  function drain(): void {
    if (!current || dispatching || !current.isIdle()) return;
    while (pending.length > 0) {
      const id = pending.shift() as string;
      const job = jobs.get(id);
      if (job) {
        if (job.final) {
          jobs.delete(id);
          clearTimer(id);
          persist();
          syncTools();
        }
        dispatch(job.prompt);
        return;
      }
      if (wakeup && wakeup.id === id) {
        const fired = wakeup;
        wakeup = null;
        tickInFlight = fired.prompt;
        persist();
        dispatch(fired.prompt);
        return;
      }
    }
  }

  function cancelWakeup(): number {
    if (!wakeup) return 0;
    clearTimer(wakeup.id);
    pending = pending.filter((id) => id !== wakeup?.id);
    wakeup = null;
    return 1;
  }

  function endDynamicLoop(): number {
    const cancelled = cancelWakeup();
    tickInFlight = null;
    keepalives = 0;
    persist();
    syncTools();
    return cancelled;
  }

  function scheduleWakeup(
    delaySeconds: number,
    prompt: string,
    options: { keepalive: boolean; reason?: string },
  ): WakeupPlan | null {
    if (!options.keepalive) keepalives = 0;
    cancelWakeup();
    const now = clock.now();
    const chain = chains[prompt];
    const stale = chain !== undefined && now > chain.lastScheduledFor + MAX_DELAY_SECONDS * SECOND_MS;
    const startedAt = chain === undefined || stale ? now : chain.startedAt;
    if (now - startedAt >= RECURRING_MAX_AGE_MS) {
      chains[prompt] = {
        startedAt,
        lastScheduledFor: now - (MAX_DELAY_SECONDS - MIN_DELAY_SECONDS) * SECOND_MS,
        agedOut: true,
      };
      tickInFlight = null;
      persist();
      return null;
    }
    const plan = planWakeup(delaySeconds, now);
    wakeup = { id: newId(), prompt, targetMs: plan.targetMs, reason: options.reason, keepalive: options.keepalive };
    chains[prompt] = { startedAt, lastScheduledFor: plan.targetMs };
    if (options.keepalive) keepalives += 1;
    armWakeup(wakeup);
    syncTools();
    persist();
    return plan;
  }

  function listing(): string {
    const rows = [...jobs.values()].map(
      (job) => `${job.id} - ${cronToHuman(job.cron)} (recurring) [session-only]: ${singleLine(job.prompt, LIST_PROMPT_CHARS)}`,
    );
    if (wakeup) {
      const at = new Date(wakeup.targetMs);
      rows.push(
        `${wakeup.id} - Once at ${clockTime(at.getMinutes(), at.getHours())} (one-shot) [session-only]: ${singleLine(wakeup.prompt, LIST_PROMPT_CHARS)}`,
      );
    }
    return rows.length > 0 ? rows.join("\n") : NO_JOBS;
  }

  function deleteJob(id: string): string {
    if (jobs.has(id)) {
      jobs.delete(id);
      clearTimer(id);
      pending = pending.filter((entry) => entry !== id);
      persist();
      syncTools();
      return `Cancelled job ${id}.`;
    }
    if (wakeup && wakeup.id === id) {
      endDynamicLoop();
      return `Cancelled job ${id}.`;
    }
    return `No scheduled job with id '${id}'`;
  }

  function tell(ctx: ExtensionContext, content: string): void {
    if (ctx.hasUI) {
      ctx.ui.notify(content, "info");
      return;
    }
    pi.sendMessage({ customType: MESSAGE_TYPE, content, display: true }, { triggerTurn: false });
  }

  function announce(content: string): void {
    pi.sendMessage({ customType: MESSAGE_TYPE, content, display: true }, { triggerTurn: false });
  }

  function createJob(cron: string, prompt: string): Job | string {
    if (jobs.size >= MAX_JOBS) return `Too many scheduled jobs (max ${MAX_JOBS}). Cancel one first.`;
    const job: Job = { id: newId(), cron, prompt, createdAt: clock.now() };
    jobs.set(job.id, job);
    armJob(job, job.createdAt);
    syncTools();
    persist();
    return job;
  }

  function startFixed(ctx: ExtensionContext, interval: string, prompt: string, immediate: string, note?: string): void {
    const plan = intervalToCron(interval);
    const job = createJob(plan.cron, prompt);
    if (typeof job === "string") {
      tell(ctx, job);
      return;
    }
    announce(scheduledConfirmation(job.id, plan, interval, note));
    if (immediate === prompt) {
      send(slashCommand(prompt), true);
      return;
    }
    send(immediate, false);
  }

  function startDynamic(prompt: string): void {
    tickInFlight = `/${COMMAND} ${prompt}`;
    syncTools();
    const resolved = slashCommand(prompt);
    announce(dynamicInstructions(prompt, resolved.startsWith("/")));
    send(resolved, true);
  }

  function markInlined(file: LoopFile | null): void {
    if (file) delivery.lastLoopFileDelivered = file.content;
    else delivery.autonomousPreambleDelivered = true;
  }

  function startDefault(ctx: ExtensionContext, interval?: string): void {
    const file = loopFile();
    markInlined(file);
    if (interval === undefined) {
      tickInFlight = file ? LOOP_FILE_DYNAMIC_SENTINEL : AUTONOMOUS_DYNAMIC_SENTINEL;
      syncTools();
      send(defaultDynamicInstructions(file), false);
      return;
    }
    const sentinel = file ? LOOP_FILE_SENTINEL : AUTONOMOUS_SENTINEL;
    const note = file
      ? `Running tasks from \`${file.path}\`.`
      : "This is the autonomous default; the autonomous-loop instructions are baked in.";
    startFixed(ctx, interval, sentinel, defaultFixedInstructions(file, interval), note);
  }

  function restore(ctx: ExtensionContext): void {
    const entries = ctx.sessionManager.getBranch();
    let snapshot: Snapshot | undefined;
    for (const entry of entries) {
      if (entry.type === "custom" && entry.customType === STATE_ENTRY) snapshot = entry.data as Snapshot;
    }
    if (!snapshot) return;
    const now = clock.now();
    chains = snapshot.chains ?? {};
    keepalives = snapshot.keepalives ?? 0;
    for (const job of snapshot.jobs ?? []) {
      if (now - job.createdAt >= RECURRING_MAX_AGE_MS) continue;
      jobs.set(job.id, { ...job });
      armJob(job, now);
    }
    if (snapshot.wakeup && snapshot.wakeup.targetMs > now) {
      wakeup = { ...snapshot.wakeup };
      armWakeup(wakeup);
    }
    if (jobs.size > 0 || wakeup) syncTools();
  }

  function release(waiters: Array<() => void>): void {
    for (const resolve of waiters) resolve();
  }

  async function holdSingleShot(ctx: ExtensionCommandContext): Promise<void> {
    if (!SINGLE_SHOT_MODES.has(ctx.mode) || (!dispatching && ctx.isIdle())) return;
    const started = await new Promise<boolean>((resolve) => {
      const timer = clock.setTimer(() => resolve(false), TURN_START_GRACE_MS);
      startWaiters.push(() => {
        clock.clearTimer(timer);
        resolve(true);
      });
    });
    if (started) await new Promise<void>((resolve) => settleWaiters.push(resolve));
  }

  function shutdown(): void {
    for (const handle of timers.values()) clock.clearTimer(handle);
    timers.clear();
    jobs.clear();
    wakeup = null;
    chains = {};
    keepalives = 0;
    tickInFlight = null;
    pending = [];
    endDispatch();
    current = null;
    release(startWaiters);
    release(settleWaiters);
    startWaiters = [];
    settleWaiters = [];
    delivery.lastLoopFileDelivered = null;
    delivery.autonomousPreambleDelivered = false;
  }

  pi.registerCommand(COMMAND, {
    description: `Run a prompt or slash command on a recurring interval (e.g. /${COMMAND} 5m /foo). Omit the interval to let the model self-pace.`,
    handler: async (args, ctx) => {
      current = ctx;
      const parsed = parseInput(args);
      switch (parsed.kind) {
        case "list":
          tell(ctx, listing());
          return;
        case "stop":
          tell(ctx, parsed.id ? deleteJob(parsed.id) : `${STOP_USAGE}\n${listing()}`);
          return;
        case "usage":
          tell(ctx, USAGE);
          return;
        case "default":
          startDefault(ctx, parsed.interval);
          break;
        case "fixed":
          startFixed(ctx, parsed.interval, parsed.prompt, parsed.prompt);
          break;
        case "dynamic":
          startDynamic(parsed.prompt);
          break;
      }
      await holdSingleShot(ctx);
    },
  });

  pi.registerTool({
    name: WAKEUP_TOOL,
    label: "Schedule wakeup",
    description: WAKEUP_DESCRIPTION,
    promptSnippet: `Schedule when to resume work in /${COMMAND} dynamic mode (always pass the \`prompt\` arg unless stopping). Call before ending the turn to keep the loop alive; call with \`stop: true\` to end the loop immediately.`,
    parameters: WAKEUP_PARAMETERS,
    defaultActive: false,
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      current = ctx;
      const finish = `Then ${OUTCOME_UPDATE} - and end the turn.`;
      if (params.stop === true) {
        const cancelled = endDynamicLoop();
        if (cancelled === 0) {
          return text(
            `Loop stopped - any dynamic loop in this session is ended; there was no pending wakeup to cancel. If you are running a fixed-interval /${COMMAND} (a recurring cron), it is NOT stopped by this call - cancel it with ${DELETE_TOOL}. ${finish}`,
          );
        }
        return text(
          `Loop stopped - cancelled ${cancelled} pending wakeup(s); no further dynamic-loop wakeups scheduled. ${finish}`,
        );
      }
      if (params.delaySeconds === undefined || params.reason === undefined) {
        throw new Error("`delaySeconds` and `reason` are required when `stop` is not true.");
      }
      if (params.prompt === undefined) throw new Error("`prompt` is required when `stop` is not true.");
      if (params.noop === undefined) throw new Error("`noop` is required when `stop` is not true.");
      const plan = scheduleWakeup(params.delaySeconds, params.prompt, { keepalive: false, reason: params.reason });
      if (plan === null) {
        return text(`Wakeup not scheduled. The loop reached its maximum duration - the loop has ended; do not re-issue. ${finish}`);
      }
      const at = new Date(plan.targetMs).toTimeString().slice(0, 8);
      const seconds = Math.max(0, Math.round((plan.targetMs - clock.now()) / SECOND_MS));
      const clampNote = plan.wasClamped ? ` (clamped to ${plan.clamped}s from your requested value)` : "";
      return text(
        `Next wakeup scheduled for ${at} (in ${seconds}s)${clampNote}. If you owe the user a status update this tick, write it now as ordinary response text; then end the turn - the harness re-invokes you when the wakeup fires.`,
      );
    },
  });

  pi.registerTool({
    name: LIST_TOOL,
    label: "List loop jobs",
    description: `List all cron jobs scheduled via /${COMMAND} in this session, including a pending ${WAKEUP_TOOL} wakeup.`,
    parameters: Type.Object({}),
    defaultActive: false,
    async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
      current = ctx;
      return text(listing());
    },
  });

  pi.registerTool({
    name: DELETE_TOOL,
    label: "Cancel loop job",
    description: `Cancel a cron job previously scheduled with /${COMMAND}. Removes it from the in-memory session store.`,
    parameters: Type.Object({ id: Type.String({ description: "Job ID returned when the job was scheduled." }) }),
    defaultActive: false,
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      current = ctx;
      const result = deleteJob(params.id);
      if (result.startsWith("No scheduled job")) throw new Error(result);
      return text(result);
    },
  });

  pi.on("session_start", (_event, ctx) => {
    shutdown();
    current = ctx;
    restore(ctx);
  });

  pi.on("agent_start", (_event, ctx) => {
    current = ctx;
    endDispatch();
    release(startWaiters);
    startWaiters = [];
  });

  pi.on("agent_before_settle", (event, ctx) => {
    current = ctx;
    lastOutcome = event.outcome;
  });

  pi.on("agent_settled", (_event, ctx) => {
    current = ctx;
    endDispatch();
    if (lastOutcome === "aborted") {
      if (wakeup || tickInFlight !== null) endDynamicLoop();
    } else if (tickInFlight !== null && wakeup === null) {
      const prompt = tickInFlight;
      if (keepalives >= KEEPALIVE_BUDGET) {
        endDynamicLoop();
        if (ctx.hasUI) ctx.ui.notify(`/${COMMAND}: the model declined to reschedule twice, so the dynamic loop ended.`, "info");
      } else {
        scheduleWakeup(KEEPALIVE_DELAY_SECONDS, prompt, { keepalive: true });
      }
    }
    tickInFlight = null;
    lastOutcome = undefined;
    syncTools();
    drain();
    if (dispatching) return;
    const waiters = settleWaiters;
    settleWaiters = [];
    release(waiters);
  });

  pi.on("session_shutdown", () => {
    shutdown();
  });
}

export default function registerCcLoop(pi: ExtensionAPI): void {
  createLoop(pi);
}
