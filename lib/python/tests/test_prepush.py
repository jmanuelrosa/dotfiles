"""bin/prepush: a push that only deletes runs nothing, and one failing check stops the push.

Nothing here reads the repository's history, because CI checks out a single commit.
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
