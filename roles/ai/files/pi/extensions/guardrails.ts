/**
 * guardrails.ts - Claude Code's four PreToolUse enforcement hooks, running in Pi.
 *
 * An adapter and nothing else. Every decision is made by the python scripts under
 * roles/ai/files/claude/hooks/, which Claude Code runs as PreToolUse hooks and which carry their
 * own pytest suite. This file maps Pi's `tool_call` event onto the JSON they read on stdin and
 * maps their exit 2 back onto Pi's block result. Nothing here parses a command, counts a dash, or
 * knows which lint a project runs: a second copy of any of that is a copy that drifts, and the
 * python half is the tested one.
 *
 * Four differences between the harnesses are handled here, and each is why this file exists:
 *
 * - Pi's `edit` carries an array of edits where Claude's carries one pair. The oldText and newText
 *   halves are joined before the hook sees them, which preserves its delta rule: a call is blocked
 *   when it adds dashes overall, never when one edit adds what another removes.
 * - Pi has no `attributionSkill`, the per-turn stamp git-skill-gate reads to tell whether the
 *   session is inside the commit or pr skill. `activeSkills` answers that question from Pi's own
 *   session and writes the answer in the shape the hook already parses, so the hook stays the only
 *   thing deciding what a gated command is.
 * - The hook's refusal names /commit and ~/.claude/settings.json, neither of which exists here, so
 *   the one message a caller can act on gets a line of Pi translation appended.
 * - Claude has three answers to a PreToolUse hook and Pi has two. cloud-readonly-gate's `ask`
 *   tier becomes a refusal, for the reasons at `askedForPermission`.
 *
 * All four of Claude's PreToolUse hooks are bridged here. The three that are not are on events
 * this file does not listen to: plan-date-stamp.sh is PostToolUse on ExitPlanMode and Pi has no
 * plan mode at all, while skill-recap.sh (Stop) and context-nudge.sh (UserPromptSubmit) would map
 * onto Pi's `turn_end` and `turn_start` and are deliberately left for their own pass.
 *
 * Everything fails open: a missing hook, a moved checkout, a spawn error or a timeout allows the
 * call, exactly as the hooks themselves do on malformed input. These are intent friction, not a
 * security boundary. That takes deliberate care here, because Pi and Claude disagree about what a
 * broken guardrail means: a `tool_call` handler that throws blocks the call, so an unwritable
 * temp directory would turn a gate nobody can run into a gate nobody can pass. Nothing below is
 * allowed to throw.
 */

import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { existsSync, realpathSync } from "node:fs";
import { unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  type ExtensionAPI,
  type ExtensionContext,
  isToolCallEventType,
  type ToolCallEvent,
  type ToolCallEventResult,
} from "@earendil-works/pi-coding-agent";

// realpath rather than dirname alone: this file is reached through the symlink the ai role puts in
// ~/.pi/agent/extensions/, so the hooks are siblings of the link's target, not of the link.
const HOOKS_DIR = join(dirname(realpathSync(fileURLToPath(import.meta.url))), "..", "..", "claude", "hooks");

// Above pre-commit-verify's own 150s ceiling, so its report of a slow lint reaches the caller
// instead of being replaced by this timeout.
const HOOK_TIMEOUT_MS = 180_000;

// User messages, where Claude counts stamped assistant events. The unit has to differ because
// the signals do: Claude re-stamps `attributionSkill` on every assistant turn for as long as the
// flow is running, while pi writes its `<skill name="...">` tag exactly once, into the user
// message that invoked it. Counting entries would therefore expire the invocation partway through
// the very flow it opened, since reading a diff and staging spends far more than 30 entries. A
// count of user messages cannot expire mid-flow (a commit flow is one message) and still bounds
// staleness, so an invocation the user has plainly moved on from stops holding the gate open.
const SKILL_WINDOW_USER_MESSAGES = 30;

// The skills git-skill-gate gates on, by name only: which command needs which one stays the hook's
// business, and this list exists solely to be looked for in the session.
const GATED_SKILLS = ["commit", "pr"] as const;

interface HookPayload {
  tool_name: string;
  tool_input: Record<string, unknown>;
  cwd: string;
  transcript_path?: string;
}

interface HookVerdict {
  blocked: boolean;
  message: string;
  // Only cloud-readonly-gate writes anything here: its middle tier is an `ask`
  // decision on stdout with exit 0, which `blocked` alone cannot represent.
  stdout?: string;
}

const ALLOW: HookVerdict = { blocked: false, message: "" };

function runHook(name: string, payload: HookPayload): Promise<HookVerdict> {
  const script = join(HOOKS_DIR, name);
  if (!existsSync(script)) {
    return Promise.resolve(ALLOW);
  }

  return new Promise((resolve) => {
    const child = spawn(script, [], { stdio: ["pipe", "pipe", "pipe"] });
    let stderr = "";
    let stdout = "";
    let settled = false;
    let timer: ReturnType<typeof setTimeout>;

    const finish = (verdict: HookVerdict) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(verdict);
    };

    timer = setTimeout(() => {
      child.kill("SIGKILL");
      finish(ALLOW);
    }, HOOK_TIMEOUT_MS);

    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });
    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });
    // A hook that cannot be spawned at all, and a broken pipe from one that exits before reading
    // its input, both mean the gate did not run. Neither is the caller's fault.
    child.on("error", () => finish(ALLOW));
    child.stdin.on("error", () => {});
    child.on("close", (code) => finish({ blocked: code === 2, message: stderr.trim(), stdout }));

    child.stdin.end(JSON.stringify(payload));
  });
}

/**
 * A hook's `ask` decision, which in Pi can only become a refusal.
 *
 * Claude Code has three answers to a PreToolUse hook and Pi has two: a `tool_call`
 * handler returns `{ block }` or nothing, and Pi ships no permission prompt at all. So
 * cloud-readonly-gate's middle tier, the one covering every non-read-only cloud command,
 * has no counterpart and has to fall to one side.
 *
 * It falls to blocked, and the direction is deliberate. Those four CLIs are the ones
 * Claude excludes from its sandbox so they can reach their own credential stores, which
 * makes this gate their only guardrail there; in Pi there is no prompt to fall back on,
 * so allowing would mean running them unasked. The reason still comes from the hook, so
 * the caller is told which command to run in a real terminal instead.
 *
 * The decision is read rather than inferred: the hook prints it as JSON and exits 0, so
 * exit status alone reports the same thing for `ask` and for `allow`.
 */
function askedForPermission(verdict: HookVerdict): string | undefined {
  const raw = verdict.stdout?.trim();
  if (!raw) return undefined;
  try {
    const output = JSON.parse(raw)?.hookSpecificOutput;
    if (output?.permissionDecision !== "ask") return undefined;
    return String(output.permissionDecisionReason || "").trim() || "asked for confirmation";
  } catch {
    // Not every hook prints JSON, and one that prints anything else has not asked.
    return undefined;
  }
}

function textOf(content: unknown): string {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((block): block is { type: string; text: string } => {
      const candidate = block as { type?: unknown; text?: unknown } | null;
      return !!candidate && candidate.type === "text" && typeof candidate.text === "string";
    })
    .map((block) => block.text)
    .join("\n");
}

/**
 * The skills this session is inside, read from user messages alone.
 *
 * Pi expands `/skill:commit` in place, into a `<skill name="commit" location="...">` block on the
 * user message, so that tag is the invocation. The model reading SKILL.md on its own does not
 * count, which mirrors Claude: `attributionSkill` marks a slash-command flow too. It also keeps
 * the fuzzier signal out, since a session that merely read a skill file, or a tool result quoting
 * one, would otherwise open the gate in the repo where those files live.
 *
 * Only user messages are counted, for the reason at SKILL_WINDOW_USER_MESSAGES: the tag is a
 * one-time invocation marker here, not a per-turn stamp, so windowing over every entry would drop
 * it while the flow it belongs to is still running.
 */
function activeSkills(ctx: ExtensionContext): Set<string> {
  const found = new Set<string>();
  let entries: unknown[];
  try {
    entries = ctx.sessionManager.getBranch();
  } catch {
    return found;
  }

  const asked: string[] = [];
  for (const entry of entries) {
    const message = (entry as { message?: { role?: string; content?: unknown } }).message;
    if (message?.role !== "user") continue;
    asked.push(textOf(message.content));
  }

  for (const text of asked.slice(-SKILL_WINDOW_USER_MESSAGES)) {
    for (const skill of GATED_SKILLS) {
      if (text.includes(`<skill name="${skill}"`)) found.add(skill);
    }
  }
  return found;
}

/**
 * The active skills, as the JSONL git-skill-gate reads.
 *
 * Written even when the set is empty, and that is the load-bearing part: the hook treats a
 * transcript it cannot open as a parse failure and allows the command, so a missing file would
 * turn the gate off rather than closing it. Which is also why a write that fails is answered with
 * no path at all rather than a throw: the skill window then goes unchecked, as it does in Claude
 * when a transcript will not parse, while the hard blocks the hook applies first still stand.
 *
 * The name is generated here rather than taken from the tool call. `toolCallId` is whatever the
 * model provider returned, so it crosses a trust boundary before reaching a path: real ids already
 * carry a `|`, one carrying a `/` would make the write fail and silently leave the window
 * unchecked, and one beginning with `../` would write and then unlink a file outside tmpdir.
 */
async function writeTranscript(skills: Set<string>): Promise<string | undefined> {
  const path = join(tmpdir(), `pi-guardrails-${randomUUID()}.jsonl`);
  const lines = [...skills].map((skill) => `${JSON.stringify({ attributionSkill: skill })}\n`);
  try {
    await writeFile(path, lines.join(""), "utf8");
    return path;
  } catch {
    return undefined;
  }
}

function blockResult(verdict: HookVerdict): ToolCallEventResult | undefined {
  if (!verdict.blocked) return undefined;
  const message = verdict.message || "Blocked by a guardrails hook.";
  const translated = message.includes("is blocked outside")
    ? `${message}\n\nIn pi those skills are /skill:commit and /skill:pr. Load the right one, then retry.`
    : message;
  return { block: true, reason: translated };
}

async function guard(event: ToolCallEvent, ctx: ExtensionContext): Promise<ToolCallEventResult | undefined> {
  if (isToolCallEventType("write", event)) {
    return blockResult(
      await runHook("em-dash-gate.sh", {
        tool_name: "Write",
        tool_input: { file_path: event.input.path, content: event.input.content },
        cwd: ctx.cwd,
      }),
    );
  }

  if (isToolCallEventType("edit", event)) {
    const edits = event.input.edits ?? [];
    return blockResult(
      await runHook("em-dash-gate.sh", {
        tool_name: "Edit",
        tool_input: {
          old_string: edits.map((edit) => edit.oldText).join("\n"),
          new_string: edits.map((edit) => edit.newText).join("\n"),
        },
        cwd: ctx.cwd,
      }),
    );
  }

  if (isToolCallEventType("bash", event)) {
    const tool_input = { command: event.input.command };

    // Order follows settings.json: the cheap gate refuses first, so a command that was never
    // allowed cannot also spend a project's full lint budget proving itself clean.
    const transcript = await writeTranscript(activeSkills(ctx));
    let gate: HookVerdict;
    try {
      gate = await runHook("git-skill-gate.sh", {
        tool_name: "Bash",
        tool_input,
        cwd: ctx.cwd,
        transcript_path: transcript,
      });
    } finally {
      if (transcript) await unlink(transcript).catch(() => {});
    }
    if (gate.blocked) return blockResult(gate);

    // Before pre-commit-verify for the same reason git-skill-gate is: this one is a
    // parse and a table lookup, and a cloud command it refuses should not first spend
    // a project's full lint budget. Claude lists it after, but nothing there depends
    // on the order and the hooks do not observe each other.
    const cloud = await runHook("cloud-readonly-gate.sh", { tool_name: "Bash", tool_input, cwd: ctx.cwd });
    if (cloud.blocked) return blockResult(cloud);
    const asked = askedForPermission(cloud);
    if (asked) {
      return {
        block: true,
        reason: `${asked}\n\nPi has no confirmation prompt, so this is refused rather than asked. Run it in a real terminal if you meant it.`,
      };
    }

    return blockResult(await runHook("pre-commit-verify.sh", { tool_name: "Bash", tool_input, cwd: ctx.cwd }));
  }

  return undefined;
}

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    try {
      return await guard(event, ctx);
    } catch {
      // The whole of the fail-open promise, in one place. Pi reads a throw here as a block, so
      // without this an unreadable session or an unwritable temp file would refuse every write,
      // edit and command in the session, and the refusal would carry no reason anyone could act on.
      return undefined;
    }
  });
}
