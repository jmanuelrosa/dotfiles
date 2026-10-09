"""`pre-commit-verify.sh` recognises a commit whichever way it is spelled, and only runs a
repo's own checks when the repo's origin is one the user trusts.

The commit skill commits through its own `apply.py`, so a gate that only parsed
`git commit` would never verify a commit made by /commit. The parser cases exercise
it directly, since running the verification itself needs a project.

The trust cases matter because the hook runs outside the agent sandbox: a stranger's
clone whose lint script runs on commit would run with the user's full access.
"""

import json
import os
import shutil
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "pre-commit-verify.sh"
verify = SourceFileLoader("pre_commit_verify", str(HOOK)).load_module()

TRUSTED = [
    ("github.com", ("jmanuelrosa",)),
    ("gitlab.com-work", ("group", "sub")),
    ("github.com", ("someone", "tool")),
]


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


# --- whose checks it runs ------------------------------------------------------


@pytest.fixture
def isolated_git(monkeypatch):
    """Keep the user's own gitconfig, with its insteadOf rewrites and hooksPath, out of the run."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(path, origin=None, other=None):
    path.mkdir()
    git(path, "init", "-q")
    if origin:
        git(path, "remote", "add", "origin", origin)
    if other:
        git(path, "remote", "add", "upstream", other)
    return path


@pytest.mark.parametrize("url", [
    "git@github.com:jmanuelrosa/dotfiles.git",
    "https://github.com/jmanuelrosa/dotfiles",
    "https://github.com/jmanuelrosa/dotfiles.git/",
    "ssh://git@github.com/jmanuelrosa/dotfiles.git",
    "ssh://git@GitHub.com:22/JManuelRosa/dotfiles",
    "https://token@github.com/jmanuelrosa/dotfiles",
])
def test_every_remote_spelling_resolves_to_one_location(url):
    assert verify.remote_location(url) == ("github.com", ("jmanuelrosa", "dotfiles"))


@pytest.mark.parametrize("url", [
    "/srv/git/repo.git",
    "../repo",
    "./odd:name",
    "file:///srv/git/repo.git",
    "github.com",
    "",
])
def test_a_local_or_hostless_remote_has_no_location(url):
    assert verify.remote_location(url) is None


@pytest.mark.parametrize("url", [
    "git@github.com:jmanuelrosa/dotfiles.git",
    "https://github.com/jmanuelrosa/dotfiles",
    "git@gitlab.com-work:group/sub/project.git",
    "git@github.com:someone/tool.git",
])
def test_a_remote_under_a_listed_namespace_or_repo_is_trusted(url):
    assert verify.is_trusted(url, TRUSTED)


@pytest.mark.parametrize("url", [
    "git@github.com:someone/dotfiles.git",
    "git@github.com:someone/tool-fork.git",
    "https://github.com/jmanuelrosa-evil/dotfiles",
    "https://github.com.evil.io/jmanuelrosa/dotfiles",
    "https://github.com@evil.io/jmanuelrosa/dotfiles",
    "git@evil.io:github.com/jmanuelrosa/dotfiles",
    "https://github.com/jmanuelrosa/../evil/dotfiles",
    "git@gitlab.com:group/sub/project.git",
    "git@gitlab.com-work:group/project.git",
    "/srv/jmanuelrosa/dotfiles",
])
def test_anything_outside_the_listed_namespaces_is_not(url):
    assert not verify.is_trusted(url, TRUSTED)


def test_the_shipped_list_parses_whole():
    entries = json.loads(verify.TRUSTED_REMOTES.read_text())["remotes"]
    assert entries
    assert len(verify.load_trusted(verify.TRUSTED_REMOTES)) == len(entries)


def test_the_repo_trust_decision(tmp_path, isolated_git):
    listed = tmp_path / "trusted-remotes.json"
    listed.write_text(json.dumps({"remotes": ["github.com/jmanuelrosa"]}))

    local = make_repo(tmp_path / "local")
    trusted = make_repo(tmp_path / "trusted", origin="git@github.com:jmanuelrosa/x.git")
    stranger = make_repo(tmp_path / "stranger", origin="https://ci:ghp_secret@github.com/someone/x")
    no_origin = make_repo(tmp_path / "no-origin", other="git@github.com:jmanuelrosa/x.git")

    assert verify.untrusted_reason(str(trusted), listed) is None
    assert "no origin" in verify.untrusted_reason(str(local), listed)
    assert "no origin" in verify.untrusted_reason(str(no_origin), listed)
    stranger_reason = verify.untrusted_reason(str(stranger), listed)
    assert "github.com/someone/x" in stranger_reason
    assert "ghp_secret" not in stranger_reason
    assert "could not be read" in verify.untrusted_reason(str(trusted), tmp_path / "missing.json")


# --- end to end ----------------------------------------------------------------


@pytest.fixture
def harness(tmp_path):
    """The hook in a harness tree of its own, so the list it reads is the test's."""
    hooks = tmp_path / "harness" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(HOOK, hooks / HOOK.name)
    (hooks.parent / "trusted-remotes.json").write_text(
        json.dumps({"remotes": ["github.com/jmanuelrosa"]})
    )
    return hooks / HOOK.name


def run_hook(hook, repo):
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": str(repo)}
    return subprocess.run(
        [sys.executable, str(hook)], input=json.dumps(payload), capture_output=True, text=True
    )


def test_an_untrusted_clone_never_runs_its_own_lint(tmp_path, harness, isolated_git):
    marker = tmp_path / "pwned"
    repo = make_repo(tmp_path / "repo", origin="https://github.com/someone/x")
    (repo / "package.json").write_text(json.dumps({"scripts": {"lint": f"touch {marker}"}}))
    (repo / "Makefile").write_text(f"lint:\n\ttouch {marker}\n")

    result = run_hook(harness, repo)

    assert result.returncode == 0
    assert not marker.exists()
    assert "skipped `npm run lint`" in result.stderr
    assert "github.com/someone/x" in result.stderr


def test_a_trusted_repo_runs_its_lint(tmp_path, harness, isolated_git):
    marker = tmp_path / "linted"
    repo = make_repo(tmp_path / "repo", origin="git@github.com:jmanuelrosa/x.git")
    (repo / "Makefile").write_text(f"lint:\n\ttouch {marker}\n")

    result = run_hook(harness, repo)

    assert result.returncode == 0, result.stderr
    assert marker.exists()
    assert result.stderr == ""
