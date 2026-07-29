"""How claude-kit reaches the machine.

The `ai` role globs files/scripts/* and symlinks each match into ~/.local/bin/, so
anything dropped in that directory lands on PATH. These guard the deployment shape
rather than the tool's behaviour.
"""

import os
import stat
import subprocess

import yaml

from conftest import PACKAGE, REPO, SCRIPTS, SHIM, subparsers

AI_TASKS = REPO / "roles/ai/tasks/main.yml"

LINK_TASK = "Link AI scripts into the user bin directory"


def scripts_task():
    tasks = yaml.safe_load(AI_TASKS.read_text())
    matching = [t for t in tasks if t.get("name") == LINK_TASK]
    assert len(matching) == 1, f"expected exactly one '{LINK_TASK}' task"
    return matching[0]


def test_the_shim_is_executable():
    """It is symlinked onto PATH, so a lost +x makes claude-kit unrunnable."""
    assert SHIM.stat().st_mode & stat.S_IXUSR


def test_every_non_doc_file_in_scripts_is_executable():
    """The glob puts each of these on PATH, so a non-executable one is a broken
    command rather than a harmless file.

    Directories are skipped because the fileglob lookup skips them too: it filters its
    matches through os.path.isfile, which is what lets the claude_kit package sit in
    this directory without the `when` guard having to name it.
    """
    for entry in sorted(SCRIPTS.iterdir()):
        if entry.is_dir() or entry.suffix == ".md" or entry.name.startswith("."):
            continue
        assert entry.stat().st_mode & stat.S_IXUSR, f"{entry.name} is on PATH but not executable"


def test_documentation_is_excluded_from_the_bin_symlinks():
    """Without this guard the README becomes ~/.local/bin/README.md.

    The glob cannot express an exclusion, so the task carries a `when`. Pinned here
    because the failure is silent: the playbook succeeds and PATH quietly gains a
    markdown file.
    """
    assert (SCRIPTS / "README.md").is_file(), "the README should live beside the script"
    when = scripts_task().get("when")
    assert when, f"'{LINK_TASK}' must skip documentation"
    assert ".md" in when, f"the guard should exclude markdown, got: {when}"


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
    sibling of the shim. Move one without the other and claude-kit stops importing."""
    assert (PACKAGE / "__init__.py").is_file()
    assert PACKAGE.parent == SCRIPTS == SHIM.parent


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


def test_the_tests_live_inside_the_package():
    """Beside the code they exercise, and with no __init__.py.

    pytest walks up from a test module while it keeps finding __init__.py to decide the
    module name. Adding one here would make it walk into claude_kit/ and import the
    tests as claude_kit.tests.*, at which point `from conftest import ...` breaks.
    """
    tests = PACKAGE / "tests"
    assert tests.is_dir()
    assert (tests / "conftest.py").is_file()
    assert not (tests / "__init__.py").exists(), "an __init__.py here breaks conftest imports"


def test_every_command_and_flag_is_documented():
    """The README is the reference, so a new flag shipping undocumented is a defect.

    Read from the parser rather than from `--help` output so this needs no subprocess
    and cannot drift from what argparse actually accepts.
    """
    readme = (SCRIPTS / "README.md").read_text()

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

    readme = (SCRIPTS / "README.md").read_text()
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
