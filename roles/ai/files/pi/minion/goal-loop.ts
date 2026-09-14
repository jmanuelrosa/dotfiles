export type MinionReport =
  | { outcome: "continue"; summary: string; nextAction: string }
  | { outcome: "done"; summary: string; changedAreas: string[]; checks: string[] }
  | { outcome: "blocked"; summary: string; blocker: string };

export interface MinionReporter {
  tool: {
    name: string;
    label: string;
    description: string;
    parameters: Record<string, unknown>;
    executionMode: "sequential";
    execute(toolCallId: string, params: unknown): Promise<{
      content: Array<{ type: "text"; text: string }>;
      details: MinionReport;
      terminate: true;
    }>;
  };
  reset(): void;
  report(): MinionReport | undefined;
}

interface GoalSession {
  prompt(text: string): Promise<void>;
  abort(): Promise<void>;
}

interface GoalLoopOptions {
  goal: string;
  deliverySummary?: string;
  maxCycles: number;
  maxNoProgressCycles: number;
  deadlineAt: number;
  reporter: MinionReporter;
  session: GoalSession;
  signal?: AbortSignal;
  checkCheckout?: () => Promise<string | undefined> | string | undefined;
  onCycle?: (cycle: number, noProgressCycles: number) => Promise<void> | void;
}

export type GoalLoopResult =
  | { state: "done"; cycles: number; noProgressCycles: number; report: Extract<MinionReport, { outcome: "done" }> }
  | { state: "blocked"; cycles: number; noProgressCycles: number; report: Extract<MinionReport, { outcome: "blocked" }> }
  | { state: "limit-reached" | "aborted"; cycles: number; noProgressCycles: number; result: string };

const CONTINUATION_PROMPT = "Continue with the next useful action. Call minion_report when this cycle is complete.";
const CORRECTION_PROMPT = "Call minion_report now with this cycle's outcome. Do not perform additional work.";

function nonEmptyString(value: unknown, name: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${name} must be a non-empty string`);
  return value.trim();
}

function stringArray(value: unknown, name: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item.trim())) {
    throw new Error(`${name} must be an array of non-empty strings`);
  }
  return value.map((item) => item.trim());
}

function parseReport(value: unknown): MinionReport {
  if (typeof value !== "object" || value === null) throw new Error("minion_report requires an object");
  const input = value as Record<string, unknown>;
  const summary = nonEmptyString(input.summary, "summary");
  if (input.outcome === "continue") {
    return { outcome: "continue", summary, nextAction: nonEmptyString(input.nextAction, "nextAction") };
  }
  if (input.outcome === "done") {
    return {
      outcome: "done",
      summary,
      changedAreas: stringArray(input.changedAreas, "changedAreas"),
      checks: stringArray(input.checks, "checks"),
    };
  }
  if (input.outcome === "blocked") {
    return { outcome: "blocked", summary, blocker: nonEmptyString(input.blocker, "blocker") };
  }
  throw new Error("outcome must be continue, done, or blocked");
}

export function createMinionReporter(): MinionReporter {
  let current: MinionReport | undefined;
  return {
    tool: {
      name: "minion_report",
      label: "Minion report",
      description: "End the current Minion cycle as continue, done, or blocked.",
      parameters: {
        type: "object",
        properties: {
          outcome: { type: "string", enum: ["continue", "done", "blocked"] },
          summary: { type: "string" },
          nextAction: { type: "string" },
          changedAreas: { type: "array", items: { type: "string" } },
          checks: { type: "array", items: { type: "string" } },
          blocker: { type: "string" },
        },
        required: ["outcome", "summary"],
        additionalProperties: false,
      },
      executionMode: "sequential",
      async execute(_toolCallId, params) {
        if (current) throw new Error("minion_report was already submitted for this cycle");
        current = parseReport(params);
        return {
          content: [{ type: "text", text: `Cycle reported as ${current.outcome}` }],
          details: current,
          terminate: true,
        };
      },
    },
    reset() {
      current = undefined;
    },
    report() {
      return current;
    },
  };
}

function checkoutBlocked(cycles: number, noProgressCycles: number, blocker: string): GoalLoopResult {
  return {
    state: "blocked",
    cycles,
    noProgressCycles,
    report: {
      outcome: "blocked",
      summary: "Minion stopped because the checkout changed outside its tools",
      blocker,
    },
  };
}

function initialPrompt(goal: string, deliverySummary?: string): string {
  return [
    "Work as an unattended Pi coding session in the current checkout.",
    `Approved goal: ${goal}`,
    ...(deliverySummary ? [`Publication authority is fixed for this mission: ${deliverySummary}.`] : []),
    "Make routine in-scope implementation decisions independently and verify observable behavior.",
    "Do not commit, push, or open a PR during implementation; the runner owns any approved delivery after done.",
    "Do not expand the goal. Call minion_report once with done, blocked, or the next useful action.",
  ].join("\n");
}

export async function runGoalLoop(options: GoalLoopOptions): Promise<GoalLoopResult> {
  let cycles = 0;
  let noProgressCycles = 0;
  let aborted = options.signal?.aborted ?? false;
  let deadlineReached = Date.now() >= options.deadlineAt;
  const abort = () => {
    aborted = true;
    void options.session.abort();
  };
  const reachDeadline = () => {
    deadlineReached = true;
    void options.session.abort();
  };
  const deadlineTimer = deadlineReached ? undefined : setTimeout(reachDeadline, options.deadlineAt - Date.now());
  options.signal?.addEventListener("abort", abort, { once: true });

  const prompt = async (text: string) => {
    try {
      await options.session.prompt(text);
    } catch (error) {
      if (!aborted && !deadlineReached) throw error;
    }
  };

  try {
    while (cycles < options.maxCycles) {
      if (aborted) return { state: "aborted", cycles, noProgressCycles, result: "SDK session aborted" };
      if (deadlineReached || Date.now() >= options.deadlineAt) {
        return { state: "limit-reached", cycles, noProgressCycles, result: "Runtime limit reached" };
      }
      const beforeCycleBlocker = await options.checkCheckout?.();
      if (beforeCycleBlocker) return checkoutBlocked(cycles, noProgressCycles, beforeCycleBlocker);

      cycles += 1;
      options.reporter.reset();
      await options.onCycle?.(cycles, noProgressCycles);
      await prompt(cycles === 1 ? initialPrompt(options.goal, options.deliverySummary) : CONTINUATION_PROMPT);
      if (aborted) return { state: "aborted", cycles, noProgressCycles, result: "SDK session aborted" };
      if (deadlineReached) return { state: "limit-reached", cycles, noProgressCycles, result: "Runtime limit reached" };
      const afterPromptBlocker = await options.checkCheckout?.();
      if (afterPromptBlocker) return checkoutBlocked(cycles, noProgressCycles, afterPromptBlocker);

      let report = options.reporter.report();
      if (!report) {
        await prompt(CORRECTION_PROMPT);
        if (aborted) return { state: "aborted", cycles, noProgressCycles, result: "SDK session aborted" };
        if (deadlineReached) return { state: "limit-reached", cycles, noProgressCycles, result: "Runtime limit reached" };
        const afterCorrectionBlocker = await options.checkCheckout?.();
        if (afterCorrectionBlocker) return checkoutBlocked(cycles, noProgressCycles, afterCorrectionBlocker);
        report = options.reporter.report();
      }

      if (!report) {
        noProgressCycles += 1;
        await options.onCycle?.(cycles, noProgressCycles);
        if (noProgressCycles >= options.maxNoProgressCycles) {
          return {
            state: "blocked",
            cycles,
            noProgressCycles,
            report: {
              outcome: "blocked",
              summary: "Minion stopped after repeated cycles without a valid report",
              blocker: "The worker did not submit minion_report after a correction request",
            },
          };
        }
        continue;
      }

      noProgressCycles = 0;
      await options.onCycle?.(cycles, noProgressCycles);
      if (report.outcome === "done") return { state: "done", cycles, noProgressCycles, report };
      if (report.outcome === "blocked") return { state: "blocked", cycles, noProgressCycles, report };
    }

    return {
      state: "limit-reached",
      cycles,
      noProgressCycles,
      result: `Cycle limit reached after ${cycles} cycles`,
    };
  } finally {
    if (deadlineTimer) clearTimeout(deadlineTimer);
    options.signal?.removeEventListener("abort", abort);
  }
}
