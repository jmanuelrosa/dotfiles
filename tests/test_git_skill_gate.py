"""`git-skill-gate.sh` gates commit and push behind the skills that own them.

The hook reads a PreToolUse event on stdin and signals with its exit code: 0
allows the command, 2 blocks it. Cases assert on that code alone, never on the
refusal text, so the messages can be reworded freely.

Skill attribution is faked by writing a transcript of `attributionSkill` events,
which is the same signal Claude Code stamps on an assistant turn inside a
slash-command flow.
"""

import json
import subprocess
import sys

import pytest

from dotkit.testing import HOOKS

HOOK = HOOKS / "git-skill-gate.sh"

ALLOW = 0
BLOCK = 2

COMMIT_WRAPPER = "~/.claude/skills/commit/scripts/apply.py"
PR_WRAPPER = "~/.claude/skills/pr/scripts/apply.py"

# Built from a codepoint so this file carries no literal dash of its own.
EM_DASH = chr(0x2014)


@pytest.fixture
def gate(tmp_path):
    """Run the hook. gate("git push", skills=["pr"]) -> exit code."""
    transcript = tmp_path / "transcript.jsonl"

    def run(command, skills=(), cwd=None, with_transcript=True):
        transcript.write_text(
            "".join(json.dumps({"attributionSkill": s}) + "\n" for s in skills)
        )
        event = {
            "tool_input": {"command": command},
            "transcript_path": str(transcript) if with_transcript else "",
            "cwd": str(cwd or tmp_path),
        }
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(event),
            capture_output=True,
            text=True,
        ).returncode

    return run


def test_no_verify_is_blocked_even_inside_the_owning_skill(gate):
    """Given --no-verify, When anything runs it, Then it is blocked regardless of skill."""
    assert gate("git commit --no-verify -m 'x'", skills=["commit"]) == BLOCK


def test_a_commit_outside_the_commit_skill_is_blocked(gate):
    """Given no skill attribution, When git commit runs, Then it is blocked."""
    assert gate("git commit -m 'feat: a thing'") == BLOCK


def test_a_commit_inside_the_commit_skill_is_allowed(gate):
    """Given /commit is active, When git commit runs, Then it is allowed."""
    assert gate("git commit -m 'feat: a thing'", skills=["commit"]) == ALLOW


def test_a_push_outside_the_pr_skill_is_blocked(gate):
    """Given no skill attribution, When git push runs, Then it is blocked."""
    assert gate("git push -u origin feature/x") == BLOCK


def test_a_push_inside_the_pr_skill_is_allowed(gate):
    """Given /pr is active, When git push runs, Then it is allowed."""
    assert gate("git push -u origin feature/x", skills=["pr"]) == ALLOW


@pytest.mark.parametrize("command", ["gh pr create --fill", "glab mr create --yes"])
def test_opening_a_pull_request_outside_the_pr_skill_is_blocked(gate, command):
    """Given no skill attribution, When a PR/MR is opened, Then it is blocked."""
    assert gate(command) == BLOCK


@pytest.mark.parametrize(
    "command",
    [
        "git -c credential.helper= push -u origin x",
        "VAR=1 git push -u origin x",
        "npm test && git push -u origin x",
    ],
)
def test_a_push_is_still_recognized_through_its_wrapping_forms(gate, command):
    """Given a push wrapped in config flags, env assignment or a chain,
    When it runs outside /pr, Then it is still blocked."""
    assert gate(command) == BLOCK


def test_the_pr_wrapper_script_is_gated_though_it_names_no_git_command(gate):
    """Given pr's apply.py, which pushes in a subprocess, When it runs outside /pr,
    Then it is blocked.

    The hook sees the Bash command, not what it spawns, so without a path-based
    gate this script would be a hole straight through the push gate.
    """
    assert gate(f"python3 {PR_WRAPPER} plan.json") == BLOCK


def test_the_pr_wrapper_script_is_allowed_inside_the_pr_skill(gate):
    """Given /pr is active, When pr's apply.py runs, Then it is allowed."""
    assert gate(f"python3 {PR_WRAPPER} plan.json", skills=["pr"]) == ALLOW


def test_the_pr_wrapper_script_is_gated_when_run_without_an_interpreter(gate):
    """Given pr's apply.py invoked directly, When it runs outside /pr, Then it is blocked."""
    assert gate(f"{PR_WRAPPER} plan.json") == BLOCK


@pytest.mark.parametrize(
    "wrapper,wrong_skill",
    [(PR_WRAPPER, "commit"), (COMMIT_WRAPPER, "pr")],
)
def test_one_skill_does_not_authorize_the_other_skills_wrapper(gate, wrapper, wrong_skill):
    """Given the wrong owning skill is active, When a wrapper script runs, Then it is blocked.

    /commit must not buy a push, and /pr must not buy a commit.
    """
    assert gate(f"python3 {wrapper} plan.json", skills=[wrong_skill]) == BLOCK


def test_the_commit_wrapper_script_is_allowed_inside_the_commit_skill(gate):
    """Given /commit is active, When commit's apply.py runs, Then it is allowed."""
    assert gate(f"python3 {COMMIT_WRAPPER} plan.json", skills=["commit"]) == ALLOW


@pytest.mark.parametrize("wrapper", [PR_WRAPPER, COMMIT_WRAPPER])
def test_reading_a_wrapper_script_is_not_running_it(gate, wrapper):
    """Given a wrapper script named as an argument rather than executed,
    When the command runs, Then it is allowed.

    Only execution positions count, so inspecting these files stays possible
    without the owning skill.
    """
    assert gate(f"wc -c {wrapper}") == ALLOW


def test_s_task_is_deliberately_not_gated(gate):
    """Given s-task, which pushes a fresh branch, When it runs, Then it is allowed.

    It pushes only an empty branch it just created, so it cannot push work, and
    it runs at the start of a task where requiring /pr would be backwards.
    """
    assert gate("s-task PROJ-123") == ALLOW


def test_an_unrelated_git_command_is_never_gated(gate):
    """Given a read-only git command, When it runs with no skill, Then it is allowed."""
    assert gate("git status --porcelain") == ALLOW


def test_a_missing_transcript_fails_open(gate):
    """Given no transcript to read, When a gated command runs, Then it is allowed.

    Harness replay and compaction can both leave the transcript unreadable, and
    locking the user out of committing is worse than missing one gate check.
    """
    assert gate("git push -u origin x", with_transcript=False) == ALLOW


def test_an_attribution_line_in_a_commit_message_is_blocked(gate):
    """Given a Co-Authored-By Claude line, When committing inside /commit, Then it is blocked.

    This one is unconditional: the owning skill does not license it, because
    attribution is handled by the attribution setting in settings.json.
    """
    message = "feat: a thing\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
    assert gate(f"git commit -m {message!r}", skills=["commit"]) == BLOCK


def test_a_typographic_dash_in_a_commit_message_is_blocked(gate):
    """Given an em dash in the message, When committing inside /commit, Then it is blocked."""
    message = f"feat: add a thing {EM_DASH} and another"
    assert gate(f"git commit -m {message!r}", skills=["commit"]) == BLOCK
