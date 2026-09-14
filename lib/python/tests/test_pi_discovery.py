"""Pi's native skill discovery, run for real against Kura's independent view.

Kura 0.3 gives Pi its own `.agents/skills` directory with one direct catalog link per
skill. Pi must follow those linked directories and skip a dangling entry without losing
the healthy set. Neither fact is guaranteed by the Agent Skills standard, so this drives
`loadSkillsFromDir` from the installed Pi package rather than duplicating its scanner.

The test skips when Pi is absent because Pi is installed by the role this suite covers
and `make test` remains the unattended target on an unprovisioned machine.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import CLAUDE

SKILL = "coderabbit"

LOADER = "dist/core/skills.js"


def pi_loader():
    """The installed pi package's skill loader, or None.

    Found through the `pi` on PATH rather than by pinning a Homebrew cellar path, so a
    version bump or an npm install is followed rather than reported as missing.
    """
    binary = shutil.which("pi")
    if binary is None:
        return None
    root = Path(binary).resolve().parent.parent
    for candidate in (
        root / "lib/node_modules/@earendil-works/pi-coding-agent" / LOADER,
        root / "libexec/lib/node_modules/@earendil-works/pi-coding-agent" / LOADER,
    ):
        if candidate.is_file():
            return candidate
    return None


@pytest.fixture(scope="module")
def loader():
    found = pi_loader()
    if found is None or shutil.which("node") is None:
        pytest.skip("pi and node are needed to exercise pi's own skill loader")
    return found


@pytest.fixture
def project(tmp_path):
    """A Pi project view as Kura 0.3 leaves it, built without calling Kura."""
    project = tmp_path / "proj"
    leaf = project / ".agents" / "skills"
    leaf.mkdir(parents=True)
    (leaf / SKILL).symlink_to(CLAUDE / "skills" / SKILL)
    return project


def discover(loader, directory):
    """What pi loads from `directory`, as {name: path} plus its diagnostics."""
    script = f"""
    import {{ loadSkillsFromDir }} from {json.dumps(str(loader))};
    const r = loadSkillsFromDir({{ dir: {json.dumps(str(directory))}, source: "project" }});
    process.stdout.write(JSON.stringify({{
        names: r.skills.map((s) => s.name).sort(),
        diagnostics: r.diagnostics ?? [],
    }}));
    """
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_pi_reads_a_direct_catalog_link_from_its_native_root(loader, project):
    found = discover(loader, project / ".agents" / "skills")
    assert SKILL in found["names"]


def test_the_scan_is_clean(loader, project):
    """No warnings, which matters because pi prints its diagnostics at startup: a link
    that works but complains every launch is one the user will delete."""
    assert discover(loader, project / ".agents" / "skills")["diagnostics"] == []


def test_a_broken_link_is_skipped_rather_than_fatal(loader, project):
    """A renamed catalog skill can leave one dangling link without hiding its peers."""
    (project / ".agents" / "skills" / "gone").symlink_to(
        CLAUDE / "skills" / "not-a-skill"
    )
    found = discover(loader, project / ".agents" / "skills")
    assert SKILL in found["names"]
