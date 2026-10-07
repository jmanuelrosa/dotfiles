"""`pre-commit-verify.sh` recognises a commit whichever way it is spelled.

The commit skill commits through its own `apply.py`, so a gate that only parsed
`git commit` would never verify a commit made by /commit. Cases exercise the
parser directly, since running the verification itself needs a project.
"""

from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "pre-commit-verify.sh"
verify = SourceFileLoader("pre_commit_verify", str(HOOK)).load_module()


def commits(command):
    return any(verify.is_git_commit(chunk) for chunk in verify.split_subcommands(command))


@pytest.mark.parametrize("command", [
    "git commit -F msg.txt",
    "git -C repo commit -m x",
    "python3 ~/.claude/skills/commit/scripts/apply.py plan.json",
    "python3 .claude/skills/commit/scripts/apply.py plan.json",
    "~/.claude/skills/commit/scripts/apply.py plan.json",
])
def test_a_commit_is_recognised(command):
    assert commits(command)


@pytest.mark.parametrize("command", [
    "git status",
    "python3 ~/.claude/skills/pr/scripts/apply.py plan.json",
    "python3 other/apply.py plan.json",
])
def test_anything_else_is_left_alone(command):
    assert not commits(command)
