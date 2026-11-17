"""bin/prepush: which commits the secret scan covers, and that a failing check stops the push.

The range logic is the part a green run cannot vouch for: a range that matches nothing
scans nothing, and gitleaks reports that as a clean pass.
"""

import io
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader

import pytest
from dotkit.testing import REPO

NULL = "0" * 40


def load():
    loader = SourceFileLoader("prepush", str(REPO / "bin/prepush"))
    module = module_from_spec(spec_from_loader("prepush", loader))
    loader.exec_module(module)
    return module


prepush = load()


def rev(name):
    return subprocess.run(
        ["git", "rev-parse", name], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_an_updated_branch_scans_only_the_new_commits():
    head, base = rev("HEAD"), rev("HEAD~1")
    assert prepush.pushed_ranges([f"refs/heads/b {head} refs/heads/b {base}"]) == [[f"{base}..{head}"]]


def test_a_new_branch_scans_every_commit_no_remote_has():
    head = rev("HEAD")
    assert prepush.pushed_ranges([f"refs/heads/b {head} refs/heads/b {NULL}"]) == [[head, "--not", "--remotes"]]


def test_a_remote_tip_never_fetched_falls_back_to_unpushed_commits():
    head, unseen = rev("HEAD"), "f" * 40
    assert prepush.pushed_ranges([f"refs/heads/b {head} refs/heads/b {unseen}"]) == [[head, "--not", "--remotes"]]


def test_a_push_that_only_deletes_checks_nothing(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"(delete) {NULL} refs/heads/b {rev('HEAD')}\n"))
    monkeypatch.setattr(prepush, "checks", lambda *_: pytest.fail("a deletion ran the checks"))
    assert prepush.main() == 0


def test_one_failing_check_blocks_the_push_and_shows_its_output(monkeypatch, capsys, tmp_path):
    head = rev("HEAD")
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"refs/heads/b {head} refs/heads/b {NULL}\n"))
    monkeypatch.setattr(prepush, "REQUIRED", ())
    monkeypatch.setattr(prepush, "SCRATCH", tmp_path)
    monkeypatch.setattr(prepush, "pinned_catalog", lambda: tmp_path)
    monkeypatch.setattr(prepush, "checks", lambda _ranges, env: [
        ("passes", ["true"], env),
        ("fails", ["sh", "-c", "echo broken-marker; exit 3"], env),
    ])
    assert prepush.main() == 1
    out = capsys.readouterr()
    assert "broken-marker" in out.out
    assert "fails" in out.err
