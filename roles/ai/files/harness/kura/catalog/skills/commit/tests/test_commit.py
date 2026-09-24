"""The /commit executor enforces branch naming before staging or committing."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REAL_GIT = shutil.which("git")
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}


def run_git(cwd, *args):
    return subprocess.run(
        [REAL_GIT, "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=cwd,
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    )


def write(project, path, text="content\n"):
    target = project / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def commit_count(project):
    return int(run_git(project, "rev-list", "--count", "HEAD").stdout)


@pytest.fixture
def repo(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    run_git(project, "init", "-q", "-b", "main")
    run_git(project, "config", "user.email", "t@example.test")
    run_git(project, "config", "user.name", "Tester")
    write(project, "README.md", "# project\n")
    run_git(project, "add", "README.md")
    run_git(project, "commit", "-q", "-m", "chore: init")
    run_git(project, "remote", "add", "origin", "git@example.test:owner/project.git")
    run_git(project, "update-ref", "refs/remotes/origin/main", "main")
    run_git(project, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    return project


def context(project):
    return subprocess.run(
        ["bash", str(SCRIPTS / "context.sh")],
        cwd=project,
        env=GIT_ENV,
        capture_output=True,
        text=True,
    )


def execute(project, tmp_path, branch, message="fix(app): change behavior"):
    if branch != "main":
        run_git(project, "switch", "-q", "-c", branch)
    write(project, "src/app.ts", "export const changed = true\n")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"commits": [{"files": ["src/app.ts"], "message": message}]}))
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "apply.py"), str(plan)],
        cwd=project,
        env=GIT_ENV,
        capture_output=True,
        text=True,
    )


def test_context_marks_a_nonstandard_working_branch(repo):
    run_git(repo, "switch", "-q", "-c", "front-reverse-proxy")

    assert "BRANCH_CONVENTION=nonstandard" in context(repo).stdout


def test_context_marks_a_conventional_working_branch(repo):
    run_git(repo, "switch", "-q", "-c", "fix/front-reverse-proxy")

    assert "BRANCH_CONVENTION=ok" in context(repo).stdout


def test_context_leaves_the_convention_unresolved_without_an_origin(repo):
    run_git(repo, "remote", "remove", "origin")

    assert "BRANCH_CONVENTION=unresolved" in context(repo).stdout


def test_a_nonstandard_working_branch_is_rejected_before_staging(repo, tmp_path):
    before = commit_count(repo)
    result = execute(repo, tmp_path, "front-reverse-proxy")

    assert result.returncode != 0
    assert commit_count(repo) == before
    assert run_git(repo, "diff", "--cached", "--name-only").stdout == ""


def test_a_conventional_working_branch_can_commit(repo, tmp_path):
    result = execute(repo, tmp_path, "fix/front-reverse-proxy")

    assert result.returncode == 0
    assert commit_count(repo) == 2


def test_the_default_branch_remains_an_allowed_explicit_choice(repo, tmp_path):
    result = execute(repo, tmp_path, "main", message="chore: update project")

    assert result.returncode == 0
    assert commit_count(repo) == 2
