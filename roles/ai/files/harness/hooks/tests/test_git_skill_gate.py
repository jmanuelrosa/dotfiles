"""`git-skill-gate.sh` gates commit and push behind the skills that own them.

The hook reads a PreToolUse event on stdin and signals with its exit code: 0
allows the command, 2 blocks it. Cases assert on that code alone, never on the
refusal text, so the messages can be reworded freely.

Skill attribution is faked by writing a transcript of `attributionSkill` events,
which is the same signal Claude Code stamps on an assistant turn inside a
slash-command flow.
"""

import json
import os
import subprocess
import sys

from pathlib import Path

import pytest

# Beside the subject it exercises, so it is located relatively: move the skill and
# these travel with it. dotkit.testing is for facts about the repo, not this.
HOOK = Path(__file__).resolve().parents[1] / "git-skill-gate.sh"

ALLOW = 0
BLOCK = 2

COMMIT_WRAPPER = "~/.claude/skills/commit/scripts/apply.py"
PR_WRAPPER = "~/.claude/skills/pr/scripts/apply.py"

# Built from a codepoint so this file carries no literal dash of its own.
EM_DASH = chr(0x2014)


# The risky shapes roles/apps/files/.gitconfig ships, copied rather than read so
# a case means the same thing however that file changes.
SHIPPED_ALIASES = {
    "a": "commit --amend --no-edit",
    "c": "commit",
    "ca": "!git add --all && git commit -am",
    "wip": "!git add --all; git c -m WIP",
    "p": "push",
    "up": "push",
    "pf": "push --force-with-lease",
    "apf": "!git amend --no-verify --no-edit && git push --force",
    "res": "reset --hard HEAD",
    "rh": "reset --hard HEAD",
    "st": "status",
    "dw": '!git -c color.diff=always diff --word-diff=color "$@" | less -RFX #',
}

# Shapes git allows that the shipped file does not use yet.
OTHER_ALIASES = {
    "cm": "commit -m",
    "pp": "p",
    "fp": '!f() { git push "$@"; }; f',
    "loop": "loop",
    "status": "push",
}


@pytest.fixture
def git_env(tmp_path):
    """An environment where git reads a throwaway global config holding the
    aliases above, never the real one, so the user's own aliases cannot change
    what a case means."""
    gitconfig = tmp_path / "gitconfig"
    aliases = {**SHIPPED_ALIASES, **OTHER_ALIASES}
    gitconfig.write_text(
        "[alias]\n" + "".join(f"\t{name} = {json.dumps(body)}\n" for name, body in aliases.items())
    )
    return {**os.environ, "GIT_CONFIG_GLOBAL": str(gitconfig), "GIT_CONFIG_NOSYSTEM": "1"}


@pytest.fixture
def gate(tmp_path, git_env):
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
            env=git_env,
            cwd=tmp_path,
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


def test_the_commit_skill_does_not_authorize_the_pr_wrapper(gate):
    """Given /commit is active, When pr's apply.py runs, Then it is blocked.

    /commit must not buy a push.
    """
    assert gate(f"python3 {PR_WRAPPER} plan.json", skills=["commit"]) == BLOCK


def test_the_commit_wrapper_script_is_allowed_inside_the_commit_skill(gate):
    """Given /commit is active, When commit's apply.py runs, Then it is allowed."""
    assert gate(f"python3 {COMMIT_WRAPPER} plan.json", skills=["commit"]) == ALLOW


def test_the_commit_wrapper_script_is_allowed_inside_the_pr_skill(gate):
    """Given /pr is active, When commit's apply.py runs, Then it is allowed.

    When /commit and /pr are invoked back to back, the turns that run this
    script are stamped `pr`, the later of the two, so a /commit-only gate
    refused real commit flows. The script re-implements the commit hard blocks.
    """
    assert gate(f"python3 {COMMIT_WRAPPER} plan.json", skills=["pr"]) == ALLOW


@pytest.mark.parametrize("command", [f"python3 {COMMIT_WRAPPER} plan.json", f"{COMMIT_WRAPPER} plan.json"])
def test_the_commit_wrapper_script_outside_any_skill_is_blocked(gate, command):
    """Given no skill attribution, When commit's apply.py runs, Then it is blocked."""
    assert gate(command) == BLOCK


@pytest.mark.parametrize("command", ["git commit -m x", f"python3 {COMMIT_WRAPPER} plan.json"])
def test_staged_task_state_blocks_every_commit_path_even_inside_the_commit_skill(gate, git_env, tmp_path, command):
    """Given a file under .claude/tasks/ is staged, When either commit path runs inside /commit,
    Then it is blocked.

    The commit script got a key of its own, and that key must still reach the
    unconditional staged-state check.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, env=git_env)
    task = tmp_path / ".claude" / "tasks" / "state.json"
    task.parent.mkdir(parents=True)
    task.write_text("{}")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", str(task)], check=True, env=git_env)
    assert gate(command, skills=["commit"]) == BLOCK


def test_a_raw_commit_inside_the_pr_skill_is_blocked(gate):
    """Given /pr is active, When a raw git commit runs, Then it is blocked.

    /pr buys only the validated commit script, never a hand-written commit.
    """
    assert gate("git commit -m x", skills=["pr"]) == BLOCK


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


def test_s_release_is_deliberately_not_gated(gate):
    """Given s-release, which opens the develop-to-master PR, When it runs, Then it is allowed.

    Its base and head are constants with no flag to reach them, it commits and
    pushes nothing, and it never merges, so /pr stays the only path that opens a
    pull request for code someone wrote.
    """
    assert gate("s-release aw-front") == ALLOW


def test_an_unrelated_git_command_is_never_gated(gate):
    """Given a read-only git command, When it runs with no skill, Then it is allowed."""
    assert gate("git status --porcelain") == ALLOW


@pytest.mark.parametrize(
    "command",
    [
        "git p",
        "git up -u origin feature/x",
        "git pf",
        "git -C . p",
        "git pp",
        "git fp origin x",
        "git -c alias.zz=push zz",
    ],
)
def test_an_alias_that_expands_to_a_push_is_gated_like_one(gate, command):
    """Given an alias whose expansion is a push, directly, through another alias,
    via a function-style `!` line or defined on the command line,
    When it runs outside /pr, Then it is blocked."""
    assert gate(command) == BLOCK


def test_an_alias_that_expands_to_a_push_is_allowed_inside_the_pr_skill(gate):
    """Given /pr is active, When a push alias runs, Then it is allowed."""
    assert gate("git p -u origin feature/x", skills=["pr"]) == ALLOW


def test_an_alias_in_another_repos_config_is_found_through_git_dir(gate, git_env, tmp_path):
    """Given a push alias defined only in a repo named by --git-dir,
    When it runs outside /pr, Then it is blocked."""
    other = tmp_path / "other"
    for args in (["init", "-q", str(other)], ["-C", str(other), "config", "alias.lp", "push"]):
        subprocess.run(["git", *args], env=git_env, check=True, capture_output=True)
    assert gate(f"git --git-dir={other}/.git lp") == BLOCK


@pytest.mark.parametrize("command", ["git c -m 'feat: x'", "git ca 'feat: x'", "git wip", "git a"])
def test_an_alias_that_expands_to_a_commit_needs_the_commit_skill(gate, command):
    """Given a commit alias, plain, `!` chained or nested, When it runs outside
    /commit, Then it is blocked."""
    assert gate(command) == BLOCK


def test_no_verify_inside_an_alias_is_blocked_even_inside_the_owning_skills(gate):
    """Given an alias whose expansion carries --no-verify, When it runs inside
    /commit and /pr, Then it is blocked, as the literal flag would be."""
    assert gate("git apf", skills=["commit", "pr"]) == BLOCK


@pytest.mark.parametrize(
    "command",
    [
        f"git cm 'feat: a {EM_DASH} b'",
        f"git ca 'feat: a {EM_DASH} b'",
        "git ca 'feat: a\n\nCo-Authored-By: Claude <noreply@anthropic.com>'",
    ],
)
def test_a_commit_message_passed_to_an_alias_is_still_checked(gate, command):
    """Given a commit alias that supplies -m or -am itself, When the message the
    caller appends breaks house style inside /commit, Then it is blocked."""
    assert gate(command, skills=["commit"]) == BLOCK


@pytest.mark.parametrize(
    "command", ["git st", "git dw", "git rh", "git res", "git loop", "git nope", "git status"]
)
def test_an_alias_that_expands_to_no_gated_command_is_not_gated(gate, command):
    """Given an alias that neither commits nor pushes, a self-referencing one, an
    unknown name, or an alias git ignores because a real command owns the name,
    When it runs with no skill, Then the gate allows it.

    A `reset --hard` alias is the deny list's to refuse, not this gate's.
    """
    assert gate(command) == ALLOW


def test_a_shell_alias_is_matched_but_never_executed(gate, tmp_path):
    """Given a `!` alias that would write a file, When the gate inspects it,
    Then the file is never written."""
    marker = tmp_path / "ran"
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text(gitconfig.read_text() + f"\ttouchit = \"!touch {marker}\"\n")
    assert gate("git touchit") == ALLOW
    assert not marker.exists()


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
