"""Group C: `add`.

plan() is pure, so the refusal ladder and dependency scoping are tested by import.
Only placement and provenance need real symlinks.

Named artifacts, chosen once so the cases read concretely. Guarded below, because
a test that silently starts exercising the wrong branch is worse than one that
fails loudly.
"""

import json
import os

import pytest

from claude_kit import catalog as cat
from claude_kit import errors, scope, state
from claude_kit.commands import add
from dotkit.testing import CLAUDE

PROJECT_SKILL = "coderabbit"
GLOBAL_SKILL = "commit"
GLOBAL_AGENT = "architect"
PROJECT_PLUGIN = "backend"
DEP_ONLY_SKILL = "grilling"
# Project-scoped, with one global dependency and three project ones. The only
# artifact in the registry that exercises cross-scope dependency resolution.
MIXED_PARENT = "spec-driven-development"
MIXED_GLOBAL_DEP = "planning-and-task-breakdown"
MIXED_PROJECT_DEPS = ("incremental-implementation", "test-driven-development", "context-engineering")
# A tag straddling both scopes, which is what makes --group a partition rather than
# a list of names, and a tag whose whole membership is global.
MIXED_TAG = "planning"
MIXED_TAG_PROJECT = ("idea-refine", "spec-driven-development")
MIXED_TAG_GLOBAL = ("grill-me", "grill-with-docs", "planning-and-task-breakdown")
GLOBAL_ONLY_TAG = ("architecture", cat.AGENT)


@pytest.fixture(scope="module", autouse=True)
def _fixtures_still_valid(catalog, effective):
    """Fail loudly if a registry edit invalidates the chosen artifacts."""
    assert not scope.belongs_global(cat.get(catalog, cat.SKILL, PROJECT_SKILL), effective)
    assert scope.belongs_global(cat.get(catalog, cat.SKILL, GLOBAL_SKILL), effective)
    assert scope.belongs_global(cat.get(catalog, cat.AGENT, GLOBAL_AGENT), effective)
    assert not scope.belongs_global(cat.get(catalog, cat.PLUGIN, PROJECT_PLUGIN), effective)
    assert cat.get(catalog, cat.SKILL, DEP_ONLY_SKILL).dependency_only
    parent = cat.get(catalog, cat.SKILL, MIXED_PARENT)
    assert not scope.belongs_global(parent, effective)
    assert MIXED_GLOBAL_DEP in parent.dependencies
    assert scope.belongs_global(cat.get(catalog, cat.SKILL, MIXED_GLOBAL_DEP), effective)
    for dep in MIXED_PROJECT_DEPS:
        assert not scope.belongs_global(cat.get(catalog, cat.SKILL, dep), effective)
    tagged = {a.name for a in cat.in_group(catalog, cat.SKILL, MIXED_TAG)}
    assert tagged == set(MIXED_TAG_PROJECT) | set(MIXED_TAG_GLOBAL)
    tag, kind = GLOBAL_ONLY_TAG
    members = cat.in_group(catalog, kind, tag)
    assert members and all(scope.belongs_global(a, effective) for a in members)


def make_plan(catalog, effective, kind, name, *, want_global=False, home=None, project=None, provenance=None):
    return add.plan(catalog, effective, kind, name, want_global, home, project, provenance or {})


def scopes_of(plan_):
    return {step.artifact.name: step.scope for step in plan_.steps}


# --- C1 to C4b: placement ---------------------------------------------------


def test_c1_a_project_skill_lands_in_the_project(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    add.apply(plan_, home, project)

    link = project / ".claude" / "skills" / PROJECT_SKILL
    assert link.is_symlink()
    assert link.resolve() == (CLAUDE / "skills" / PROJECT_SKILL).resolve()


def test_c1_a_project_skill_leaves_home_untouched(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    add.apply(plan_, home, project)
    assert list((home / ".claude").iterdir()) == []


def test_c2_an_agent_gets_the_md_suffix_and_agents_leaf(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.AGENT, GLOBAL_AGENT, want_global=True, home=home, project=project)
    add.apply(plan_, home, project)
    assert (home / ".claude" / "agents" / f"{GLOBAL_AGENT}.md").is_symlink()


def test_c3_a_plugin_is_a_directory_symlink_in_the_skills_leaf(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.PLUGIN, PROJECT_PLUGIN, home=home, project=project)
    add.apply(plan_, home, project)

    link = project / ".claude" / "skills" / PROJECT_PLUGIN
    assert link.is_symlink()
    assert link.is_dir()
    assert (link / ".claude-plugin" / "plugin.json").is_file()


def test_c3_a_plugin_says_a_restart_is_needed(catalog, effective, home, project, capsys):
    """The `home` fixture makes ~/.claude but no ~/.claude.json, so this is also the
    untrusted case: the hint checks the workspace rather than asserting as prose that it
    must be trusted, because nobody could act on the prose without checking anyway."""
    args = _args(cat.PLUGIN, [PROJECT_PLUGIN])
    _run_in(args, project)
    out = capsys.readouterr().out
    assert "Restart Claude Code" in out
    assert "not a trusted workspace" in out
    assert "claude-kit trust --on" in out


def test_c3b_a_trusted_workspace_gets_no_trust_warning(catalog, effective, home, project, capsys):
    (home / ".claude.json").write_text(
        json.dumps({"projects": {str(project.resolve()): {"hasTrustDialogAccepted": True}}})
    )
    _run_in(_args(cat.PLUGIN, [PROJECT_PLUGIN]), project)
    out = capsys.readouterr().out
    assert "Restart Claude Code" in out
    assert "trusted workspace" not in out


def test_c4b_the_leaf_directory_is_created(catalog, effective, home, project):
    assert not (project / ".claude").exists()
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    add.apply(plan_, home, project)
    assert (project / ".claude" / "skills").is_dir()


# --- C5 to C10: --global ----------------------------------------------------


def test_c5_a_global_skill_without_the_flag_is_refused(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, GLOBAL_SKILL, home=home, project=project)
    assert plan_.code == errors.WRONG_SCOPE
    assert plan_.steps == []


def test_c5_the_refusal_prints_the_corrected_command(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, GLOBAL_SKILL, home=home, project=project)
    assert f"claude-kit add {GLOBAL_SKILL} --type skill --global" in plan_.message


def test_c5_applies_to_a_skill_global_only_by_dependency(catalog, effective, home, project):
    """MIXED_GLOBAL_DEP carries no tag; it is global because a global agent needs it.
    The refusal must still fire, and should say why."""
    art = cat.get(catalog, cat.SKILL, MIXED_GLOBAL_DEP)
    assert not art.tagged_global
    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_GLOBAL_DEP, home=home, project=project)
    assert plan_.code == errors.WRONG_SCOPE
    assert "required by a global artifact" in plan_.message


def test_c5_a_tagged_skill_says_it_carries_the_tag(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, GLOBAL_SKILL, home=home, project=project)
    assert "carries the global tag" in plan_.message


def test_c6_a_global_skill_with_the_flag_lands_in_home(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, GLOBAL_SKILL, want_global=True, home=home, project=project)
    add.apply(plan_, home, project)
    assert (home / ".claude" / "skills" / GLOBAL_SKILL).is_symlink()
    assert not (project / ".claude").exists()


def test_c7_an_untagged_skill_with_the_flag_lands_in_home(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, want_global=True, home=home, project=project)
    add.apply(plan_, home, project)
    assert (home / ".claude" / "skills" / PROJECT_SKILL).is_symlink()


def test_c7_no_pin_record_is_written_anywhere(catalog, effective, home, project):
    """The symlink outside the effective global set is itself the evidence."""
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, want_global=True, home=home, project=project)
    add.apply(plan_, home, project)
    assert add.provenance_entries(plan_) == {}
    assert not (home / ".claude" / "claude-kit.json").exists()
    assert not (project / ".claude" / "claude-kit.json").exists()


def test_c8_global_needs_no_project(catalog, effective, home):
    plan_ = make_plan(catalog, effective, cat.SKILL, GLOBAL_SKILL, want_global=True, home=home, project=None)
    assert not plan_.refused
    add.apply(plan_, home, None)
    assert (home / ".claude" / "skills" / GLOBAL_SKILL).is_symlink()


def test_c10_a_global_dependency_needs_no_flag(catalog, effective, home, project):
    """The live case: a project skill whose dependency belongs in ~/.claude."""
    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_PARENT, home=home, project=project)
    assert not plan_.refused
    placed = scopes_of(plan_)
    assert placed[MIXED_PARENT] == scope.PROJECT
    assert placed[MIXED_GLOBAL_DEP] == scope.GLOBAL
    for dep in MIXED_PROJECT_DEPS:
        assert placed[dep] == scope.PROJECT


def test_c10_each_dependency_lands_in_its_own_scope_on_disk(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_PARENT, home=home, project=project)
    add.apply(plan_, home, project)
    assert (home / ".claude" / "skills" / MIXED_GLOBAL_DEP).is_symlink()
    assert not (project / ".claude" / "skills" / MIXED_GLOBAL_DEP).exists()
    for dep in MIXED_PROJECT_DEPS:
        assert (project / ".claude" / "skills" / dep).is_symlink()


def test_c10_no_provenance_is_recorded_for_a_global_dependency(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_PARENT, home=home, project=project)
    entries = add.provenance_entries(plan_)
    assert (cat.SKILL, MIXED_GLOBAL_DEP) not in entries


# --- C11 to C15: refusals ---------------------------------------------------


def test_c12_no_project_is_refused(catalog, effective, home):
    """project=None now means one thing only: cwd is $HOME."""
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=None)
    assert plan_.code == errors.NO_PROJECT
    assert plan_.steps == []


def test_c12_the_refusal_offers_global_as_the_remedy(catalog, effective, home):
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=None)
    assert "--global" in plan_.message


def test_c12_the_home_refusal_explains_why(catalog, effective, home):
    """The message must name the cause it actually hit.

    It used to describe $HOME for every NO_PROJECT, including a plain directory
    outside any repo, so the explanation contradicted what the user was looking at.
    Now that $HOME is the only cause, naming it is correct rather than confusing.
    """
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=None)
    assert "$HOME" in plan_.message
    assert "repo" not in plan_.message, "a repo is no longer what makes a project"


def test_c13_a_dependency_only_skill_is_refused(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, DEP_ONLY_SKILL, home=home, project=project)
    assert plan_.code == errors.DEPENDENCY_ONLY
    assert plan_.steps == []


def test_c13_refused_even_with_global(catalog, effective, home, project):
    """DEP_ONLY_SKILL is also effectively global, so the ladder order matters: the
    dependency-only refusal must win, since --global cannot fix it."""
    plan_ = make_plan(catalog, effective, cat.SKILL, DEP_ONLY_SKILL, want_global=True, home=home, project=project)
    assert plan_.code == errors.DEPENDENCY_ONLY


def test_c14_already_installed_is_refused(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    add.apply(plan_, home, project)
    again = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    assert again.code == errors.ALREADY


def test_c14_the_existing_link_is_untouched(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    add.apply(plan_, home, project)
    link = project / ".claude" / "skills" / PROJECT_SKILL
    before = link.readlink()
    make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    assert link.readlink() == before


def test_c14_project_and_global_are_separate_targets(catalog, effective, home, project):
    """An untagged skill installed globally does not block a project install."""
    globally = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, want_global=True, home=home, project=project)
    add.apply(globally, home, project)
    locally = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    assert not locally.refused


def test_c15_an_unknown_name_is_not_found(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, "no-such-thing", home=home, project=project)
    assert plan_.code == errors.NOT_FOUND
    assert "not a known skill" in plan_.message


def test_a3_the_type_is_authoritative_with_no_cross_type_fallback(catalog, effective, home, project):
    """Given a name that exists only as a plugin, When --type skill, Then NOT_FOUND."""
    assert cat.get(catalog, cat.PLUGIN, PROJECT_PLUGIN) is not None
    assert cat.get(catalog, cat.SKILL, PROJECT_PLUGIN) is None
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_PLUGIN, home=home, project=project)
    assert plan_.code == errors.NOT_FOUND


def test_c15_registered_but_missing_reads_differently_from_unknown(catalog, effective, home, project, tmp_path):
    ghost = cat.Artifact(name="ghost", type=cat.SKILL, source=tmp_path / "nowhere")
    doctored = {**catalog, (cat.SKILL, "ghost"): ghost}
    plan_ = make_plan(doctored, effective, cat.SKILL, "ghost", home=home, project=project)
    assert plan_.code == errors.NOT_FOUND
    assert "missing from the repo" in plan_.message


# --- C16 to C21: dependencies ----------------------------------------------


def test_c17_an_installed_dependency_does_not_abort_the_parent(catalog, effective, home, project):
    dep = cat.get(catalog, cat.SKILL, MIXED_PROJECT_DEPS[0])
    target = scope.link_path(dep, scope.PROJECT, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(dep.source)

    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_PARENT, home=home, project=project)
    assert not plan_.refused
    assert dep.name not in scopes_of(plan_), "an installed dependency should not be re-linked"
    assert MIXED_PARENT in scopes_of(plan_)


def test_c18_an_unknown_dependency_warns_but_still_installs(catalog, effective, home, project):
    parent = cat.Artifact(
        name="parent", type=cat.SKILL, dependencies=("nope",), source=CLAUDE / "skills" / PROJECT_SKILL
    )
    doctored = {**catalog, (cat.SKILL, "parent"): parent}
    plan_ = make_plan(doctored, effective, cat.SKILL, "parent", home=home, project=project)
    assert plan_.code == errors.OK
    assert any("unknown dependency 'nope'" in w for w in plan_.warnings)
    assert "parent" in scopes_of(plan_)


def test_c19_a_dependency_only_skill_installs_as_a_dependency(catalog, effective, home, project):
    """The C13 refusal governs direct naming only. Without this, `add grill-me`
    would be impossible: it needs grilling, which is dependency_only."""
    plan_ = make_plan(catalog, effective, cat.SKILL, "grill-me", want_global=True, home=home, project=project)
    assert not plan_.refused
    assert DEP_ONLY_SKILL in scopes_of(plan_)


def test_c20_a_plugin_installs_its_skill_dependencies(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.PLUGIN, "product-team", home=home, project=project)
    add.apply(plan_, home, project)
    assert (project / ".claude" / "skills" / "product-team").is_symlink()
    assert (project / ".claude" / "skills" / "idea-refine").is_symlink()


def test_c20_the_closure_is_transitive(catalog, effective, home, project):
    """A dependency's own dependencies come too, or the artifact ships broken."""
    leaf = cat.Artifact(name="leaf", type=cat.SKILL, source=CLAUDE / "skills" / PROJECT_SKILL)
    mid = cat.Artifact(name="mid", type=cat.SKILL, dependencies=("leaf",), source=CLAUDE / "skills" / PROJECT_SKILL)
    top = cat.Artifact(name="top", type=cat.SKILL, dependencies=("mid",), source=CLAUDE / "skills" / PROJECT_SKILL)
    doctored = {
        **catalog,
        (cat.SKILL, "leaf"): leaf,
        (cat.SKILL, "mid"): mid,
        (cat.SKILL, "top"): top,
    }
    plan_ = make_plan(doctored, effective, cat.SKILL, "top", home=home, project=project)
    assert {"top", "mid", "leaf"} <= set(scopes_of(plan_))


def test_dependency_cycles_terminate(catalog, effective, home, project):
    source = CLAUDE / "skills" / PROJECT_SKILL
    a = cat.Artifact(name="a", type=cat.SKILL, dependencies=("b",), source=source)
    b = cat.Artifact(name="b", type=cat.SKILL, dependencies=("a",), source=source)
    doctored = {**catalog, (cat.SKILL, "a"): a, (cat.SKILL, "b"): b}
    plan_ = make_plan(doctored, effective, cat.SKILL, "a", home=home, project=project)
    assert {"a", "b"} <= set(scopes_of(plan_))


def test_the_named_artifact_is_linked_last(catalog, effective, home, project):
    """Dependencies first, so an interrupted run never leaves a parent whose
    dependencies are missing."""
    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_PARENT, home=home, project=project)
    assert plan_.steps[-1].artifact.name == MIXED_PARENT
    assert all(step.is_dependency for step in plan_.steps[:-1])


# --- C22 to C25: provenance -------------------------------------------------


def test_c22_the_named_artifact_is_recorded_direct(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    assert add.provenance_entries(plan_) == {(cat.SKILL, PROJECT_SKILL): state.DIRECT}


def test_c22_dependencies_are_recorded_with_their_parent(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_PARENT, home=home, project=project)
    entries = add.provenance_entries(plan_)
    assert entries[(cat.SKILL, MIXED_PARENT)] == state.DIRECT
    for dep in MIXED_PROJECT_DEPS:
        assert entries[(cat.SKILL, dep)] == state.dep_of(MIXED_PARENT)


def test_c24_a_purely_global_install_records_nothing(catalog, effective, home, project):
    plan_ = make_plan(catalog, effective, cat.SKILL, GLOBAL_SKILL, want_global=True, home=home, project=project)
    assert add.provenance_entries(plan_) == {}


def test_c23_naming_a_recorded_dependency_upgrades_it(catalog, effective, home, project, capsys):
    """History A, end to end: tdd arrives for sdd, then is named directly.

    No new symlink is made, but the record must flip to direct. Reporting this as a
    bare ALREADY refusal would leave the record untouched, and removing sdd would
    then delete a skill the user asked for by name.
    """
    dep_name = MIXED_PROJECT_DEPS[1]
    _run_in(_args(cat.SKILL, [MIXED_PARENT]), project)
    assert state.read(project)[(cat.SKILL, dep_name)] == state.dep_of(MIXED_PARENT)

    code = _run_in(_args(cat.SKILL, [dep_name]), project)
    assert code == errors.OK, "the record changed, so this is a success not a refusal"
    assert state.read(project)[(cat.SKILL, dep_name)] == state.DIRECT
    assert "in its own right" in capsys.readouterr().out


def test_c23_no_second_symlink_is_created(catalog, effective, home, project):
    dep_name = MIXED_PROJECT_DEPS[1]
    _run_in(_args(cat.SKILL, [MIXED_PARENT]), project)
    link = project / ".claude" / "skills" / dep_name
    before = link.readlink()
    _run_in(_args(cat.SKILL, [dep_name]), project)
    assert link.readlink() == before


def test_c23_an_already_direct_artifact_is_still_refused(catalog, effective, home, project):
    """C14 survives: promotion only applies when there is a dependency record to
    change. A second `add` of something already wanted directly is a no-op."""
    _run_in(_args(cat.SKILL, [PROJECT_SKILL]), project)
    assert state.read(project)[(cat.SKILL, PROJECT_SKILL)] == state.DIRECT
    assert _run_in(_args(cat.SKILL, [PROJECT_SKILL]), project) == errors.ALREADY


def test_c23_an_untracked_installed_artifact_is_refused_not_promoted(catalog, effective, home, project):
    """Given no record at all, Then ALREADY. Promotion needs a dependency record to
    upgrade; inventing one for a hand-made link would be a guess."""
    art = cat.get(catalog, cat.SKILL, PROJECT_SKILL)
    target = scope.link_path(art, scope.PROJECT, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(art.source)
    plan_ = make_plan(catalog, effective, cat.SKILL, PROJECT_SKILL, home=home, project=project)
    assert plan_.code == errors.ALREADY


def test_c23_promotion_does_not_apply_in_global_scope(catalog, effective, home, project):
    """~/.claude holds no provenance, so there is nothing to promote there."""
    art = cat.get(catalog, cat.SKILL, PROJECT_SKILL)
    target = scope.link_path(art, scope.GLOBAL, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(art.source)
    provenance = {(cat.SKILL, PROJECT_SKILL): state.dep_of("whatever")}
    plan_ = make_plan(
        catalog, effective, cat.SKILL, PROJECT_SKILL, want_global=True,
        home=home, project=project, provenance=provenance,
    )
    assert plan_.code == errors.ALREADY


def test_an_untracked_installed_dependency_is_claimed(catalog, effective, home, project):
    """Given a dependency was linked by hand, When its parent is added, Then we
    record why it is there rather than leaving the cascade blind."""
    dep = cat.get(catalog, cat.SKILL, MIXED_PROJECT_DEPS[0])
    target = scope.link_path(dep, scope.PROJECT, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(dep.source)

    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_PARENT, home=home, project=project)
    assert add.provenance_entries(plan_)[(cat.SKILL, dep.name)] == state.dep_of(MIXED_PARENT)


def test_an_already_tracked_dependency_is_not_reclaimed(catalog, effective, home, project):
    """A direct record must survive its parent being added afterwards."""
    dep = cat.get(catalog, cat.SKILL, MIXED_PROJECT_DEPS[0])
    target = scope.link_path(dep, scope.PROJECT, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(dep.source)
    provenance = {(cat.SKILL, dep.name): state.DIRECT}

    plan_ = make_plan(catalog, effective, cat.SKILL, MIXED_PARENT, home=home, project=project, provenance=provenance)
    assert (cat.SKILL, dep.name) not in add.provenance_entries(plan_)


# --- C26 to C28: batches ---------------------------------------------------


class _Args:
    def __init__(self, kind, names, want_global=False, group=None):
        self.type = kind
        self.names = names
        self.want_global = want_global
        self.group = group
        self.command = "add"


def _args(kind, names, want_global=False, group=None):
    return _Args(kind, names, want_global, group)


def _run_in(args, project):
    """Run add.run with cwd inside the project, as the CLI would.

    try/finally rather than monkeypatch.chdir so the helper needs no fixture at its
    twelve call sites. Restoring cwd is not optional: scope.project_root reads it, so a
    leak would silently retarget every later test in the session.
    """
    previous = os.getcwd()
    os.chdir(project)
    try:
        return add.run(args)
    finally:
        os.chdir(previous)


def test_c26_a_failure_does_not_strand_the_rest(home, project, capsys):
    code = _run_in(_args(cat.SKILL, [PROJECT_SKILL, "no-such-thing", "coderabbit-review"]), project)
    assert code == errors.NOT_FOUND
    assert (project / ".claude" / "skills" / PROJECT_SKILL).is_symlink(), "first name should be installed"


def test_c26_every_name_is_reported(home, project, capsys):
    _run_in(_args(cat.SKILL, [PROJECT_SKILL, "no-such-thing"]), project)
    captured = capsys.readouterr()
    assert PROJECT_SKILL in captured.out
    assert "no-such-thing" in captured.err


def test_c27_the_exit_code_is_the_failures(home, project, capsys):
    code = _run_in(_args(cat.SKILL, [DEP_ONLY_SKILL]), project)
    assert code == errors.DEPENDENCY_ONLY


def test_c28_two_failures_yield_the_first_code(home, project, capsys):
    """DEPENDENCY_ONLY comes first in the call, NOT_FOUND second."""
    code = _run_in(_args(cat.SKILL, [DEP_ONLY_SKILL, "no-such-thing"]), project)
    assert code == errors.DEPENDENCY_ONLY
    err = capsys.readouterr().err
    assert DEP_ONLY_SKILL in err and "no-such-thing" in err, "both failures reported"


def test_c28_order_decides_the_code(home, project, capsys):
    code = _run_in(_args(cat.SKILL, ["no-such-thing", DEP_ONLY_SKILL]), project)
    assert code == errors.NOT_FOUND


def test_a_wholly_successful_batch_exits_ok(home, project, capsys):
    code = _run_in(_args(cat.SKILL, [PROJECT_SKILL, "frontend-design"]), project)
    assert code == errors.OK
    assert (project / ".claude" / "skills" / PROJECT_SKILL).is_symlink()
    assert (project / ".claude" / "skills" / "frontend-design").is_symlink()


# --- --group ---------------------------------------------------------------


def test_a_group_expands_to_the_project_half(catalog, effective):
    members, elsewhere = add.expand_group(catalog, cat.SKILL, MIXED_TAG, False, effective)
    assert set(members) == set(MIXED_TAG_PROJECT)
    assert set(elsewhere) == set(MIXED_TAG_GLOBAL)


def test_the_global_flag_selects_the_other_half(catalog, effective):
    """--global picks which half of a tag to act on, so the two runs are disjoint."""
    members, elsewhere = add.expand_group(catalog, cat.SKILL, MIXED_TAG, True, effective)
    assert set(members) == set(MIXED_TAG_GLOBAL)
    assert set(elsewhere) == set(MIXED_TAG_PROJECT)


def test_an_unknown_tag_expands_to_nothing(catalog, effective):
    assert add.expand_group(catalog, cat.SKILL, "no-such-tag", False, effective) == ([], [])


def test_a_group_installs_its_project_members_only(home, project):
    code = _run_in(_args(cat.SKILL, [], group=MIXED_TAG), project)
    assert code == errors.OK
    for name in MIXED_TAG_PROJECT:
        assert (project / ".claude" / "skills" / name).is_symlink()
    for name in MIXED_TAG_GLOBAL:
        assert not (project / ".claude" / "skills" / name).exists()


def test_the_skipped_half_reaches_home_only_as_a_dependency(home, project):
    """The one global link a project group add may make, and the reason it may.

    MIXED_GLOBAL_DEP is in the skipped half *and* required by a member, so it is
    installed while the members beside it are not: a dependency resolves its own
    scope and consenting to the parent consents to what it needs.
    """
    _run_in(_args(cat.SKILL, [], group=MIXED_TAG), project)
    globals_ = home / ".claude" / "skills"
    assert (globals_ / MIXED_GLOBAL_DEP).is_symlink()
    for name in MIXED_TAG_GLOBAL:
        if name != MIXED_GLOBAL_DEP:
            assert not (globals_ / name).exists()


def test_a_group_member_is_recorded_as_wanted_in_its_own_right(home, project):
    """Named by tag is still named, so a later cascade must not take it."""
    _run_in(_args(cat.SKILL, [], group=MIXED_TAG), project)
    recorded = state.read(project)
    for name in MIXED_TAG_PROJECT:
        assert recorded[(cat.SKILL, name)] == state.DIRECT
    assert recorded[(cat.SKILL, MIXED_PROJECT_DEPS[0])] == state.dep_of(MIXED_PARENT)


def test_a_second_group_run_changes_nothing_and_still_succeeds(home, project, capsys):
    """The idempotence rule: a tag is a set to converge on, not a list of names."""
    _run_in(_args(cat.SKILL, [], group=MIXED_TAG), project)
    capsys.readouterr()

    code = _run_in(_args(cat.SKILL, [], group=MIXED_TAG), project)
    assert code == errors.OK
    out = capsys.readouterr().out
    assert "Already installed" in out
    assert f"Linked 0 of {len(MIXED_TAG_PROJECT) + len(MIXED_TAG_GLOBAL)}" in out


def test_a_group_names_the_half_it_left_alone(home, project, capsys):
    _run_in(_args(cat.SKILL, [], group=MIXED_TAG), project)
    out = capsys.readouterr().out
    assert f"The global half of '{MIXED_TAG}' is untouched" in out
    assert "--global" in out, "the note has to say how to install that half"


def test_a_wholly_global_tag_is_a_no_op_rather_than_a_refusal(home, project, capsys):
    """Nothing to do in this scope is not an error: the other half exists and is named."""
    tag, kind = GLOBAL_ONLY_TAG
    code = _run_in(_args(kind, [], group=tag), project)
    assert code == errors.OK
    out = capsys.readouterr().out
    assert f"The global half of '{tag}' is untouched" in out
    assert not (project / ".claude").exists()


def test_a_group_and_names_together_are_refused(home, project, capsys):
    code = _run_in(_args(cat.SKILL, [PROJECT_SKILL], group=MIXED_TAG), project)
    assert code == errors.USAGE
    assert not (project / ".claude").exists(), "a refused call installs nothing"


def test_neither_a_name_nor_a_group_is_refused(home, project, capsys):
    """argparse allowed no names once --group existed, so run() owns this check."""
    assert _run_in(_args(cat.SKILL, []), project) == errors.USAGE


def test_an_unknown_tag_is_not_found(home, project, capsys):
    code = _run_in(_args(cat.SKILL, [], group="no-such-tag"), project)
    assert code == errors.NOT_FOUND
    assert "list --type skill --group" in capsys.readouterr().err


# --- end to end ------------------------------------------------------------


def test_end_to_end_add_then_refuse(kit, project):
    first = kit("add", PROJECT_SKILL, "--type", "skill", cwd=project)
    assert first.returncode == errors.OK
    assert (project / ".claude" / "skills" / PROJECT_SKILL).is_symlink()

    again = kit("add", PROJECT_SKILL, "--type", "skill", cwd=project)
    assert again.returncode == errors.ALREADY


def test_end_to_end_global_refusal_names_the_flag(kit, project):
    result = kit("add", GLOBAL_SKILL, "--type", "skill", cwd=project)
    assert result.returncode == errors.WRONG_SCOPE
    assert "--global" in result.stderr
    assert not (project / ".claude").exists()


def test_end_to_end_home_is_refused(kit):
    """Running from $HOME must refuse, since $HOME/.claude is ~/.claude.

    The last remaining NO_PROJECT case, so this is the whole guard end to end.
    Nothing may land in ~/.claude/skills: a silent global install is exactly the
    outcome being prevented.
    """
    result = kit("add", PROJECT_SKILL, "--type", "skill", cwd=kit.home)
    assert result.returncode == errors.NO_PROJECT
    assert not (kit.home / ".claude" / "skills").exists()
    assert "$HOME" in result.stderr


def test_end_to_end_a_directory_outside_any_repo_installs(kit, tmp_path):
    """The reported case: `add` in a plain directory with no .git anywhere above.

    Exercised through the shim rather than at the pure altitude because the bug was
    that the real command refused, and only a subprocess run covers cwd resolution,
    leaf creation and the symlink together.
    """
    plain = tmp_path / "loose"
    plain.mkdir()
    (plain / "package.json").write_text("{}\n")

    result = kit("add", PROJECT_SKILL, "--type", "skill", cwd=plain)
    assert result.returncode == errors.OK, result.stderr

    link = plain / ".claude" / "skills" / PROJECT_SKILL
    assert link.is_symlink()
    assert link.resolve() == (CLAUDE / "skills" / PROJECT_SKILL).resolve()
    assert not (kit.home / ".claude" / "skills" / PROJECT_SKILL).exists()


def test_end_to_end_a_subdirectory_installs_into_itself(kit, project):
    """The inverted anchor: cwd wins, so a subdirectory gets its own .claude.

    Previously this landed at the project root. Pinned end to end because it is the
    behaviour change a user is most likely to notice.
    """
    deep = project / "src" / "nested"
    deep.mkdir(parents=True)

    result = kit("add", PROJECT_SKILL, "--type", "skill", cwd=deep)
    assert result.returncode == errors.OK, result.stderr
    assert (deep / ".claude" / "skills" / PROJECT_SKILL).is_symlink()
    assert not (project / ".claude").exists()


def test_end_to_end_writes_provenance(kit, project):
    kit("add", MIXED_PARENT, "--type", "skill", cwd=project)
    recorded = state.read(project)
    assert recorded[(cat.SKILL, MIXED_PARENT)] == state.DIRECT
    for dep in MIXED_PROJECT_DEPS:
        assert recorded[(cat.SKILL, dep)] == state.dep_of(MIXED_PARENT)
    assert (cat.SKILL, MIXED_GLOBAL_DEP) not in recorded
