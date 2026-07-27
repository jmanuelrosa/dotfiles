"""Scope routing: the rule that decides WHERE an artifact installs.

This is the highest-risk logic in the fish layer. A regression here is what put a
non-global `idea-refine` into ~/.claude, where it auto-fired in every repo.

Tests drive the real fish functions as a black box through HOME + DOTFILES_DIR +
cwd, which are the only inputs they read, so they stay valid across the planned
claude-skill/claude-agent -> claude-kit rewrite.
"""

import pytest


def target(fish, kind, name, cwd):
    r = fish(f"_claude_scope_target {kind} {name}", cwd=cwd)
    return r.returncode, r.stdout.strip()


def test_global_skill_installs_into_home(fish, git_project):
    rc, out = target(fish, "skill", "commit", cwd=git_project)
    assert rc == 0
    assert out == f"{fish.home}/.claude/skills", (
        "a global-tagged skill must resolve to ~/.claude even from inside a project"
    )


def test_global_agent_uses_the_agents_leaf(fish, git_project):
    rc, out = target(fish, "agent", "architect", cwd=git_project)
    assert rc == 0
    assert out == f"{fish.home}/.claude/agents"


def test_non_global_skill_installs_into_the_project(fish, git_project):
    rc, out = target(fish, "skill", "idea-refine", cwd=git_project)
    assert rc == 0
    assert out == f"{git_project}/.claude/skills"


def test_non_global_skill_is_refused_outside_a_repo(fish, tmp_path):
    """The idea-refine regression: installing from a non-repo used to silently
    write into ~/.claude, making a project skill fire in every session."""
    loose = tmp_path / "loose"
    loose.mkdir()
    rc, out = target(fish, "skill", "idea-refine", cwd=loose)
    assert rc != 0, "must refuse rather than fall back to ~/.claude"
    assert out == ""


def test_non_global_skill_is_refused_from_home_itself(fish):
    rc, out = target(fish, "skill", "idea-refine", cwd=fish.home)
    assert rc != 0, "HOME is explicitly not a project root, even if it is a git repo"
    assert out == ""


def test_scope_resolves_from_a_subdirectory_to_the_repo_root(fish, git_project):
    """Claude Code scans the repo root, so 'linked' must mean 'linked where the
    session will look', not relative to cwd."""
    nested = git_project / "src" / "deep"
    nested.mkdir(parents=True)
    rc, out = target(fish, "skill", "idea-refine", cwd=nested)
    assert rc == 0
    assert out == f"{git_project}/.claude/skills"


@pytest.mark.parametrize("name", ["grilling", "domain-modeling"])
def test_dependency_only_skills_still_count_as_global(fish, git_project, name):
    """These carry no `global` tag; they reach ~/.claude only as declared
    dependencies of global entries. _claude_scope_global_skills must agree with
    GLOBAL_CLAUDE_SKILLS_EFFECTIVE in the ai role, or the role's prune deletes
    what the CLI just linked."""
    rc, out = target(fish, "skill", name, cwd=git_project)
    assert rc == 0
    assert out == f"{fish.home}/.claude/skills"


def test_global_set_matches_what_the_role_would_link(fish):
    """The fish predicate and the Ansible derivation are two implementations of
    one rule. This pins them together until they become one jq program."""
    r = fish("_claude_scope_global_skills")
    assert r.returncode == 0, r.stderr
    names = sorted(n for n in r.stdout.split() if n)
    assert names, "derivation returned nothing, which would make the role prune everything"
    # Tagged global, plus one level of dependencies pulled in by global entries.
    for expected in ("commit", "pr", "research", "grilling", "domain-modeling"):
        assert expected in names, f"{expected} missing from the effective global set"
