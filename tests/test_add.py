"""`claude-kit add`, one test per Given / When / Then case.

Assertions are about observable behaviour: the exit code, where the symlink
lands, what it resolves to, and what was left untouched. Never about how the
CLI is implemented. Refusal *messages* are deliberately not asserted, only
their exit codes, so wording stays free to change.

The scope rule under test: an artifact tagged `global` belongs in ~/.claude and
nowhere else; everything else belongs in a project and nowhere else; `--global`
overrides the second half by recording a machine-local pin.
"""

import json
import os
import subprocess

import pytest

from conftest import (
    A_GLOBAL_AGENT,
    A_GLOBAL_SKILL,
    A_PROJECT_PLUGIN,
    A_PROJECT_SKILL,
    AGENTS_DIR,
    EXIT_ALREADY_GLOBAL,
    EXIT_ALREADY_LOCAL,
    EXIT_DEPENDENCY_ONLY,
    EXIT_NEEDS_GLOBAL,
    EXIT_NO_PROJECT,
    EXIT_NOT_FOUND,
    EXIT_OK,
    PLUGINS_DIR,
    SKILLS_DIR,
)


def ok(result):
    """Readable failure output when a command was expected to succeed."""
    return f"exit {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"


def link_in(root, leaf, name):
    return root / ".claude" / leaf / name


def pins(home):
    path = home / ".claude/claude-kit.json"
    return json.loads(path.read_text())["pinned"] if path.exists() else {}


# --------------------------------------------------------------------------
# Skill NOT tagged global
# --------------------------------------------------------------------------


def test_project_skill_links_into_the_project(kit, git_project):
    """
    Given  a git project
      and  a skill that is not tagged `global`
    When   the user runs `claude-kit add <skill>` from inside a project
    Then   the skill is linked into <project>/.claude/skills/<skill>
      and  the link resolves to the dotfiles copy, so edits stay live
      and  ~/.claude is left untouched
    """
    local = link_in(git_project, "skills", A_PROJECT_SKILL)
    globl = link_in(kit.home, "skills", A_PROJECT_SKILL)
    assert not local.exists() and not globl.exists(), "precondition: both clean"

    result = kit("add", A_PROJECT_SKILL, cwd=git_project)

    assert result.returncode == EXIT_OK, ok(result)
    assert local.is_symlink()
    assert local.resolve() == (SKILLS_DIR / A_PROJECT_SKILL).resolve(), (
        "must point back into the dotfiles repo; a copy would break live editing"
    )
    assert not globl.exists(), (
        "a project skill leaked into ~/.claude, which is the bug that made "
        "idea-refine auto-fire in every repo"
    )


def test_project_skill_with_global_flag_links_into_home(kit, git_project):
    """
    Given  a git project
      and  a skill that is not tagged `global`
    When   the user runs `claude-kit add <skill> --global` from inside a project
    Then   the skill is linked into ~/.claude/skills/<skill>
      and  the link resolves to the dotfiles copy, so edits stay live
      and  <project>/.claude is left untouched
      and  the override is recorded as a machine-local pin
    """
    local = link_in(git_project, "skills", A_PROJECT_SKILL)
    globl = link_in(kit.home, "skills", A_PROJECT_SKILL)

    result = kit("add", A_PROJECT_SKILL, "--global", cwd=git_project)

    assert result.returncode == EXIT_OK, ok(result)
    assert globl.is_symlink()
    assert globl.resolve() == (SKILLS_DIR / A_PROJECT_SKILL).resolve()
    assert not local.exists(), "--global must not also install into the project"
    assert A_PROJECT_SKILL in pins(kit.home).get("skills", []), (
        "an untagged skill installed globally must be recorded as a pin"
    )


def test_project_skill_already_local_is_refused(kit, git_project):
    """
    Given  a git project with the skill already installed locally
      and  a skill that is not tagged `global`
    When   the user runs `claude-kit add <skill>` from inside a project
    Then   the command fails, reporting it was installed before
      and  <project>/.claude and ~/.claude are left untouched
    """
    assert kit("add", A_PROJECT_SKILL, cwd=git_project).returncode == EXIT_OK
    local = link_in(git_project, "skills", A_PROJECT_SKILL)
    before = local.readlink()

    result = kit("add", A_PROJECT_SKILL, cwd=git_project)

    assert result.returncode == EXIT_ALREADY_LOCAL, ok(result)
    assert local.readlink() == before, "the existing link must not be rewritten"
    assert not link_in(kit.home, "skills", A_PROJECT_SKILL).exists()


def test_project_skill_already_global_is_refused(kit, git_project):
    """
    Given  a git project with the skill already installed globally
      and  a skill that is not tagged `global`
    When   the user runs `claude-kit add <skill>` from inside a project
    Then   the command fails, reporting it is already installed globally
      and  <project>/.claude and ~/.claude are left untouched

    A global install already makes the skill active inside this project, so a
    second project-scoped link would be redundant, not additive.
    """
    assert kit("add", A_PROJECT_SKILL, "--global", cwd=git_project).returncode == EXIT_OK

    result = kit("add", A_PROJECT_SKILL, cwd=git_project)

    assert result.returncode == EXIT_ALREADY_GLOBAL, ok(result)
    assert not link_in(git_project, "skills", A_PROJECT_SKILL).exists()
    assert link_in(kit.home, "skills", A_PROJECT_SKILL).is_symlink()


def test_project_skill_already_local_can_still_be_promoted_to_global(kit, git_project):
    """
    Given  a git project with the skill already installed locally
      and  a skill that is not tagged `global`
    When   the user runs `claude-kit add <skill> --global`
    Then   the command succeeds and links it into ~/.claude
      and  the existing project link is left alone

    The symmetric case to the one above: the target differs, so there is no
    conflict to refuse. Promoting makes the project link redundant, which is
    the user's to clean up.
    """
    assert kit("add", A_PROJECT_SKILL, cwd=git_project).returncode == EXIT_OK

    result = kit("add", A_PROJECT_SKILL, "--global", cwd=git_project)

    assert result.returncode == EXIT_OK, ok(result)
    assert link_in(kit.home, "skills", A_PROJECT_SKILL).is_symlink()
    assert link_in(git_project, "skills", A_PROJECT_SKILL).is_symlink()


# --------------------------------------------------------------------------
# Skill tagged global
# --------------------------------------------------------------------------


def test_global_skill_with_flag_links_into_home(kit, git_project):
    """
    Given  a git project
      and  a skill that is tagged `global`, installed neither globally nor locally
    When   the user runs `claude-kit add <skill> --global` from inside a project
    Then   the skill is linked into ~/.claude/skills/<skill>
      and  the link resolves to the dotfiles copy, so edits stay live
      and  <project>/.claude is left untouched
      and  no pin is written, because the tag already puts it in the global set
    """
    globl = link_in(kit.home, "skills", A_GLOBAL_SKILL)
    local = link_in(git_project, "skills", A_GLOBAL_SKILL)
    assert not globl.exists() and not local.exists(), "precondition: both clean"

    result = kit("add", A_GLOBAL_SKILL, "--global", cwd=git_project)

    assert result.returncode == EXIT_OK, ok(result)
    assert globl.is_symlink()
    assert globl.resolve() == (SKILLS_DIR / A_GLOBAL_SKILL).resolve()
    assert not local.exists()
    assert A_GLOBAL_SKILL not in pins(kit.home).get("skills", []), (
        "pinning a tagged entry would duplicate the registry as machine-local state"
    )


def test_global_skill_without_flag_is_refused(kit, git_project):
    """
    Given  a git project
      and  a skill that is tagged `global`, installed neither globally nor locally
    When   the user runs `claude-kit add <skill>` from inside a project
    Then   the command fails with an error saying the skill is global
      and  the message recommends the command to run instead
      and  <project>/.claude and ~/.claude are left untouched
    """
    result = kit("add", A_GLOBAL_SKILL, cwd=git_project)

    assert result.returncode == EXIT_NEEDS_GLOBAL, ok(result)
    assert "--global" in result.stderr, "the refusal must name the fix, not just the problem"
    assert not link_in(git_project, "skills", A_GLOBAL_SKILL).exists()
    assert not link_in(kit.home, "skills", A_GLOBAL_SKILL).exists()


def test_global_skill_with_a_stale_local_link_still_refuses_on_the_tag(kit, git_project):
    """
    Given  a git project with the skill already linked locally
      and  a skill that is tagged `global`
    When   the user runs `claude-kit add <skill>` from inside a project
    Then   the command fails on the tag, exactly as if the local link were absent
      and  <project>/.claude and ~/.claude are left untouched

    Two guards fire at once here. The tag wins: "already installed" would send
    the user to the wrong fix when the real answer is that it should never be
    project-scoped at all.
    """
    stale = link_in(git_project, "skills", A_GLOBAL_SKILL)
    stale.parent.mkdir(parents=True)
    stale.symlink_to(SKILLS_DIR / A_GLOBAL_SKILL)

    result = kit("add", A_GLOBAL_SKILL, cwd=git_project)

    assert result.returncode == EXIT_NEEDS_GLOBAL, ok(result)
    assert not link_in(kit.home, "skills", A_GLOBAL_SKILL).exists()


def test_global_skill_already_installed_is_refused(kit, git_project):
    """
    Given  a git project with the skill already installed globally
      and  a skill that is tagged `global`
    When   the user runs `claude-kit add <skill> --global` from inside a project
    Then   the command fails, reporting it was installed globally before
      and  <project>/.claude and ~/.claude are left untouched
    """
    assert kit("add", A_GLOBAL_SKILL, "--global", cwd=git_project).returncode == EXIT_OK
    globl = link_in(kit.home, "skills", A_GLOBAL_SKILL)
    before = globl.readlink()

    result = kit("add", A_GLOBAL_SKILL, "--global", cwd=git_project)

    assert result.returncode == EXIT_ALREADY_GLOBAL, ok(result)
    assert globl.readlink() == before
    assert not link_in(git_project, "skills", A_GLOBAL_SKILL).exists()


# --------------------------------------------------------------------------
# Guards the cases above assume but never state
# --------------------------------------------------------------------------


def test_project_scope_outside_a_git_repo_is_refused(kit, tmp_path):
    """
    Given  a directory that is not inside any git repo
      and  a skill that is not tagged `global`
    When   the user runs `claude-kit add <skill>`
    Then   the command fails, because there is no project to install into
      and  ~/.claude is left untouched

    This is the idea-refine regression: falling back to ~/.claude here is what
    made a project skill fire in every session.
    """
    loose = tmp_path / "loose"
    loose.mkdir()

    result = kit("add", A_PROJECT_SKILL, cwd=loose)

    assert result.returncode == EXIT_NO_PROJECT, ok(result)
    assert not link_in(kit.home, "skills", A_PROJECT_SKILL).exists()
    assert not (loose / ".claude").exists()


def test_global_add_outside_a_git_repo_succeeds(kit, tmp_path):
    """
    Given  a directory that is not inside any git repo
    When   the user runs `claude-kit add <skill> --global`
    Then   the command succeeds, because a global install needs no project
    """
    loose = tmp_path / "loose"
    loose.mkdir()

    result = kit("add", A_GLOBAL_SKILL, "--global", cwd=loose)

    assert result.returncode == EXIT_OK, ok(result)
    assert link_in(kit.home, "skills", A_GLOBAL_SKILL).is_symlink()


def test_unknown_name_is_refused(kit, git_project):
    """
    Given  a name that matches no skill, agent or plugin
    When   the user runs `claude-kit add <name>`
    Then   the command fails without creating anything
    """
    result = kit("add", "no-such-artifact", cwd=git_project)

    assert result.returncode == EXIT_NOT_FOUND, ok(result)
    assert "no-such-artifact" in result.stderr, (
        "the refusal must name what was not found; asserting on the exit code "
        "alone also matches the interpreter failing to open the CLI at all"
    )
    assert not (git_project / ".claude/skills").exists()


def test_dependency_only_skill_cannot_be_added_directly(kit, git_project, skills):
    """
    Given  a skill flagged `dependency_only`
    When   the user runs `claude-kit add <skill>`
    Then   the command fails, pointing at the parent skill instead

    These exist only to satisfy another skill's `dependencies`; installing one
    alone gives you a skill nothing invokes.
    """
    hidden = next(
        (name for name, entry, _ in skills if entry.get("dependency_only")), None
    )
    if hidden is None:
        pytest.skip("no dependency_only skill in the registry")

    result = kit("add", hidden, cwd=git_project)

    assert result.returncode == EXIT_DEPENDENCY_ONLY, ok(result)


def test_the_repo_is_found_through_the_path_symlink(kit, git_project, tmp_path):
    """
    Given  claude-kit invoked through a ~/.local/bin symlink, as the ai role installs it
      and  DOTFILES_DIR unset
    When   the user runs any command
    Then   it still locates the dotfiles checkout, by resolving its own path

    Every other test sets DOTFILES_DIR, so without this the production
    invocation path would be the one thing never exercised.
    """
    from conftest import KIT

    bin_dir = tmp_path / "localbin"
    bin_dir.mkdir()
    installed = bin_dir / "claude-kit"
    installed.symlink_to(KIT)

    env = {k: v for k, v in os.environ.items() if k != "DOTFILES_DIR"}
    env["HOME"] = str(kit.home)
    result = subprocess.run(
        [str(installed), "add", A_GLOBAL_SKILL],
        cwd=str(git_project),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == EXIT_NEEDS_GLOBAL, (
        f"could not read the registry without DOTFILES_DIR:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_an_unwritable_target_fails_cleanly(kit, git_project):
    """
    Given  a project where .claude cannot be created
    When   the user runs `claude-kit add <skill>`
    Then   the command reports the filesystem error and exits non-zero
      and  does not print a Python traceback
    """
    (git_project / ".claude").write_text("not a directory")

    result = kit("add", A_PROJECT_SKILL, cwd=git_project)

    assert result.returncode != EXIT_OK
    assert "Traceback" not in result.stderr, (
        f"a filesystem error must be reported, not raised:\n{result.stderr}"
    )


def test_declared_dependencies_are_installed_alongside_the_parent(kit, git_project, skills):
    """
    Given  a skill that declares dependencies
    When   the user adds it
    Then   each dependency is linked too, resolving its own scope

    A project skill may depend on a global one and vice versa, so the parent's
    scope is not inherited.
    """
    parent = next(
        (
            (name, entry["dependencies"])
            for name, entry, _ in skills
            if entry.get("dependencies") and "global" not in entry.get("groups", [])
        ),
        None,
    )
    if parent is None:
        pytest.skip("no project-scoped skill declares dependencies")
    name, deps = parent

    result = kit("add", name, cwd=git_project)

    assert result.returncode == EXIT_OK, ok(result)
    for dep in deps:
        landed = link_in(git_project, "skills", dep).exists() or link_in(
            kit.home, "skills", dep
        ).exists()
        assert landed, f"dependency {dep!r} of {name!r} was not installed"


# --------------------------------------------------------------------------
# Agents and plugins: same rules, different destination
# --------------------------------------------------------------------------


def test_agent_lands_in_the_agents_leaf(kit, git_project):
    """
    Given  an agent tagged `global`
    When   the user runs `claude-kit add <agent> --global`
    Then   it is linked into ~/.claude/agents/<agent>.md, not skills/

    Every agent in the registry is tagged `global` today, so the project-scoped
    half of the matrix has no fixture to test against.
    """
    result = kit("add", A_GLOBAL_AGENT, "--global", cwd=git_project)

    assert result.returncode == EXIT_OK, ok(result)
    link = link_in(kit.home, "agents", f"{A_GLOBAL_AGENT}.md")
    assert link.is_symlink()
    assert link.resolve() == (AGENTS_DIR / f"{A_GLOBAL_AGENT}.md").resolve()


def test_plugin_lands_in_the_skills_leaf(kit, git_project):
    """
    Given  a plugin, none of which are tagged `global`
    When   the user runs `claude-kit add <plugin>` from inside a project
    Then   it is linked into <project>/.claude/skills/<plugin>

    Plugins share the skills leaf because that is how Claude Code loads a
    skills-dir plugin, as <plugin>@skills-dir.
    """
    result = kit("add", A_PROJECT_PLUGIN, cwd=git_project)

    assert result.returncode == EXIT_OK, ok(result)
    link = link_in(git_project, "skills", A_PROJECT_PLUGIN)
    assert link.is_symlink()
    assert link.resolve() == (PLUGINS_DIR / A_PROJECT_PLUGIN).resolve()
