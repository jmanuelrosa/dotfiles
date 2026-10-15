"""The /ship skill's two scripts: `context.py` gathers, `apply.py` commits, pushes and opens.

The cases run against a throwaway repo whose `origin` has no server behind it,
with `git push`, `gh` and `glab` stubbed on a narrowed PATH so a real remote can
never be reached. Cases assert on the scripts' named exit codes, on the git
state left behind, and on what the stubs recorded, never on message wording.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys

from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name):
    """Import a script by path, leaving no __pycache__ inside the shipped skill."""
    cached = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(f"ship_{name}", SCRIPTS / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = cached


apply_ship = _load("apply")

REAL_GIT = shutil.which("git")
URL = "https://example.test/o/r/pull/1"
EXISTING_URL = "https://example.test/o/r/pull/7"
EM_DASH = chr(0x2014)

GIT_STUB = '''#!{interpreter}
import json, os, sys

argv = sys.argv[1:]
if "push" in argv:
    with open(os.environ["SHIP_STUB_LOG"], "a") as log:
        log.write(json.dumps(["git"] + argv) + "\\n")
    sys.exit(int(os.environ.get("SHIP_STUB_PUSH_CODE", "0")))
os.execv(os.environ["SHIP_REAL_GIT"], [os.environ["SHIP_REAL_GIT"]] + argv)
'''

CLI_STUB = '''#!{interpreter}
import json, os, sys

with open(os.environ["SHIP_STUB_LOG"], "a") as log:
    log.write(json.dumps([os.path.basename(sys.argv[0])] + sys.argv[1:]) + "\\n")
if "list" in sys.argv:
    sys.stdout.write(os.environ.get("SHIP_STUB_LIST", "[]") + "\\n")
    sys.exit(0)
code = int(os.environ.get("SHIP_STUB_CREATE_CODE", "0"))
if code:
    sys.stderr.write("refused\\n")
    sys.exit(code)
sys.stdout.write(os.environ["SHIP_STUB_URL"] + "\\n")
'''


def git_out(cwd, *args):
    return subprocess.run([REAL_GIT, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def write(project, path, text="content\n"):
    target_path = project / path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(text)


def commit(project, message):
    git_out(project, "add", "-A")
    git_out(project, "commit", "-q", "-m", message)


def subjects(project, count):
    return git_out(project, "log", f"-n{count}", "--pretty=%s").splitlines()


@pytest.fixture
def repo(tmp_path):
    """A repo on `main` with a GitHub origin and no server behind it."""
    project = tmp_path / "project"
    project.mkdir()
    git_out(project, "init", "-q", "-b", "main")
    for key, value in (
        ("user.email", "t@example.test"),
        ("user.name", "Tester"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", "/dev/null"),
    ):
        git_out(project, "config", key, value)
    write(project, "README.md", "# project\n")
    commit(project, "chore: init")
    git_out(project, "remote", "add", "origin", "git@github.com:owner/project.git")
    git_out(project, "update-ref", "refs/remotes/origin/main", "main")
    git_out(project, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    return project


@pytest.fixture
def stubs(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "git").write_text(GIT_STUB.format(interpreter=sys.executable))
    for name in ("gh", "glab"):
        (bindir / name).write_text(CLI_STUB.format(interpreter=sys.executable))
    for name in ("git", "gh", "glab"):
        (bindir / name).chmod(0o755)
    log = tmp_path / "calls.log"

    def run(*argv, cwd, extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{bindir}:/usr/bin:/bin",
            "SHIP_STUB_LOG": str(log),
            "SHIP_REAL_GIT": REAL_GIT,
            "SHIP_STUB_URL": URL,
            **(extra_env or {}),
        }
        return subprocess.run([sys.executable, *argv], cwd=str(cwd), env=env, capture_output=True, text=True)

    def calls():
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line]

    run.calls = calls
    return run


def target(stdout):
    found = {}
    for line in stdout.splitlines():
        if line.startswith("=="):
            if found:
                break
            continue
        key, sep, value = line.partition("=")
        if sep:
            found[key] = value
    return found


def gather(stubs, project, *argv):
    return stubs(str(SCRIPTS / "context.py"), *argv, cwd=project)


def plan_file(tmp_path, branch, commits, body="Adds the banner.\n", **pr):
    body_file = tmp_path / "body.md"
    body_file.write_text(body)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({
        "branch": branch,
        "commits": commits,
        "pr": {"base": "main", "body_file": str(body_file), **pr},
    }))
    return plan


def execute(stubs, project, plan, *extra, env=None):
    return stubs(str(SCRIPTS / "apply.py"), str(plan), *extra, cwd=project, extra_env=env)


def created(stubs):
    return [call for call in stubs.calls() if call[:3] == ["gh", "pr", "create"]]


def pushes(stubs):
    return [call for call in stubs.calls() if call[0] == "git"]


# context.py


def test_context_reports_unpushed_commits_and_a_dirty_tree(stubs, repo):
    git_out(repo, "switch", "-q", "-c", "fix/banner")
    write(repo, "src/banner.ts")
    commit(repo, "fix(banner): keep state")
    write(repo, "src/other.ts")

    found = target(gather(stubs, repo).stdout)

    assert found["BRANCH_CONVENTION"] == "ok"
    assert found["UNPUSHED_COMMITS"] == "1"
    assert found["PUSHED_COMMITS"] == "0"
    assert found["WORKTREE"] == "dirty"


def test_context_splits_pushed_from_unpushed_commits(stubs, repo):
    git_out(repo, "switch", "-q", "-c", "fix/banner")
    write(repo, "a.ts")
    commit(repo, "fix: a")
    git_out(repo, "update-ref", "refs/remotes/origin/fix/banner", "HEAD")
    git_out(repo, "branch", "-q", "--set-upstream-to=origin/fix/banner")
    write(repo, "b.ts")
    commit(repo, "fix: b")

    found = target(gather(stubs, repo).stdout)

    assert (found["PUSHED_COMMITS"], found["UNPUSHED_COMMITS"]) == ("1", "1")


def test_context_flags_the_default_branch(stubs, repo):
    write(repo, "a.ts")
    assert target(gather(stubs, repo).stdout)["BRANCH_CONVENTION"] == "default"


def test_context_counts_local_commits_on_the_default_branch_as_unpushed(stubs, repo):
    write(repo, "a.ts")
    commit(repo, "fix: a")
    assert target(gather(stubs, repo).stdout)["UNPUSHED_COMMITS"] == "1"


# apply.py: the full run


def test_a_kept_branch_is_committed_pushed_and_opened_in_order(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/banner")
    write(repo, "src/banner/state.ts")
    write(repo, "src/banner/state.test.ts")
    write(repo, "package.json", "{}\n")
    plan = plan_file(tmp_path, {"action": "keep", "name": "fix/banner"}, [
        {"files": ["package.json"], "message": "build: add manifest"},
        {"files": ["src/banner/state.ts", "src/banner/state.test.ts"], "message": "fix(banner): keep state\n\n- why"},
    ])

    result = execute(stubs, repo, plan)

    assert result.returncode == apply_ship.EXIT_OK, result.stderr
    assert subjects(repo, 2) == ["fix(banner): keep state", "build: add manifest"]
    assert [call[-1] for call in pushes(stubs)] == ["fix/banner"]
    create = created(stubs)
    assert len(create) == 1
    assert create[0][create[0].index("--title") + 1] == "fix: banner"
    assert f"Created: {URL}" in result.stdout


def test_work_on_the_default_branch_moves_to_a_new_branch(stubs, repo, tmp_path):
    write(repo, "src/banner.ts")
    plan = plan_file(tmp_path, {"action": "create", "name": "feature/banner"}, [
        {"files": ["src/banner.ts"], "message": "feat: add banner"},
    ])

    result = execute(stubs, repo, plan)

    assert result.returncode == apply_ship.EXIT_OK, result.stderr
    assert git_out(repo, "branch", "--show-current") == "feature/banner"
    assert subjects(repo, 1) == ["feat: add banner"]
    assert git_out(repo, "rev-parse", "main") == git_out(repo, "rev-parse", "origin/main")
    assert created(stubs)[0][created(stubs)[0].index("--title") + 1] == "feat: banner"


def test_leaving_existing_commits_out_branches_off_the_base(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "chore/bump-deps")
    write(repo, "deps.txt")
    commit(repo, "chore: bump deps")
    write(repo, "src/banner.ts")
    plan = plan_file(tmp_path, {"action": "create-from-base", "name": "fix/banner"}, [
        {"files": ["src/banner.ts"], "message": "fix: keep banner"},
    ])

    result = execute(stubs, repo, plan)

    assert result.returncode == apply_ship.EXIT_OK, result.stderr
    assert git_out(repo, "log", "origin/main..HEAD", "--pretty=%s").splitlines() == ["fix: keep banner"]
    assert subjects(repo, 1) == ["fix: keep banner"]
    assert git_out(repo, "log", "-n1", "--pretty=%s", "chore/bump-deps") == "chore: bump deps"


def test_a_nonstandard_branch_is_renamed_before_committing(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "my-work")
    write(repo, "a.ts")
    plan = plan_file(tmp_path, {"action": "rename", "name": "fix/a"}, [{"files": ["a.ts"], "message": "fix: a"}])

    result = execute(stubs, repo, plan)

    assert result.returncode == apply_ship.EXIT_OK, result.stderr
    assert git_out(repo, "branch", "--show-current") == "fix/a"


def test_existing_commits_alone_are_pushed_and_opened(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    write(repo, "a.ts")
    commit(repo, "fix: a")
    plan = plan_file(tmp_path, {"action": "keep"}, [])

    result = execute(stubs, repo, plan)

    assert result.returncode == apply_ship.EXIT_OK, result.stderr
    assert len(pushes(stubs)) == 1 and len(created(stubs)) == 1


def test_an_open_pr_for_the_branch_is_reused(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    write(repo, "a.ts")
    plan = plan_file(tmp_path, {"action": "keep"}, [{"files": ["a.ts"], "message": "fix: a"}])

    result = execute(stubs, repo, plan, env={"SHIP_STUB_LIST": json.dumps([{"url": EXISTING_URL}])})

    assert result.returncode == apply_ship.EXIT_OK, result.stderr
    assert created(stubs) == []
    assert f"Updated: {EXISTING_URL}" in result.stdout


def test_a_github_issue_branch_closes_its_issue(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/gh-42-banner")
    write(repo, "a.ts")
    plan = plan_file(tmp_path, {"action": "keep"}, [{"files": ["a.ts"], "message": "fix: a"}])

    result = execute(stubs, repo, plan)

    assert result.returncode == apply_ship.EXIT_OK, result.stderr
    create = created(stubs)[0]
    assert create[create.index("--title") + 1] == "fix: banner"
    assert apply_ship.with_closes("Body.\n", "Closes #42").endswith("Closes #42\n")
    assert apply_ship.with_closes("Body.\nCloses #42\n", "Closes #42") == "Body.\nCloses #42\n"


# apply.py: refusals happen before the first write


def head(project):
    return git_out(project, "rev-parse", "HEAD")


def test_keeping_the_default_branch_is_refused(stubs, repo, tmp_path):
    write(repo, "a.ts")
    before = head(repo)
    plan = plan_file(tmp_path, {"action": "keep"}, [{"files": ["a.ts"], "message": "fix: a"}])

    assert execute(stubs, repo, plan).returncode == apply_ship.EXIT_BLOCKED
    assert head(repo) == before and stubs.calls() == []


@pytest.mark.parametrize("name", ["my-work", "feat/a", "fix/A"])
def test_a_nonstandard_new_branch_name_is_refused(stubs, repo, tmp_path, name):
    write(repo, "a.ts")
    plan = plan_file(tmp_path, {"action": "create", "name": name}, [{"files": ["a.ts"], "message": "fix: a"}])

    assert execute(stubs, repo, plan).returncode == apply_ship.EXIT_BLOCKED
    assert git_out(repo, "branch", "--show-current") == "main"


def test_a_typographic_dash_in_a_message_is_refused_before_any_commit(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    write(repo, "a.ts")
    write(repo, "b.ts")
    before = head(repo)
    plan = plan_file(tmp_path, {"action": "keep"}, [
        {"files": ["a.ts"], "message": "fix: a"},
        {"files": ["b.ts"], "message": f"fix: b {EM_DASH} c"},
    ])

    assert execute(stubs, repo, plan).returncode == apply_ship.EXIT_BLOCKED
    assert head(repo) == before


def test_an_attribution_line_in_the_body_is_refused(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    write(repo, "a.ts")
    plan = plan_file(
        tmp_path, {"action": "keep"}, [{"files": ["a.ts"], "message": "fix: a"}],
        body="Body.\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n",
    )

    assert execute(stubs, repo, plan).returncode == apply_ship.EXIT_BLOCKED
    assert stubs.calls() == []


@pytest.mark.parametrize("path", [".env", "keys/service-key.json", ".claude/tasks/1.json"])
def test_secrets_and_agent_state_are_refused(stubs, repo, tmp_path, path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    write(repo, path)
    plan = plan_file(tmp_path, {"action": "keep"}, [{"files": [path], "message": "fix: a"}])

    assert execute(stubs, repo, plan).returncode == apply_ship.EXIT_BLOCKED


def test_an_existing_branch_name_is_refused(stubs, repo, tmp_path):
    git_out(repo, "branch", "fix/a")
    write(repo, "a.ts")
    plan = plan_file(tmp_path, {"action": "create", "name": "fix/a"}, [{"files": ["a.ts"], "message": "fix: a"}])

    assert execute(stubs, repo, plan).returncode == apply_ship.EXIT_BLOCKED


def test_a_branch_with_nothing_to_ship_is_refused(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    plan = plan_file(tmp_path, {"action": "keep"}, [])

    assert execute(stubs, repo, plan).returncode == apply_ship.EXIT_BLOCKED
    assert stubs.calls() == []


# apply.py: failure and resume


def test_a_failed_push_keeps_the_commits_and_never_opens_a_pr(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    write(repo, "a.ts")
    plan = plan_file(tmp_path, {"action": "keep"}, [{"files": ["a.ts"], "message": "fix: a"}])

    failed = execute(stubs, repo, plan, env={"SHIP_STUB_PUSH_CODE": "1"})

    assert failed.returncode == apply_ship.EXIT_PUSH_FAILED
    assert subjects(repo, 1) == ["fix: a"]
    assert created(stubs) == []

    resumed = execute(stubs, repo, plan, "--from", "pr")

    assert resumed.returncode == apply_ship.EXIT_OK, resumed.stderr
    assert subjects(repo, 2) == ["fix: a", "chore: init"]
    assert len(pushes(stubs)) == 1 and len(created(stubs)) == 1


def test_a_refused_create_is_a_named_failure(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    write(repo, "a.ts")
    plan = plan_file(tmp_path, {"action": "keep"}, [{"files": ["a.ts"], "message": "fix: a"}])

    result = execute(stubs, repo, plan, env={"SHIP_STUB_CREATE_CODE": "1"})

    assert result.returncode == apply_ship.EXIT_CREATE_FAILED


def test_a_stray_staged_path_stops_the_commit_loop(stubs, repo, tmp_path):
    git_out(repo, "switch", "-q", "-c", "fix/a")
    write(repo, "a.ts")
    write(repo, "stray.ts")
    git_out(repo, "add", "stray.ts")
    before = head(repo)
    plan = plan_file(tmp_path, {"action": "keep"}, [{"files": ["a.ts"], "message": "fix: a"}])

    assert execute(stubs, repo, plan).returncode == apply_ship.EXIT_COMMIT_FAILED
    assert head(repo) == before
