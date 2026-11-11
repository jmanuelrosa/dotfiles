"""`git-skill-gate.sh` lets /ship's apply.py run only after a confirmation.

/ship is model-invocable, and Claude Code stamps no `attributionSkill` on the
turns of a model-invoked skill, nor on any turn after a prose reply. So these
transcripts carry the real event shapes: the `/ship` command message, the Skill
tool call, the AskUserQuestion round-trip, and typed messages.
"""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "git-skill-gate.sh"

ALLOW = 0
BLOCK = 2

SHIP = "python3 ~/.claude/skills/ship/scripts/apply.py /tmp/claude/ship-plan.json"
QUESTION_ID = "toolu_ask"
ORIGIN_URL = "git@github.com:example/project.git"
HTTPS_PUSH = (
    "git -c url.https://github.com/.pushInsteadOf=git@github.com: "
    "-c credential.helper= -c 'credential.helper=!gh auth git-credential' "
    "push -u origin feature/reylo-query-trial"
)


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
def git_env():
    return {
        **{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_ALLOW_PROTOCOL": "",
        "GIT_TERMINAL_PROMPT": "0",
    }


@pytest.fixture
def repo_on(tmp_path, git_env):
    def make(name="repo", origin=ORIGIN_URL):
        repo = tmp_path / name
        commands = [["init", "-q", "-b", "feature/reylo-query-trial", str(repo)]]
        if origin is not None:
            commands += [
                ["-C", str(repo), "remote", "add", "origin", origin],
                ["-C", str(repo), "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/develop"],
            ]
        for args in commands:
            subprocess.run(["git", *args], check=True, capture_output=True, text=True, env=git_env)
        return repo

    return make


@pytest.fixture
def gate(tmp_path, git_env, repo_on):
    transcript = tmp_path / "transcript.jsonl"
    repo = repo_on()

    def run(events, command=SHIP, *, cwd=None, transcript_path=None):
        if events is not None:
            transcript.write_text("".join(json.dumps(event) + "\n" for event in events))
        event = {
            "tool_input": {"command": command},
            "transcript_path": str(transcript) if transcript_path is None else str(transcript_path),
            "cwd": str(repo if cwd is None else cwd),
        }
        return subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True, text=True,
            cwd=tmp_path, env=git_env,
        )

    return run


def test_ship_outside_any_skill_is_blocked(gate):
    """Given no /ship invocation, When ship's apply.py runs, Then it is blocked."""
    assert gate([typed("please ship it"), assistant_turn()]).returncode == BLOCK


def test_a_model_invoked_ship_without_an_answer_is_blocked(gate):
    """Given a model loaded /ship and asked nothing, When apply.py runs, Then it is blocked.

    The confirmation is the whole contract of a model-invoked /ship.
    """
    assert gate([typed("done?"), skill_tool(), skill_body(), assistant_turn()]).returncode == BLOCK


def test_a_model_invoked_ship_after_an_answered_question_is_allowed(gate):
    """Given a model loaded /ship and the user answered its gate, When apply.py runs, Then it is allowed."""
    assert gate([skill_tool(), skill_body(), asked(), answered(), assistant_turn()]).returncode == ALLOW


def test_a_prose_go_after_a_model_invoked_ship_is_allowed(gate):
    """Given the user answered the gate in prose, When apply.py runs, Then it is allowed.

    A prose reply drops `attributionSkill`, which is what made /commit and /pr
    refuse a typed "go".
    """
    assert gate([skill_tool(), skill_body(), asked(), typed("go"), assistant_turn()]).returncode == ALLOW


def test_a_typed_ship_answered_in_prose_is_allowed(gate):
    """Given the user typed /ship and answered in prose, When apply.py runs, Then it is allowed."""
    assert gate([slash_ship(), skill_body(), asked(), typed("continue"), assistant_turn()]).returncode == ALLOW


def test_a_dismissed_question_is_not_a_confirmation(gate):
    """Given the gate question was rejected, When apply.py runs, Then it is blocked."""
    assert gate([skill_tool(), skill_body(), asked(), answered(is_error=True)]).returncode == BLOCK


def test_a_task_notification_is_not_a_confirmation(gate):
    """Given only an automated notification followed /ship, When apply.py runs, Then it is blocked."""
    assert gate([skill_tool(), skill_body(), notification(), assistant_turn()]).returncode == BLOCK


def test_an_answer_before_the_latest_invocation_does_not_count(gate):
    """Given /ship was invoked again after an earlier answer, When apply.py runs, Then it is blocked.

    Each run asks its own question.
    """
    events = [skill_tool(), asked(), answered(), skill_tool(), skill_body(), assistant_turn()]
    assert gate(events).returncode == BLOCK


def test_another_skill_invocation_does_not_open_ship(gate):
    """Given a different skill was invoked and answered, When apply.py runs, Then it is blocked."""
    assert gate([skill_tool("commit"), asked(), typed("go")]).returncode == BLOCK


def test_an_attributed_ship_turn_is_allowed(gate):
    """Given the classic attribution stamp (a typed /ship, or pi's synthetic transcript), Then it is allowed."""
    assert gate([{"attributionSkill": "ship"}]).returncode == ALLOW


def test_a_confirmed_ship_allows_a_plain_push(gate):
    """Given a confirmed /ship, When a plain push runs, Then it is allowed."""
    events = [skill_tool(), skill_body(), asked(), answered()]
    assert gate(events, command="git push -u origin fix/x").returncode == ALLOW


@pytest.mark.parametrize("events", [
    [skill_tool(), skill_body(), asked(), answered()],
    [slash_ship(), skill_body(), asked(), typed("go")],
    [{"attributionSkill": "pr"}],
], ids=["confirmed-model-ship", "confirmed-typed-ship", "owning-pr"])
def test_an_authorized_skill_allows_the_generated_https_push(gate, events):
    result = gate(events, command=HTTPS_PUSH)
    assert result.returncode == ALLOW, result.stderr


def test_a_confirmed_ship_does_not_buy_a_raw_commit(gate):
    """Given a confirmed /ship, When a raw git commit runs, Then it is blocked: ship commits through apply.py."""
    events = [skill_tool(), skill_body(), asked(), answered()]
    assert gate(events, command="git commit -m 'fix: x'").returncode == BLOCK


def test_ship_does_not_authorize_the_pr_wrapper(gate):
    """Given a confirmed /ship, When pr's apply.py runs, Then it is blocked."""
    events = [skill_tool(), skill_body(), asked(), answered()]
    assert gate(events, command="python3 ~/.claude/skills/pr/scripts/apply.py plan.json").returncode == BLOCK


def test_ship_wrapper_still_refuses_a_destructive_push_shape(gate):
    """Given a confirmed /ship, When a force push runs, Then the hard block still applies."""
    events = [skill_tool(), skill_body(), asked(), answered()]
    assert gate(events, command="git push --force origin fix/x").returncode == BLOCK


@pytest.mark.parametrize("events", [
    [],
    [typed("please ship it"), assistant_turn()],
    [skill_tool(), skill_body(), asked()],
    [skill_tool(), asked(), answered(is_error=True)],
    [skill_tool(), notification()],
    [skill_tool("commit"), asked(), answered()],
], ids=["empty", "outside-skill", "unconfirmed", "dismissed", "notification", "wrong-skill"])
def test_the_generated_https_push_requires_owning_skill_evidence(gate, events):
    result = gate(events, command=HTTPS_PUSH)
    assert result.returncode == BLOCK, result.stderr
    assert "blocked" in result.stderr.lower()


@pytest.mark.parametrize("transcript_state", ["absent", "missing", "unreadable"])
def test_the_generated_https_push_fails_closed_without_a_readable_transcript(gate, tmp_path, transcript_state):
    transcript = tmp_path / "unavailable.jsonl"
    if transcript_state == "unreadable":
        transcript.write_bytes(b"\xff")
    result = gate(None, command=HTTPS_PUSH, transcript_path="" if transcript_state == "absent" else transcript)
    assert result.returncode == BLOCK, result.stderr
    assert "blocked" in result.stderr.lower()


@pytest.mark.parametrize("repository_state", ["missing-origin", "not-a-repository"])
def test_the_generated_https_push_fails_closed_without_origin(gate, repo_on, tmp_path, repository_state):
    cwd = repo_on("without-origin", origin=None) if repository_state == "missing-origin" else tmp_path
    result = gate([skill_tool(), asked(), answered()], command=HTTPS_PUSH, cwd=cwd)
    assert result.returncode == BLOCK, result.stderr
    assert "blocked" in result.stderr.lower()


@pytest.mark.parametrize("command", [
    HTTPS_PUSH.replace("url.https://github.com/", "url.https://elsewhere.invalid/"),
    HTTPS_PUSH.replace("url.https://github.com/", "url.https://github.com/other-project/"),
    HTTPS_PUSH.replace("git@github.com:", "git@elsewhere.invalid:"),
    HTTPS_PUSH.replace("pushInsteadOf", "insteadOf"),
    HTTPS_PUSH.replace("push -u origin", "push -u https://github.com/elsewhere/project.git"),
    HTTPS_PUSH.replace("push -u origin", "push -u unknown"),
    HTTPS_PUSH.replace("push -u origin", "push origin"),
    HTTPS_PUSH.replace("push -u", "push --force -u"),
], ids=["host-redirect", "repository-redirect", "source-host-mismatch", "ordinary-insteadof",
        "url-destination", "unknown-remote", "not-generated-push-form", "force-flag"])
def test_the_generated_https_push_exception_does_not_authorize_other_rewrites(gate, command):
    result = gate([skill_tool(), asked(), answered()], command=command)
    assert result.returncode == BLOCK, result.stderr
    assert "blocked" in result.stderr.lower()


@pytest.mark.parametrize("origin", ["git@elsewhere.invalid:example/project.git", "https://github.com/example/project.git"])
def test_the_generated_https_push_requires_a_matching_ssh_origin(gate, repo_on, origin):
    result = gate([skill_tool(), asked(), answered()], command=HTTPS_PUSH, cwd=repo_on("other-origin", origin=origin))
    assert result.returncode == BLOCK, result.stderr
    assert "blocked" in result.stderr.lower()


@pytest.mark.parametrize("pushurl", ["git@elsewhere.invalid:example/project.git", "git@github.com:elsewhere/project.git"])
def test_the_generated_https_push_cannot_hide_an_origin_pushurl_redirect(gate, repo_on, git_env, pushurl):
    repo = repo_on("redirected-pushurl")
    subprocess.run(["git", "-C", str(repo), "config", "remote.origin.pushurl", pushurl], check=True, env=git_env)
    result = gate([skill_tool(), asked(), answered()], command=HTTPS_PUSH, cwd=repo)
    assert result.returncode == BLOCK, result.stderr
    assert "blocked" in result.stderr.lower()


@pytest.mark.parametrize("option", ["-C", "--git-dir"])
@pytest.mark.parametrize("selected_origin", [ORIGIN_URL, "git@elsewhere.invalid:example/project.git"], ids=["same-host", "other-host"])
def test_the_generated_https_push_checks_the_repository_selected_by_git_options(gate, repo_on, option, selected_origin):
    outer_origin = "git@elsewhere.invalid:example/project.git" if selected_origin == ORIGIN_URL else ORIGIN_URL
    outer = repo_on("outer", origin=outer_origin)
    selected = repo_on("selected", origin=selected_origin)
    path = selected if option == "-C" else selected / ".git"
    command = HTTPS_PUSH.replace("git ", f"git {option} {shlex.quote(str(path))} ", 1)
    result = gate([skill_tool(), asked(), answered()], command=command, cwd=outer)
    assert result.returncode == (ALLOW if selected_origin == ORIGIN_URL else BLOCK), result.stderr


@pytest.mark.parametrize(("command", "reason"), [
    (HTTPS_PUSH.replace("feature/reylo-query-trial", "+feature/reylo-query-trial"), "force push"),
    (HTTPS_PUSH.replace("feature/reylo-query-trial", ":feature/reylo-query-trial"), "deletes remote branches"),
    (HTTPS_PUSH.replace("feature/reylo-query-trial", "main"), "push to main"),
    (HTTPS_PUSH.replace("feature/reylo-query-trial", "develop"), "push to develop"),
    (HTTPS_PUSH.replace("push -u", "push --no-verify -u"), "skipping git hooks"),
    (HTTPS_PUSH.replace(" push -u", " -c core.hooksPath=/tmp/hooks push -u"), "core.hookspath"),
    (HTTPS_PUSH.replace(" push -u", " -c remote.origin.url=https://elsewhere.invalid/project.git push -u"), "remote.origin.url"),
    (HTTPS_PUSH.replace(" push -u", " -c url.https://elsewhere.invalid/.insteadOf=git@github.com: push -u"), "elsewhere.invalid"),
    (HTTPS_PUSH + "; git config core.hooksPath /tmp/hooks", "core.hookspath"),
    (HTTPS_PUSH + "; git config --local url.https://elsewhere.invalid/.pushInsteadOf git@github.com:", "elsewhere.invalid"),
], ids=["force", "deletion", "main", "remote-default", "no-verify", "hookspath", "remote-url",
        "second-rewrite", "chained-hookspath", "chained-persistent-rewrite"])
def test_the_generated_https_push_does_not_bypass_other_guards(gate, command, reason):
    result = gate([skill_tool(), asked(), answered()], command=command)
    assert result.returncode == BLOCK, result.stderr
    assert reason in result.stderr.lower()


@pytest.mark.parametrize("command", [
    "git config --local url.https://github.com/.pushInsteadOf git@github.com:",
    "git --config-env=url.https://github.com/.pushInsteadOf=REWRITE push -u origin feature/reylo-query-trial",
    ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.https://github.com/.pushInsteadOf GIT_CONFIG_VALUE_0=git@github.com: "
     "git push -u origin feature/reylo-query-trial"),
])
def test_the_generated_https_push_exception_never_authorizes_persistent_or_environment_config(gate, command):
    result = gate([skill_tool(), asked(), answered()], command=command)
    assert result.returncode == BLOCK, result.stderr
    assert "pushinsteadof" in result.stderr.lower()
