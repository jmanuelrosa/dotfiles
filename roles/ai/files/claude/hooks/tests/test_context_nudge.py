"""`context-nudge.sh` warns once per band when the context window fills up.

The hook reads a UserPromptSubmit event on stdin and always exits 0, since an
advisory must never cost the user a prompt. So cases assert on the emitted JSON
and never on the exit code, and never on the wording, so the messages can be
reworded freely.

The percentage is faked by writing the state file statusline.sh publishes,
which is the same signal the hook reads in a real session. TMPDIR redirects
`tempfile.gettempdir()` into tmp_path so a test run never touches the real
state of a live session.
"""

import json
import subprocess
import sys

from pathlib import Path

import pytest

# Beside the subject it exercises, so it is located relatively: move the hook and
# these travel with it. dotkit.testing is for facts about the repo, not this.
HOOK = Path(__file__).resolve().parents[1] / "context-nudge.sh"

SESSION = "96371f64-022a-4060-83c1-441aa230c0dd"


@pytest.fixture
def nudge(tmp_path):
    """Run the hook. nudge(pct) -> the JSON it printed, or None."""

    def publish(pct, session=SESSION):
        (tmp_path / f"claude-context-{session}.json").write_text(json.dumps({"pct": pct}))

    def run(session=SESSION, payload=None, raw=None):
        if raw is None:
            raw = json.dumps(payload if payload is not None else {
                "hook_event_name": "UserPromptSubmit",
                "session_id": session,
            })
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=raw,
            capture_output=True,
            text=True,
            env={"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"},
        )
        assert result.returncode == 0, result.stderr
        out = result.stdout.strip()
        return json.loads(out) if out else None

    run.publish = publish
    return run


def test_silent_below_threshold(nudge):
    nudge.publish(34)
    assert nudge() is None


def test_warns_user_and_model_on_first_crossing(nudge):
    nudge.publish(37)
    out = nudge()
    assert "systemMessage" in out
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert out["hookSpecificOutput"]["additionalContext"]


def test_repeat_in_same_band_costs_the_model_nothing(nudge):
    nudge.publish(37)
    nudge()
    nudge.publish(39)
    out = nudge()
    assert "systemMessage" in out
    assert "hookSpecificOutput" not in out


def test_new_band_pays_the_model_again(nudge):
    nudge.publish(37)
    nudge()
    nudge.publish(41)
    out = nudge()
    assert "hookSpecificOutput" in out


def test_dropping_below_threshold_rearms_the_band(nudge):
    nudge.publish(37)
    nudge()
    nudge.publish(20)
    assert nudge() is None
    nudge.publish(37)
    assert "hookSpecificOutput" in nudge()


def test_silent_when_status_line_has_not_run(nudge):
    assert nudge() is None


def test_silent_when_percentage_is_null(nudge):
    nudge.publish(None)
    assert nudge() is None


@pytest.mark.parametrize("raw", ["", "not json", "[]", "null"])
def test_fails_open_on_malformed_stdin(nudge, raw):
    nudge.publish(90)
    assert nudge(raw=raw) is None


def test_silent_without_a_session_id(nudge):
    nudge.publish(90)
    assert nudge(payload={"hook_event_name": "UserPromptSubmit"}) is None


@pytest.mark.parametrize("session", ["../escape", "a/b", "with space", "semi;colon"])
def test_rejects_a_session_id_that_is_not_a_bare_identifier(nudge, session):
    nudge.publish(90)
    assert nudge(session=session) is None
