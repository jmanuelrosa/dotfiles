"""Group P: the `.agents/skills` link that lets pi see a project's skills.

Two things are worth testing here and they are not the same thing. The first is this
module's own contract: converge is derived from two paths, so every case is a pair of
states and an outcome, and the ones that matter are the refusals (a path we did not
make is never touched) rather than the happy one.

The second is the assumption the whole feature rests on, which lives in someone else's
code: that pi follows a symlinked skill directory and recurses to find a nested
`SKILL.md`. `test_pi_discovery.py` holds that one, because it can only be answered by
running pi's own loader and so needs node.
"""

import pytest

from claude_kit import checks, pi
from claude_kit.commands import add, remove
from dotkit.testing import CLAUDE


@pytest.fixture
def skilled(project):
    """A project with one claude skill linked, which is the state that wants the link."""
    leaf = project / ".claude" / "skills"
    leaf.mkdir(parents=True)
    (leaf / "coderabbit").symlink_to(CLAUDE / "skills" / "coderabbit")
    return project


# --- P1 to P4: converge ------------------------------------------------------


def test_a_project_with_skills_gets_the_link(skilled):
    assert pi.converge(skilled) == "linked"
    link = pi.link_path(skilled)
    assert link.is_symlink()
    assert pi.is_ours(skilled)


def test_the_target_is_relative_so_the_project_can_move(skilled):
    """An absolute target would name this checkout's copy of the project and break the
    moment it is moved or cloned. Every other link claude-kit makes points into the
    dotfiles repo and must be absolute; this one points at a sibling and must not be."""
    pi.converge(skilled)
    import os

    raw = os.readlink(pi.link_path(skilled))
    assert not os.path.isabs(raw)
    assert pi.link_path(skilled).resolve() == (skilled / ".claude" / "skills").resolve()


def test_converge_is_idempotent(skilled):
    assert pi.converge(skilled) == "linked"
    assert pi.converge(skilled) is None
    assert pi.converge(skilled) is None


def test_the_link_goes_when_the_last_skill_does(skilled):
    pi.converge(skilled)
    (skilled / ".claude" / "skills" / "coderabbit").unlink()
    assert pi.converge(skilled) == "unlinked"
    assert not pi.link_path(skilled).exists()
    # The parent was ours to create, so it goes too rather than being left empty.
    assert not (skilled / pi.PARENT).exists()


def test_an_empty_skills_directory_never_earns_a_link(project):
    """The leaf outlives its contents: `remove` unlinks skills and leaves the directory,
    so "exists" and "has skills" are different questions and only the second matters."""
    (project / ".claude" / "skills").mkdir(parents=True)
    assert pi.converge(project) is None
    assert not pi.link_path(project).exists()


def test_a_project_with_no_claude_at_all_is_left_alone(project):
    assert pi.converge(project) is None
    assert not (project / pi.PARENT).exists()


def test_home_is_never_a_project(skilled):
    """project is None outside a project, and converge takes that as nothing to do
    rather than as a path to compute from None."""
    assert pi.converge(None) is None


# --- P5 to P7: what is never touched ----------------------------------------


def test_a_real_agents_skills_directory_is_never_replaced(skilled):
    """Somebody's own pi skills. Ours to leave alone, and the reason is_ours exists."""
    theirs = pi.link_path(skilled)
    theirs.mkdir(parents=True)
    (theirs / "mine").mkdir()

    assert pi.converge(skilled) == "blocked"
    assert theirs.is_dir() and not theirs.is_symlink()
    assert (theirs / "mine").is_dir()


def test_a_link_pointing_somewhere_else_is_never_repointed(skilled, tmp_path):
    elsewhere = tmp_path / "their-skills"
    elsewhere.mkdir()
    link = pi.link_path(skilled)
    link.parent.mkdir(parents=True)
    link.symlink_to(elsewhere)

    assert pi.converge(skilled) == "blocked"
    assert link.resolve() == elsewhere.resolve()


def test_a_foreign_link_is_not_deleted_when_the_skills_go(skilled, tmp_path):
    """The delete branch is gated on the same question as the write branch. Without
    that, emptying a project would silently remove a link this tool never made."""
    elsewhere = tmp_path / "their-skills"
    elsewhere.mkdir()
    link = pi.link_path(skilled)
    link.parent.mkdir(parents=True)
    link.symlink_to(elsewhere)
    (skilled / ".claude" / "skills" / "coderabbit").unlink()

    assert pi.converge(skilled) is None
    assert link.is_symlink()


def test_other_agents_content_survives_the_unlink(skilled):
    """Only the `skills` leaf is ours. `.agents/` is a shared path by design, so a
    prompts directory beside it is what stops the parent being removed."""
    pi.converge(skilled)
    (skilled / pi.PARENT / "prompts").mkdir()
    (skilled / ".claude" / "skills" / "coderabbit").unlink()

    assert pi.converge(skilled) == "unlinked"
    assert (skilled / pi.PARENT / "prompts").is_dir()


# --- P8 and P9: the commands converge it ------------------------------------


def test_add_links_it(catalog, effective, home, project):
    """Through install_one rather than run(), which is the seam scout --add and restore
    reach too, so all three inherit it."""
    add.install_one(catalog, effective, "skill", "coderabbit", False, home, project)
    assert pi.is_ours(project)


def test_remove_unlinks_it(catalog, effective, home, project, monkeypatch):
    add.install_one(catalog, effective, "skill", "coderabbit", False, home, project)
    assert pi.is_ours(project)

    monkeypatch.chdir(project)
    remove.run(
        type("Args", (), {
            "names": ["coderabbit"], "type": "skill", "want_global": False,
            "group": None, "no_cascade": True,
        })()
    )
    assert not pi.link_path(project).exists()


# --- P10: doctor ------------------------------------------------------------


def test_doctor_reports_a_project_pi_cannot_read(skilled):
    found = checks.pi_skills_unreachable(skilled)
    assert len(found) == 1
    assert found[0].check == "pi-unreachable"
    # A note: nothing about Claude Code is broken, and a machine not running pi has
    # nothing to do about it.
    assert not found[0].is_problem


def test_doctor_is_quiet_once_the_link_is_there(skilled):
    pi.converge(skilled)
    assert checks.pi_skills_unreachable(skilled) == []


def test_doctor_names_the_occupant_when_something_else_holds_the_path(skilled):
    pi.link_path(skilled).mkdir(parents=True)
    detail = checks.pi_skills_unreachable(skilled)[0].detail
    assert "not the link" in detail


def test_doctor_says_nothing_about_a_project_with_no_skills(project):
    assert checks.pi_skills_unreachable(project) == []
    assert checks.pi_skills_unreachable(None) == []


# --- P11 to P15: the .agents/agents view for pi-subagents ---------------------
#
# Same shape as the skills link, one level down: derived from what is on disk,
# idempotent, and never touching anything it did not make. Run against a fabricated
# checkout rather than the real one, because the no-agents plugin this needs does not
# exist there: every real seat ships an agent today.


SEAT_AGENT = "backendish-staff-engineer.md"


@pytest.fixture
def seat_repo(tmp_path, monkeypatch):
    """A fabricated checkout holding two plugins: one shipping an agent, one not.

    DOTFILES_DIR is the seam, exactly as the kit fixture uses it, so converge_agents
    reads this store rather than the real repo's.
    """
    claude = tmp_path / "repo" / "roles" / "ai" / "files" / "claude"
    seat = claude / "plugins" / "backendish" / "agents"
    seat.mkdir(parents=True)
    (seat / SEAT_AGENT).write_text("---\nname: backendish-staff-engineer\n---\n")
    (claude / "plugins" / "toolbelt" / "skills").mkdir(parents=True)
    monkeypatch.setenv("DOTFILES_DIR", str(tmp_path / "repo"))
    return claude


@pytest.fixture
def plugged(project, seat_repo):
    """A project with the agent-shipping plugin installed."""
    leaf = project / ".claude" / "skills"
    leaf.mkdir(parents=True)
    (leaf / "backendish").symlink_to(seat_repo / "plugins" / "backendish")
    return project


def test_an_installed_plugins_agents_are_linked(plugged, seat_repo):
    result = pi.converge_agents(plugged)
    assert result.linked == [SEAT_AGENT]
    entry = pi.agents_path(plugged) / SEAT_AGENT
    assert entry.is_symlink()
    source = seat_repo / "plugins" / "backendish" / "agents" / SEAT_AGENT
    assert entry.resolve() == source.resolve()


def test_agent_convergence_is_idempotent(plugged):
    assert pi.converge_agents(plugged) is not None
    assert pi.converge_agents(plugged) is None
    assert pi.converge_agents(plugged) is None


def test_removing_the_plugin_drops_its_agent_links(plugged):
    pi.converge_agents(plugged)
    (plugged / ".claude" / "skills" / "backendish").unlink()

    result = pi.converge_agents(plugged)
    assert result.pruned == [SEAT_AGENT]
    # The run emptied the directory, so it goes too rather than being left behind.
    assert not pi.agents_path(plugged).exists()


def test_a_plugin_with_no_agents_directory_earns_nothing(project, seat_repo):
    leaf = project / ".claude" / "skills"
    leaf.mkdir(parents=True)
    (leaf / "toolbelt").symlink_to(seat_repo / "plugins" / "toolbelt")

    assert pi.converge_agents(project) is None
    assert not pi.agents_path(project).exists()


def test_a_hand_copied_plugin_directory_earns_nothing(project, seat_repo):
    """Only a symlink resolving into the plugins store counts as installed, the same
    narrowing installed_names applies everywhere else this tool derives from disk."""
    copy = project / ".claude" / "skills" / "backendish" / "agents"
    copy.mkdir(parents=True)
    (copy / SEAT_AGENT).write_text("a hand-managed copy")

    assert pi.converge_agents(project) is None
    assert not pi.agents_path(project).exists()


def test_a_foreign_agent_link_is_never_pruned(plugged, tmp_path):
    pi.converge_agents(plugged)
    theirs = tmp_path / "their-agent.md"
    theirs.write_text("theirs")
    foreign = pi.agents_path(plugged) / "their-agent.md"
    foreign.symlink_to(theirs)
    (plugged / ".claude" / "skills" / "backendish").unlink()

    result = pi.converge_agents(plugged)
    assert result.pruned == [SEAT_AGENT]
    assert foreign.is_symlink()
    # The run did not empty the directory, so it stays.
    assert pi.agents_path(plugged).is_dir()


def test_a_real_agent_file_is_never_pruned(plugged):
    pi.converge_agents(plugged)
    directory = pi.agents_path(plugged)
    (directory / "hand-authored.md").write_text("mine")
    (plugged / ".claude" / "skills" / "backendish").unlink()

    result = pi.converge_agents(plugged)
    assert result.pruned == [SEAT_AGENT]
    assert (directory / "hand-authored.md").read_text() == "mine"


def test_a_foreign_occupant_of_a_desired_name_blocks_it(plugged):
    directory = pi.agents_path(plugged)
    directory.mkdir(parents=True)
    (directory / SEAT_AGENT).write_text("hand-authored")

    result = pi.converge_agents(plugged)
    assert result.blocked == [SEAT_AGENT]
    assert result.linked == []
    assert (directory / SEAT_AGENT).read_text() == "hand-authored"


def test_a_stale_link_of_ours_is_repointed(plugged, seat_repo):
    """A right-named link at a wrong target loads the wrong agent under a name that
    looks correct, so re-pointing it is the fix, exactly as sync relinks."""
    directory = pi.agents_path(plugged)
    directory.mkdir(parents=True)
    stale = seat_repo / "plugins" / "backendish" / "agents" / "old.md"
    (directory / SEAT_AGENT).symlink_to(stale)

    result = pi.converge_agents(plugged)
    assert result.linked == [SEAT_AGENT]
    source = seat_repo / "plugins" / "backendish" / "agents" / SEAT_AGENT
    assert (directory / SEAT_AGENT).resolve() == source.resolve()


def test_the_agents_path_occupied_by_a_file_is_blocked(plugged):
    (plugged / pi.PARENT).mkdir()
    occupant = plugged / pi.PARENT / pi.AGENTS_LEAF
    occupant.write_text("not a directory")

    result = pi.converge_agents(plugged)
    assert result.blocked_dir
    assert occupant.read_text() == "not a directory"


def test_home_is_never_a_project_for_agents_either():
    assert pi.converge_agents(None) is None


# --- P16: the commands converge the agent view --------------------------------


def test_add_of_a_plugin_links_its_agents(catalog, effective, home, project):
    add.install_one(catalog, effective, "plugin", "backend", False, home, project)
    entry = pi.agents_path(project) / "backend-staff-engineer.md"
    assert entry.is_symlink()
    source = CLAUDE / "plugins" / "backend" / "agents" / "backend-staff-engineer.md"
    assert entry.resolve() == source.resolve()


def test_add_of_a_skill_makes_no_agent_links(catalog, effective, home, project):
    add.install_one(catalog, effective, "skill", "coderabbit", False, home, project)
    assert not pi.agents_path(project).exists()


def test_remove_of_a_plugin_drops_its_agent_links(catalog, effective, home, project, monkeypatch):
    add.install_one(catalog, effective, "plugin", "backend", False, home, project)
    entry = pi.agents_path(project) / "backend-staff-engineer.md"
    assert entry.is_symlink()

    monkeypatch.chdir(project)
    remove.run(
        type("Args", (), {
            "names": ["backend"], "type": "plugin", "want_global": False,
            "group": None, "no_cascade": True,
        })()
    )
    assert not entry.exists()
    assert not pi.agents_path(project).exists()
