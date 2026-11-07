"""`cloud-readonly-gate.sh` tells Claude when an exempt CLI will still run sandboxed.

`sandbox.excludedCommands` lets a call out only when every command in it is
excluded and it has none of the confining shapes (a file redirect, a substitution,
`cd`, `sudo`, `eval`, `xargs`, a subshell). An env prefix and a `2>&1` do not
confine. The hint is context, never a decision, so cases assert on whether
`additionalContext` is present and never on its wording.

CLAUDE_CONFIG_DIR points the hook at a settings file in tmp_path, so the
exclusions under test never depend on the live ~/.claude.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "cloud-readonly-gate.sh"

CLAUDE_TRANSCRIPT = "/Users/someone/.claude/projects/repo/session.jsonl"


@pytest.fixture
def gate(tmp_path):
    """gate(command, transcript=...) -> the hookSpecificOutput it printed, or None."""
    (tmp_path / "settings.json").write_text(json.dumps({
        "sandbox": {"excludedCommands": [
            "git *", "acli *", "bq *", "bunx ctx7 *",
            "python3 ~/.claude/skills/commit/scripts/apply.py *",
        ]},
    }))

    def run(command, transcript=CLAUDE_TRANSCRIPT, cwd=None):
        payload = {"tool_name": "Bash", "tool_input": {"command": command}}
        if transcript:
            payload["transcript_path"] = transcript
        if cwd:
            payload["cwd"] = str(cwd)
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload), capture_output=True, text=True,
            env={"CLAUDE_CONFIG_DIR": str(tmp_path), "PATH": "/usr/bin:/bin"},
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)["hookSpecificOutput"] if result.stdout.strip() else None

    return run


@pytest.mark.parametrize("command", [
    "acli jira workitem view X-1 | head",
    "npm ci && git status",
    "cd repo && git status",
    "bunx ctx7 docs /x 'q' > out.txt",
    "git status $(echo x)",
    "xargs git rm",
    "sudo git status",
])
def test_an_exempt_cli_that_still_runs_sandboxed_gets_the_hint(gate, command):
    output = gate(command)
    assert output and output.get("additionalContext")


@pytest.mark.parametrize("command", [
    "git status",
    "acli jira workitem view X-1",
    "git commit -m 'a | b; c'",
    "echo hi | grep h",
    "git add x && git commit -m y",
    "FOO=1 acli jira workitem view X-1",
    "python3 ~/.claude/skills/commit/scripts/apply.py plan.json 2>&1",
])
def test_a_call_that_leaves_the_sandbox_or_never_names_an_exempt_cli_gets_nothing(gate, command):
    assert gate(command) is None


def test_no_hint_where_the_project_turns_the_sandbox_off(gate, tmp_path):
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    (project / ".claude" / "settings.local.json").write_text(json.dumps({"sandbox": {"enabled": False}}))
    (project / "sub").mkdir()

    assert gate("acli jira workitem view X-1 | head", cwd=project / "sub") is None
    assert gate("acli jira workitem view X-1 | head", cwd=tmp_path)


def test_the_hint_rides_along_with_an_ask_rather_than_replacing_it(gate):
    output = gate("bq query 'select 1' | jq .")
    assert output["permissionDecision"] == "ask"
    assert output.get("additionalContext")


def test_other_harnesses_never_receive_the_hint(gate):
    assert gate("acli jira workitem view X-1 | head", transcript=None) is None
