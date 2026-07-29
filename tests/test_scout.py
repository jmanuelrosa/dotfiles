"""`claude-kit scout` ranks catalogue skills against the current project.

Cases assert on which report section a skill lands in and on exit codes, never on
refusal wording, so the report can be reworded without touching the suite.
"""

import json
import re

import pytest

from conftest import CLAUDE, EXIT_NO_PROJECT, EXIT_OK

# Fixture skills, chosen once so the cases read concretely. The guard below fails
# loudly if a registry edit invalidates a choice, which beats a test that
# silently starts exercising the wrong branch.
A_REACT_SKILL = "react-best-practices"
AN_ASTRO_SKILL = "astro"
A_TESTING_SKILL = "test-driven-development"
A_DEPENDENCY_ONLY_SKILL = "grilling"

SECTIONS = {
    "STRONG MATCH": "strong",
    "WORTH CONSIDERING": "consider",
    "ALREADY IN THIS PROJECT (skipped)": "already",
}
ENTRY = re.compile(r"^\s*(?:\d+\.|✓)\s+(\S+)")

# Only the tags each case actually depends on, so an unrelated retag stays quiet.
REQUIRED_TAGS = {
    A_REACT_SKILL: "react",
    AN_ASTRO_SKILL: "astro",
    A_TESTING_SKILL: "testing",
}


@pytest.fixture(scope="module", autouse=True)
def _fixture_skills_still_valid(skills):
    by_name = {name: entry for name, entry, _ in skills}
    for name, tag in REQUIRED_TAGS.items():
        assert tag in by_name[name]["groups"], f"{name} no longer carries {tag}"
        assert "global" not in by_name[name]["groups"], f"{name} became global"
    assert by_name[A_DEPENDENCY_ONLY_SKILL].get("dependency_only") is True
    # test-driven-development must stay free of framework tags, or the
    # competing-tech guard filters it out of a project that does not use them.
    assert not {"react", "astro", "swift", "expo"} & set(by_name[A_TESTING_SKILL]["groups"])


def report(stdout):
    """The report split into {section: [skill names]}."""
    found = {key: [] for key in SECTIONS.values()}
    current = None
    for line in stdout.splitlines():
        if line.strip() in SECTIONS:
            current = SECTIONS[line.strip()]
            continue
        match = ENTRY.match(line)
        if match and current:
            found[current].append(match.group(1))
    return found


def js_project(project, **dependencies):
    (project / "package.json").write_text(json.dumps({"dependencies": dependencies}))
    return project


def link(directory, name):
    """Stand in for an installed artifact. scout only reads the entry's name."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).symlink_to(CLAUDE / "skills" / name)


def test_outside_a_git_repo_scout_refuses(kit, tmp_path):
    """Given no enclosing git repo, When scout runs, Then it refuses with EXIT_NO_PROJECT."""
    loose = tmp_path / "loose"
    loose.mkdir()
    result = kit("scout", cwd=loose)
    assert result.returncode == EXIT_NO_PROJECT


def test_a_react_dependency_makes_a_react_skill_a_strong_match(kit, git_project):
    """Given react in package.json, When scout runs, Then the react skill is a strong match."""
    result = kit("scout", cwd=js_project(git_project, react="19.0.0"))
    assert result.returncode == EXIT_OK
    assert A_REACT_SKILL in report(result.stdout)["strong"]


def test_the_evidence_for_a_strong_match_names_the_dependency(kit, git_project):
    """Given react in package.json, When scout runs, Then the Why cites that dependency."""
    result = kit("scout", cwd=js_project(git_project, react="19.0.0"))
    assert "react@19.0.0 in package.json" in result.stdout


def test_a_framework_the_project_does_not_use_is_not_recommended(kit, git_project):
    """Given a react project, When scout runs, Then an astro skill is absent entirely.

    Both skills carry `frontend`, so without the competing-tech guard the implied
    frontend hit pulls astro into a project that has no astro.
    """
    result = kit("scout", cwd=js_project(git_project, react="19.0.0"))
    sections = report(result.stdout)
    assert AN_ASTRO_SKILL not in sections["strong"] + sections["consider"]


def test_a_globally_installed_skill_is_never_recommended(kit, git_project):
    """Given a skill linked in ~/.claude/skills, When scout runs, Then it is absent.

    It is already available everywhere, so offering it again is noise.
    """
    link(kit.home / ".claude" / "skills", A_REACT_SKILL)
    result = kit("scout", cwd=js_project(git_project, react="19.0.0"))
    sections = report(result.stdout)
    assert A_REACT_SKILL not in sections["strong"] + sections["consider"] + sections["already"]


def test_a_project_linked_skill_is_listed_but_never_offered(kit, git_project):
    """Given a skill already linked in the project, When scout runs, Then it is only listed."""
    project = js_project(git_project, react="19.0.0")
    link(project / ".claude" / "skills", A_REACT_SKILL)
    result = kit("scout", cwd=project)
    sections = report(result.stdout)
    assert A_REACT_SKILL in sections["already"]
    assert A_REACT_SKILL not in sections["strong"] + sections["consider"]


def test_a_dependency_only_skill_is_never_recommended(kit, git_project):
    """Given a dependency-only skill, When scout runs, Then it never appears."""
    result = kit("scout", cwd=js_project(git_project, react="19.0.0"))
    sections = report(result.stdout)
    assert A_DEPENDENCY_ONLY_SKILL not in sections["strong"] + sections["consider"]


def test_a_stack_the_catalogue_does_not_cover_still_gets_a_report(kit, git_project):
    """Given a project with no catalogue tech, When scout runs, Then the report is not empty.

    A Rust or Go repo has no tech match, and returning nothing is a worse answer
    than the stack-agnostic picks.
    """
    (git_project / "Cargo.toml").write_text("[package]\nname = 'x'\n")
    result = kit("scout", cwd=git_project)
    assert result.returncode == EXIT_OK
    sections = report(result.stdout)
    assert sections["strong"] + sections["consider"]


def test_the_stack_agnostic_fallback_is_never_claimed_as_strong(kit, git_project):
    """Given no tech evidence and no gaps either, When scout runs, Then the
    fallback picks land in the weaker tier and nothing is claimed as strong.

    Absence of tests or CI is real evidence and does rank strongly, so this case
    supplies all three to isolate the fallback from it.
    """
    (git_project / "Cargo.toml").write_text("[package]\nname = 'x'\n")
    (git_project / "tests").mkdir()
    (git_project / "docs").mkdir()
    (git_project / ".github" / "workflows").mkdir(parents=True)
    sections = report(kit("scout", cwd=git_project).stdout)
    assert sections["strong"] == []
    assert sections["consider"]


def test_a_missing_test_suite_ranks_a_testing_skill_strongly(kit, git_project):
    """Given a project with no tests, When scout runs, Then a testing skill is strong.

    Absence is concrete evidence, so it earns the strong tier.
    """
    (git_project / "docs").mkdir()
    (git_project / ".github" / "workflows").mkdir(parents=True)
    result = kit("scout", cwd=git_project)
    assert A_TESTING_SKILL in report(result.stdout)["strong"]
    assert "no test directory and no test files" in result.stdout


def test_focus_promotes_its_own_matches_to_the_front(kit, git_project):
    """Given --focus testing, When scout runs, Then a testing skill leads the strong tier."""
    result = kit("scout", "--focus", "testing", cwd=js_project(git_project, react="19.0.0"))
    assert report(result.stdout)["strong"][0] == A_TESTING_SKILL


def test_a_focus_that_matches_nothing_says_so(kit, git_project):
    """Given a focus tag no available skill carries, When scout runs, Then it says so.

    Every git-tagged skill is global, so the fallback picks would otherwise read as
    the answer to the focus.
    """
    result = kit("scout", "--focus", "nosuchtag", cwd=js_project(git_project, react="19.0.0"))
    assert result.returncode == EXIT_OK
    assert "carries the 'nosuchtag' tag" in result.stdout


def test_the_report_ends_with_a_runnable_install_command(kit, git_project):
    """Given recommendations, When scout runs, Then it prints the command that installs them."""
    result = kit("scout", cwd=js_project(git_project, react="19.0.0"))
    assert "To install: claude-kit add " in result.stdout
    assert A_REACT_SKILL in result.stdout.rsplit("To install: claude-kit add ", 1)[1]


def test_add_links_the_strong_matches_into_the_project(kit, git_project):
    """Given --add, When scout runs, Then each strong match lands in the project."""
    project = js_project(git_project, react="19.0.0")
    result = kit("scout", "--add", cwd=project)
    assert result.returncode == EXIT_OK
    assert (project / ".claude" / "skills" / A_REACT_SKILL).is_symlink()


def test_add_leaves_the_weaker_tier_alone(kit, git_project):
    """Given --add, When scout runs, Then only strong matches are installed."""
    project = js_project(git_project, react="19.0.0")
    sections = report(kit("scout", "--add", cwd=project).stdout)
    installed = {path.name for path in (project / ".claude" / "skills").iterdir()}
    assert installed == set(sections["strong"])


def test_a_block_scalar_description_is_still_reported(kit, git_project):
    """Given a skill whose description is a YAML block scalar, When scout runs,
    Then its What line carries text.

    A single-line grep returns empty for the `description: >-` form, which is how
    these skills used to reach the report with no description at all.
    """
    project = js_project(git_project, react="19.0.0")
    stdout = kit("scout", cwd=project).stdout
    whats = [line for line in stdout.splitlines() if line.strip().startswith("What:")]
    numbered = [line for line in stdout.splitlines() if ENTRY.match(line) and "[" in line]
    assert len(whats) == len(numbered)
