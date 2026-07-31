"""The suite layout itself, asserted.

Tests here guard the collection mechanics rather than any script's behaviour. They
exist because the failure they catch is silent in both directions: a suite reached by
no `testpaths` entry does not run and reports nothing, and a module imported under a
name another directory also claims binds to the wrong file without complaint.

Both happened. Commit 7d66f96 deleted `tests/conftest.py` while moving claude-kit's
suite into the package, and `make test` named the new path explicitly. Four suites
(coderabbit, pr, jira-adf, git-skill-gate) plus weekly-recap went dark for two
commits: 2,174 lines that CI reported as passing because CI never collected them.
Running both roots together showed the second failure on top of the first, with four
of the five silently binding `REPO` off claude-kit's conftest.
"""

import configparser
import json

import pytest
from dotkit.testing import REPO, SKILL_REGISTRY, SKILLS

PYTEST_INI = REPO / "pytest.ini"

# A directory holding a suite, by family. Globs rather than a literal list, so a new
# tool or a newly tested skill is discovered and then checked against pytest.ini.
SUITE_GLOBS = (
    "roles/*/files/scripts/*/tests",
    "roles/*/files/claude/hooks/tests",
    "lib/python/tests",
    "tests",
)


def configured_testpaths():
    """The `testpaths` entries from pytest.ini, as absolute paths."""
    parser = configparser.ConfigParser()
    parser.read(PYTEST_INI)
    raw = parser.get("pytest", "testpaths")
    return [REPO / entry for entry in raw.split()]


def local_skill_names():
    """Skills authored here, as opposed to synced from an upstream repo.

    Only these may hold a `tests/` directory. An upstream skill's tree is replaced
    wholesale by `claude-kit update` (upstream.copy_tree swaps the directory and
    preserves nothing), so a suite added under one would be deleted on the next sync
    and would read as permanently `behind` until then.
    """
    registry = json.loads(SKILL_REGISTRY.read_text())
    return sorted(entry["name"] for entry in registry.get("local_skills", []))


def discovered_suites():
    found = set()
    for pattern in SUITE_GLOBS:
        found |= {path for path in REPO.glob(pattern) if path.is_dir()}
    for name in local_skill_names():
        candidate = SKILLS / name / "tests"
        if candidate.is_dir():
            found.add(candidate)
    return found


def suite_modules():
    """Every .py under a configured suite directory, as (basename, path)."""
    for directory in configured_testpaths():
        if not directory.is_dir():
            continue
        for module in sorted(directory.rglob("*.py")):
            if "__pycache__" in module.parts:
                continue
            yield module.name, module


def test_every_configured_testpath_exists():
    """pytest only *warns* on a path that collects nothing.

    So a typo, or a suite that moved without its entry being updated, reads exactly
    like a suite with no failures. That is the shape of the original outage.
    """
    missing = [str(path.relative_to(REPO)) for path in configured_testpaths() if not path.is_dir()]
    assert missing == [], f"testpaths entries that do not exist: {missing}"


def test_no_suite_directory_is_left_uncollected():
    """A suite nobody runs is worse than no suite: it reports success.

    Discovery is scoped to the families that may legitimately hold one, rather than
    walking the repo, so an upstream skill that one day ships its own `tests/` cannot
    turn this red on an unrelated `claude-kit update`.
    """
    configured = set(configured_testpaths())
    orphaned = sorted(
        str(path.relative_to(REPO)) for path in discovered_suites() if path not in configured
    )
    assert orphaned == [], "suite directories missing from pytest.ini testpaths: " + ", ".join(
        orphaned
    )


def test_no_module_imports_conftest():
    """`conftest` is not a unique name, so importing it binds to the wrong file.

    In prepend import mode a conftest.py in a directory with no __init__.py is named
    literally `conftest`. pytest copes, because it keys its own registry by path and
    clears sys.modules before each load. A test module doing `from conftest import X`
    does not: it hits whatever sys.modules holds, which is whichever suite loaded last.

    Shared paths come from dotkit.testing; a suite's own helpers come from a module
    named so no other directory can claim it, which the next test enforces.
    """
    offenders = []
    for _, module in suite_modules():
        for number, line in enumerate(module.read_text().splitlines(), 1):
            # Column zero only: an import statement is never indented here, and prose
            # in a docstring that names the idiom is not an instance of it.
            if line.startswith(("from conftest import", "import conftest")):
                offenders.append(f"{module.relative_to(REPO)}:{number}")
    assert offenders == [], "modules importing conftest: " + ", ".join(offenders)


def test_suite_module_basenames_are_unique():
    """Every suite directory ends up on sys.path, so a basename is a global name.

    Two test modules sharing one is the loud version, an ImportPathMismatchError from
    pytest's own importer. Two *helper* modules sharing one is the quiet version, and
    the same bug as importing conftest. conftest.py is exempt: pytest special-cases it.
    """
    seen = {}
    collisions = []
    for name, module in suite_modules():
        if name == "conftest.py":
            continue
        if name in seen:
            collisions.append(f"{name}: {seen[name]} and {module.relative_to(REPO)}")
        else:
            seen[name] = module.relative_to(REPO)
    assert collisions == [], "duplicate module basenames across suites: " + "; ".join(collisions)


@pytest.mark.parametrize("name", ["ui", "colors"])
def test_dotkit_stays_stdlib_only(name):
    """Tools import dotkit from ~/.local/bin on a machine that may have only python3.

    Parametrised over the modules that are moving in here, so the check is already in
    place when they arrive rather than being remembered afterwards.
    """
    module = REPO / "lib/python/dotkit" / f"{name}.py"
    if not module.exists():
        pytest.skip(f"dotkit/{name}.py has not moved here yet")
    third_party = {"yaml", "requests", "jinja2", "pytest"}
    offenders = []
    for number, line in enumerate(module.read_text().splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            continue
        if stripped.split()[1].split(".")[0] in third_party:
            offenders.append(f"{module.name}:{number}: {stripped}")
    assert offenders == [], "third-party imports in dotkit: " + "; ".join(offenders)


def test_the_repo_anchor_resolves():
    """REPO is derived through resolve(), so it must hold however dotkit was reached.

    In PR B each tool reaches this package through a committed symlink beside its
    executable. If anything here ever compares an unresolved path, that is where it
    breaks, and it breaks per import site rather than everywhere at once.
    """
    assert (REPO / "dotfiles.yml").is_file(), f"REPO does not look like the checkout: {REPO}"


# --- the dotkit symlinks -----------------------------------------------------


def dotkit_links():
    """Every `dotkit` entry in the repo that is a symlink rather than the real thing."""
    return sorted(
        path
        for path in REPO.glob("roles/*/files/scripts/**/dotkit")
        if path.is_symlink()
    )


def test_every_dotkit_link_resolves_to_the_one_real_copy():
    """These are the first committed symlinks in this repo, so they get a check.

    A clone with core.symlinks=false materialises a symlink as a regular file holding
    its target path, and the failure that follows is an ImportError deep in a tool with
    nothing pointing at the cause. Better to say so here.

    Relative targets on purpose: an absolute one would bake this checkout's path in and
    break every other clone.
    """
    real = REPO / "lib/python/dotkit"
    assert real.is_dir() and not real.is_symlink(), "lib/python/dotkit should be the real package"

    links = dotkit_links()
    assert links, "no dotkit symlink found; a python tool needing the vocabulary cannot import it"
    for link in links:
        target = link.readlink()
        assert not target.is_absolute(), f"{link.relative_to(REPO)} -> {target} must be relative"
        assert link.resolve() == real.resolve(), (
            f"{link.relative_to(REPO)} resolves to {link.resolve()}, not {real}"
        )


def test_a_dotkit_link_sits_beside_the_tool_that_imports_it():
    """The runtime contract: a tool inserts its own directory, so dotkit must be in it.

    Checked per link rather than per tool, because the link is the thing that has to be
    in the right place; a tool with no link simply does not import dotkit.
    """
    for link in dotkit_links():
        siblings = {entry.name for entry in link.parent.iterdir()}
        executables = {
            entry.name
            for entry in link.parent.iterdir()
            if entry.is_file() and entry.stat().st_mode & 0o100
        }
        assert executables or "claude_kit" in siblings, (
            f"{link.relative_to(REPO)} sits beside no executable and no package, "
            "so nothing there can import it"
        )
