"""Pi's skill discovery, run for real, because the whole `.agents/skills` link rests on it.

`claude_kit.pi` links one directory and claims that pi then sees every skill a project
installed. Three facts have to hold for that to be true, and all three live in pi's code
rather than ours:

  - a symlinked skill *directory* is followed, so a tree of absolute links into this
    checkout scans as though the skills were copied there
  - a directory with no `SKILL.md` is recursed into, so a seat plugin arrives whole and
    its bundled skill is found nested two levels down
  - the chain survives being entered through a symlink itself, since `.agents/skills` is
    a link to `.claude/skills`, whose entries are links in turn

None of that is guaranteed by the Agent Skills standard, and a version of pi that stopped
doing any of it would break this silently: the link stays valid, `add` still reports
success, and the skills simply do not exist in pi. There is no error to notice.

So this drives `loadSkillsFromDir` out of the installed pi package directly. That costs a
node process and no API call, and it is the only way to answer a question about someone
else's loader. It skips rather than fails when pi is absent, because pi is installed by
the same role these tests cover and `make test` promises to run with nothing configured.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import CLAUDE

# A plain skill and a seat plugin: the two shapes a project's .claude/skills/ holds, and
# the second is the one with a nested SKILL.md that only recursion finds.
SKILL = "coderabbit"
PLUGIN = "backend"
PLUGIN_SKILL = "backend-failure-modes"

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
    """A project as `claude-kit add` leaves it, plus the link `pi.converge` makes.

    Built by hand rather than by calling claude-kit, so a change in this module's
    verdict is a change in pi and never in ours.
    """
    leaf = tmp_path / "proj" / ".claude" / "skills"
    leaf.mkdir(parents=True)
    (leaf / SKILL).symlink_to(CLAUDE / "skills" / SKILL)
    (leaf / PLUGIN).symlink_to(CLAUDE / "plugins" / PLUGIN)
    agents = tmp_path / "proj" / ".agents"
    agents.mkdir()
    (agents / "skills").symlink_to(Path("..") / ".claude" / "skills")
    return tmp_path / "proj"


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


def test_pi_reads_a_project_through_the_agents_link(loader, project):
    found = discover(loader, project / ".agents" / "skills")
    assert SKILL in found["names"]


def test_a_bundled_plugin_skill_is_found_by_recursion(loader, project):
    """The plugin is one symlink and its skill is two directories inside it. This is the
    fact that decides whether a seat is usable in pi at all."""
    found = discover(loader, project / ".agents" / "skills")
    assert PLUGIN_SKILL in found["names"]


def test_the_scan_is_clean(loader, project):
    """No warnings, which matters because pi prints its diagnostics at startup: a link
    that works but complains every launch is one the user will delete."""
    assert discover(loader, project / ".agents" / "skills")["diagnostics"] == []


def test_a_plugins_agent_is_not_mistaken_for_a_skill(loader, project):
    """A seat bundles `agents/<name>.md`, and pi's skill loader must not read it as a
    skill: agents are pi-subagents' business, reached through `.agents/agents/`, never
    through a skills scan. A loose .md only counts at the root of a scanned path, so
    the file is ignored rather than loaded as a skill named after the seat."""
    names = discover(loader, project / ".agents" / "skills")["names"]
    assert f"{PLUGIN}-staff-engineer" not in names


def test_a_broken_link_is_skipped_rather_than_fatal(loader, project):
    """Every link in .claude/skills/ is absolute into this checkout, so a moved or
    renamed artifact leaves one dangling. It must cost the other skills nothing."""
    (project / ".claude" / "skills" / "gone").symlink_to(CLAUDE / "skills" / "not-a-skill")
    found = discover(loader, project / ".agents" / "skills")
    assert SKILL in found["names"]
