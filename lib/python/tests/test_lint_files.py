"""bin/lint-files: which tracked files each linter in `make lint-static` sees.

Every mistake here is silent: a file routed to the wrong language is never linted at all.
"""

import subprocess
from pathlib import Path

import pytest
from dotkit.testing import HARNESS, REPO

LINT_FILES = REPO / "bin/lint-files"


def files(language):
    result = subprocess.run([LINT_FILES, language], cwd=REPO, capture_output=True, text=True, check=True)
    return {Path(line) for line in result.stdout.splitlines()}


def test_shebang_wins_over_extension():
    hook = (HARNESS / "hooks/git-skill-gate.sh").relative_to(REPO)
    assert hook in files("python")
    assert hook not in files("shell")


def test_extensionless_scripts_are_found_by_shebang():
    assert Path("roles/work/files/scripts/s-task/s-task") in files("fish")


def tracked_ignored():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--ignored", "--exclude-standard"],
        cwd=REPO, capture_output=True, text=True, check=True,
    )
    return {Path(line) for line in result.stdout.splitlines()}


def test_git_ignored_tracked_files_are_skipped():
    ignored = tracked_ignored()
    if not ignored:
        pytest.skip("no tracked file is git-ignored")
    leaked = sorted(ignored & files("markdown"))
    assert not leaked, f"git-ignored files reached the markdown linter: {leaked}"
