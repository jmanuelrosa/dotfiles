"""bin/lint-files: which tracked files each linter in `make lint-static` sees.

Every mistake here is silent. A file routed to the wrong language is never linted at all,
and an upstream entry that slips through fails CI on code `kura update` will overwrite.
"""

import json
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import CATALOG, HARNESS, REPO

LINT_FILES = REPO / "bin/lint-files"


def files(language):
    result = subprocess.run([LINT_FILES, language], cwd=REPO, capture_output=True, text=True, check=True)
    return {Path(line) for line in result.stdout.splitlines()}


def upstream_skills():
    registry = json.loads((CATALOG / "skill-registry.json").read_text())
    for source in registry["upstream"].values():
        for entry in source["skills"]:
            yield entry.get("name") or Path(entry["upstream_path"]).name


def test_shebang_wins_over_extension():
    hook = (HARNESS / "hooks/git-skill-gate.sh").relative_to(REPO)
    assert hook in files("python")
    assert hook not in files("shell")


def test_extensionless_scripts_are_found_by_shebang():
    assert Path("roles/work/files/scripts/s-task/s-task") in files("fish")


@pytest.mark.parametrize("language", ["markdown", "python", "shell", "fish"])
def test_upstream_skills_are_never_linted(language):
    upstream = {(CATALOG / "skills" / name).relative_to(REPO) for name in upstream_skills()}
    leaked = [path for path in files(language) if upstream & set(path.parents)]
    assert not leaked, f"upstream files reached the {language} linter: {leaked}"


def test_git_ignored_tracked_files_are_skipped():
    ignored = Path("docs/research/subagent-plugin-structure.md")
    assert (REPO / ignored).exists()
    assert ignored not in files("markdown")


def test_local_skills_are_linted():
    registry = json.loads((CATALOG / "skill-registry.json").read_text())
    local = registry["local"][0]["name"]
    assert (CATALOG / "skills" / local / "SKILL.md").relative_to(REPO) in files("markdown")
