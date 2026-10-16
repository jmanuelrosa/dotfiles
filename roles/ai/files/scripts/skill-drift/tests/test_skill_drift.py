"""`skill-drift` decides which upstream commits deserve a reviewer, so the cases pin that.

`gh` on PATH is the single environmental seam: a stand-in answers each endpoint from a
JSON table and logs every request, so a case can assert both what was printed and which
requests were never made. The stand-in drops `per_page` and sorts the query, so a table
key reads as the request means rather than as it happens to be encoded.
"""

import json
import os
import subprocess
import sys

import pytest
from dotkit.testing import AI_SCRIPTS_DIR, SKILL_REGISTRY

SKILL_DRIFT = AI_SCRIPTS_DIR / "skill-drift" / "skill-drift"

EXIT_OK = 0
EXIT_FAILED = 1

SHORT = 7
PIN = "a" * 40
NEW = "b" * 40
OLD = "c" * 40
OTHER = "d" * 40

FAKE_GH = """\
import json, os, sys
from urllib.parse import parse_qsl
endpoint = sys.argv[2]
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(endpoint + "\\n")
base, _, query = endpoint.partition("?")
params = sorted((k, v) for k, v in parse_qsl(query) if k != "per_page")
key = base + ("?" + "&".join(f"{k}={v}" for k, v in params) if params else "")
table = json.load(open(os.environ["FAKE_GH_TABLE"]))
answer = table.get(key, table.get("*"))
if answer is None or "error" in answer:
    sys.stderr.write((answer or {}).get("error", "gh: Not Found (HTTP 404)") + "\\n")
    sys.exit(1)
print(json.dumps(answer["pages"]))
"""


def compare_page(ahead=0, behind=0, commits=(), files=()):
    return {
        "ahead_by": ahead,
        "behind_by": behind,
        "commits": [{"sha": sha, "commit": {"message": f"{msg}\n\nbody"}} for sha, msg in commits],
        "files": list(files),
    }


def history(*shas):
    return {"pages": [[{"sha": sha} for sha in shas]]}


def compare_key(repo, branch="main"):
    return f"repos/{repo}/compare/{PIN}...{branch}"


def commits_key(repo, path, branch="main"):
    return f"repos/{repo}/commits?path={path}&sha={branch}"


@pytest.fixture
def run(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "gh"
    fake.write_text(f"#!{sys.executable}\n{FAKE_GH}")
    fake.chmod(0o755)
    log = tmp_path / "gh.log"

    def invoke(upstreams, answers, registry=None):
        if registry is None:
            registry = tmp_path / "skill-registry.json"
            registry.write_text(json.dumps({"upstream": upstreams}))
        table = tmp_path / "gh.json"
        table.write_text(json.dumps(answers))
        log.write_text("")
        env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "FAKE_GH_TABLE": str(table),
            "FAKE_GH_LOG": str(log),
            "NO_COLOR": "1",
        }
        env.pop("FORCE_COLOR", None)
        command = [sys.executable, str(SKILL_DRIFT), "--registry", str(registry)]
        result = subprocess.run(command, capture_output=True, text=True, env=env)
        result.requests = log.read_text().splitlines()
        result.merged = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
        ).stdout
        return result

    return invoke


def upstream(*paths, pin=PIN, branch="main"):
    entry = {"branch": branch, "skills": [{"upstream_path": p} for p in paths]}
    if pin is not None:
        entry["commit"] = pin
    return entry


def test_an_upstream_at_its_pin_is_up_to_date_after_one_request(run):
    result = run(
        {"a/b": upstream("skills/x")},
        {compare_key("a/b"): {"pages": [compare_page()]}},
    )
    assert result.returncode == EXIT_OK
    assert "✓ a/b: up to date with main" in result.stdout
    assert len(result.requests) == 1


def test_new_commits_outside_every_vendored_path_are_not_listed(run):
    result = run(
        {"a/b": upstream("skills/x")},
        {
            compare_key("a/b"): {
                "pages": [
                    compare_page(
                        ahead=2,
                        commits=[(NEW, "touch y"), (OTHER, "touch readme")],
                        files=[{"filename": "skills/y/SKILL.md"}, {"filename": "skills/x-two/a"}],
                    )
                ]
            }
        },
    )
    assert result.returncode == EXIT_OK
    assert "✓ a/b: 2 new commits on main, none touch a vendored skill" in result.stdout
    assert result.requests == [f"{compare_key('a/b')}?per_page=100"]


def test_only_new_commits_that_touch_a_vendored_path_are_listed(run):
    result = run(
        {"a/b": upstream("skills/x", "skills/z")},
        {
            compare_key("a/b"): {
                "pages": [
                    compare_page(
                        ahead=2,
                        commits=[(NEW, "fix x prompt"), (OTHER, "touch readme")],
                        files=[{"filename": "skills/x/SKILL.md"}, {"filename": "README.md"}],
                    )
                ]
            },
            # OLD predates the pin, so it is in the path's history but not new.
            commits_key("a/b", "skills/x"): history(NEW, OLD),
        },
    )
    assert result.returncode == EXIT_OK
    out = result.stdout
    assert "⚠ a/b: 1 of 2 new commits on main touches a vendored skill" in out
    assert f"· {NEW[:7]} fix x prompt" in out
    assert OLD[:7] not in out and OTHER[:7] not in out
    assert f"https://github.com/a/b/compare/{PIN[:7]}...main" in out
    assert not any("skills%2Fz" in r for r in result.requests), "skills/z was not touched"
    assert "✨ 1 of 1 upstream with changes to review" in out


def test_a_rename_out_of_a_vendored_path_counts_as_touching_it(run):
    result = run(
        {"a/b": upstream("skills/x")},
        {
            compare_key("a/b"): {
                "pages": [
                    compare_page(
                        ahead=1,
                        commits=[(NEW, "move x")],
                        files=[{"filename": "archive/x/SKILL.md", "previous_filename": "skills/x/SKILL.md"}],
                    )
                ]
            },
            commits_key("a/b", "skills/x"): history(NEW),
        },
    )
    assert f"· {NEW[:7]} move x" in result.stdout


def test_a_truncated_file_list_queries_every_vendored_path(run):
    files = [{"filename": f"other/{n}"} for n in range(300)]
    result = run(
        {"a/b": upstream("skills/x", "skills/z")},
        {
            compare_key("a/b"): {"pages": [compare_page(ahead=1, commits=[(NEW, "big")], files=files)]},
            commits_key("a/b", "skills/x"): history(),
            commits_key("a/b", "skills/z"): history(NEW),
        },
    )
    assert result.returncode == EXIT_OK
    assert "1 of 1 new commit on main touches a vendored skill" in result.stdout
    assert f"· {NEW[:7]} big" in result.stdout
    assert len(result.requests) == 3


def test_commits_on_later_compare_pages_are_still_considered(run):
    result = run(
        {"a/b": upstream("skills/x")},
        {
            compare_key("a/b"): {
                "pages": [
                    compare_page(ahead=2, commits=[(OTHER, "first")], files=[{"filename": "skills/x/a"}]),
                    {"commits": [{"sha": NEW, "commit": {"message": "second"}}]},
                ]
            },
            commits_key("a/b", "skills/x"): history(NEW),
        },
    )
    assert f"· {NEW[:7]} second" in result.stdout


def test_a_pin_that_left_the_branch_is_a_warning(run):
    result = run(
        {"a/b": upstream("skills/x")},
        {compare_key("a/b"): {"pages": [compare_page(behind=3)]}},
    )
    assert "⚠ a/b: the pinned commit is not on main" in result.stdout
    assert "up to date" not in result.stdout


def test_the_tracked_branch_comes_from_the_registry_and_a_trailing_slash_is_dropped(run):
    result = run(
        {"cursor/plugins/": upstream("skills/x", branch="dev")},
        {compare_key("cursor/plugins", "dev"): {"pages": [compare_page()]}},
    )
    assert result.returncode == EXIT_OK
    assert "✓ cursor/plugins: up to date with dev" in result.stdout


def test_an_upstream_without_a_commit_is_skipped_without_a_request(run):
    result = run(
        {"a/b": upstream("skills/x"), "c/d": upstream("skills/y", pin=None)},
        {compare_key("a/b"): {"pages": [compare_page()]}},
    )
    assert result.returncode == EXIT_OK
    assert "⚠ c/d: is not pinned to a commit, skipped" in result.stdout
    assert result.requests == [f"{compare_key('a/b')}?per_page=100"]


def test_an_upstream_without_a_branch_is_skipped_without_a_request(run):
    result = run({"a/b": upstream("skills/x", branch=None)}, {})
    assert result.returncode == EXIT_OK
    assert "⚠ a/b: names no branch, skipped" in result.stdout
    assert result.requests == []


def test_a_failed_request_fails_that_upstream_and_the_run_but_not_the_others(run):
    result = run(
        {"a/b": upstream("skills/x"), "c/d": upstream("skills/y")},
        {
            compare_key("a/b"): {"error": "gh: No commit found for SHA (HTTP 404)"},
            compare_key("c/d"): {"pages": [compare_page()]},
        },
    )
    assert result.returncode == EXIT_FAILED
    assert "✗ a/b: gh: No commit found for SHA (HTTP 404)" in result.stderr
    assert "✓ c/d: up to date with main" in result.stdout
    assert "1 failed" in result.stdout
    lines = result.merged.splitlines()
    assert lines.index("🔄 Upstream skill drift") < lines.index(
        "✗ a/b: gh: No commit found for SHA (HTTP 404)"
    ), "a failure must print under the title, in registry order"


def test_a_commit_that_is_not_a_full_sha_is_skipped(run):
    result = run({"a/b": upstream("skills/x", pin=PIN[:SHORT])}, {})
    assert result.returncode == EXIT_OK
    assert "⚠ a/b: is not pinned to a commit, skipped" in result.stdout
    assert result.requests == []


def test_every_shipped_upstream_names_a_branch_and_a_full_sha_commit(run):
    result = run({}, {"*": {"pages": [compare_page()]}}, registry=SKILL_REGISTRY)
    assert result.returncode == EXIT_OK, result.stderr
    assert "✗" not in result.stdout + result.stderr
    assert "skipped" not in result.stdout
    upstreams = json.loads(SKILL_REGISTRY.read_text())["upstream"]
    assert len(result.requests) == len(upstreams)
