"""The cc-loop extension ports Claude Code's /loop to pi, so its rules are Claude's rules.

Every expectation here comes from the /loop prompt, the ScheduleWakeup tool and the cron
scheduler compiled into the Claude Code binary: the parsing precedence and its worked examples,
the 7-day expiry, the [60, 3600] wakeup clamp, the 1200s keepalive with its budget of one, and
the 25000-character loop.md cap. The pure functions run as table tests; the scheduler runs
against a fake pi and a fake clock, so ticks, expiry and keepalives are asserted without waiting.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from dotkit.testing import PI_EXTENSIONS, REPO

EXTENSION = PI_EXTENSIONS / "cc-loop" / "index.ts"
README = PI_EXTENSIONS / "cc-loop" / "README.md"
DEFAULTS = REPO / "roles" / "ai" / "defaults" / "main.yml"
PI_PACKAGE = "@earendil-works/pi-coding-agent"
SCHEMA_PACKAGE = "typebox"
DASHES = (chr(0x2014), chr(0x2013))

HARNESS = """
export function fakeClock(start) {
  let now = start;
  let timers = [];
  let next = 0;
  return {
    now: () => now,
    setTimer: (callback, delay) => { const id = next++; timers.push({ id, at: now + Math.max(0, delay), callback }); return id; },
    clearTimer: (id) => { timers = timers.filter((timer) => timer.id !== id); },
    advance(ms) {
      const end = now + ms;
      for (;;) {
        timers.sort((a, b) => a.at - b.at);
        const due = timers[0];
        if (!due || due.at > end) break;
        timers.shift();
        now = due.at;
        due.callback();
      }
      now = end;
    },
    pending: () => timers.length,
  };
}

export function fakePi() {
  const state = { commands: {}, tools: {}, handlers: {}, sent: [], messages: [], entries: [], active: ["read"], idle: true };
  const ctx = {
    cwd: process.cwd(),
    mode: "tui",
    hasUI: true,
    ui: { notify: (text) => state.messages.push({ notify: text }) },
    isIdle: () => state.idle,
    sessionManager: { getBranch: () => state.entries.map((entry) => ({ type: "custom", ...entry })) },
  };
  const pi = {
    registerCommand: (name, options) => { state.commands[name] = options; },
    registerTool: (tool) => { state.tools[tool.name] = tool; },
    on: (event, handler) => { (state.handlers[event] ??= []).push(handler); },
    sendUserMessage: (content, options) => {
      state.sent.push([content, options ?? {}]);
      const command = options?.expandPromptTemplates && content.match(/^\\/(\\S+)\\s*(.*)$/s);
      if (command && state.commands[command[1]]) state.commands[command[1]].handler(command[2], ctx);
      else state.idle = false;
    },
    sendMessage: (message) => state.messages.push({ custom: message.content }),
    appendEntry: (customType, data) => state.entries.push({ customType, data: JSON.parse(JSON.stringify(data)) }),
    getActiveTools: () => [...state.active],
    setActiveTools: (names) => { state.active = [...names]; },
    getCommands: () => [{ name: "cc-loop", source: "extension" }, { name: "skill:babysit-prs", source: "skill" }],
  };
  const emit = async (event, payload = {}) => {
    for (const handler of state.handlers[event] ?? []) await handler({ type: event, ...payload }, ctx);
  };
  const settle = async (outcome = "completed") => {
    state.idle = true;
    await emit("agent_before_settle", { outcome });
    await emit("agent_settled");
  };
  return { pi, ctx, state, emit, settle };
}
"""


def pi_package():
    binary = shutil.which("pi")
    if binary is None:
        return None
    root = Path(binary).resolve().parent.parent
    for candidate in (root / "lib/node_modules" / PI_PACKAGE, root / "libexec/lib/node_modules" / PI_PACKAGE):
        if candidate.is_dir():
            return candidate
    return None


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    package = pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are needed to execute the extension")
    schema = package / "node_modules" / SCHEMA_PACKAGE
    if not schema.is_dir():
        pytest.skip("pi's bundled typebox is needed to load the extension")

    root = tmp_path_factory.mktemp("cc-loop")
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    (root / "node_modules" / SCHEMA_PACKAGE).symlink_to(schema)
    (root / "cc-loop.ts").write_text(EXTENSION.read_text())
    (root / "harness.ts").write_text(HARNESS)
    return root


def run(workspace, body):
    script = f"""
      import * as loop from "./cc-loop.ts";
      import {{ fakeClock, fakePi }} from "./harness.ts";
      const out = await (async () => {{ {body} }})();
      process.stdout.write(JSON.stringify(out));
    """
    result = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=workspace,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5m /babysit-prs", {"kind": "fixed", "interval": "5m", "prompt": "/babysit-prs"}),
        ("check the deploy every 20m", {"kind": "fixed", "interval": "20m", "prompt": "check the deploy"}),
        ("run tests every 5 minutes", {"kind": "fixed", "interval": "5m", "prompt": "run tests"}),
        ("check the deploy every 2 hours", {"kind": "fixed", "interval": "2h", "prompt": "check the deploy"}),
        ("check the deploy", {"kind": "dynamic", "prompt": "check the deploy"}),
        ("check every PR", {"kind": "dynamic", "prompt": "check every PR"}),
        ("5m", {"kind": "default", "interval": "5m"}),
        ("every 5 minutes", {"kind": "default", "interval": "5m"}),
        ("", {"kind": "default"}),
        ("list", {"kind": "list"}),
        ("stop ab12cd34", {"kind": "stop", "id": "ab12cd34"}),
    ],
)
def test_parsing_follows_claude_precedence(workspace, raw, expected):
    assert run(workspace, f"return loop.parseInput({json.dumps(raw)});") == expected


@pytest.mark.parametrize(
    ("interval", "cron", "human", "rounded"),
    [
        ("5m", "*/5 * * * *", "Every 5 minutes", False),
        ("1h", "0 * * * *", "Every hour", False),
        ("2h", "0 */2 * * *", "Every 2 hours", False),
        ("1d", "0 0 * * *", "Every day at 12:00 AM", False),
        ("120m", "0 */2 * * *", "Every 2 hours", False),
        ("7m", "*/6 * * * *", "Every 6 minutes", True),
        ("90m", "0 * * * *", "Every hour", True),
        ("30s", "* * * * *", "Every minute", True),
    ],
)
def test_intervals_become_claude_cron_expressions(workspace, interval, cron, human, rounded):
    plan = run(workspace, f"return loop.intervalToCron({json.dumps(interval)});")

    assert (plan["cron"], plan["human"], plan["rounded"]) == (cron, human, rounded)


@pytest.mark.parametrize(
    ("requested", "clamped", "was_clamped"),
    [("30", 60, True), ("60", 60, False), ("1800", 1800, False), ("5000", 3600, True), ("NaN", 60, True), ("Infinity", 3600, True)],
)
def test_wakeup_delay_is_clamped_to_claude_bounds(workspace, requested, clamped, was_clamped):
    plan = run(workspace, f"return loop.planWakeup({requested}, new Date(2026, 0, 1, 10, 0, 30).getTime());")

    assert (plan["clamped"], plan["wasClamped"]) == (clamped, was_clamped)
    assert plan["targetMs"] % 60000 == 0


def test_loop_file_is_truncated_at_claude_limit(workspace):
    result = run(
        workspace,
        "const t = loop.truncateLoopFile('x\\n'.repeat(20000)); return [t.length < 40000, t.endsWith('Keep the task list concise.')];",
    )

    assert result == [True, True]


def test_loop_file_prefers_pi_then_claude_locations(workspace, tmp_path):
    project, home = tmp_path / "project", tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "loop.md").write_text("claude user tasks")
    (project / ".claude").mkdir(parents=True)
    (project / ".claude" / "loop.md").write_text("claude project tasks")
    first = run(workspace, f"return loop.readLoopFile({json.dumps(str(project))}, {json.dumps(str(home))});")
    (project / ".pi").mkdir()
    (project / ".pi" / "loop.md").write_text("pi project tasks")
    second = run(workspace, f"return loop.readLoopFile({json.dumps(str(project))}, {json.dumps(str(home))});")

    assert first["content"] == "claude project tasks"
    assert second["content"] == "pi project tasks"


def test_autonomous_sentinel_delivers_the_preamble_once(workspace):
    result = run(
        workspace,
        """
        const delivery = { lastLoopFileDelivered: null, autonomousPreambleDelivered: false };
        const first = loop.resolveSentinel(delivery, "<<autonomous-loop>>", () => null);
        const second = loop.resolveSentinel(delivery, "<<autonomous-loop>>", () => null);
        return [first.startsWith("# Autonomous loop check"), second.startsWith("# Autonomous loop tick")];
        """,
    )

    assert result == [True, True]


def test_fixed_loop_runs_now_then_ticks_without_overlapping_a_turn(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(new Date(2026, 0, 1, 10, 0, 30).getTime());
        const { pi, ctx, state, emit, settle } = fakePi();
        loop.createLoop(pi, clock);
        await emit("session_start", { reason: "startup" });
        await state.commands["cc-loop"].handler("1m reply with the word tick", ctx);
        const confirmation = state.messages[0].custom;
        const immediate = state.sent.length;
        clock.advance(2 * 60000);
        const whileBusy = state.sent.length;
        await settle();
        const afterSettle = state.sent.length;
        await settle();
        clock.advance(60000);
        return { confirmation, immediate, whileBusy, afterSettle, ticks: state.sent.length, active: state.active };
        """,
    )

    assert "Auto-expires after 7 days" in result["confirmation"]
    assert "cron `* * * * *`" in result["confirmation"]
    assert result["immediate"] == 1
    assert result["whileBusy"] == 1
    assert result["afterSettle"] == 2
    assert result["ticks"] == 3
    assert {"schedule_wakeup", "cron_list", "cron_delete"} <= set(result["active"])


def test_skill_prompts_expand_through_pi_skill_syntax(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(Date.now());
        const { pi, ctx, state, emit } = fakePi();
        loop.createLoop(pi, clock);
        await emit("session_start", { reason: "startup" });
        await state.commands["cc-loop"].handler("5m /babysit-prs now", ctx);
        return state.sent[0];
        """,
    )

    assert result == ["/skill:babysit-prs now", {"expandPromptTemplates": True}]


def test_recurring_job_fires_once_more_then_expires_after_seven_days(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(new Date(2026, 0, 1, 10, 0, 30).getTime());
        const { pi, ctx, state, emit, settle } = fakePi();
        loop.createLoop(pi, clock);
        await emit("session_start", { reason: "startup" });
        await state.commands["cc-loop"].handler("1d daily report", ctx);
        await settle();
        for (let day = 0; day < 9; day++) { clock.advance(86400000); await settle(); }
        await state.commands["cc-loop"].handler("list", ctx);
        return { runs: state.sent.length, listing: state.messages.at(-1).notify, timers: clock.pending() };
        """,
    )

    immediate, inside_the_window, final = 1, 7, 1
    assert result["runs"] == immediate + inside_the_window + final
    assert result["listing"] == "No scheduled jobs."
    assert result["timers"] == 0


def test_list_and_stop_mirror_cron_list_and_cron_delete(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(Date.now());
        const { pi, ctx, state, emit, settle } = fakePi();
        loop.createLoop(pi, clock);
        await emit("session_start", { reason: "startup" });
        await state.commands["cc-loop"].handler("5m check the deploy", ctx);
        await settle();
        const id = state.messages[0].custom.match(/job ([0-9a-f]+)/)[1];
        await state.commands["cc-loop"].handler("list", ctx);
        const listing = state.messages.at(-1).notify;
        await state.commands["cc-loop"].handler(`stop ${id}`, ctx);
        const stopped = state.messages.at(-1).notify;
        await state.commands["cc-loop"].handler(`stop ${id}`, ctx);
        return { id, listing, stopped, missing: state.messages.at(-1).notify, timers: clock.pending() };
        """,
    )

    assert result["listing"] == f"{result['id']} - Every 5 minutes (recurring) [session-only]: check the deploy"
    assert result["stopped"] == f"Cancelled job {result['id']}."
    assert result["missing"] == f"No scheduled job with id '{result['id']}'"
    assert result["timers"] == 0


def test_dynamic_loop_rearms_through_the_wakeup_tool(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(new Date(2026, 0, 1, 10, 0, 30).getTime());
        const { pi, ctx, state, emit, settle } = fakePi();
        loop.createLoop(pi, clock);
        await emit("session_start", { reason: "startup" });
        const inactive = !state.active.includes("schedule_wakeup");
        await state.commands["cc-loop"].handler("check the time", ctx);
        const instructions = state.messages[0].custom;
        const tool = state.tools.schedule_wakeup;
        const scheduled = await tool.execute("t1", { delaySeconds: 30, reason: "polling", prompt: "/cc-loop check the time", noop: true }, undefined, undefined, ctx);
        await settle();
        clock.advance(3 * 60000);
        const stopped = await tool.execute("t2", { stop: true }, undefined, undefined, ctx);
        const announced = state.messages.filter((message) => message.custom?.startsWith("# /cc-loop - self-paced loop")).length;
        await settle();
        const activeAfterStop = state.active.includes("schedule_wakeup");
        return { inactive, instructions, announced, scheduled: scheduled.content[0].text, fired: state.sent.slice(-2), stopped: stopped.content[0].text, defaultActive: tool.defaultActive, activeAfterStop };
        """,
    )

    assert result["inactive"] is True
    assert result["defaultActive"] is False
    assert "schedule_wakeup" in result["instructions"]
    assert "(clamped to 60s from your requested value)" in result["scheduled"]
    assert result["fired"] == [
        ["/cc-loop check the time", {"expandPromptTemplates": True}],
        ["check the time", {"expandPromptTemplates": True}],
    ]
    assert result["announced"] == 2
    assert result["stopped"].startswith("Loop stopped")
    assert result["activeAfterStop"] is False


def test_dynamic_loop_falls_back_to_one_keepalive_then_ends(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(new Date(2026, 0, 1, 10, 0, 30).getTime());
        const { pi, ctx, state, emit, settle } = fakePi();
        loop.createLoop(pi, clock);
        await emit("session_start", { reason: "startup" });
        await state.commands["cc-loop"].handler("check the time", ctx);
        await settle();
        const armed = clock.pending();
        clock.advance(1199 * 1000);
        const early = state.sent.length;
        clock.advance(120 * 1000);
        const fired = state.sent.length;
        await settle();
        return { armed, early, fired, after: clock.pending() };
        """,
    )

    assert result["armed"] == 1
    assert result["early"] == 1
    reentry_and_prompt = 2
    assert result["fired"] == 1 + reentry_and_prompt
    assert result["after"] == 0


def test_user_abort_cancels_the_dynamic_loop(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(Date.now());
        const { pi, ctx, state, emit, settle } = fakePi();
        loop.createLoop(pi, clock);
        await emit("session_start", { reason: "startup" });
        await state.commands["cc-loop"].handler("check the time", ctx);
        await state.tools.schedule_wakeup.execute("t", { delaySeconds: 600, reason: "r", prompt: "/cc-loop check the time", noop: false }, undefined, undefined, ctx);
        await settle("aborted");
        return clock.pending();
        """,
    )

    assert result == 0


def test_live_jobs_are_restored_on_resume_and_cleared_on_shutdown(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(Date.now());
        const first = fakePi();
        loop.createLoop(first.pi, clock);
        await first.emit("session_start", { reason: "startup" });
        await first.state.commands["cc-loop"].handler("10m check the deploy", first.ctx);
        await first.emit("session_shutdown", { reason: "quit" });
        const afterShutdown = clock.pending();
        const second = fakePi();
        second.state.entries = first.state.entries;
        loop.createLoop(second.pi, clock);
        await second.emit("session_start", { reason: "resume" });
        await second.state.commands["cc-loop"].handler("list", second.ctx);
        return { afterShutdown, restored: clock.pending(), listing: second.state.messages.at(-1).notify };
        """,
    )

    assert result["afterShutdown"] == 0
    assert result["restored"] == 1
    assert "check the deploy" in result["listing"]


def test_sources_carry_no_em_or_en_dashes():
    for path in (EXTENSION, README):
        text = path.read_text()
        assert not any(dash in text for dash in DASHES), path


def test_default_run_inlines_the_preamble_so_the_first_tick_sends_the_reminder(workspace):
    result = run(
        workspace,
        """
        const clock = fakeClock(new Date(2026, 0, 1, 10, 0, 30).getTime());
        const { pi, ctx, state, emit, settle } = fakePi();
        loop.createLoop(pi, clock, "/nonexistent-home");
        await emit("session_start", { reason: "startup" });
        await state.commands["cc-loop"].handler("5m", ctx);
        await settle();
        clock.advance(10 * 60000);
        return [state.sent[0][0].includes("# Autonomous loop check"), state.sent[1][0].startsWith("# Autonomous loop tick")];
        """,
    )

    assert result == [True, True]


def test_role_activates_the_extension():
    assert "cc-loop" in yaml.safe_load(DEFAULTS.read_text())["PI_EXTENSIONS"]
