"""`plan-date-stamp.sh` prefixes an approved plan file with the date.

The hook reads a PostToolUse event on stdin and always exits 0, since a failed
rename must never cost the user an approved plan. So cases assert on the
filesystem and on the emitted JSON, never on the exit code.

The plan path is faked by writing a transcript carrying the `plan_mode`
attachment Claude Code injects when plan mode starts, which is the same signal
the hook reads in a real session.
"""

import json
import subprocess
import sys

from datetime import date
from pathlib import Path

import pytest

# Beside the subject it exercises, so it is located relatively: move the hook and
# these travel with it. dotkit.testing is for facts about the repo, not this.
HOOK = Path(__file__).resolve().parents[1] / "plan-date-stamp.sh"

SLUG = "right-now-we-save-glimmering-sun.md"
TODAY = date.today().isoformat()


@pytest.fixture
def plans(tmp_path):
    """A plans directory, as a repo's docs/plans/ would be."""
    directory = tmp_path / "docs" / "plans"
    directory.mkdir(parents=True)
    return directory


@pytest.fixture
def stamp(tmp_path):
    """Run the hook. stamp(plan_path) -> the JSON it printed, or None."""
    transcript = tmp_path / "transcript.jsonl"

    def run(plan_path=None, is_subagent=False, events=None, with_transcript=True):
        if events is None:
            events = []
            if plan_path is not None:
                events.append({
                    "type": "attachment",
                    "attachment": {
                        "type": "plan_mode",
                        "reminderType": "full",
                        "isSubAgent": is_subagent,
                        "planFilePath": str(plan_path),
                        "planExists": True,
                    },
                })
        transcript.write_text(
            "".join(
                (e if isinstance(e, str) else json.dumps(e)) + "\n" for e in events
            )
        )
        event = {
            "tool_name": "ExitPlanMode",
            "tool_input": {},
            "transcript_path": str(transcript) if with_transcript else "",
            "cwd": str(tmp_path),
        }
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout) if result.stdout.strip() else None

    return run


def test_an_approved_plan_gains_todays_date(stamp, plans):
    """Given an undated plan file, When the plan is approved, Then it is date-prefixed."""
    plan = plans / SLUG
    plan.write_text("# A plan\n")

    output = stamp(plan)

    assert not plan.exists()
    assert (plans / f"{TODAY}-{SLUG}").read_text() == "# A plan\n"
    assert output["suppressOutput"] is True
    assert f"{TODAY}-{SLUG}" in output["systemMessage"]


def test_an_already_dated_plan_is_left_alone(stamp, plans):
    """Given a plan already carrying a date, When it is approved again, Then nothing changes.

    Re-approving a revised plan must not stack a second date onto the name.
    """
    plan = plans / f"{TODAY}-{SLUG}"
    plan.write_text("# A plan\n")

    assert stamp(plan) is None
    assert [p.name for p in plans.iterdir()] == [f"{TODAY}-{SLUG}"]


def test_a_date_from_another_day_is_still_left_alone(stamp, plans):
    """Given a plan dated on an earlier day, When it is approved, Then it keeps that date.

    The plan records when it was written, so a re-approval does not restamp it.
    """
    plan = plans / f"2026-01-02-{SLUG}"
    plan.write_text("# A plan\n")

    assert stamp(plan) is None
    assert plan.exists()


def test_a_subagent_plan_is_never_renamed(stamp, plans):
    """Given isSubAgent, When the plan is approved, Then it is untouched.

    A subagent's plan is its own scratch file, not the user-facing deliverable.
    """
    plan = plans / "right-now-we-save-glimmering-sun-agent-a9ce7cf2680acefd6.md"
    plan.write_text("# A subagent plan\n")

    assert stamp(plan, is_subagent=True) is None
    assert plan.exists()


def test_the_last_plan_attachment_wins(stamp, plans):
    """Given plan mode was re-entered, When the plan is approved, Then the latest file is renamed.

    Each entry into plan mode injects its own attachment, so the newest names
    the file this approval is finalizing.
    """
    stale = plans / "an-earlier-plan.md"
    stale.write_text("# Stale\n")
    current = plans / SLUG
    current.write_text("# Current\n")

    def attachment(path):
        return {
            "type": "attachment",
            "attachment": {
                "type": "plan_mode",
                "isSubAgent": False,
                "planFilePath": str(path),
            },
        }

    stamp(events=[attachment(stale), attachment(current)])

    assert stale.exists()
    assert (plans / f"{TODAY}-{SLUG}").exists()


def test_a_transcript_with_no_plan_attachment_is_a_no_op(stamp, plans):
    """Given a transcript that never entered plan mode, When the hook runs, Then nothing happens."""
    plan = plans / SLUG
    plan.write_text("# A plan\n")

    assert stamp(events=[{"type": "assistant", "message": {"content": []}}]) is None
    assert plan.exists()


def test_a_plan_missing_from_disk_is_a_no_op(stamp, plans):
    """Given the recorded plan file does not exist, When the hook runs, Then it reports nothing."""
    assert stamp(plans / SLUG) is None


def test_an_existing_destination_is_never_clobbered(stamp, plans):
    """Given today's name is already taken, When the plan is approved, Then neither file is lost."""
    plan = plans / SLUG
    plan.write_text("# The new plan\n")
    occupied = plans / f"{TODAY}-{SLUG}"
    occupied.write_text("# The earlier plan\n")

    assert stamp(plan) is None
    assert plan.read_text() == "# The new plan\n"
    assert occupied.read_text() == "# The earlier plan\n"


def test_a_malformed_transcript_fails_open(stamp, plans):
    """Given unparseable lines, When the hook runs, Then the valid attachment is still used.

    A truncated write mid-transcript must not cost the rename.
    """
    plan = plans / SLUG
    plan.write_text("# A plan\n")
    events = [
        "{not json at all",
        {
            "type": "attachment",
            "attachment": {
                "type": "plan_mode",
                "isSubAgent": False,
                "planFilePath": str(plan),
            },
        },
    ]

    assert stamp(events=events) is not None
    assert (plans / f"{TODAY}-{SLUG}").exists()


def test_a_missing_transcript_fails_open(stamp, plans):
    """Given no transcript to read, When the hook runs, Then it exits quietly.

    Harness replay and compaction can both leave the transcript unreadable, and
    a missing date is worth less than a crash on an approved plan.
    """
    plan = plans / SLUG
    plan.write_text("# A plan\n")

    assert stamp(plan, with_transcript=False) is None
    assert plan.exists()
