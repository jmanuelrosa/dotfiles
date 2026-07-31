"""How claude-kit reaches the machine.

The `ai` role names its tools in AI_SCRIPTS and symlinks files/scripts/<name>/<name>
into ~/.local/bin/ for each. These guard the deployment shape rather than the tool's
behaviour: one directory per tool, the executable named after its directory, and every
directory accounted for in the manifest.
"""

import os
import stat
import subprocess

import pytest
import yaml

from dotkit.testing import REPO
from kit_helpers import PACKAGE, SCRIPTS, SHIM, TOOL, subparsers

AI_TASKS = REPO / "roles/ai/tasks/main.yml"

LINK_TASK = "Link AI scripts into the user bin directory"

# Both roles install scripts the same way, so the shape is checked for both here. The
# work role had no packaging test at all before, which is why its link task could sit
# next to a dead `Ensure scripts directory exists` creating a path nothing wrote to.
INSTALLERS = [
    ("ai", "AI_SCRIPTS", LINK_TASK),
    ("work", "WORK_SCRIPTS", "Link work scripts into the user bin directory"),
]


def role_task(role, name):
    tasks = yaml.safe_load((REPO / f"roles/{role}/tasks/main.yml").read_text())
    matching = [t for t in tasks if t.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the {role} role"
    return matching[0]


def scripts_task():
    return role_task("ai", LINK_TASK)


def role_manifest(role, var):
    return yaml.safe_load((REPO / f"roles/{role}/defaults/main.yml").read_text())[var]


def test_the_shim_is_executable():
    """It is symlinked onto PATH, so a lost +x makes claude-kit unrunnable."""
    assert SHIM.stat().st_mode & stat.S_IXUSR


@pytest.mark.parametrize(("role", "var", "task_name"), INSTALLERS)
def test_the_link_task_loops_the_manifest_with_an_absolute_source(role, var, task_name):
    """A relative src here is the silent failure worth pinning.

    ansible.builtin.file does not resolve src through the role search path the way copy
    and template do, and with force: true it skips the existence guard too. Drop
    role_path and the play still reports changed while ~/.local/bin/claude-kit is a
    dangling link.
    """
    task = role_task(role, task_name)
    assert task.get("loop") == "{{ %s }}" % var, "the task should loop the manifest"
    src = task["ansible.builtin.file"]["src"]
    assert "{{ role_path }}" in src, f"src must be absolute, got: {src}"
    assert "{{ item }}/{{ item }}" in src, f"src should be <name>/<name>, got: {src}"
    assert "when" not in task, "the manifest replaces the .md guard; nothing left to skip"
    assert "with_fileglob" not in task, "a glob would match only directories, which fileglob drops"


@pytest.mark.parametrize(("role", "var", "task_name"), INSTALLERS)
def test_every_tool_directory_is_in_the_manifest(role, var, task_name):
    """A tool absent from AI_SCRIPTS is simply never installed, and nothing says so.

    The glob this replaced had the opposite failure, installing whatever was dropped in
    the directory. Both are silent, so the manifest and the directory are pinned to
    each other.
    """
    scripts = REPO / f"roles/{role}/files/scripts"
    on_disk = {
        entry.name
        for entry in scripts.iterdir()
        if entry.is_dir() and not entry.is_symlink() and not entry.name.startswith(".")
    }
    declared = set(role_manifest(role, var))
    assert on_disk == declared, (
        f"{role} tool directories {sorted(on_disk)} do not match {var} {sorted(declared)}"
    )


@pytest.mark.parametrize(("role", "var", "task_name"), INSTALLERS)
def test_every_tool_ships_an_executable_named_after_its_directory(role, var, task_name):
    """The convention the one-line loop depends on: files/scripts/<name>/<name>."""
    for name in role_manifest(role, var):
        executable = REPO / f"roles/{role}/files/scripts" / name / name
        assert executable.is_file(), f"{name}/ has no executable named {name}"
        assert executable.stat().st_mode & stat.S_IXUSR, f"{name}/{name} is on PATH but not +x"


def test_the_readme_lives_beside_the_tool_it_documents():
    """No `when` guard needed any more: a file inside a tool directory is not on PATH,
    because only <name>/<name> is linked."""
    assert (TOOL / "README.md").is_file()


def test_the_shim_stays_thin():
    """Logic belongs in the importable package. An extensionless executable cannot be
    imported, so anything that grows here is code the fast tests cannot reach."""
    body = [
        line
        for line in SHIM.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code = [line for line in body if not line.strip().startswith(('"""', "'''"))]
    assert len(code) < 20, f"the shim has grown to {len(code)} lines; move logic into claude_kit/"


def test_the_package_is_importable_from_beside_the_shim():
    """The shim inserts its own directory on sys.path, so the package has to be a
    sibling of the shim. Move one without the other and claude-kit stops importing.

    PACKAGE comes from the suite's own location and SHIM from the repo anchor, so this
    compares two independent derivations rather than restating one.
    """
    assert (PACKAGE / "__init__.py").is_file()
    assert PACKAGE.parent == TOOL == SHIM.parent
    assert TOOL.parent == SCRIPTS


def test_the_shim_finds_the_package_with_the_implicit_path_entry_suppressed(tmp_path):
    """The only invocation that actually exercises the shim's sys.path insert.

    CPython already resolves a symlinked script before deriving sys.path[0], so running
    through ~/.local/bin/claude-kit lands the real scripts directory there and the
    package imports whether or not the shim inserts anything. PYTHONSAFEPATH suppresses
    that implicit entry, which is what makes the insert load-bearing and is the only
    condition under which a wrong one is observable: a stale `.parent.parent` pointing at
    roles/ai/files/ passes every other subprocess test in this suite.

    Run through a symlink as well, since that is how the ai role deploys it.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    link = bin_dir / "claude-kit"
    link.symlink_to(SHIM)

    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    env = {
        **os.environ,
        "HOME": str(home),
        "DOTFILES_DIR": str(REPO),
        "PYTHONSAFEPATH": "1",
    }
    env.pop("XDG_CONFIG_HOME", None)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [str(link), "list", "--type", "plugin"],
        cwd=str(home),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Available plugins:" in result.stdout


def test_the_tests_live_beside_the_package():
    """Inside the tool directory, and with no __init__.py.

    Every suite directory in this repo is named `tests`, and an __init__.py in any of
    them makes pytest name its modules `tests.test_x`. sys.modules['tests'] is then
    claimed by whichever suite loads first and the others resolve against the wrong
    package, with nothing reporting it as a collision.

    A second reason applies here specifically: the tool directory is `claude-kit`, and
    "claude-kit".isidentifier() is False, so the walk could not produce a usable module
    name from it even if the collision did not exist.
    """
    tests = TOOL / "tests"
    assert tests.is_dir()
    assert (tests / "conftest.py").is_file()
    assert not (tests / "__init__.py").exists(), "an __init__.py here collides across suites"


def test_every_command_and_flag_is_documented():
    """The README is the reference, so a new flag shipping undocumented is a defect.

    Read from the parser rather than from `--help` output so this needs no subprocess
    and cannot drift from what argparse actually accepts.
    """
    readme = (TOOL / "README.md").read_text()

    commands = subparsers()
    assert commands, "expected a subcommand parser"

    undocumented = []
    for command, parser in commands.items():
        if f"`{command}`" not in readme:
            undocumented.append(f"command {command}")
        for action in parser._actions:
            for flag in action.option_strings:
                if flag in ("-h", "--help"):
                    continue
                # Backtick then the flag, so `--group GROUP` counts alongside
                # `--group`. Requiring a closing backtick would reject documenting a
                # flag together with its metavariable, which reads better.
                if f"`{flag}" not in readme:
                    undocumented.append(f"{command} {flag}")
    assert undocumented == [], "undocumented in README.md: " + ", ".join(undocumented)


def test_every_exit_code_is_documented():
    """Callers branch on these, so the table has to stay complete."""
    from claude_kit import errors

    readme = (TOOL / "README.md").read_text()
    missing = [name for name in errors.NAMES.values() if f"`{name}`" not in readme]
    assert missing == [], f"exit codes absent from README.md: {missing}"


def test_the_runtime_imports_only_the_standard_library():
    """PyYAML is a test dependency. A runtime import of it, or of anything else
    third-party, would break claude-kit on a machine that only has python3.

    There is no exemption. checks.py held the last one until the frontmatter scanner
    replaced it, and that import is what made G8 skip itself on a real machine.

    tests/ is skipped: it lives inside the package but is never imported at runtime, and
    it imports pytest and PyYAML by design.
    """
    third_party = {"yaml", "requests", "jinja2", "pytest"}
    offenders = []
    for module in sorted(PACKAGE.rglob("*.py")):
        if module.is_relative_to(PACKAGE / "tests"):
            continue
        for number, line in enumerate(module.read_text().splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith(("import ", "from ")):
                continue
            root = stripped.split()[1].split(".")[0]
            if root not in third_party:
                continue
            offenders.append(f"{module.relative_to(PACKAGE)}:{number}: {stripped}")
    assert offenders == [], "third-party imports at runtime: " + "; ".join(offenders)
