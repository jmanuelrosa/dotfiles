"""`git-skill-gate.sh` lets /ship's apply.py run only after a confirmation.

/ship is model-invocable, and Claude Code stamps no `attributionSkill` on the
turns of a model-invoked skill, nor on any turn after a prose reply. So these
transcripts carry the real event shapes: the `/ship` command message, the Skill
tool call, the AskUserQuestion round-trip, and typed messages.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "git-skill-gate.sh"

ALLOW = 0
BLOCK = 2

SHIP = "python3 ~/.claude/skills/ship/scripts/apply.py /tmp/claude/ship-plan.json"
QUESTION_ID = "toolu_ask"


def typed(text):
    return {"type": "user", "origin": {"kind": "human"}, "message": {"role": "user", "content": text}}


def slash_ship():
    return typed("<command-message>ship</command-message>\n<command-name>/ship</command-name>")


def skill_tool(skill="ship"):
    return {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "id": "toolu_skill", "name": "Skill", "input": {"skill": skill}}]},
    }


def skill_body():
    return {"type": "user", "isMeta": True, "message": {"content": [{"type": "text", "text": "Base directory for this skill: ship"}]}}


def asked():
    return {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "id": QUESTION_ID, "name": "AskUserQuestion", "input": {}}]},
    }


def answered(is_error=False):
    return {
        "type": "user",
        "message": {"content": [{"type": "tool_result", "tool_use_id": QUESTION_ID, "content": "Go", "is_error": is_error}]},
    }


def notification():
    return {
        "type": "user",
        "origin": {"kind": "task-notification"},
        "message": {"content": "<task-notification>done</task-notification>"},
    }


def assistant_turn():
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": "working"}]}}


@pytest.fixture
def gate(tmp_path):
    transcript = tmp_path / "transcript.jsonl"

    def run(events, command=SHIP):
        transcript.write_text("".join(json.dumps(event) + "\n" for event in events))
        event = {"tool_input": {"command": command}, "transcript_path": str(transcript), "cwd": str(tmp_path)}
        return subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True, text=True, cwd=tmp_path
        ).returncode

    return run


def test_ship_outside_any_skill_is_blocked(gate):
    """Given no /ship invocation, When ship's apply.py runs, Then it is blocked."""
    assert gate([typed("please ship it"), assistant_turn()]) == BLOCK


def test_a_model_invoked_ship_without_an_answer_is_blocked(gate):
    """Given a model loaded /ship and asked nothing, When apply.py runs, Then it is blocked.

    The confirmation is the whole contract of a model-invoked /ship.
    """
    assert gate([typed("done?"), skill_tool(), skill_body(), assistant_turn()]) == BLOCK


def test_a_model_invoked_ship_after_an_answered_question_is_allowed(gate):
    """Given a model loaded /ship and the user answered its gate, When apply.py runs, Then it is allowed."""
    assert gate([skill_tool(), skill_body(), asked(), answered(), assistant_turn()]) == ALLOW


def test_a_prose_go_after_a_model_invoked_ship_is_allowed(gate):
    """Given the user answered the gate in prose, When apply.py runs, Then it is allowed.

    A prose reply drops `attributionSkill`, which is what made /commit and /pr
    refuse a typed "go".
    """
    assert gate([skill_tool(), skill_body(), asked(), typed("go"), assistant_turn()]) == ALLOW


def test_a_typed_ship_answered_in_prose_is_allowed(gate):
    """Given the user typed /ship and answered in prose, When apply.py runs, Then it is allowed."""
    assert gate([slash_ship(), skill_body(), asked(), typed("continue"), assistant_turn()]) == ALLOW


def test_a_dismissed_question_is_not_a_confirmation(gate):
    """Given the gate question was rejected, When apply.py runs, Then it is blocked."""
    assert gate([skill_tool(), skill_body(), asked(), answered(is_error=True)]) == BLOCK


def test_a_task_notification_is_not_a_confirmation(gate):
    """Given only an automated notification followed /ship, When apply.py runs, Then it is blocked."""
    assert gate([skill_tool(), skill_body(), notification(), assistant_turn()]) == BLOCK


def test_an_answer_before_the_latest_invocation_does_not_count(gate):
    """Given /ship was invoked again after an earlier answer, When apply.py runs, Then it is blocked.

    Each run asks its own question.
    """
    events = [skill_tool(), asked(), answered(), skill_tool(), skill_body(), assistant_turn()]
    assert gate(events) == BLOCK


def test_another_skill_invocation_does_not_open_ship(gate):
    """Given a different skill was invoked and answered, When apply.py runs, Then it is blocked."""
    assert gate([skill_tool("commit"), asked(), typed("go")]) == BLOCK


def test_an_attributed_ship_turn_is_allowed(gate):
    """Given the classic attribution stamp (a typed /ship, or pi's synthetic transcript), Then it is allowed."""
    assert gate([{"attributionSkill": "ship"}]) == ALLOW


def test_a_confirmed_ship_allows_the_sandbox_fallback_push(gate):
    """Given a confirmed /ship, When the standalone push apply.py printed runs, Then it is allowed."""
    events = [skill_tool(), skill_body(), asked(), answered()]
    assert gate(events, command="git push -u origin fix/x") == ALLOW


def test_a_confirmed_ship_does_not_buy_a_raw_commit(gate):
    """Given a confirmed /ship, When a raw git commit runs, Then it is blocked: ship commits through apply.py."""
    events = [skill_tool(), skill_body(), asked(), answered()]
    assert gate(events, command="git commit -m 'fix: x'") == BLOCK


def test_ship_does_not_authorize_the_pr_wrapper(gate):
    """Given a confirmed /ship, When pr's apply.py runs, Then it is blocked."""
    events = [skill_tool(), skill_body(), asked(), answered()]
    assert gate(events, command="python3 ~/.claude/skills/pr/scripts/apply.py plan.json") == BLOCK


def test_ship_wrapper_still_refuses_a_destructive_push_shape(gate):
    """Given a confirmed /ship, When a force push runs, Then the hard block still applies."""
    events = [skill_tool(), skill_body(), asked(), answered()]
    assert gate(events, command="git push --force origin fix/x") == BLOCK
