"""Scope resolution: project_root, link_path, installed_scope.

project_root is pure path arithmetic, so nothing here shells out. It used to run
`git rev-parse --show-toplevel`; a project is now simply the directory you are in.
"""

import pytest

from claude_kit import catalog as cat
from claude_kit import scope
from dotkit.testing import CLAUDE

SKILL = cat.Artifact(name="coderabbit", type=cat.SKILL)
GLOBAL_SKILL = cat.Artifact(name="commit", type=cat.SKILL, groups=("global",))
AGENT = cat.Artifact(name="architect", type=cat.AGENT)
PLUGIN = cat.Artifact(name="backend", type=cat.PLUGIN)


# --- link_path: leaf and suffix per type ------------------------------------


@pytest.mark.parametrize(
    "art,expected",
    [
        (SKILL, ".claude/skills/coderabbit"),
        (AGENT, ".claude/agents/architect.md"),
        # A plugin lands in the skills leaf, because Claude Code loads it as
        # <name>@skills-dir.
        (PLUGIN, ".claude/skills/backend"),
    ],
)
def test_link_path_per_type(tmp_path, art, expected):
    home, project = tmp_path / "home", tmp_path / "project"
    assert scope.link_path(art, scope.PROJECT, home, project) == project / expected
    assert scope.link_path(art, scope.GLOBAL, home, project) == home / expected


def test_link_path_ignores_the_other_root(tmp_path):
    """Global resolution must not depend on there being a project at all."""
    home = tmp_path / "home"
    assert scope.link_path(GLOBAL_SKILL, scope.GLOBAL, home, None) == home / ".claude/skills/commit"


# --- project_root: cwd is the project ---------------------------------------


def test_c4_a_subdirectory_is_its_own_project(project, tmp_path):
    """Given cwd is a subdirectory, Then it is the project, not the tree above it.

    The inverse of the rule this used to assert. Anchoring at the git top level
    meant a directory outside any repo could not be installed into at all, which
    is the refusal that got this changed. cwd is now taken at face value.
    """
    deep = project / "src" / "nested"
    deep.mkdir(parents=True)
    assert scope.project_root(deep, tmp_path / "home") == deep.resolve()


def test_project_root_is_cwd_itself(project, tmp_path):
    assert scope.project_root(project, tmp_path / "home") == project.resolve()


def test_a_directory_outside_any_repo_is_a_project(tmp_path):
    """The reported case: a plain directory with no .git anywhere above it.

    This used to return None, so `add` refused with NO_PROJECT.
    """
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "package.json").write_text("{}\n")
    assert scope.project_root(plain, tmp_path / "home") == plain.resolve()


def test_git_is_not_consulted_at_all(tmp_path, monkeypatch):
    """Resolution must not depend on git being installed or on cwd's repo status.

    Guards the reason the refusal happened: any git call reintroduces a way for an
    ordinary directory to stop being a project. Breaking PATH would not catch a
    call through an absolute path, so this forbids spawning anything.
    """
    import subprocess as sp

    def explode(*args, **kwargs):
        raise AssertionError(f"project_root spawned a subprocess: {args}")

    monkeypatch.setattr(sp, "run", explode)
    monkeypatch.setattr(sp, "Popen", explode)
    monkeypatch.setattr(sp, "check_output", explode)

    plain = tmp_path / "plain"
    plain.mkdir()
    assert scope.project_root(plain, tmp_path / "home") == plain.resolve()


def test_c12_home_is_never_a_project(tmp_path):
    """Given cwd is $HOME, Then it is not a project.

    The one exception, and not project detection in disguise: $HOME/.claude *is*
    ~/.claude, so a project-scoped install there would silently be a global one,
    load in every repo, and be pruned by the ai role on its next run.
    """
    home = tmp_path / "home"
    home.mkdir()
    assert scope.project_root(home, home) is None


def test_c12_a_directory_below_home_still_resolves(tmp_path):
    """The $HOME guard must reject $HOME itself, not everything beneath it.

    Otherwise the exception would swallow every project under ~/, which is where
    they all live.
    """
    home = tmp_path / "home"
    home.mkdir()
    inner = home / "work" / "api"
    inner.mkdir(parents=True)
    assert scope.project_root(inner, home) == inner.resolve()


def test_c12_the_home_guard_resolves_the_cwd_side(tmp_path):
    """A symlinked route to $HOME is still $HOME.

    On macOS this is not hypothetical: /tmp is a symlink to /private/tmp, so an
    unresolved comparison would let `cd` via one spelling defeat the guard.
    """
    home = tmp_path / "home"
    home.mkdir()
    alias = tmp_path / "home-alias"
    alias.symlink_to(home)
    assert scope.project_root(alias, home) is None


def test_c12_the_home_guard_resolves_the_home_side(tmp_path):
    """$HOME itself may be the unresolved spelling, and the guard must still fire.

    The mirror of the case above, and the one that actually bites: HOME comes from
    the environment, so it is whatever the user's shell was given. `HOME=/tmp/me` on
    macOS is a symlinked spelling of /private/tmp/me, and resolving only cwd would
    compare a resolved path against an unresolved one, miss, and treat $HOME as an
    ordinary project.
    """
    real = tmp_path / "real-home"
    real.mkdir()
    alias = tmp_path / "home-link"
    alias.symlink_to(real)
    assert scope.project_root(real, alias) is None


# --- installed_scope --------------------------------------------------------


def link(root, art, target):
    path = scope.link_path(art, scope.PROJECT if root.name == "project" else scope.GLOBAL, root, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)
    return path


def test_installed_scope_reports_none_when_absent(tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    assert scope.installed_scope(SKILL, home, project) is None


def test_installed_scope_finds_a_project_link(tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    source = tmp_path / "src"
    source.mkdir()
    link(project, SKILL, source)
    assert scope.installed_scope(SKILL, home, project) == scope.PROJECT


def test_installed_scope_finds_a_global_link(tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    source = tmp_path / "src"
    source.mkdir()
    link(home, SKILL, source)
    assert scope.installed_scope(SKILL, home, project) == scope.GLOBAL


def test_installed_scope_tolerates_no_project(tmp_path):
    home = tmp_path / "home"
    source = tmp_path / "src"
    source.mkdir()
    link(home, SKILL, source)
    assert scope.installed_scope(SKILL, home, None) == scope.GLOBAL


def test_d5_a_broken_symlink_still_counts_as_installed(tmp_path):
    """It occupies the path, and it is exactly what needs cleaning."""
    home, project = tmp_path / "home", tmp_path / "project"
    link(project, SKILL, tmp_path / "gone")
    assert scope.installed_scope(SKILL, home, project) == scope.PROJECT


def test_d4_a_real_directory_is_not_a_symlink(tmp_path):
    """Hand-authored content must never be mistaken for something we installed."""
    home, project = tmp_path / "home", tmp_path / "project"
    real = project / ".claude" / "skills" / "coderabbit"
    real.mkdir(parents=True)
    assert scope.installed_scope(SKILL, home, project) is None


# --- installed_names --------------------------------------------------------


def test_installed_names_lists_only_symlinks(tmp_path):
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "linked").symlink_to(CLAUDE / "skills" / "coderabbit")
    (skills / "handmade").mkdir()
    assert scope.installed_names(project, cat.SKILL, CLAUDE) == {"linked": skills / "linked"}


def test_installed_names_strips_the_agent_suffix(tmp_path):
    project = tmp_path / "project"
    agents = project / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "architect.md").symlink_to(CLAUDE / "agents" / "architect.md")
    (agents / "notes.txt").symlink_to(CLAUDE / "agents" / "architect.md")
    assert scope.installed_names(project, cat.AGENT, CLAUDE) == {"architect": agents / "architect.md"}


def test_installed_names_handles_a_missing_directory(tmp_path):
    assert scope.installed_names(tmp_path / "nope", cat.SKILL, CLAUDE) == {}
    assert scope.installed_names(None, cat.SKILL, CLAUDE) == {}


def test_installed_names_ignores_a_link_pointing_outside_the_store(tmp_path):
    """A symlink someone else put in .claude/skills is not ours to report or remove."""
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    foreign = tmp_path / "somebody-elses-skill"
    foreign.mkdir()
    (skills / "foreign").symlink_to(foreign)
    assert scope.installed_names(project, cat.SKILL, CLAUDE) == {}


# --- skills and plugins share .claude/skills/, so the target decides ---------


def test_a_plugin_link_is_not_counted_as_a_skill(tmp_path):
    """Given a plugin is linked, When asking for skills, Then it does not appear.

    Both install into .claude/skills/, so the filename alone is ambiguous and only
    the store the link points into says which type it is. Classifying by name
    reported every link as both a skill and a plugin.
    """
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "backend").symlink_to(CLAUDE / "plugins" / "backend")

    assert scope.installed_names(project, cat.PLUGIN, CLAUDE) == {"backend": skills / "backend"}
    assert scope.installed_names(project, cat.SKILL, CLAUDE) == {}


def test_a_skill_link_is_not_counted_as_a_plugin(tmp_path):
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "coderabbit").symlink_to(CLAUDE / "skills" / "coderabbit")

    assert scope.installed_names(project, cat.SKILL, CLAUDE) == {"coderabbit": skills / "coderabbit"}
    assert scope.installed_names(project, cat.PLUGIN, CLAUDE) == {}


def test_installed_scope_disambiguates_by_store_too(tmp_path):
    """Given a plugin named X is linked, When asking about a skill named X, Then it
    reads as absent. Same shared-leaf hazard, at the single-artifact level."""
    home, project = tmp_path / "home", tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "backend").symlink_to(CLAUDE / "plugins" / "backend")

    plugin = cat.Artifact(name="backend", type=cat.PLUGIN)
    same_name_skill = cat.Artifact(name="backend", type=cat.SKILL)
    assert scope.installed_scope(plugin, home, project, CLAUDE) == scope.PROJECT
    assert scope.installed_scope(same_name_skill, home, project, CLAUDE) is None


# --- all_links: type-agnostic, for broken-link detection --------------------


def test_all_links_returns_every_symlink_including_foreign_ones(tmp_path):
    """Broken-link detection needs links a per-type view would filter out."""
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    agents = project / ".claude" / "agents"
    skills.mkdir(parents=True)
    agents.mkdir(parents=True)
    (skills / "ours").symlink_to(CLAUDE / "skills" / "coderabbit")
    (skills / "foreign").symlink_to(tmp_path / "elsewhere")
    (agents / "an-agent.md").symlink_to(CLAUDE / "agents" / "architect.md")

    found = {(leaf, name) for leaf, name, _ in scope.all_links(project)}
    assert found == {("skills", "ours"), ("skills", "foreign"), ("agents", "an-agent.md")}


def test_all_links_tolerates_no_root():
    assert scope.all_links(None) == []


# --- link_target works on broken links -------------------------------------


def test_link_target_reads_a_dangling_link(tmp_path):
    """readlink rather than resolve, so a broken link can still be classified."""
    link = tmp_path / "broken"
    link.symlink_to(tmp_path / "gone")
    assert scope.link_target(link) == tmp_path / "gone"


def test_link_target_makes_a_relative_link_absolute(tmp_path):
    directory = tmp_path / "d"
    directory.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    link = directory / "rel"
    link.symlink_to("../target")
    assert scope.link_target(link) == target


def test_link_target_is_none_for_a_non_link(tmp_path):
    plain = tmp_path / "plain"
    plain.write_text("x")
    assert scope.link_target(plain) is None


def test_points_into_classifies_a_broken_link_by_its_intended_target(tmp_path):
    """A link into our store that has since been deleted upstream is still ours."""
    link = tmp_path / "gone-skill"
    link.symlink_to(CLAUDE / "skills" / "deleted-upstream")
    assert not link.exists()
    assert scope.points_into(link, CLAUDE / "skills") is True
    assert scope.points_into(link, CLAUDE / "plugins") is False


# --- points_into: our links versus foreign ones ----------------------------------------------------------


def test_points_into_distinguishes_our_links_from_foreign_ones(tmp_path):
    claude = tmp_path / "claude" / "skills"
    claude.mkdir(parents=True)
    ours = claude / "mine"
    ours.mkdir()
    foreign = tmp_path / "elsewhere"
    foreign.mkdir()

    here = tmp_path / "a"
    here.symlink_to(ours)
    there = tmp_path / "b"
    there.symlink_to(foreign)

    assert scope.points_into(here, tmp_path / "claude") is True
    assert scope.points_into(there, tmp_path / "claude") is False


def test_points_into_is_false_for_a_broken_link(tmp_path):
    claude = tmp_path / "claude"
    claude.mkdir()
    broken = tmp_path / "broken"
    broken.symlink_to(tmp_path / "gone")
    assert scope.points_into(broken, claude) is False
