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


def test_a_symlinked_agents_path_is_blocked_even_when_it_leads_to_a_directory(plugged, tmp_path):
    """A link here is a decision someone made about where pi reads agents.

    Writing through it would put our links in a directory we were never pointed at, so
    it is refused for the same reason a foreign .agents/skills is left alone.
    """
    theirs = tmp_path / "their-agents"
    theirs.mkdir()
    (plugged / pi.PARENT).mkdir()
    pi.agents_path(plugged).symlink_to(theirs)

    result = pi.converge_agents(plugged)
    assert result.blocked_dir
    assert list(theirs.iterdir()) == []


def test_a_broken_symlink_at_the_agents_path_is_blocked_too(plugged, tmp_path):
    (plugged / pi.PARENT).mkdir()
    pi.agents_path(plugged).symlink_to(tmp_path / "gone")

    assert pi.converge_agents(plugged).blocked_dir


def test_home_is_never_a_project_for_agents_either():
    assert pi.converge_agents(None) is None


# --- P15b: two plugins claiming one agent filename -----------------------------
#
# The basename is the only name pi has for an agent, so the collision cannot be
# resolved here in a way that keeps both. What it must not do is pick one silently:
# `claude-kit list` shows both plugins installed and Claude Code loads both from
# inside their own plugins, so this is the only place the repo's one-name-one-artifact
# rule can break without anything saying so.

RIVAL = "aardvark"


@pytest.fixture
def rivals(plugged, seat_repo):
    """A second installed plugin shipping an agent under the first one's filename."""
    agents = seat_repo / "plugins" / RIVAL / "agents"
    agents.mkdir(parents=True)
    (agents / SEAT_AGENT).write_text("---\nname: backendish-staff-engineer\n---\n")
    (plugged / ".claude" / "skills" / RIVAL).symlink_to(seat_repo / "plugins" / RIVAL)
    return plugged


def test_a_filename_two_plugins_claim_is_reported_rather_than_settled(rivals, seat_repo):
    result = pi.converge_agents(rivals)
    assert result.collided == {SEAT_AGENT: [RIVAL, "backendish"]}
    # One of them still reaches pi, because a name pi cannot load at all is worse than
    # an arbitrary winner that was named out loud.
    assert result.linked == [SEAT_AGENT]
    entry = pi.agents_path(rivals) / SEAT_AGENT
    source = seat_repo / "plugins" / RIVAL / "agents" / SEAT_AGENT
    assert entry.resolve() == source.resolve(), "plugin order decides, and it decides stably"


def test_a_collision_outlives_the_run_that_made_the_link(rivals):
    """Idempotence would make this a one-time warning, and the collision is not
    one-time: it is a repo state that stays wrong until a plugin renames its agent."""
    pi.converge_agents(rivals)
    result = pi.converge_agents(rivals)
    assert result is not None
    assert result.linked == []
    assert result.collided == {SEAT_AGENT: [RIVAL, "backendish"]}


def test_the_report_names_both_plugins(rivals, capsys):
    pi.report_agents(pi.converge_agents(rivals), rivals)
    printed = capsys.readouterr()
    text = printed.out + printed.err
    assert RIVAL in text
    assert "backendish" in text
    assert SEAT_AGENT in text


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


# --- P17: doctor, the agents half ---------------------------------------------
#
# G19 one directory over. It needs its own group because the two halves of pi's view
# are converged separately and so fail separately: the skills link is one directory
# link covering every skill, and the agent links are per-file because no single
# directory holds every agent the installed plugins ship.


def test_doctor_reports_plugin_agents_pi_cannot_read(plugged):
    """The state `add` leaves behind if its per-file links are pruned by hand.

    `claude-kit list` still shows the plugin installed and Claude Code loads it, so
    nothing else in the tool reports this.
    """
    found = checks.pi_agents_unreachable(plugged)
    assert len(found) == 1
    assert found[0].check == "pi-agents-unreachable"
    assert SEAT_AGENT in found[0].detail
    # A note, for G19's reason: Claude Code is fine and a machine without pi has
    # nothing to act on.
    assert not found[0].is_problem


def test_doctor_is_quiet_once_the_agent_links_are_there(plugged):
    pi.converge_agents(plugged)
    assert checks.pi_agents_unreachable(plugged) == []


def test_doctor_names_the_occupant_when_something_else_holds_the_agents_path(plugged):
    """A file at .agents/agents is not a directory anything can be written under, and
    the reader needs telling that rather than a list of missing links."""
    path = pi.agents_path(plugged)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not a directory")
    detail = checks.pi_agents_unreachable(plugged)[0].detail
    assert "not a directory" in detail


@pytest.mark.parametrize("occupant", ["directory", "broken"])
def test_doctor_reports_the_occupied_path_for_every_shape_converge_refuses(
    plugged, tmp_path, occupant
):
    """Doctor's remedy is the command converge_agents refuses on, so the two have to
    refuse the same paths.

    A link to a real directory reads as a directory and a broken one reads as absent, so
    both used to fall through to the missing-links branch: the note named `claude-kit
    add`, the command then reported the path as blocked, and nothing the user could do
    from the note cleared it.
    """
    target = tmp_path / "their-agents"
    if occupant == "directory":
        target.mkdir()
    (plugged / pi.PARENT).mkdir()
    pi.agents_path(plugged).symlink_to(target)

    found = checks.pi_agents_unreachable(plugged)
    assert len(found) == 1
    assert "Move it aside" in found[0].detail
    assert SEAT_AGENT not in found[0].detail, "a blocked path is not a list of missing links"


def test_doctor_says_nothing_when_no_plugin_ships_an_agent(project, seat_repo):
    """No agent installed means no agent for pi to be missing, so the check is silent
    rather than reporting an empty directory as a fault."""
    leaf = project / ".claude" / "skills"
    leaf.mkdir(parents=True)
    (leaf / "toolbelt").symlink_to(seat_repo / "plugins" / "toolbelt")
    assert checks.pi_agents_unreachable(project) == []
    assert checks.pi_agents_unreachable(None) == []


def test_doctor_only_counts_agents_the_installed_plugins_ship(plugged):
    """A stray .md nobody declares is not a missing link, so it must not silence or
    inflate the finding."""
    path = pi.agents_path(plugged)
    path.mkdir(parents=True)
    (path / "stray.md").write_text("not ours")
    found = checks.pi_agents_unreachable(plugged)
    assert len(found) == 1
    assert "stray.md" not in found[0].detail


# --- P18: restore and adopt converge it too -----------------------------------
#
# These live here rather than in test_restore.py and test_adopt.py because the
# fixtures and every other "a command converged pi's view" assertion are here, and
# because what is being tested is pi's view rather than either command's own logic.
#
# Both were blind before. `add.install_one` is the seam that converges, so a command
# reaching it inherits the convergence, and each of these had a path that does not.


def test_restore_converges_pi_when_there_was_nothing_to_install(
    catalog, effective, home, project, monkeypatch
):
    """The exact state doctor's pi-unreachable note fires on, and names restore to fix.

    Every recorded artifact already linked, and `.agents/` gone. restore returned on its
    "nothing to restore" branch before reaching install_one, so the command doctor told
    the reader to run could not fix what doctor had reported.
    """
    from claude_kit.commands import restore

    add.install_one(catalog, effective, "skill", "coderabbit", False, home, project)
    assert pi.is_ours(project)

    # Someone deletes the link by hand; the manifest and the .claude links are intact.
    pi.link_path(project).unlink()
    assert checks.pi_skills_unreachable(project)

    monkeypatch.chdir(project)
    restore.run(type("Args", (), {"type": None, "dry_run": False})())

    assert pi.is_ours(project)
    assert checks.pi_skills_unreachable(project) == []


def test_restore_dry_run_still_writes_nothing(catalog, effective, home, project, monkeypatch):
    """The convergence above must not leak into the preview path, or --dry-run stops
    being a preview."""
    from claude_kit.commands import restore

    add.install_one(catalog, effective, "skill", "coderabbit", False, home, project)
    pi.link_path(project).unlink()

    monkeypatch.chdir(project)
    restore.run(type("Args", (), {"type": None, "dry_run": True})())

    assert not pi.link_path(project).exists()


def test_adopt_converges_pi_for_a_project_that_predates_it(
    catalog, effective, home, project, monkeypatch
):
    """adopt's whole population is projects set up before claude-kit, which is exactly
    the population with no .agents/ link, and it wrote only the manifest."""
    from claude_kit.commands import adopt

    add.install_one(catalog, effective, "skill", "coderabbit", False, home, project)
    # Roll the project back to the pre-claude-kit shape: links on disk, no manifest,
    # and nothing pi can read.
    pi.link_path(project).unlink()
    state_file = project / ".claude" / "claude-kit.json"
    if state_file.exists():
        state_file.unlink()

    monkeypatch.chdir(project)
    adopt.run(type("Args", (), {"type": None, "dry_run": False})())

    assert pi.is_ours(project)


def test_adopt_dry_run_writes_neither_manifest_nor_links(
    catalog, effective, home, project, monkeypatch
):
    from claude_kit.commands import adopt

    add.install_one(catalog, effective, "skill", "coderabbit", False, home, project)
    pi.link_path(project).unlink()

    monkeypatch.chdir(project)
    adopt.run(type("Args", (), {"type": None, "dry_run": True})())

    assert not pi.link_path(project).exists()
