import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from dotkit.testing import PI

PROBE = PI / "minion" / "runtime-probe.ts"
EXERCISE = Path(__file__).parent / "fixtures" / "minion-tool-execution.mjs"
MODEL = {"provider": "anthropic", "id": "claude-haiku-4-5"}
CANCELLATION = EXERCISE.with_name("minion-cancellation.mjs")
POLICY = EXERCISE.with_name("minion-policy-tampering.mjs")
FAKE_PROVIDER = EXERCISE.with_name("minion-fake-provider.mjs")
FAKE_GIT = EXERCISE.with_name("minion-fake-git.mjs")
CONTROL = PI / "minion" / "control.ts"
DELIVERY = PI / "minion" / "delivery.ts"
CHECKOUT = PI / "minion" / "checkout.ts"
GOAL_LOOP = PI / "minion" / "goal-loop.ts"
RUNTIME = PI / "minion" / "runtime.ts"
MINION_EXTENSION = PI / "extensions" / "minion.ts"
COMMIT_SKILL = PI.parent / "claude" / "skills" / "commit" / "SKILL.md"
PR_SKILL = PI.parent / "claude" / "skills" / "pr" / "SKILL.md"
PI_PACKAGE = "@earendil-works/pi-coding-agent"


def installed_pi_package():
    binary = shutil.which("pi")
    if binary is None:
        return None
    root = Path(binary).resolve().parent.parent
    for candidate in (
        root / "lib/node_modules" / PI_PACKAGE,
        root / "libexec/lib/node_modules" / PI_PACKAGE,
    ):
        if candidate.is_dir():
            return candidate
    return None


def package_import(package):
    manifest = json.loads((package / "package.json").read_text())
    return (package / manifest["exports"]["."]["import"]).resolve()


def install_minion_fake_provider(agent_dir, package, responses, observation_path):
    ai_import = (package / "node_modules" / "@earendil-works" / "pi-ai" / "dist" / "index.js").resolve()
    extension = agent_dir / "extensions" / "minion-fake.ts"
    extension.parent.mkdir(parents=True)
    extension.write_text(
        "\n".join(
            [
                f'import * as ai from {json.dumps(ai_import.as_uri())};',
                f'import {{ registerMinionFakeProvider }} from {json.dumps(FAKE_PROVIDER.as_uri())};',
                "export default function register(pi) {",
                "  registerMinionFakeProvider(",
                "    pi,",
                "    ai,",
                f"    {json.dumps(responses)},",
                f"    {json.dumps(str(observation_path))},",
                "  );",
                "}",
                "",
            ]
        )
    )


def install_delivery_skills(agent_dir):
    for source in (COMMIT_SKILL, PR_SKILL):
        destination = agent_dir / "skills" / source.parent.name / source.name
        destination.parent.mkdir(parents=True)
        shutil.copyfile(source, destination)


def install_minion_fake_git(tmp_path, monkeypatch):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    git = fake_bin / "git"
    git.write_text(FAKE_GIT.read_text())
    git.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    return git


def start_minion_runner(
    agent_dir,
    work,
    package,
    max_runtime_ms=5_000,
    max_cycles=4,
    max_no_progress_cycles=2,
    delivery_authority=None,
    goal="exercise detached SDK runner",
):
    delivery_line = (
        f"deliveryAuthority: {json.dumps(delivery_authority)},"
        if delivery_authority is not None
        else ""
    )
    script = f'''
    import {{ startRunner }} from {json.dumps(CONTROL.as_uri())};
    const started = await startRunner({{
      agentDir: {json.dumps(str(agent_dir))},
      cwd: {json.dumps(str(work))},
      goal: {json.dumps(goal)},
      sdkPath: {json.dumps(str(package_import(package)))},
      model: {{ provider: "minion-fake", id: "minion-fake" }},
      thinkingLevel: "off",
      maxRuntimeMs: {max_runtime_ms},
      heartbeatMs: 25,
      maxCycles: {max_cycles},
      maxNoProgressCycles: {max_no_progress_cycles},
      {delivery_line}
    }});
    process.stdout.write(JSON.stringify(started));
    '''
    launched = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert launched.returncode == 0, launched.stderr
    return json.loads(launched.stdout)


def wait_for_minion_status(status_path, states, timeout=5):
    deadline = time.monotonic() + timeout
    status = None
    while time.monotonic() < deadline:
        if status_path.exists():
            status = json.loads(status_path.read_text())
            if status["state"] in states:
                return status
        time.sleep(0.02)
    pytest.fail(f"Minion did not reach {states}: {status}")


def test_minion_extension_resolves_helpers_from_its_realpath():
    source = MINION_EXTENSION.read_text()
    assert 'from "../minion/' not in source
    assert 'import { getAgentDir' not in source
    assert "realpathSync(fileURLToPath(import.meta.url))" in source
    assert "realpathSync(process.argv[1])" in source


def test_minion_extension_loads_from_the_deployed_symlink(tmp_path):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify the deployed Minion extension")
    agent_dir = tmp_path / "agent"
    extension = agent_dir / "extensions" / "minion.ts"
    extension.parent.mkdir(parents=True)
    extension.symlink_to(MINION_EXTENSION)
    script = f'''
    process.argv[1] = {json.dumps(str(package / "dist" / "bundle" / "cli.js"))};
    const loaded = await import({json.dumps(extension.as_uri())});
    if (typeof loaded.default !== "function") process.exit(2);
    '''
    loaded = subprocess.run(
        ["node", "--preserve-symlinks", "--input-type=module", "-e", script],
        env={**os.environ, "MINION_ENABLE": "1", "PI_CODING_AGENT_DIR": str(agent_dir)},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert loaded.returncode == 0, loaded.stderr


@pytest.fixture
def minion_extension(tmp_path):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion extension")
    root = tmp_path / "extension"
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    copied = root / "extensions" / "minion.ts"
    copied.parent.mkdir()
    copied.write_text(MINION_EXTENSION.read_text())
    shutil.copytree(PI / "minion", root / "minion")
    return copied


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({}, "denied"),
        ({"mutated": True}, "mutated"),
        ({"mutated": True, "toolError": False}, "mutated"),
        ({"toolError": False}, "unchanged-unconfirmed"),
        ({"toolError": None}, "not-exercised"),
        ({"refusalObserved": False}, "tool-error-unconfirmed"),
        ({"controlSucceeded": False}, "control-not-exercised"),
        ({"attempted": False}, "not-exercised"),
        ({"promptError": "rejected"}, "prompt-rejected"),
        ({"rejections": ["listen EPERM"], "attempted": False}, "startup-refused"),
    ],
)
def test_policy_classifier_requires_control_and_snapshots_not_just_tool_flags(changes, expected):
    observation = {
        "rejections": [], "controlSucceeded": True, "attempted": True,
        "mutated": False, "toolError": True, "promptError": None, "refusalObserved": True,
    }
    script = f'''
    import {{ classifyPolicy }} from {json.dumps(POLICY.as_uri())};
    process.stdout.write(JSON.stringify(classifyPolicy({json.dumps(observation | changes)})));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"outcome": expected, "containmentGate": "blocked"}


@pytest.mark.parametrize(
    "provider_path, expected",
    [
        (
            {"provider": "cursor", "api": "anthropic-messages", "registeredConfig": False, "registeredNative": False},
            {"outcome": "pi-core-provider", "providerPathGate": "eligible", "containmentGate": "blocked"},
        ),
        (
            {"provider": "provider-alias", "api": "cursor-sdk", "registeredConfig": False, "registeredNative": False},
            {"outcome": "known-host-tools", "providerPathGate": "blocked", "containmentGate": "blocked"},
        ),
        (
            {"provider": "custom", "api": "anthropic-messages", "registeredConfig": True, "registeredNative": False},
            {"outcome": "extension-config-unverified", "providerPathGate": "blocked", "containmentGate": "blocked"},
        ),
        (
            {"provider": "custom", "api": "anthropic-messages", "registeredConfig": False, "registeredNative": True},
            {"outcome": "extension-native-unverified", "providerPathGate": "blocked", "containmentGate": "blocked"},
        ),
    ],
)
def test_provider_classifier_uses_execution_path_not_provider_name(provider_path, expected):
    script = f'''
    import {{ classifyProviderPath }} from {json.dumps(PROBE.as_uri())};
    process.stdout.write(JSON.stringify(classifyProviderPath({json.dumps(provider_path)})));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == expected


@pytest.mark.parametrize(
    "dirty_status, operation, expected",
    [
        (" M tracked.txt", None, "clean checkout"),
        (None, "MERGE_HEAD", "unresolved Git operation"),
    ],
)
def test_minion_refuses_dirty_or_unresolved_checkout_before_creating_mission(
    tmp_path, monkeypatch, dirty_status, operation, expected
):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion checkout admission")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    (work / "tracked.txt").write_text("baseline\n")
    if dirty_status:
        monkeypatch.setenv("MINION_FAKE_GIT_STATUS", dirty_status)
    if operation:
        (work / ".git" / operation).write_text("in progress\n")
    script = f'''
    import {{ startRunner }} from {json.dumps(CONTROL.as_uri())};
    try {{
      await startRunner({{
        agentDir: {json.dumps(str(agent_dir))},
        cwd: {json.dumps(str(work))},
        goal: "must be refused",
        sdkPath: {json.dumps(str(package_import(package)))},
        model: {{ provider: "minion-fake", id: "minion-fake" }},
        thinkingLevel: "off",
        maxRuntimeMs: 500,
        heartbeatMs: 25,
        maxCycles: 2,
        maxNoProgressCycles: 1,
      }});
      process.stdout.write(JSON.stringify({{ started: true }}));
    }} catch (error) {{
      process.stdout.write(JSON.stringify({{ started: false, error: error.message }}));
    }}
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["started"] is False
    assert expected in result["error"]
    assert not (agent_dir / "minion").exists()


def test_minion_refuses_a_second_runner_for_the_same_checkout(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion checkout lease")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(agent_dir, package, [{"text": "working", "delayMs": 5_000}], observations)
    first = start_minion_runner(agent_dir, work, package, max_runtime_ms=5_000)
    wait_for_minion_status(Path(first["statusPath"]), {"running"}, timeout=2)
    script = f'''
    import {{ startRunner }} from {json.dumps(CONTROL.as_uri())};
    try {{
      const started = await startRunner({{
        agentDir: {json.dumps(str(agent_dir))},
        cwd: {json.dumps(str(work))},
        goal: "must be refused",
        sdkPath: {json.dumps(str(package_import(package)))},
        model: {{ provider: "minion-fake", id: "minion-fake" }},
        thinkingLevel: "off",
        maxRuntimeMs: 1_000,
        heartbeatMs: 25,
        maxCycles: 2,
        maxNoProgressCycles: 1,
      }});
      process.stdout.write(JSON.stringify({{ started: true, id: started.id }}));
    }} catch (error) {{
      process.stdout.write(JSON.stringify({{ started: false, error: error.message }}));
    }}
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["started"] is False
    assert "already active" in result["error"]
    assert len(list((agent_dir / "minion" / "missions").iterdir())) == 1
    wait_for_minion_status(Path(first["statusPath"]), {"limit-reached"})


def test_minion_extension_is_inert_until_explicitly_enabled(minion_extension, tmp_path):
    script = f'''
    import register from {json.dumps(minion_extension.as_uri())};
    const commands = {{}};
    register({{registerCommand: (name, options) => commands[name] = options}});
    process.stdout.write(JSON.stringify(Object.keys(commands)));
    '''
    env = {key: value for key, value in os.environ.items() if key != "MINION_ENABLE"}
    env["PI_CODING_AGENT_DIR"] = str(tmp_path / "agent")
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == []
    assert not (tmp_path / "agent" / "minion").exists()


@pytest.mark.parametrize(
    "trusted, model, expected",
    [
        (False, {"provider": "minion-fake", "id": "minion-fake"}, "trusted project"),
        (True, None, "selected model"),
    ],
)
def test_minion_start_refuses_missing_trust_or_model(minion_extension, tmp_path, trusted, model, expected):
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    work.mkdir()
    script = f'''
    import register from {json.dumps(minion_extension.as_uri())};
    const commands = {{}};
    const notifications = [];
    register({{ registerCommand: (name, options) => commands[name] = options }});
    await commands.minion.handler("start refused goal", {{
      cwd: {json.dumps(str(work))},
      hasUI: true,
      isProjectTrusted: () => {json.dumps(trusted)},
      model: {json.dumps(model)},
      ui: {{
        confirm: async () => true,
        notify: (message, type = "info") => notifications.push({{ message, type }}),
      }},
    }});
    process.stdout.write(JSON.stringify(notifications));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={**os.environ, "MINION_ENABLE": "1", "PI_CODING_AGENT_DIR": str(agent_dir)},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    notifications = json.loads(done.stdout)
    assert notifications == [{"message": f"Minion requires a {expected}", "type": "error"}]
    assert not (agent_dir / "minion").exists()


def test_minion_start_requires_confirmation_and_exposes_status_and_watch(minion_extension, tmp_path, monkeypatch):
    package = installed_pi_package()
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [{"report": {"outcome": "done", "summary": "finished", "changedAreas": [], "checks": []}, "delayMs": 1_000}],
        tmp_path / "model-calls.jsonl",
    )
    script = f'''
    import register from {json.dumps(minion_extension.as_uri())};
    const commands = {{}};
    const notifications = [];
    let approved = false;
    register({{registerCommand: (name, options) => commands[name] = options}});
    const ctx = {{
      cwd: {json.dumps(str(work))},
      hasUI: true,
      isProjectTrusted: () => true,
      model: {{ provider: "minion-fake", id: "minion-fake" }},
      thinkingLevel: "off",
      ui: {{
        confirm: async () => approved,
        notify: (message, type = "info") => notifications.push({{message, type}}),
      }},
    }};
    await commands.minion.handler("start fake goal", ctx);
    const beforeApproval = notifications.length;
    const filesBeforeApproval = await import("node:fs").then(fs => fs.existsSync({json.dumps(str(agent_dir / "minion"))}));
    approved = true;
    await commands.minion.handler("start fake goal", ctx);
    await new Promise(resolve => setTimeout(resolve, 120));
    await commands.minion.handler("status", ctx);
    await commands.minion.handler("watch", ctx);
    process.stdout.write(JSON.stringify({{
      names: Object.keys(commands),
      beforeApproval,
      filesBeforeApproval,
      notifications,
    }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=work,
        env={
            **os.environ,
            "MINION_ENABLE": "1",
            "MINION_MAX_RUNTIME_MS": "5000",
            "MINION_HEARTBEAT_MS": "25",
            "PI_CODING_AGENT_DIR": str(agent_dir),
        },
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["names"] == ["minion"]
    assert result["beforeApproval"] == 0
    assert result["filesBeforeApproval"] is False
    messages = [entry["message"] for entry in result["notifications"]]
    assert any(message.startswith("Minion started: ") for message in messages)
    running = next(message for message in messages if "state: running" in message)
    assert "delivery: not-authorized" in running
    assert "last activity:" in running
    assert any("runner started" in message for message in messages)


def test_fake_runner_survives_its_launcher_and_stops_at_its_limit(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion SDK runtime")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(agent_dir, package, [{"text": "working", "delayMs": 5_000}], tmp_path / "model-calls.jsonl")
    script = f'''
    import {{ startRunner }} from {json.dumps(CONTROL.as_uri())};
    const started = await startRunner({{
      agentDir: {json.dumps(str(agent_dir))},
      cwd: {json.dumps(str(work))},
      goal: "exercise the detached runner",
      sdkPath: {json.dumps(str(package_import(package)))},
      model: {{ provider: "minion-fake", id: "minion-fake" }},
      thinkingLevel: "off",
      maxRuntimeMs: 1200,
      heartbeatMs: 50,
      maxCycles: 4,
      maxNoProgressCycles: 2,
    }});
    process.stdout.write(JSON.stringify(started));
    '''
    launcher = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert launcher.returncode == 0, launcher.stderr
    started = json.loads(launcher.stdout)
    status_path = Path(started["statusPath"])
    log_path = Path(started["logPath"])
    deadline = time.monotonic() + 2
    status = None
    while time.monotonic() < deadline:
        if status_path.exists():
            status = json.loads(status_path.read_text())
            if status["state"] in {"running", "limit-reached"}:
                break
        time.sleep(0.02)
    assert status is not None
    assert status["state"] in {"running", "limit-reached"}
    assert status["pid"] == started["pid"]
    assert "runner started" in log_path.read_text()

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = json.loads(status_path.read_text())
        if status["state"] == "limit-reached":
            break
        time.sleep(0.02)
    assert status["state"] == "limit-reached"


def test_cancel_signals_only_a_matching_runner_identity(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion SDK runtime")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(agent_dir, package, [{"text": "working", "delayMs": 5_000}], tmp_path / "model-calls.jsonl")
    script = f'''
    import {{ cancelMission, readMissionStatus, startRunner }} from {json.dumps(CONTROL.as_uri())};
    const started = await startRunner({{
      agentDir: {json.dumps(str(agent_dir))},
      cwd: {json.dumps(str(work))},
      goal: "exercise cancellation identity",
      sdkPath: {json.dumps(str(package_import(package)))},
      model: {{ provider: "minion-fake", id: "minion-fake" }},
      thinkingLevel: "off",
      maxRuntimeMs: 5_000,
      heartbeatMs: 50,
      maxCycles: 4,
      maxNoProgressCycles: 2,
    }});
    let status;
    for (let attempt = 0; attempt < 50; attempt++) {{
      status = await readMissionStatus({json.dumps(str(agent_dir))}, started.id);
      if (status.state === "running" && status.heartbeat >= 2) break;
      await new Promise(resolve => setTimeout(resolve, 10));
    }}
    const expectedCommand = [status.runnerPath, status.missionDir, status.token].join(" ");
    const staleSignals = [];
    const stale = await cancelMission({json.dumps(str(agent_dir))}, started.id, {{
      inspectCommand: () => "node unrelated-runner.ts",
      signalProcessGroup: pid => staleSignals.push(pid),
    }});
    const matchingSignals = [];
    const matching = await cancelMission({json.dumps(str(agent_dir))}, started.id, {{
      inspectCommand: () => expectedCommand,
      signalProcessGroup: pid => {{ matchingSignals.push(pid); process.kill(-pid, "SIGTERM"); }},
    }});
    let cancelled;
    for (let attempt = 0; attempt < 50; attempt++) {{
      cancelled = await readMissionStatus({json.dumps(str(agent_dir))}, started.id);
      if (cancelled.state === "cancelled") break;
      await new Promise(resolve => setTimeout(resolve, 10));
    }}
    process.stdout.write(JSON.stringify({{matching, matchingSignals, stale, staleSignals, pid: status.pid, state: cancelled.state}}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["matching"]["outcome"] == "requested"
    assert result["matchingSignals"] == [result["pid"]]
    assert result["stale"]["outcome"] == "identity-mismatch"
    assert result["staleSignals"] == []
    assert result["state"] == "cancelled"


def test_goal_loop_continues_one_session_until_done():
    script = f'''
    import {{ createMinionReporter, runGoalLoop }} from {json.dumps(GOAL_LOOP.as_uri())};
    const reporter = createMinionReporter();
    const scriptedReports = [
      {{ outcome: "continue", summary: "first slice complete", nextAction: "finish the checks" }},
      {{ outcome: "done", summary: "goal complete", changedAreas: ["runner"], checks: ["focused tests"] }},
    ];
    const prompts = [];
    const session = {{
      abort: async () => {{}},
      prompt: async prompt => {{
        prompts.push(prompt);
        const report = scriptedReports.shift();
        await reporter.tool.execute(String(prompts.length), report);
      }},
    }};
    const result = await runGoalLoop({{
      goal: "implement one persistent session",
      maxCycles: 4,
      maxNoProgressCycles: 2,
      deadlineAt: Date.now() + 5_000,
      reporter,
      session,
    }});
    process.stdout.write(JSON.stringify({{ result, prompts }}));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["result"] == {
        "state": "done",
        "cycles": 2,
        "noProgressCycles": 0,
        "report": {
            "outcome": "done",
            "summary": "goal complete",
            "changedAreas": ["runner"],
            "checks": ["focused tests"],
        },
    }
    assert len(observation["prompts"]) == 2
    assert "implement one persistent session" in observation["prompts"][0]
    assert "Continue with the next useful action" in observation["prompts"][1]


@pytest.mark.parametrize(
    "reports, max_cycles, max_no_progress, expected_state, expected_cycles, expected_prompts",
    [
        ([{"outcome": "blocked", "summary": "need input", "blocker": "missing requirement"}], 4, 2, "blocked", 1, 1),
        ([None, {"outcome": "done", "summary": "corrected", "changedAreas": [], "checks": []}], 4, 2, "done", 1, 2),
        ([None, None, None, None], 4, 2, "blocked", 2, 4),
        ([
            {"outcome": "continue", "summary": "one", "nextAction": "two"},
            {"outcome": "continue", "summary": "two", "nextAction": "three"},
        ], 2, 2, "limit-reached", 2, 2),
    ],
)
def test_goal_loop_stops_on_reports_and_cycle_limits(
    reports, max_cycles, max_no_progress, expected_state, expected_cycles, expected_prompts
):
    script = f'''
    import {{ createMinionReporter, runGoalLoop }} from {json.dumps(GOAL_LOOP.as_uri())};
    const reporter = createMinionReporter();
    const reports = {json.dumps(reports)};
    const prompts = [];
    const session = {{
      abort: async () => {{}},
      prompt: async prompt => {{
        prompts.push(prompt);
        const report = reports.shift();
        if (report) await reporter.tool.execute(String(prompts.length), report);
      }},
    }};
    const result = await runGoalLoop({{
      goal: "exercise stopping",
      maxCycles: {max_cycles},
      maxNoProgressCycles: {max_no_progress},
      deadlineAt: Date.now() + 5_000,
      reporter,
      session,
    }});
    process.stdout.write(JSON.stringify({{ result, promptCount: prompts.length }}));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["result"]["state"] == expected_state
    assert observation["result"]["cycles"] == expected_cycles
    assert observation["promptCount"] == expected_prompts


def test_sdk_runtime_uses_one_persistent_session_for_multiple_goal_cycles(tmp_path):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion SDK runtime")
    agent_dir = tmp_path / "agent"
    mission_dir = agent_dir / "minion" / "missions" / "runtime-test"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    mission_dir.mkdir(parents=True)
    work.mkdir()
    install_minion_fake_provider(
        agent_dir,
        package,
        [
            {"report": {"outcome": "continue", "summary": "first cycle", "nextAction": "finish"}},
            {"report": {"outcome": "done", "summary": "finished", "changedAreas": ["runtime"], "checks": ["fake"]}},
        ],
        observations,
    )
    script = f'''
    import {{ runSdkMission }} from {json.dumps(RUNTIME.as_uri())};
    const result = await runSdkMission({{
      sdkPath: {json.dumps(str(package_import(package)))},
      agentDir: {json.dumps(str(agent_dir))},
      missionDir: {json.dumps(str(mission_dir))},
      cwd: {json.dumps(str(work))},
      goal: "exercise the real SDK session",
      model: {{ provider: "minion-fake", id: "minion-fake" }},
      thinkingLevel: "off",
      maxCycles: 4,
      maxNoProgressCycles: 2,
      deadlineAt: Date.now() + 5_000,
      log: () => {{}},
    }});
    process.stdout.write(JSON.stringify(result));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    calls = [json.loads(line) for line in observations.read_text().splitlines()]
    assert result["state"] == "done"
    assert result["cycles"] == 2
    assert Path(result["sessionFile"]).is_file()
    assert len({call["sessionId"] for call in calls}) == 1
    assert calls[0]["roles"] == ["user"]
    assert calls[1]["roles"][-1] == "user"
    assert "toolResult" in calls[1]["roles"]


def test_sdk_runtime_corrects_one_malformed_report_before_counting_progress(tmp_path):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion SDK runtime")
    agent_dir = tmp_path / "agent"
    mission_dir = agent_dir / "minion" / "missions" / "correction-test"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    mission_dir.mkdir(parents=True)
    work.mkdir()
    install_minion_fake_provider(
        agent_dir,
        package,
        [
            {"report": {"outcome": "done", "summary": "missing required details"}},
            {"text": "report rejected"},
            {"report": {"outcome": "done", "summary": "corrected", "changedAreas": [], "checks": []}},
        ],
        observations,
    )
    script = f'''
    import {{ runSdkMission }} from {json.dumps(RUNTIME.as_uri())};
    const result = await runSdkMission({{
      sdkPath: {json.dumps(str(package_import(package)))},
      agentDir: {json.dumps(str(agent_dir))},
      missionDir: {json.dumps(str(mission_dir))},
      cwd: {json.dumps(str(work))},
      goal: "exercise report correction",
      model: {{ provider: "minion-fake", id: "minion-fake" }},
      thinkingLevel: "off",
      maxCycles: 4,
      maxNoProgressCycles: 2,
      deadlineAt: Date.now() + 5_000,
      log: () => {{}},
    }});
    process.stdout.write(JSON.stringify(result));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    calls = [json.loads(line) for line in observations.read_text().splitlines()]
    assert result["state"] == "done"
    assert result["cycles"] == 1
    assert result["noProgressCycles"] == 0
    assert len(calls) == 3
    assert calls[-1]["roles"].count("user") == 2


@pytest.mark.parametrize(
    "responses, max_cycles, expected_state, expected_cycles",
    [
        ([{"report": {"outcome": "done", "summary": "finished", "changedAreas": [], "checks": []}}], 4, "done", 1),
        ([{"report": {"outcome": "blocked", "summary": "cannot continue", "blocker": "missing input"}}], 4, "blocked", 1),
        ([{"text": "missing"}] * 4, 4, "blocked", 2),
        ([{"report": {"outcome": "continue", "summary": "working", "nextAction": "continue"}}] * 2, 2, "limit-reached", 2),
    ],
)
def test_detached_sdk_runner_records_terminal_goal_outcomes(
    tmp_path, monkeypatch, responses, max_cycles, expected_state, expected_cycles
):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion SDK runtime")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(agent_dir, package, responses, observations)
    started = start_minion_runner(agent_dir, work, package, max_cycles=max_cycles)
    status = wait_for_minion_status(Path(started["statusPath"]), {expected_state})
    assert status["cycle"] == expected_cycles
    assert Path(status["sessionPath"]).is_file()
    assert status["result"]
    assert list((agent_dir / "minion" / "leases").iterdir()) == []


def test_detached_sdk_runner_reports_guard_startup_failure_as_blocked(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute Minion startup guards")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [{"report": {"outcome": "done", "summary": "must not run", "changedAreas": [], "checks": []}}],
        observations,
    )
    (agent_dir / "extensions" / "required-guard.ts").write_text('''
    export default function register(pi) {
      pi.on("session_start", () => { throw new Error("required guard failed to start"); });
    }
    ''')
    started = start_minion_runner(agent_dir, work, package)
    status = wait_for_minion_status(Path(started["statusPath"]), {"blocked", "crashed"})
    assert status["state"] == "blocked"
    assert "required guard failed to start" in status["result"]
    assert not observations.exists()


def test_detached_sdk_worker_edits_checkout_runs_check_and_loads_project_instructions(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute trusted checkout tools")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    (work / "AGENTS.md").write_text("PROJECT_INSTRUCTION_MARKER\n")
    install_minion_fake_provider(
        agent_dir,
        package,
        [
            {"tool": {"name": "write", "arguments": {"path": "result.txt", "content": "ready\n"}}},
            {"tool": {"name": "bash", "arguments": {"command": "test -f result.txt && grep -q ready result.txt"}}},
            {"report": {"outcome": "done", "summary": "implemented and checked", "changedAreas": ["result.txt"], "checks": ["grep"]}},
        ],
        observations,
    )
    started = start_minion_runner(agent_dir, work, package)
    status = wait_for_minion_status(Path(started["statusPath"]), {"done"})
    calls = [json.loads(line) for line in observations.read_text().splitlines()]
    assert (work / "result.txt").read_text() == "ready\n"
    assert status["branch"] == "feature/minion-exercise-detached-sdk-runner"
    assert "PROJECT_INSTRUCTION_MARKER" in calls[0]["systemPrompt"]
    assert "exercise detached SDK runner" in calls[0]["userMessages"][-1]
    assert "routine in-scope implementation decisions independently" in calls[0]["userMessages"][-1]
    assert "Do not commit, push, or open a PR during implementation" in calls[0]["userMessages"][-1]
    assert "Publication authority is fixed for this mission: commit: no, push: no, PR: no" in calls[0]["userMessages"][-1]
    assert len(calls) == 3


def test_detached_sdk_worker_blocks_on_checkout_changes_outside_its_tools(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to observe trusted checkout changes")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [
            {"tool": {"name": "write", "arguments": {"path": "owned.txt", "content": "owned\n"}}},
            {
                "report": {"outcome": "continue", "summary": "first cycle", "nextAction": "continue"},
                "externalWrite": {"path": str(work / "external.txt"), "content": "external\n"},
            },
        ],
        observations,
    )
    started = start_minion_runner(agent_dir, work, package)
    status = wait_for_minion_status(Path(started["statusPath"]), {"blocked"})
    assert "Checkout changed outside Minion tool execution" in status["result"]
    assert len(observations.read_text().splitlines()) == 2
    assert (work / "owned.txt").read_text() == "owned\n"
    assert (work / "external.txt").read_text() == "external\n"


def test_detached_sdk_runner_cancel_stops_the_active_model_stream(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to execute the Minion SDK runtime")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(agent_dir, package, [{"text": "working", "delayMs": 5_000}], observations)
    started = start_minion_runner(agent_dir, work, package)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not observations.exists():
        time.sleep(0.02)
    assert observations.exists()
    status = json.loads(Path(started["statusPath"]).read_text())
    script = f'''
    import {{ cancelMission }} from {json.dumps(CONTROL.as_uri())};
    const result = await cancelMission({json.dumps(str(agent_dir))}, {json.dumps(started["id"])}, {{
      inspectCommand: () => {json.dumps(" ".join([status["runnerPath"], status["missionDir"], status["token"]]))},
      signalProcessGroup: pid => process.kill(-pid, "SIGTERM"),
    }});
    process.stdout.write(JSON.stringify(result));
    '''
    cancelled = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert cancelled.returncode == 0, cancelled.stderr
    assert json.loads(cancelled.stdout)["outcome"] == "requested"
    final = wait_for_minion_status(Path(started["statusPath"]), {"cancelled"})
    assert final["result"] == "Cancellation requested"
    assert list((agent_dir / "minion" / "leases").iterdir()) == []
    time.sleep(0.2)
    assert len(observations.read_text().splitlines()) == 1


def test_delivery_skill_prompts_follow_approved_authority():
    script = f'''
    import {{
      deliverySkillPrompts,
      formatDeliveryAuthority,
      parseStartArgs,
    }} from {json.dumps(DELIVERY.as_uri())};
    const parsed = parseStartArgs("--publish ship the fix");
    const rejected = [];
    for (const flag of ["--commit", "--push", "--pr"]) {{
      try {{
        parseStartArgs(`${{flag}} ship the fix`);
      }} catch (error) {{
        rejected.push(error.message);
      }}
    }}
    process.stdout.write(JSON.stringify({{
      goal: parsed.goal,
      authority: parsed.authority,
      summary: formatDeliveryAuthority(parsed.authority),
      prompts: deliverySkillPrompts(parsed.authority),
      unapproved: deliverySkillPrompts({{ commit: false, push: false, openPr: false }}),
      rejected,
    }}));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["goal"] == "ship the fix"
    assert result["authority"] == {"commit": True, "push": True, "openPr": True}
    assert "commit: yes" in result["summary"]
    assert result["prompts"] == [
        "/skill:commit --minion-approved-at-launch",
        "/skill:pr --minion-approved-at-launch",
    ]
    assert result["unapproved"] == []
    assert len(result["rejected"]) == 3
    assert all("Unknown Minion start flag" in message for message in result["rejected"])


def test_minion_launch_record_preserves_delivery_authority(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to record Minion delivery authority")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [{"report": {"outcome": "done", "summary": "finished", "changedAreas": [], "checks": []}}],
        tmp_path / "model-calls.jsonl",
    )
    authority = {"commit": True, "push": True, "openPr": True}
    started = start_minion_runner(agent_dir, work, package, delivery_authority=authority, goal="record authority")
    wait_for_minion_status(Path(started["statusPath"]), {"done", "blocked"})
    launch = json.loads((Path(started["missionDir"]) / "launch.json").read_text())
    assert launch["deliveryAuthority"] == authority
    status = json.loads(Path(started["statusPath"]).read_text())
    assert status["deliveryAuthority"] == authority


def test_worker_report_cannot_add_publication_authority(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion authority isolation")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [
            {
                "report": {
                    "outcome": "done",
                    "summary": "attempted escalation",
                    "changedAreas": [],
                    "checks": [],
                    "deliveryAuthority": {"commit": True, "push": True, "openPr": True},
                }
            },
            {"report": {"outcome": "done", "summary": "finished", "changedAreas": [], "checks": []}},
        ],
        observations,
    )
    started = start_minion_runner(agent_dir, work, package)
    status = wait_for_minion_status(Path(started["statusPath"]), {"done"})
    launch = json.loads((Path(started["missionDir"]) / "launch.json").read_text())
    calls = observations.read_text().splitlines()
    assert len(calls) == 2
    assert launch["deliveryAuthority"] == {"commit": False, "push": False, "openPr": False}
    assert status["deliveryAuthority"] == launch["deliveryAuthority"]
    assert status["deliveryState"] == "not-authorized"


def test_unapproved_mission_skips_delivery_skill_prompts(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion delivery gating")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [
            {"tool": {"name": "write", "arguments": {"path": "result.txt", "content": "ready\n"}}},
            {"report": {"outcome": "done", "summary": "finished", "changedAreas": ["result.txt"], "checks": ["test"]}},
        ],
        observations,
    )
    started = start_minion_runner(agent_dir, work, package)
    status = wait_for_minion_status(Path(started["statusPath"]), {"done"})
    calls = [json.loads(line) for line in observations.read_text().splitlines()]
    joined = json.dumps(calls)
    assert "/skill:commit" not in joined
    assert "/skill:pr" not in joined
    assert '<skill name="commit"' not in joined
    assert '<skill name="pr"' not in joined
    assert status["deliveryState"] == "not-authorized"
    assert (work / "result.txt").read_text() == "ready\n"
    git_state = json.loads((work / ".git" / "minion-fake-state.json").read_text())
    assert git_state["head"] == "0000000000000000000000000000000000000001"


def test_approved_mission_runs_delivery_skill_prompts(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion delivery prompts")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    observations = tmp_path / "model-calls.jsonl"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [
            {"tool": {"name": "write", "arguments": {"path": "result.txt", "content": "ready\n"}}},
            {"report": {"outcome": "done", "summary": "finished", "changedAreas": ["result.txt"], "checks": ["test"]}},
            {"tool": {"name": "bash", "arguments": {"command": "git add result.txt && git commit -m fake"}}},
            {"text": "commit complete"},
            {"text": "Created: https://github.com/example/project/pull/1"},
        ],
        observations,
    )
    install_delivery_skills(agent_dir)
    authority = {"commit": True, "push": True, "openPr": True}
    started = start_minion_runner(agent_dir, work, package, delivery_authority=authority, goal="publish work")
    status = wait_for_minion_status(Path(started["statusPath"]), {"done"})
    calls = [json.loads(line) for line in observations.read_text().splitlines()]
    user_messages = [message for call in calls for message in call["userMessages"]]
    assert any('<skill name="commit"' in message for message in user_messages)
    assert any('<skill name="pr"' in message for message in user_messages)
    assert all("--minion-approved-at-launch" in message for message in user_messages[-2:])
    assert status["deliveryState"] == "published"
    assert status["commitSha"] == "0000000000000000000000000000000000000002"
    assert status["pullRequestUrl"] == "https://github.com/example/project/pull/1"


def test_publication_failure_blocks_and_preserves_committed_work(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion publication failure")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [
            {"tool": {"name": "write", "arguments": {"path": "result.txt", "content": "ready\n"}}},
            {"report": {"outcome": "done", "summary": "finished", "changedAreas": ["result.txt"], "checks": ["test"]}},
            {"tool": {"name": "bash", "arguments": {"command": "git add result.txt && git commit -m fake"}}},
            {"text": "commit complete"},
            {"text": "PR creation failed"},
        ],
        tmp_path / "model-calls.jsonl",
    )
    install_delivery_skills(agent_dir)
    authority = {"commit": True, "push": True, "openPr": True}
    started = start_minion_runner(agent_dir, work, package, delivery_authority=authority, goal="preserve failure")
    status = wait_for_minion_status(Path(started["statusPath"]), {"blocked"})
    launch = json.loads((Path(started["missionDir"]) / "launch.json").read_text())
    git_state = json.loads((work / ".git" / "minion-fake-state.json").read_text())
    assert status["deliveryState"] == "failed"
    assert "did not report a created PR URL" in status["result"]
    assert (work / "result.txt").read_text() == "ready\n"
    assert git_state["branch"] == "feature/minion-preserve-failure"
    assert git_state["head"] == "0000000000000000000000000000000000000002"
    assert not Path(launch["leasePath"]).exists()
    assert Path(started["logPath"]).read_text()


def test_run_delivery_blocks_when_checkout_changes_during_publication(tmp_path, monkeypatch):
    if shutil.which("node") is None:
        pytest.skip("node is required to verify Minion delivery checkout changes")
    install_minion_fake_git(tmp_path, monkeypatch)
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    script = f'''
    import {{ writeFileSync }} from "node:fs";
    import {{ runDelivery }} from {json.dumps(DELIVERY.as_uri())};
    const messages = [];
    let calls = 0;
    const session = {{
      state: {{ messages }},
      prompt: async () => {{
        calls += 1;
        if (calls === 2) {{
          writeFileSync({json.dumps(str(work / "external.txt"))}, "changed");
          messages.push({{ role: "assistant", content: [{{ type: "text", text: "Created: https://github.com/example/project/pull/1" }}] }});
        }}
      }},
    }};
    const result = await runDelivery(
      session,
      {{ commit: true, push: true, openPr: true }},
      {json.dumps(str(work))},
      "main",
    );
    process.stdout.write(JSON.stringify({{ result, calls }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["calls"] == 2
    assert observation["result"]["ok"] is False
    assert "checkout changed" in observation["result"]["blocker"]


def test_run_delivery_blocks_when_a_skill_leaves_the_mission_branch(tmp_path, monkeypatch):
    if shutil.which("node") is None:
        pytest.skip("node is required to verify the Minion mission branch")
    install_minion_fake_git(tmp_path, monkeypatch)
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    state = {
        "branch": "feature/minion-work",
        "head": "0000000000000000000000000000000000000001",
        "branches": {
            "feature/minion-work": "0000000000000000000000000000000000000001",
            "feature/other": "0000000000000000000000000000000000000001",
        },
    }
    (work / ".git" / "minion-fake-state.json").write_text(json.dumps(state))
    script = f'''
    import {{ readFileSync, writeFileSync }} from "node:fs";
    import {{ runDelivery }} from {json.dumps(DELIVERY.as_uri())};
    let calls = 0;
    const session = {{
      state: {{ messages: [] }},
      prompt: async () => {{
        calls += 1;
        const path = {json.dumps(str(work / ".git" / "minion-fake-state.json"))};
        const state = JSON.parse(readFileSync(path, "utf8"));
        state.branch = "feature/other";
        writeFileSync(path, JSON.stringify(state));
      }},
    }};
    const result = await runDelivery(
      session,
      {{ commit: true, push: true, openPr: true }},
      {json.dumps(str(work))},
      "feature/minion-work",
    );
    process.stdout.write(JSON.stringify({{ result, calls }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["calls"] == 1
    assert observation["result"]["ok"] is False
    assert "mission branch" in observation["result"]["blocker"]


def test_run_delivery_blocks_when_commit_skill_leaves_changes(tmp_path, monkeypatch):
    if shutil.which("node") is None:
        pytest.skip("node is required to verify Minion commit evidence")
    install_minion_fake_git(tmp_path, monkeypatch)
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    script = f'''
    import {{ runDelivery }} from {json.dumps(DELIVERY.as_uri())};
    const messages = [];
    let calls = 0;
    const session = {{
      state: {{ messages }},
      prompt: async (text) => {{
        calls += 1;
        messages.push({{ role: "assistant", content: [{{ type: "text", text: "claimed success" }}] }});
      }},
    }};
    const result = await runDelivery(
      session,
      {{ commit: true, push: true, openPr: true }},
      {json.dumps(str(work))},
    );
    process.stdout.write(JSON.stringify({{ result, calls }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={
            **os.environ,
            "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "MINION_FAKE_GIT_STATUS": " M result.txt",
        },
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["calls"] == 1
    assert observation["result"]["ok"] is False
    assert "did not commit" in observation["result"]["blocker"]


def test_run_delivery_requires_a_created_pr_url():
    script = f'''
    import {{ runDelivery }} from {json.dumps(DELIVERY.as_uri())};
    const messages = [];
    const session = {{
      state: {{ messages }},
      prompt: async (text) => {{
        messages.push({{ role: "user", content: [{{ type: "text", text }}] }});
        messages.push({{ role: "assistant", content: [{{ type: "text", text: "finished without a PR URL" }}] }});
      }},
    }};
    const result = await runDelivery(session, {{ commit: true, push: true, openPr: true }});
    process.stdout.write(JSON.stringify(result));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["ok"] is False
    assert "PR URL" in result["blocker"]


def test_run_delivery_blocks_when_a_skill_prompt_fails():
    script = f'''
    import {{ runDelivery }} from {json.dumps(DELIVERY.as_uri())};
    let calls = 0;
    const session = {{
      state: {{ messages: [] }},
      prompt: async (text) => {{
        calls += 1;
        if (text.includes("/skill:pr")) throw new Error("PR creation failed");
      }},
    }};
    const result = await runDelivery(
      session,
      {{ commit: true, push: true, openPr: true }},
    );
    process.stdout.write(JSON.stringify({{ result, calls }}));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["calls"] == 2
    assert observation["result"]["ok"] is False
    assert "PR creation failed" in observation["result"]["blocker"]


def test_minion_creates_mission_branch_from_default(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion branch creation")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [{"report": {"outcome": "done", "summary": "finished", "changedAreas": [], "checks": []}}],
        tmp_path / "model-calls.jsonl",
    )
    started = start_minion_runner(agent_dir, work, package, goal="branch the work")
    status = wait_for_minion_status(Path(started["statusPath"]), {"done"})
    assert status["branch"] == "feature/minion-branch-the-work"
    launch = json.loads((Path(started["missionDir"]) / "launch.json").read_text())
    assert launch["missionBranchCreated"] is True


def test_minion_refuses_an_active_checkout_lease_without_switching_branches(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion lease admission")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    script = f'''
    import {{ acquireCheckoutLease, releaseCheckoutLease }} from {json.dumps(CHECKOUT.as_uri())};
    import {{ startRunner }} from {json.dumps(CONTROL.as_uri())};
    import {{ readFileSync }} from "node:fs";
    const lease = await acquireCheckoutLease(
      {json.dumps(str(agent_dir))},
      {json.dumps(str(work))},
      "existing-mission",
      "existing-token",
    );
    let message = "";
    try {{
      await startRunner({{
        agentDir: {json.dumps(str(agent_dir))},
        cwd: {json.dumps(str(work))},
        goal: "leave branch alone",
        sdkPath: {json.dumps(str(package_import(package)))},
        model: {{ provider: "minion-fake", id: "minion-fake" }},
        thinkingLevel: "off",
        maxRuntimeMs: 5000,
        heartbeatMs: 25,
        maxCycles: 4,
        maxNoProgressCycles: 2,
      }});
    }} catch (error) {{
      message = error.message;
    }} finally {{
      await releaseCheckoutLease(lease);
    }}
    const state = JSON.parse(readFileSync({json.dumps(str(work / ".git" / "minion-fake-state.json"))}, "utf8"));
    process.stdout.write(JSON.stringify({{ message, branch: state.branch }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert "already active" in result["message"]
    assert result["branch"] == "main"


def test_checkout_fingerprint_changes_when_branch_changes_at_same_head(tmp_path, monkeypatch):
    if shutil.which("node") is None:
        pytest.skip("node is required to verify checkout fingerprints")
    install_minion_fake_git(tmp_path, monkeypatch)
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    script = f'''
    import {{ readFileSync, writeFileSync }} from "node:fs";
    import {{ checkoutFingerprint }} from {json.dumps(CHECKOUT.as_uri())};
    const first = checkoutFingerprint({json.dumps(str(work))});
    const statePath = {json.dumps(str(work / ".git" / "minion-fake-state.json"))};
    const state = JSON.parse(readFileSync(statePath, "utf8"));
    state.branches["feature/minion-other"] = state.head;
    state.branch = "feature/minion-other";
    writeFileSync(statePath, JSON.stringify(state));
    const second = checkoutFingerprint({json.dumps(str(work))});
    process.stdout.write(JSON.stringify({{ first, second }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    fingerprints = json.loads(done.stdout)
    assert fingerprints["first"] != fingerprints["second"]


def test_minion_restores_branch_when_mission_creation_fails(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion branch rollback")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    (agent_dir / "minion").mkdir(parents=True)
    (agent_dir / "minion" / "missions").write_text("not a directory")
    script = f'''
    import {{ startRunner }} from {json.dumps(CONTROL.as_uri())};
    let message = "";
    try {{
      await startRunner({{
        agentDir: {json.dumps(str(agent_dir))},
        cwd: {json.dumps(str(work))},
        goal: "rollback failed launch",
        sdkPath: {json.dumps(str(package_import(package)))},
        model: {{ provider: "minion-fake", id: "minion-fake" }},
        thinkingLevel: "off",
        maxRuntimeMs: 5000,
        heartbeatMs: 25,
        maxCycles: 4,
        maxNoProgressCycles: 2,
      }});
    }} catch (error) {{
      message = error.message;
    }}
    process.stdout.write(JSON.stringify({{ message }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["message"]
    state = json.loads((work / ".git" / "minion-fake-state.json").read_text())
    assert state["branch"] == "main"
    assert "feature/minion-rollback-failed-launch" not in state["branches"]
    leases = agent_dir / "minion" / "leases"
    assert leases.exists()
    assert list(leases.iterdir()) == []


def test_minion_refuses_conflicting_mission_branch(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion branch conflicts")
    install_minion_fake_git(tmp_path, monkeypatch)
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    state = {
        "branch": "main",
        "head": "0000000000000000000000000000000000000001",
        "branches": {
            "main": "0000000000000000000000000000000000000001",
            "feature/minion-conflicting-branch": "0000000000000000000000000000000000000002",
        },
    }
    (work / ".git" / "minion-fake-state.json").write_text(json.dumps(state))
    script = f'''
    import {{ startRunner }} from {json.dumps(CONTROL.as_uri())};
    try {{
      await startRunner({{
        agentDir: {json.dumps(str(tmp_path / "agent"))},
        cwd: {json.dumps(str(work))},
        goal: "conflicting branch",
        sdkPath: {json.dumps(str(package_import(package)))},
        model: {{ provider: "minion-fake", id: "minion-fake" }},
        thinkingLevel: "off",
        maxRuntimeMs: 5000,
        heartbeatMs: 25,
        maxCycles: 4,
        maxNoProgressCycles: 2,
      }});
      process.stdout.write(JSON.stringify({{ ok: true }}));
    }} catch (error) {{
      process.stdout.write(JSON.stringify({{ ok: false, message: error.message }}));
    }}
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["ok"] is False
    assert "different history" in result["message"]
    assert not (tmp_path / "agent" / "minion" / "missions").exists()


def test_minion_reuses_a_conventional_current_branch(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion branch reuse")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    state = {
        "branch": "feature/existing-work",
        "head": "0000000000000000000000000000000000000001",
        "branches": {
            "main": "0000000000000000000000000000000000000001",
            "feature/existing-work": "0000000000000000000000000000000000000001",
        },
    }
    (work / ".git" / "minion-fake-state.json").write_text(json.dumps(state))
    install_minion_fake_provider(
        agent_dir,
        package,
        [{"report": {"outcome": "done", "summary": "finished", "changedAreas": [], "checks": []}}],
        tmp_path / "model-calls.jsonl",
    )
    started = start_minion_runner(agent_dir, work, package, goal="reuse branch")
    status = wait_for_minion_status(Path(started["statusPath"]), {"done"})
    launch = json.loads((Path(started["missionDir"]) / "launch.json").read_text())
    assert status["branch"] == "feature/existing-work"
    assert launch["missionBranchCreated"] is False


def test_minion_refuses_a_nonstandard_current_branch(tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion branch admission")
    install_minion_fake_git(tmp_path, monkeypatch)
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    state = {
        "branch": "wip/local",
        "head": "0000000000000000000000000000000000000001",
        "branches": {
            "main": "0000000000000000000000000000000000000001",
            "wip/local": "0000000000000000000000000000000000000001",
        },
    }
    (work / ".git" / "minion-fake-state.json").write_text(json.dumps(state))
    script = f'''
    import {{ startRunner }} from {json.dumps(CONTROL.as_uri())};
    let message = "";
    try {{
      await startRunner({{
        agentDir: {json.dumps(str(tmp_path / "agent"))},
        cwd: {json.dumps(str(work))},
        goal: "reject branch",
        sdkPath: {json.dumps(str(package_import(package)))},
        model: {{ provider: "minion-fake", id: "minion-fake" }},
        thinkingLevel: "off",
        maxRuntimeMs: 5000,
        heartbeatMs: 25,
        maxCycles: 4,
        maxNoProgressCycles: 2,
      }});
    }} catch (error) {{
      message = error.message;
    }}
    process.stdout.write(JSON.stringify({{ message }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        env={**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    assert "nonstandard branch" in json.loads(done.stdout)["message"]
    unchanged = json.loads((work / ".git" / "minion-fake-state.json").read_text())
    assert unchanged["branch"] == "wip/local"
    assert not (tmp_path / "agent" / "minion" / "missions").exists()


def test_minion_start_confirmation_includes_publication_authority(minion_extension, tmp_path, monkeypatch):
    package = installed_pi_package()
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    install_minion_fake_provider(
        agent_dir,
        package,
        [{"report": {"outcome": "done", "summary": "finished", "changedAreas": [], "checks": []}}],
        tmp_path / "model-calls.jsonl",
    )
    script = f'''
    import register from {json.dumps(minion_extension.as_uri())};
    const commands = {{}};
    let confirmMessage = "";
    register({{registerCommand: (name, options) => commands[name] = options}});
    const ctx = {{
      cwd: {json.dumps(str(work))},
      hasUI: true,
      isProjectTrusted: () => true,
      model: {{ provider: "minion-fake", id: "minion-fake" }},
      thinkingLevel: "off",
      ui: {{
        confirm: async (_title, message) => {{ confirmMessage = message; return false; }},
        notify: () => {{}},
      }},
    }};
    await commands.minion.handler("start --publish ship it", ctx);
    process.stdout.write(JSON.stringify({{ confirmMessage }}));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=work,
        env={**os.environ, "MINION_ENABLE": "1", "PI_CODING_AGENT_DIR": str(agent_dir)},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    message = json.loads(done.stdout)["confirmMessage"]
    assert f"Repository: {work}" in message
    assert "Current branch: main" in message
    assert "Goal, success conditions, and constraints: ship it" in message
    assert "Model: minion-fake/minion-fake" in message
    assert "Limits: 3600s elapsed, 20 cycles" in message
    assert "Publication: commit: yes, push: yes, PR: yes" in message


def test_minion_revalidates_checkout_after_start_confirmation(minion_extension, tmp_path, monkeypatch):
    package = installed_pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are required to verify Minion checkout revalidation")
    install_minion_fake_git(tmp_path, monkeypatch)
    agent_dir = tmp_path / "agent"
    work = tmp_path / "work"
    (work / ".git").mkdir(parents=True)
    script = f'''
    import {{ writeFileSync }} from "node:fs";
    import register from {json.dumps(minion_extension.as_uri())};
    const commands = {{}};
    const notifications = [];
    register({{ registerCommand: (name, options) => commands[name] = options }});
    const ctx = {{
      cwd: {json.dumps(str(work))},
      hasUI: true,
      isProjectTrusted: () => true,
      model: {{ provider: "minion-fake", id: "minion-fake" }},
      thinkingLevel: "off",
      ui: {{
        confirm: async () => {{
          writeFileSync({json.dumps(str(work / "external.txt"))}, {json.dumps("changed\n")});
          return true;
        }},
        notify: (message, type) => notifications.push({{ message, type }}),
      }},
    }};
    await commands.minion.handler("start keep checkout stable", ctx);
    process.stdout.write(JSON.stringify(notifications));
    '''
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=work,
        env={**os.environ, "MINION_ENABLE": "1", "PI_CODING_AGENT_DIR": str(agent_dir)},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    notifications = json.loads(done.stdout)
    assert notifications == [{"message": "The checkout changed after Minion confirmation", "type": "error"}]
    assert not (agent_dir / "minion").exists()
    state = json.loads((work / ".git" / "minion-fake-state.json").read_text())
    assert state["branch"] == "main"


def test_goal_loop_blocks_when_checkout_changes_outside_worker_tools():
    script = f'''
    import {{ createMinionReporter, runGoalLoop }} from {json.dumps(GOAL_LOOP.as_uri())};
    const reporter = createMinionReporter();
    let checks = 0;
    let prompts = 0;
    const session = {{
      abort: async () => {{}},
      prompt: async () => {{
        prompts += 1;
        await reporter.tool.execute("report", {{
          outcome: "continue",
          summary: "cycle complete",
          nextAction: "continue",
        }});
      }},
    }};
    const result = await runGoalLoop({{
      goal: "detect external changes",
      maxCycles: 4,
      maxNoProgressCycles: 2,
      deadlineAt: Date.now() + 5_000,
      reporter,
      session,
      checkCheckout: () => ++checks === 2 ? "Checkout changed outside Minion tool execution" : undefined,
    }});
    process.stdout.write(JSON.stringify({{ result, checks, prompts }}));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["result"]["state"] == "blocked"
    assert observation["result"]["cycles"] == 1
    assert "outside Minion" in observation["result"]["report"]["blocker"]
    assert observation["checks"] == 2
    assert observation["prompts"] == 1


def test_goal_loop_aborts_an_active_prompt_at_its_elapsed_limit():
    script = f'''
    import {{ createMinionReporter, runGoalLoop }} from {json.dumps(GOAL_LOOP.as_uri())};
    const reporter = createMinionReporter();
    let settlePrompt;
    let aborts = 0;
    const session = {{
      abort: async () => {{ aborts += 1; settlePrompt?.(); }},
      prompt: async () => new Promise(resolve => settlePrompt = resolve),
    }};
    const started = Date.now();
    const result = await runGoalLoop({{
      goal: "exercise elapsed limit",
      maxCycles: 4,
      maxNoProgressCycles: 2,
      deadlineAt: started + 30,
      reporter,
      session,
    }});
    process.stdout.write(JSON.stringify({{ result, aborts, elapsed: Date.now() - started }}));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=2)
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["result"]["state"] == "limit-reached"
    assert observation["aborts"] == 1
    assert observation["elapsed"] < 500


def test_goal_loop_abort_stops_new_prompts():
    script = f'''
    import {{ createMinionReporter, runGoalLoop }} from {json.dumps(GOAL_LOOP.as_uri())};
    const reporter = createMinionReporter();
    const controller = new AbortController();
    let prompts = 0;
    let aborts = 0;
    const session = {{
      abort: async () => {{ aborts += 1; }},
      prompt: async () => {{ prompts += 1; controller.abort(); }},
    }};
    const result = await runGoalLoop({{
      goal: "exercise abort",
      maxCycles: 4,
      maxNoProgressCycles: 2,
      deadlineAt: Date.now() + 5_000,
      reporter,
      session,
      signal: controller.signal,
    }});
    process.stdout.write(JSON.stringify({{ result, aborts, prompts }}));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["result"]["state"] == "aborted"
    assert observation["prompts"] == 1
    assert observation["aborts"] == 1


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({}, "stopped-before-cleanup"),
        ({"writesAfterAbortReturn": 2}, "writes-after-abort"),
        ({"aliveBeforeCleanup": True}, "survived-abort"),
        ({"promptSettled": False}, "prompt-unsettled"),
        ({"abortReturned": False}, "abort-unsettled"),
        ({"deadlineReachedBeforeCleanup": True}, "deadline-confounded"),
        ({"ready": False}, "not-exercised"),
        ({"groupVerified": False}, "group-unverified"),
        ({"aliveBeforeCleanup": None}, "termination-unverified"),
        ({"promptError": "failed"}, "prompt-rejected"),
    ],
)
def test_cancellation_classifier_does_not_equate_prompt_or_cleanup_with_containment(changes, expected):
    observation = {
        "ready": True, "groupVerified": True, "abortReturned": True,
        "promptSettled": True, "writesAfterAbortReturn": 0,
        "aliveBeforeCleanup": False, "deadlineReachedBeforeCleanup": False,
        "cleanupRequested": True, "aliveAfterCleanup": False,
    }
    script = f'''
    import {{ classifyCancellation }} from {json.dumps(CANCELLATION.as_uri())};
    process.stdout.write(JSON.stringify(classifyCancellation({json.dumps(observation | changes)})));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"outcome": expected, "containmentGate": "blocked"}



@pytest.fixture
def probe(tmp_path):
    binary = shutil.which("pi")
    if binary is None or shutil.which("node") is None:
        pytest.skip("pi and node are required for the Minion SDK compatibility probe")
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()

    def run(extensions=(), calls=(), model=MODEL, exercise=False, cwd=None, cancellation=None, policy=None):
        working_dir = cwd or tmp_path
        options = {
            "piExecutable": binary,
            "cwd": str(working_dir),
            "agentDir": str(agent_dir),
            "extensionPaths": [str(path) for path in extensions],
            "model": model,
            "calls": list(calls),
        }
        callback = f'session => exerciseTools(session, {json.dumps(list(calls))})' if exercise else 'undefined'
        if cancellation:
            callback = f'session => exerciseCancellation(session, {json.dumps(str(working_dir))}, {json.dumps(cancellation)})'
        if policy:
            callback = 'session => exercisePolicy(session, policyOptions)'
        script = f"""
        import {{ probeRuntime }} from {json.dumps(PROBE.as_uri())};
        {f'import {{ exerciseTools }} from {json.dumps(EXERCISE.as_uri())};' if exercise else ''}
        {f'import {{ exerciseCancellation }} from {json.dumps(CANCELLATION.as_uri())};' if cancellation else ''}
        {f'import {{ exercisePolicy, observePolicy, snapshotPolicies }} from {json.dumps(POLICY.as_uri())};' if policy else ''}
        {f'const policyOptions = {json.dumps(policy)}; policyOptions.before = snapshotPolicies(policyOptions.paths);' if policy else ''}
        const result = await probeRuntime({json.dumps(options)}, {callback});
        {'result.policyObservation = observePolicy(result, policyOptions);' if policy else ''}
        process.stdout.write(JSON.stringify(result));
        """
        done = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=working_dir,
            env={**os.environ, "PI_CODING_AGENT_DIR": str(agent_dir), "PI_OFFLINE": "1"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)

    return run


POLICY_CASES = [
    (target, kind)
    for target in ["global-sandbox", "global-permission", "project-sandbox", "absent-project-sandbox"]
    for kind in ["write", "edit", "shell-write", "shell-replace"]
    if not (target == "absent-project-sandbox" and kind == "edit")
]


def build_sandbox_policy(work, agent, protect_project):
    deny_write = [str(agent)]
    if protect_project:
        deny_write.append(str(work / ".pi"))
    return {
        "enabled": True,
        "network": {"allowedDomains": [], "deniedDomains": []},
        "filesystem": {
            "allowRead": [str(work)], "denyRead": [],
            "allowWrite": [str(work)], "denyWrite": deny_write,
        },
    }


def test_minion_project_policy_denies_its_own_override_path(tmp_path):
    work = tmp_path / "work"
    agent = tmp_path / "agent"
    ordinary = build_sandbox_policy(work, agent, protect_project=False)
    protected = build_sandbox_policy(work, agent, protect_project=True)
    assert str(work / ".pi") not in ordinary["filesystem"]["denyWrite"]
    assert str(work / ".pi") in protected["filesystem"]["denyWrite"]
    assert protected["filesystem"]["allowWrite"] == [str(work)]


def test_probe_rejects_installed_sandbox_disabled_by_project_config(probe, tmp_path):
    installed_agent = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent"))
    packages = installed_agent / "npm" / "node_modules"
    extensions = [
        packages / "pi-sandbox" / "index.ts",
        packages / "@gotgenes" / "pi-permission-system" / "src" / "index.ts",
        PI / "extensions" / "guardrails.ts",
    ]
    if not all(path.is_file() for path in extensions):
        pytest.skip("installed guard packages are required for the disabled-project diagnostic")
    agent = tmp_path / "agent"
    work = tmp_path / "work"
    work.mkdir()
    permission = agent / "extensions" / "pi-permission-system" / "config.json"
    permission.parent.mkdir(parents=True)
    shutil.copyfile(PI / "permission-system" / "config.json", permission)
    (agent / "sandbox.json").write_text(json.dumps(build_sandbox_policy(work, agent, protect_project=True)))
    project = work / ".pi" / "sandbox.json"
    project.parent.mkdir()
    project.write_text('{"enabled":false}')
    target = work / "untouched.txt"
    result = probe(
        extensions,
        calls=[{"name": "write", "input": {"path": str(target), "content": "probe"}}],
        exercise=True,
        cwd=work,
    )
    assert result["notifications"] == [{"message": "Sandbox disabled via config", "type": "info"}]
    assert result["rejections"] == ["Sandbox disabled via config"]
    assert result["calls"] == []
    assert result["exercise"] is None
    assert not target.exists()


@pytest.fixture
def policy_probe(probe, tmp_path):
    def run(target, kind, extensions, protect_project=False):
        agent = tmp_path / "agent"
        work = tmp_path / "work"
        work.mkdir()
        permission = agent / "extensions" / "pi-permission-system" / "config.json"
        permission.parent.mkdir(parents=True)
        shutil.copyfile(PI / "permission-system" / "config.json", permission)
        project = work / ".pi" / "sandbox.json"
        project.parent.mkdir()
        sandbox = json.dumps(build_sandbox_policy(work, agent, protect_project))
        (agent / "sandbox.json").write_text(sandbox)
        if target != "absent-project-sandbox":
            project.write_text(sandbox)
        paths = {
            "global-sandbox": agent / "sandbox.json",
            "global-permission": permission,
            "project-sandbox": project,
        }
        selected = paths["project-sandbox" if target == "absent-project-sandbox" else target]
        candidate = '{"enabled":false}\n'
        control = work / "ordinary.json"
        if selected.exists():
            control.write_bytes(selected.read_bytes())
        shutil.copyfile(POLICY.with_name("minion-policy-child.mjs"), work / "minion-policy-child.mjs")
        (work / "minion-policy-case.json").write_text(json.dumps({"target": target, "candidate": candidate}))
        options = {
            "cwd": str(work), "target": target, "kind": kind, "path": str(selected),
            "paths": {name: str(path) for name, path in paths.items()},
            "candidate": candidate,
        }
        result = probe(extensions, cwd=work, policy=options)
        return result["policyObservation"]

    return run


@pytest.mark.parametrize("target, kind", POLICY_CASES)
@pytest.mark.parametrize("mode", ["allow", "deny"])
def test_policy_synthetic_allow_and_deny_exercise_real_tools(policy_probe, tmp_path, target, kind, mode, record_property):
    guard = tmp_path / "policy-guard.mjs"
    guard.write_text(
        'export default pi => { let calls = 0; pi.on("tool_call", () => {'
        f'const block = ++calls === 2 && {json.dumps(mode)} === "deny";'
        'return {block, reason: "synthetic policy denial"}; }); };'
    )
    observation = policy_probe(target, kind, [guard])
    record_property("synthetic_policy_observation", json.dumps(observation))
    print(json.dumps(observation))
    assert observation["rejections"] == []
    assert observation["controlSucceeded"] is True
    assert observation["attempted"] is True
    assert observation["classification"] == {
        "outcome": "mutated" if mode == "allow" else "denied", "containmentGate": "blocked",
    }
    assert observation["mutated"] is (mode == "allow")
    assert observation["toolError"] is (mode == "deny")
    selected = "project-sandbox" if target == "absent-project-sandbox" else target
    assert observation["before"][selected]["exists"] is (target != "absent-project-sandbox")
    for name, snapshot in observation["after"].items():
        if mode == "allow" and name == selected:
            assert snapshot["exists"] is True
            assert snapshot["bytes"] == observation["candidateBytes"]
        else:
            assert snapshot == observation["before"][name]
    assert len(observation["control"]["hooks"]) == len(observation["attempt"]["hooks"]) == 1
    assert len(observation["control"]["results"]) == len(observation["attempt"]["results"]) == 1
    if kind.startswith("shell"):
        assert observation["control"]["child"]["completed"] is True
        if mode == "deny":
            assert observation["attempt"]["child"] is None
        else:
            assert observation["attempt"]["child"]["completed"] is True
            assert observation["attempt"]["child"]["destination"] == observation["path"]
            assert observation["attempt"]["child"]["kind"] == kind


@pytest.mark.parametrize(
    "mode, expected",
    [("mutate-error", "mutated"), ("noop", "unchanged-unconfirmed"),
     ("noop-control", "control-not-exercised"), ("control-denied", "control-not-exercised"),
     ("startup-refused", "startup-refused")],
)
def test_policy_synthetic_failures_do_not_masquerade_as_resistance(policy_probe, tmp_path, mode, expected, record_property):
    guard = tmp_path / "policy-guard.mjs"
    guard.write_text(
        'import {readFileSync, writeFileSync} from "node:fs";'
        f'const mode = {json.dumps(mode)};'
        'export default pi => { let calls = 0;'
        'pi.on("session_start", () => { if (mode === "startup-refused") throw new Error("listen EPERM synthetic"); });'
        'pi.on("tool_call", event => { calls++;'
        'if (mode === "control-denied") return {block: true, reason: "control denied"};'
        'if ((mode === "noop" && calls === 2) || mode === "noop-control") event.input.content = readFileSync(event.input.path, "utf8");'
        'if (mode === "mutate-error" && calls === 2) {'
        'writeFileSync(event.input.path, event.input.content); return {block: true, reason: "error after mutation"}; }'
        '}); };'
    )
    observation = policy_probe("global-sandbox", "write", [guard])
    record_property("synthetic_policy_observation", json.dumps(observation))
    print(json.dumps(observation))
    assert observation["classification"] == {"outcome": expected, "containmentGate": "blocked"}
    if mode == "mutate-error":
        assert observation["mutated"] is True
        assert observation["toolError"] is True
    if mode in {"noop-control", "control-denied", "startup-refused"}:
        assert observation["attempted"] is False
        assert observation["attempt"] is None
        assert observation["mutated"] is False


@pytest.mark.parametrize("target, kind", POLICY_CASES)
def test_installed_guards_report_policy_immutability_or_startup_refusal(policy_probe, target, kind, record_property):
    installed_agent = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent"))
    packages = installed_agent / "npm" / "node_modules"
    extensions = [
        packages / "pi-sandbox" / "index.ts",
        packages / "@gotgenes" / "pi-permission-system" / "src" / "index.ts",
        PI / "extensions" / "guardrails.ts",
    ]
    if not all(path.is_file() for path in extensions):
        pytest.skip("installed guard packages are required for the policy exercise")
    observation = policy_probe(target, kind, extensions)
    record_property("installed_policy_observation", json.dumps(observation))
    print(json.dumps({
        **{key: observation[key] for key in (
            "target", "kind", "rejections", "controlSucceeded", "attempted", "mutated",
            "toolError", "refusalObserved", "layerEvidence", "promptError", "classification",
        )},
        "controlResults": (observation["control"] or {}).get("results", []),
        "attemptResults": (observation["attempt"] or {}).get("results", []),
    }))
    assert observation["classification"]["containmentGate"] == "blocked"
    if observation["rejections"]:
        assert observation["classification"]["outcome"] == "startup-refused"
        assert observation["control"] is None
        assert observation["attempt"] is None
        assert observation["attempted"] is False
        assert observation["mutated"] is False
    else:
        assert observation["classification"]["outcome"] in {
            "mutated", "denied", "control-not-exercised", "not-exercised", "unchanged-unconfirmed", "prompt-rejected", "tool-error-unconfirmed",
        }
        if observation["classification"]["outcome"] == "denied":
            assert observation["controlSucceeded"] is True
            assert observation["attempted"] is True
            assert observation["toolError"] is True
            assert observation["refusalObserved"] is True
            assert observation["mutated"] is False


@pytest.mark.parametrize(
    "target, kind",
    [case for case in POLICY_CASES if case[0] in {"project-sandbox", "absent-project-sandbox"}],
)
def test_installed_guards_report_minion_project_policy_protection_or_startup_refusal(
    policy_probe, target, kind, record_property,
):
    installed_agent = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent"))
    packages = installed_agent / "npm" / "node_modules"
    extensions = [
        packages / "pi-sandbox" / "index.ts",
        packages / "@gotgenes" / "pi-permission-system" / "src" / "index.ts",
        PI / "extensions" / "guardrails.ts",
    ]
    if not all(path.is_file() for path in extensions):
        pytest.skip("installed guard packages are required for the Minion project-policy exercise")
    observation = policy_probe(target, kind, extensions, protect_project=True)
    record_property("installed_minion_policy_observation", json.dumps(observation))
    print(json.dumps({
        **{key: observation[key] for key in (
            "target", "kind", "rejections", "controlSucceeded", "attempted", "mutated",
            "toolError", "refusalObserved", "layerEvidence", "promptError", "classification",
        )},
        "controlResults": (observation["control"] or {}).get("results", []),
        "attemptResults": (observation["attempt"] or {}).get("results", []),
    }))
    assert observation["classification"]["containmentGate"] == "blocked"
    if observation["rejections"]:
        assert observation["classification"]["outcome"] == "startup-refused"
        assert observation["control"] is None
        assert observation["attempt"] is None
        assert observation["mutated"] is False
    else:
        assert observation["classification"]["outcome"] == "denied"
        assert observation["controlSucceeded"] is True
        assert observation["attempted"] is True
        assert observation["toolError"] is True
        assert observation["refusalObserved"] is True
        assert observation["mutated"] is False


def test_policy_snapshot_detects_equal_byte_symlink_retargeting(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text('{"enabled":true}')
    second.write_bytes(first.read_bytes())
    target = tmp_path / "policy.json"
    target.symlink_to(first)
    script = f'''
    import {{ snapshotPolicies, observePolicy }} from {json.dumps(POLICY.as_uri())};
    import {{ unlinkSync, symlinkSync }} from "node:fs";
    const paths = {{policy: {json.dumps(str(target))}}};
    const before = snapshotPolicies(paths);
    unlinkSync(paths.policy);
    symlinkSync({json.dumps(str(second))}, paths.policy);
    process.stdout.write(JSON.stringify(observePolicy({{rejections: [], exercise: null}}, {{paths, before, candidate: "changed"}})));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    observation = json.loads(done.stdout)
    assert observation["before"]["policy"]["bytes"] == observation["after"]["policy"]["bytes"]
    assert observation["classification"] == {"outcome": "mutated", "containmentGate": "blocked"}


def test_probe_resolves_installed_sdk_and_keeps_explicit_model(probe):
    result = probe()
    assert Path(result["sdkPath"]).is_file()
    assert result["model"] == MODEL
    assert result["providerPath"] == {
        "provider": MODEL["provider"],
        "api": "anthropic-messages",
        "registeredConfig": False,
        "registeredNative": False,
        "classification": {
            "outcome": "pi-core-provider",
            "providerPathGate": "eligible",
            "containmentGate": "blocked",
        },
    }
    assert result["loadErrors"] == []
    assert result["startupErrors"] == []
    assert result["extensions"] == []
    assert set(result["tools"]) == {"read", "bash", "write", "edit"}
    assert result["modelFallbackMessage"] is None


def test_probe_rejects_cursor_sdk_api_under_another_provider_id_before_session(probe, tmp_path):
    extension = tmp_path / "provider-alias.ts"
    session_started = tmp_path / "session-started.txt"
    extension.write_text(
        'import { writeFileSync } from "node:fs";'
        'export default pi => {'
        'pi.registerProvider("anthropic", {'
        'api: "cursor-sdk",'
        'streamSimple: () => { throw new Error("provider stream must not run"); },'
        'models: [{'
        'id: "host-alias", name: "Host alias", api: "cursor-sdk", reasoning: false, input: ["text"],'
        'cost: {input: 0, output: 0, cacheRead: 0, cacheWrite: 0}, contextWindow: 1024, maxTokens: 128'
        '}]});'
        f'pi.on("session_start", () => writeFileSync({json.dumps(str(session_started))}, "started"));'
        '};'
    )
    result = probe(
        [extension],
        calls=[{"name": "bash", "input": {"command": "printf must-not-run"}}],
        model={"provider": "anthropic", "id": "host-alias"},
        exercise=True,
    )
    assert result["providerPath"]["classification"] == {
        "outcome": "known-host-tools", "providerPathGate": "blocked", "containmentGate": "blocked",
    }
    assert any("provider-owned host tools" in rejection for rejection in result["rejections"])
    assert result["calls"] == []
    assert result["exercise"] is None
    assert not session_started.exists()


def test_probe_rejects_config_registered_provider_as_unverified_before_session(probe, tmp_path):
    extension = tmp_path / "custom-provider.ts"
    session_started = tmp_path / "session-started.txt"
    extension.write_text(
        'import { writeFileSync } from "node:fs";'
        'export default pi => {'
        'pi.registerProvider("anthropic", {'
        'api: "anthropic-messages",'
        'streamSimple: () => { throw new Error("provider stream must not run"); }'
        '});'
        f'pi.on("session_start", () => writeFileSync({json.dumps(str(session_started))}, "started"));'
        '};'
    )
    result = probe(
        [extension],
        calls=[{"name": "bash", "input": {"command": "printf must-not-run"}}],
        exercise=True,
    )
    assert result["providerPath"]["classification"] == {
        "outcome": "extension-config-unverified", "providerPathGate": "blocked", "containmentGate": "blocked",
    }
    assert any("extension-registered provider" in rejection for rejection in result["rejections"])
    assert result["calls"] == []
    assert result["exercise"] is None
    assert not session_started.exists()


def test_installed_cursor_provider_is_rejected_offline_before_session(probe, monkeypatch):
    installed_agent = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent"))
    extension = installed_agent / "npm" / "node_modules" / "pi-cursor-sdk" / "dist" / "index.js"
    if not extension.is_file():
        pytest.skip("the installed pi-cursor-sdk extension is required for the provider-path diagnostic")
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    result = probe(
        [extension],
        calls=[{"name": "bash", "input": {"command": "printf must-not-run"}}],
        model={"provider": "cursor", "id": "auto-smart"},
        exercise=True,
    )
    assert result["extensions"] == [str(extension)]
    assert result["providerPath"] == {
        "provider": "cursor",
        "api": "cursor-sdk",
        "registeredConfig": True,
        "registeredNative": False,
        "classification": {
            "outcome": "known-host-tools",
            "providerPathGate": "blocked",
            "containmentGate": "blocked",
        },
    }
    assert any("provider-owned host tools" in rejection for rejection in result["rejections"])
    assert result["startupErrors"] == []
    assert result["calls"] == []
    assert result["exercise"] is None


def test_probe_reports_missing_extensions(probe, tmp_path):
    missing = tmp_path / "missing.ts"
    result = probe([missing])
    assert result["loadErrors"]
    assert result["loadErrors"][0]["path"] == str(missing)
    assert result["calls"] == []


def test_probe_does_not_discover_unlisted_extensions(probe, tmp_path):
    folder = tmp_path / "agent" / "extensions"
    folder.mkdir()
    (folder / "unapproved.ts").write_text('throw new Error("unapproved extension loaded");')
    assert probe()["extensions"] == []


def test_probe_rejects_missing_model_instead_of_falling_back(probe):
    result = probe(model={"provider": MODEL["provider"], "id": "not-a-model"})
    assert result["model"] is None
    assert result["modelError"] == "Selected model not found: anthropic/not-a-model"
    assert result["calls"] == []


@pytest.mark.parametrize("failure", [False, True])
def test_probe_observes_blocking_tool_hooks_without_executing_tools(probe, tmp_path, failure):
    extension = tmp_path / "guard.ts"
    action = 'throw new Error("probe denied")' if failure else 'return {block: true, reason: "probe denied"}'
    extension.write_text(f'export default pi => {{ pi.on("tool_call", () => {{ {action}; }}); }}')
    target = tmp_path / "untouched.txt"
    result = probe([extension], [{"name": "write", "input": {"path": str(target), "content": "probe"}}])
    assert result["calls"][0]["blocked"] is True
    assert "probe denied" in result["calls"][0]["reason"]
    assert not target.exists()


def test_probe_reports_startup_failure_separately_from_successful_loading(probe, tmp_path):
    extension = tmp_path / "broken-start.ts"
    extension.write_text('export default pi => { pi.on("session_start", () => { throw new Error("guard unavailable"); }); }')
    result = probe([extension])
    assert result["loadErrors"] == []
    assert str(extension) in result["extensions"]
    assert any("guard unavailable" in error["error"] for error in result["startupErrors"])


def test_probe_does_not_execute_unblocked_calls(probe, tmp_path):
    target = tmp_path / "untouched.txt"
    result = probe(calls=[{"name": "write", "input": {"path": str(target), "content": "probe"}}])
    assert result["calls"][0]["blocked"] is False
    assert not target.exists()


def test_probe_reports_extension_factory_failure(probe, tmp_path):
    extension = tmp_path / "broken-load.ts"
    extension.write_text('export default () => { throw new Error("failed to load guard"); };')
    result = probe([extension])
    assert result["loadErrors"]
    assert "failed to load guard" in result["loadErrors"][0]["error"]
    assert result["calls"] == []


def test_probe_captures_headless_notifications_without_enabling_ui(probe, tmp_path):
    extension = tmp_path / "notifies.ts"
    extension.write_text(
        'export default pi => { pi.on("session_start", (_event, ctx) => {'
        'if (ctx.hasUI) throw new Error("probe accidentally enabled UI");'
        'ctx.ui.notify("initialization failed", "error");'
        '}); };'
    )
    result = probe([extension])
    assert result["startupErrors"] == []
    assert result["notifications"] == [{"message": "initialization failed", "type": "error"}]


def test_probe_rejects_a_guard_reporting_itself_disabled(probe, tmp_path):
    extension = tmp_path / "disabled-guard.ts"
    marker = tmp_path / "hook-ran.txt"
    extension.write_text(
        'import { writeFileSync } from "node:fs";'
        'export default pi => {'
        'pi.on("session_start", (_event, ctx) => ctx.ui.notify("Sandbox disabled via config", "info"));'
        f'pi.on("tool_call", () => writeFileSync({json.dumps(str(marker))}, "unsafe"));'
        '};'
    )
    result = probe(
        [extension],
        [{"name": "write", "input": {"path": str(tmp_path / "untouched.txt"), "content": "probe"}}],
        exercise=True,
    )
    assert result["rejections"] == ["Sandbox disabled via config"]
    assert result["exercise"] is None
    assert result["calls"] == []
    assert not marker.exists()


def test_headless_extensions_can_format_status_without_enabling_ui(probe, tmp_path):
    extension = tmp_path / "status.ts"
    extension.write_text(
        'export default pi => { pi.on("session_start", (_event, ctx) => {'
        'if (ctx.hasUI) throw new Error("probe accidentally enabled UI");'
        'ctx.ui.setStatus("probe", ctx.ui.theme.fg("accent", "probe"));'
        '}); };'
    )
    result = probe([extension])
    assert result["rejections"] == []
    assert result["startupErrors"] == []


@pytest.mark.parametrize(
    "failure",
    ['throw new Error("guard unavailable")', 'ctx.ui.notify("guard unavailable", "error")'],
)
def test_probe_rejects_failed_startup_before_invoking_tool_hooks(probe, tmp_path, failure):
    extension = tmp_path / "failed-guard.ts"
    marker = tmp_path / "hook-ran.txt"
    extension.write_text(
        'import { writeFileSync } from "node:fs";'
        'export default pi => {'
        f'pi.on("session_start", (_event, ctx) => {{ {failure}; }});'
        f'pi.on("tool_call", () => {{ writeFileSync({json.dumps(str(marker))}, "unsafe"); }});'
        '};'
    )
    result = probe([extension], [{"name": "bash", "input": {"command": "printf probe"}}])
    assert any("guard unavailable" in reason for reason in result["rejections"])
    assert result["calls"] == []
    assert not marker.exists()


def test_probe_rejects_a_model_changed_during_startup(probe, tmp_path):
    extension = tmp_path / "changes-model.ts"
    extension.write_text(
        'export default pi => { pi.on("session_start", (_event, ctx) => {'
        'ctx.model.id = "unapproved-model";'
        '}); };'
    )
    result = probe([extension], [{"name": "bash", "input": {"command": "printf probe"}}])
    assert result["model"]["id"] == "unapproved-model"
    assert any("Selected model changed" in reason for reason in result["rejections"])
    assert result["calls"] == []


@pytest.mark.parametrize("tool", ["write", "bash"])
@pytest.mark.parametrize("denied", [False, True])
def test_agent_executes_allowed_scratch_tools_and_does_not_execute_denied_tools(probe, tmp_path, tool, denied):
    target = tmp_path / "scratch.txt"
    extension = tmp_path / "tool-policy.ts"
    extension.write_text(
        'export default pi => { pi.on("tool_call", () => '
        f'({{block: {str(denied).lower()}, reason: "scratch probe policy"}})); }};'
    )
    arguments = (
        {"path": str(target), "content": "probe"}
        if tool == "write"
        else {"command": "printf probe > scratch.txt"}
    )
    result = probe([extension], [{"name": tool, "input": arguments}], exercise=True)
    assert result["rejections"] == []
    assert result["exercise"]["results"][0]["isError"] is denied
    if denied:
        assert not target.exists()
    else:
        assert target.read_text() == "probe"


def test_failed_startup_never_exercises_scratch_tools(probe, tmp_path):
    extension = tmp_path / "failed-sandbox.ts"
    extension.write_text(
        'export default pi => { pi.on("session_start", (_event, ctx) => '
        'ctx.ui.notify("Sandbox initialization failed", "error")); };'
    )
    target = tmp_path / "scratch.txt"
    result = probe([extension], [{"name": "write", "input": {"path": str(target), "content": "probe"}}], exercise=True)
    assert result["rejections"]
    assert result["exercise"] is None
    assert not target.exists()


def test_tool_exercise_requires_explicit_extensions(probe, tmp_path):
    target = tmp_path / "unprotected.txt"
    result = probe(calls=[{"name": "write", "input": {"path": str(target), "content": "probe"}}], exercise=True)
    assert result["rejections"]
    assert result["exercise"] is None
    assert not target.exists()


def test_probe_rejects_a_required_extension_path_that_loads_nothing(probe, tmp_path):
    empty = tmp_path / "empty-extension"
    empty.mkdir()
    result = probe([empty], exercise=True)
    assert result["rejections"]
    assert result["exercise"] is None


def test_installed_guards_reject_startup_or_protect_scratch_files(probe, tmp_path, record_property):
    installed_agent = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent"))
    packages = installed_agent / "npm" / "node_modules"
    extensions = [
        packages / "pi-sandbox" / "index.ts",
        packages / "@gotgenes" / "pi-permission-system" / "src" / "index.ts",
        PI / "extensions" / "guardrails.ts",
    ]
    if not all(path.is_file() for path in extensions):
        pytest.skip("installed guard packages are required for the compatibility exercise")
    agent = tmp_path / "agent"
    work = tmp_path / "work"
    work.mkdir()
    config = agent / "extensions" / "pi-permission-system" / "config.json"
    config.parent.mkdir(parents=True)
    shutil.copyfile(PI / "permission-system" / "config.json", config)
    (agent / "sandbox.json").write_text(json.dumps({
        "enabled": True,
        "network": {"allowedDomains": [], "deniedDomains": []},
        "filesystem": {
            "allowRead": [str(work)], "denyRead": [],
            "allowWrite": [str(work)], "denyWrite": [str(agent)],
        },
    }))
    protected = agent / "authority.txt"
    protected.write_text("unchanged")
    (work / "scratch-child.mjs").write_text(
        'import { writeFileSync } from "node:fs";'
        'const target = process.argv[2] === "protected" ? "../agent/authority.txt" : "./allowed-child.txt";'
        'writeFileSync(new URL(target, import.meta.url), "probe");'
    )
    calls = [
        {"name": "write", "input": {"path": str(work / "allowed-file.txt"), "content": "probe"}},
        {"name": "write", "input": {"path": str(protected), "content": "forbidden"}},
        {"name": "bash", "input": {"command": "printf probe > allowed-shell.txt"}},
        {"name": "bash", "input": {"command": "printf forbidden > ../agent/authority.txt"}},
        {"name": "bash", "input": {"command": "node scratch-child.mjs allowed"}},
        {"name": "bash", "input": {"command": "node scratch-child.mjs protected"}},
    ]
    result = probe(extensions, calls, exercise=True, cwd=work)
    observation = {"rejections": result["rejections"], "exercise": result["exercise"]}
    record_property("installed_guard_observation", json.dumps(observation))
    print(json.dumps(observation))
    assert protected.read_text() == "unchanged"
    if result["rejections"]:
        assert result["exercise"] is None
        assert not (work / "allowed-file.txt").exists()
        assert not (work / "allowed-shell.txt").exists()
        assert not (work / "allowed-child.txt").exists()
    else:
        results = result["exercise"]["results"]
        assert [entry["isError"] for entry in results] == [False, True, False, True, False, True]
        assert (work / "allowed-file.txt").read_text() == "probe"
        assert (work / "allowed-shell.txt").read_text() == "probe"
        assert (work / "allowed-child.txt").read_text() == "probe"
        child_error = json.dumps(results[-1]["result"])
        assert "EACCES" in child_error or "EPERM" in child_error
        assert "[pi-permission-system]" not in child_error


def test_probe_shuts_down_started_extensions(probe, tmp_path):
    marker = tmp_path / "shutdown.txt"
    extension = tmp_path / "cleanup.ts"
    extension.write_text(
        'import { writeFileSync } from "node:fs";'
        'export default pi => { pi.on("session_shutdown", () => {'
        f'writeFileSync({json.dumps(str(marker))}, "closed");'
        '}); };'
    )
    probe([extension])
    assert marker.read_text() == "closed"


@pytest.mark.parametrize("mode", ["same-group", "detached-group"])
def test_cancellation_observes_bash_descendants_after_ready(probe, tmp_path, mode, record_property):
    guard = tmp_path / "guard.ts"
    guard.write_text('export default pi => { pi.on("tool_call", () => ({block: false})); };')
    result = probe([guard], cancellation=mode)
    assert result["rejections"] == []
    observation = result["exercise"]
    record_property("synthetic_cancellation_observation", json.dumps(observation))
    print(json.dumps(observation))
    assert observation["ready"] is True
    if not observation["groupVerified"]:
        assert observation["processInspectionError"]
        assert observation["classification"]["outcome"] == "group-unverified"
    assert observation["writesAtReady"] > 0
    assert observation["readyAt"] <= observation["abortRequestedAt"] <= observation["abortReturnedAt"]
    assert observation["promptSettled"] is True
    assert observation["abortReturned"] is True
    assert observation["deadlineReachedBeforeCleanup"] is False
    if observation["processInspectionError"]:
        assert observation["aliveAfterCleanup"] is None
        assert observation["launcherAliveAfterCleanup"] is None
    else:
        assert observation["aliveAfterCleanup"] is False
        assert observation["launcherAliveAfterCleanup"] is False
    assert observation["classification"]["containmentGate"] == "blocked"
    assert observation["classification"]["outcome"] in {
        "stopped-before-cleanup", "survived-abort", "writes-after-abort", "group-unverified",
    }
    assert observation["cleanupRequestedAt"] >= observation["observationEndedAt"]


def test_cancellation_never_aborts_before_child_readiness(probe, tmp_path):
    guard = tmp_path / "denied.ts"
    guard.write_text('export default pi => { pi.on("tool_call", () => ({block: true, reason: "denied"})); };')
    result = probe([guard], cancellation="same-group")
    observation = result["exercise"]
    assert observation["ready"] is False
    assert observation["abortRequestedAt"] is None
    assert observation["classification"] == {"outcome": "not-exercised", "containmentGate": "blocked"}
    assert observation["results"][0]["isError"] is True


@pytest.mark.parametrize("mode", ["same-group", "detached-group"])
def test_installed_guards_report_cancellation_or_startup_refusal(probe, tmp_path, mode, record_property):
    installed_agent = Path(os.environ.get("PI_CODING_AGENT_DIR", Path.home() / ".pi" / "agent"))
    packages = installed_agent / "npm" / "node_modules"
    extensions = [
        packages / "pi-sandbox" / "index.ts",
        packages / "@gotgenes" / "pi-permission-system" / "src" / "index.ts",
        PI / "extensions" / "guardrails.ts",
    ]
    if not all(path.is_file() for path in extensions):
        pytest.skip("installed guard packages are required for the cancellation exercise")
    agent = tmp_path / "agent"
    work = tmp_path / "work"
    work.mkdir()
    config = agent / "extensions" / "pi-permission-system" / "config.json"
    config.parent.mkdir(parents=True)
    shutil.copyfile(PI / "permission-system" / "config.json", config)
    (agent / "sandbox.json").write_text(json.dumps({
        "enabled": True,
        "network": {"allowedDomains": [], "deniedDomains": []},
        "filesystem": {
            "allowRead": [str(work)], "denyRead": [],
            "allowWrite": [str(work)], "denyWrite": [str(agent)],
        },
    }))
    result = probe(extensions, cwd=work, cancellation=mode)
    observation = {
        "mode": mode,
        "outcome": "startup-refused" if result["rejections"] else "cancellation-exercised",
        "rejections": result["rejections"], "exercise": result["exercise"],
        "containmentGate": "blocked",
    }
    record_property("installed_cancellation_observation", json.dumps(observation))
    print(json.dumps(observation))
    if result["rejections"]:
        assert result["exercise"] is None
        assert not list(work.iterdir())
    else:
        exercised = result["exercise"]
        assert exercised["classification"]["containmentGate"] == "blocked"
        if exercised["processInspectionError"]:
            assert exercised["aliveAfterCleanup"] is None
            assert exercised["launcherAliveAfterCleanup"] is None
        else:
            assert exercised["aliveAfterCleanup"] is False
            assert exercised["launcherAliveAfterCleanup"] is False
        if exercised["ready"]:
            assert exercised["readyAt"] <= exercised["abortRequestedAt"]
        else:
            assert exercised["abortRequestedAt"] is None
            assert exercised["classification"]["outcome"] == "not-exercised"


@pytest.mark.parametrize("mode", ["same-group", "detached-group"])
def test_cancellation_children_have_independent_deadlines_without_abort_or_cleanup(tmp_path, mode):
    child = CANCELLATION.with_name("minion-cancellation-child.mjs")
    shutil.copyfile(child, tmp_path / child.name)
    directory = tmp_path / mode
    directory.mkdir()
    lifetime_ms = 1000
    poll_ms = 25
    script = f'''
    import {{ spawn }} from "node:child_process";
    const child = spawn(process.execPath, [{json.dumps(str(tmp_path / child.name))}, "launcher", {json.dumps(mode)}, String(Date.now() + {lifetime_ms}), "{poll_ms}"], {{stdio: "ignore"}});
    child.on("exit", code => process.exit(code));
    '''
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=5)
    assert done.returncode == 0, done.stderr
    for role in ["launcher", "writer"]:
        record = directory / f"{role}.exit.json"
        # The writer's independent deadline may fire just after the launcher exits.
        end = time.monotonic() + 1
        while not record.exists() and time.monotonic() < end:
            time.sleep(0.01)
        exited = json.loads(record.read_text())
        ready = json.loads((directory / f"{role}.ready.json").read_text())
        assert exited["reason"] == "deadline"
        assert exited["pid"] == ready["pid"]
        assert ready["at"] < ready["deadline"] <= exited["at"]
    assert not (directory / "cleanup").exists()


