"""Group D: `remove` and the project-scope cascade.

The cascade is a function of (installed set, provenance, registry) returning a
set, so D8 to D14 are unit tests over literal dicts. Only the deletions
themselves need real symlinks.
"""

import pytest

from claude_kit import catalog as cat
from claude_kit import errors, scope, state
from claude_kit.commands import add, remove
from conftest import CLAUDE

SKILL = cat.SKILL
AGENT = cat.AGENT
PLUGIN = cat.PLUGIN

PROJECT_SKILL = "coderabbit"
GLOBAL_SKILL = "commit"
MIXED_PARENT = "spec-driven-development"
MIXED_GLOBAL_DEP = "planning-and-task-breakdown"
MIXED_PROJECT_DEPS = ("incremental-implementation", "test-driven-development", "context-engineering")
# The tag MIXED_PARENT carries, whose other members are global. Its project half is
# what a --group run acts on.
MIXED_TAG = "planning"
MIXED_TAG_MEMBER = MIXED_PARENT


# --- a synthetic registry, so cascade cases read at a glance -----------------


def synth(**deps):
    """A catalog of project-scoped skills with the given dependency edges."""
    return {
        (SKILL, name): cat.Artifact(name=name, type=SKILL, dependencies=tuple(needs))
        for name, needs in deps.items()
    }


def keys(*names):
    return {(SKILL, n) for n in names}


# --- D8 to D14: the cascade, pure -------------------------------------------


def test_d8_an_unneeded_dependency_is_cascaded():
    """Given a dependency recorded dep-of and needed by nothing else, Then it goes."""
    catalog = synth(parent=["dep"], dep=[])
    doomed, kept = remove.cascade(
        catalog,
        installed=keys("parent", "dep"),
        provenance={(SKILL, "parent"): state.DIRECT, (SKILL, "dep"): state.dep_of("parent")},
        removing=keys("parent"),
    )
    assert doomed == [(SKILL, "dep")]
    assert kept == []


def test_d9_a_dependency_another_installed_artifact_needs_is_kept():
    """Given two installed parents share a dependency, Then removing one keeps it."""
    catalog = synth(one=["shared"], two=["shared"], shared=[])
    doomed, kept = remove.cascade(
        catalog,
        installed=keys("one", "two", "shared"),
        provenance={
            (SKILL, "one"): state.DIRECT,
            (SKILL, "two"): state.DIRECT,
            (SKILL, "shared"): state.dep_of("one"),
        },
        removing=keys("one"),
    )
    assert doomed == []
    assert kept == [("shared", ["still needed by two"])]


def test_d9_names_every_remaining_dependant():
    catalog = synth(one=["shared"], two=["shared"], three=["shared"], shared=[])
    _, kept = remove.cascade(
        catalog,
        installed=keys("one", "two", "three", "shared"),
        provenance={(SKILL, "shared"): state.dep_of("one")},
        removing=keys("one"),
    )
    assert kept == [("shared", ["still needed by three", "still needed by two"])]


def test_d10_a_directly_installed_dependency_is_kept():
    """History A. tdd was named directly before sdd pulled it in, so removing sdd
    must not take it: the user asked for it in its own right."""
    catalog = synth(sdd=["tdd"], tdd=[])
    doomed, kept = remove.cascade(
        catalog,
        installed=keys("sdd", "tdd"),
        provenance={(SKILL, "sdd"): state.DIRECT, (SKILL, "tdd"): state.DIRECT},
        removing=keys("sdd"),
    )
    assert doomed == []
    assert kept == [("tdd", ["installed directly"])]


def test_history_a_and_history_b_diverge_on_identical_directories():
    """The case that justifies the state file existing at all.

    Same catalog, same installed set, same removal. Only the provenance differs,
    and the correct answers are opposites.
    """
    catalog = synth(sdd=["tdd"], tdd=[])
    installed = keys("sdd", "tdd")

    history_a = {(SKILL, "sdd"): state.DIRECT, (SKILL, "tdd"): state.DIRECT}
    history_b = {(SKILL, "sdd"): state.DIRECT, (SKILL, "tdd"): state.dep_of("sdd")}

    doomed_a, _ = remove.cascade(catalog, installed, history_a, keys("sdd"))
    doomed_b, _ = remove.cascade(catalog, installed, history_b, keys("sdd"))

    assert doomed_a == []
    assert doomed_b == [(SKILL, "tdd")]


def test_d11_a_global_dependency_is_never_a_candidate(catalog, effective, home, project):
    """Given a project parent with a global dependency, Then the global one stays.

    claude-kit in ~/work/api cannot see ~/work/web, so it cannot know the global
    dependency is unneeded. The live case: spec-driven-development needs the global
    planning-and-task-breakdown.
    """
    plan_ = add.plan(catalog, effective, SKILL, MIXED_PARENT, False, home, project, {})
    add.apply(plan_, home, project)
    assert (home / ".claude" / "skills" / MIXED_GLOBAL_DEP).is_symlink()

    removal = remove.plan(
        catalog, SKILL, MIXED_PARENT, False, home, project,
        add.provenance_entries(plan_), no_cascade=False, claude=CLAUDE,
    )
    remove.apply(removal, project)

    assert (home / ".claude" / "skills" / MIXED_GLOBAL_DEP).is_symlink(), (
        "the global dependency must survive"
    )
    for dep in MIXED_PROJECT_DEPS:
        assert not (project / ".claude" / "skills" / dep).exists(), f"{dep} should cascade"


def test_d11_the_cascade_only_considers_the_installed_project_set():
    """A dependency that is not linked in this project cannot be cascaded."""
    catalog = synth(parent=["absent"], absent=[])
    doomed, kept = remove.cascade(
        catalog,
        installed=keys("parent"),
        provenance={(SKILL, "absent"): state.dep_of("parent")},
        removing=keys("parent"),
    )
    assert doomed == []


def test_d12_removing_a_global_artifact_cascades_nothing(catalog, effective, home, project):
    """~/.claude holds no provenance, and the shared-scope reasoning applies."""
    plan_ = add.plan(catalog, effective, SKILL, "grill-me", True, home, project, {})
    add.apply(plan_, home, project)
    assert (home / ".claude" / "skills" / "grilling").is_symlink()

    removal = remove.plan(
        catalog, SKILL, "grill-me", True, home, project, {}, no_cascade=False, claude=CLAUDE,
    )
    assert removal.cascaded == []
    remove.apply(removal, None)
    assert not (home / ".claude" / "skills" / "grill-me").exists()
    assert (home / ".claude" / "skills" / "grilling").is_symlink()


def test_d12_a_global_removal_cannot_reach_into_a_project(catalog, effective, home, project):
    """Given a global artifact's dependency is also linked *in the project*, When the
    global artifact is removed, Then the project's link survives.

    Constructed so the cascade would find a candidate if the global short-circuit
    were missing: without the guard, removing the global grill-me would compute
    dependants over the project's installed set, find the project's grilling
    recorded as its dependency, and delete it. Scope is what forbids that, not the
    absence of anything to find.
    """
    global_parent = add.plan(catalog, effective, SKILL, "grill-me", True, home, project, {})
    add.apply(global_parent, home, project)

    grilling = cat.get(catalog, SKILL, "grilling")
    project_copy = scope.link_path(grilling, scope.PROJECT, home, project)
    project_copy.parent.mkdir(parents=True, exist_ok=True)
    project_copy.symlink_to(grilling.source)
    provenance = {(SKILL, "grilling"): state.dep_of("grill-me")}

    removal = remove.plan(
        catalog, SKILL, "grill-me", True, home, project, provenance, no_cascade=False, claude=CLAUDE,
    )
    assert removal.cascaded == [], "a global removal must not consider project links"
    remove.apply(removal, None)
    assert project_copy.is_symlink(), "the project's own link must survive"


def test_d13_the_cascade_is_transitive():
    """A cascaded skill's own dependencies become candidates in turn."""
    catalog = synth(top=["mid"], mid=["leaf"], leaf=[])
    doomed, _ = remove.cascade(
        catalog,
        installed=keys("top", "mid", "leaf"),
        provenance={
            (SKILL, "top"): state.DIRECT,
            (SKILL, "mid"): state.dep_of("top"),
            (SKILL, "leaf"): state.dep_of("mid"),
        },
        removing=keys("top"),
    )
    assert doomed == [(SKILL, "leaf"), (SKILL, "mid")]


def test_d13_a_transitive_cascade_stops_at_a_direct_install():
    """Keeping mid must also keep leaf, since mid still needs it."""
    catalog = synth(top=["mid"], mid=["leaf"], leaf=[])
    doomed, kept = remove.cascade(
        catalog,
        installed=keys("top", "mid", "leaf"),
        provenance={
            (SKILL, "top"): state.DIRECT,
            (SKILL, "mid"): state.DIRECT,
            (SKILL, "leaf"): state.dep_of("mid"),
        },
        removing=keys("top"),
    )
    assert doomed == []
    assert dict(kept)["mid"] == ["installed directly"]


def test_d14_an_untracked_dependency_is_kept():
    """Given no provenance record, Then it is kept and said to be untracked.

    Absent provenance must never cause a deletion: a wrong keep costs one stale
    link, a wrong delete loses something the user may have hand-placed.
    """
    catalog = synth(parent=["dep"], dep=[])
    doomed, kept = remove.cascade(
        catalog,
        installed=keys("parent", "dep"),
        provenance={(SKILL, "parent"): state.DIRECT},
        removing=keys("parent"),
    )
    assert doomed == []
    assert kept == [("dep", ["not tracked by claude-kit"])]


def test_d14_an_untracked_artifact_still_counts_as_a_dependant():
    """A hand-made symlink keeps its dependencies alive."""
    catalog = synth(tracked=["shared"], handmade=["shared"], shared=[])
    doomed, kept = remove.cascade(
        catalog,
        installed=keys("tracked", "handmade", "shared"),
        provenance={
            (SKILL, "tracked"): state.DIRECT,
            (SKILL, "shared"): state.dep_of("tracked"),
        },
        removing=keys("tracked"),
    )
    assert doomed == []
    assert kept == [("shared", ["still needed by handmade"])]


def test_a_diamond_is_cascaded_once():
    catalog = synth(top=["left", "right"], left=["shared"], right=["shared"], shared=[])
    doomed, _ = remove.cascade(
        catalog,
        installed=keys("top", "left", "right", "shared"),
        provenance={
            (SKILL, "top"): state.DIRECT,
            (SKILL, "left"): state.dep_of("top"),
            (SKILL, "right"): state.dep_of("top"),
            (SKILL, "shared"): state.dep_of("left"),
        },
        removing=keys("top"),
    )
    assert doomed == [(SKILL, "left"), (SKILL, "right"), (SKILL, "shared")]


def test_a_cycle_terminates():
    catalog = synth(a=["b"], b=["a"])
    doomed, _ = remove.cascade(
        catalog,
        installed=keys("a", "b"),
        provenance={(SKILL, "a"): state.DIRECT, (SKILL, "b"): state.dep_of("a")},
        removing=keys("a"),
    )
    assert doomed == [(SKILL, "b")]


def test_an_agent_counts_as_a_dependant():
    """Every dependency edge names a skill, but an agent or plugin can be the
    dependant, so the installed set has to span all three types."""
    catalog = {
        (SKILL, "parent"): cat.Artifact(name="parent", type=SKILL, dependencies=("shared",)),
        (SKILL, "shared"): cat.Artifact(name="shared", type=SKILL),
        (AGENT, "watcher"): cat.Artifact(name="watcher", type=AGENT, dependencies=("shared",)),
    }
    doomed, kept = remove.cascade(
        catalog,
        installed={(SKILL, "parent"), (SKILL, "shared"), (AGENT, "watcher")},
        provenance={(SKILL, "shared"): state.dep_of("parent")},
        removing={(SKILL, "parent")},
    )
    assert doomed == []
    assert kept == [("shared", ["still needed by watcher"])]


def test_a_plugin_counts_as_a_dependant():
    catalog = {
        (SKILL, "parent"): cat.Artifact(name="parent", type=SKILL, dependencies=("shared",)),
        (SKILL, "shared"): cat.Artifact(name="shared", type=SKILL),
        (PLUGIN, "bundle"): cat.Artifact(name="bundle", type=PLUGIN, dependencies=("shared",)),
    }
    doomed, kept = remove.cascade(
        catalog,
        installed={(SKILL, "parent"), (SKILL, "shared"), (PLUGIN, "bundle")},
        provenance={(SKILL, "shared"): state.dep_of("parent")},
        removing={(SKILL, "parent")},
    )
    assert doomed == []


# --- D1 to D7: basics -------------------------------------------------------


def install(catalog, effective, kind, name, home, project, want_global=False):
    plan_ = add.plan(catalog, effective, kind, name, want_global, home, project, {})
    add.apply(plan_, home, project)
    entries = add.provenance_entries(plan_)
    if entries:
        state.record(project, entries)
    return plan_


def test_d1_the_symlink_goes_and_the_source_stays(catalog, effective, home, project):
    install(catalog, effective, SKILL, PROJECT_SKILL, home, project)
    removal = remove.plan(catalog, SKILL, PROJECT_SKILL, False, home, project, {}, False, CLAUDE)
    remove.apply(removal, project)

    assert not (project / ".claude" / "skills" / PROJECT_SKILL).exists()
    assert (CLAUDE / "skills" / PROJECT_SKILL).is_dir(), "the repo source must be untouched"


def test_d2_a_global_skill_is_removed_from_home(catalog, effective, home, project):
    install(catalog, effective, SKILL, GLOBAL_SKILL, home, project, want_global=True)
    removal = remove.plan(catalog, SKILL, GLOBAL_SKILL, True, home, project, {}, False, CLAUDE)
    remove.apply(removal, None)
    assert not (home / ".claude" / "skills" / GLOBAL_SKILL).exists()


def test_d3_not_installed_is_refused(catalog, effective, home, project):
    removal = remove.plan(catalog, SKILL, PROJECT_SKILL, False, home, project, {}, False, CLAUDE)
    assert removal.code == errors.NOT_INSTALLED
    assert removal.unlink == []


def test_d3_an_unknown_name_is_not_found(catalog, effective, home, project):
    removal = remove.plan(catalog, SKILL, "no-such-thing", False, home, project, {}, False, CLAUDE)
    assert removal.code == errors.NOT_FOUND


def test_d4_a_real_directory_is_refused_and_kept(catalog, effective, home, project):
    """Hand-authored content must survive a remove aimed at the same name."""
    real = project / ".claude" / "skills" / PROJECT_SKILL
    real.mkdir(parents=True)
    (real / "SKILL.md").write_text("mine")

    removal = remove.plan(catalog, SKILL, PROJECT_SKILL, False, home, project, {}, False, CLAUDE)
    assert removal.code == errors.USAGE
    assert "real directory" in removal.message
    assert (real / "SKILL.md").read_text() == "mine"


def test_d5_a_broken_symlink_is_removed(catalog, effective, home, project):
    """Exactly what needs cleaning, so this must succeed rather than refuse."""
    link = project / ".claude" / "skills" / PROJECT_SKILL
    link.parent.mkdir(parents=True)
    link.symlink_to(project / "gone")

    removal = remove.plan(catalog, SKILL, PROJECT_SKILL, False, home, project, {}, False, CLAUDE)
    assert not removal.refused
    remove.apply(removal, project)
    assert not link.is_symlink()


def test_d6_an_agent_is_removed_with_its_suffix(catalog, effective, home, project):
    install(catalog, effective, AGENT, "architect", home, project, want_global=True)
    assert (home / ".claude" / "agents" / "architect.md").is_symlink()
    removal = remove.plan(catalog, AGENT, "architect", True, home, project, {}, False, CLAUDE)
    remove.apply(removal, None)
    assert not (home / ".claude" / "agents" / "architect.md").exists()


def test_d7_no_project_is_refused(catalog, effective, home):
    removal = remove.plan(catalog, SKILL, PROJECT_SKILL, False, home, None, {}, False, CLAUDE)
    assert removal.code == errors.NO_PROJECT


def test_d7_matches_adds_refusal_so_the_two_agree(catalog, effective, home):
    """Asymmetry would let you install somewhere you cannot uninstall from."""
    added = add.plan(catalog, effective, SKILL, PROJECT_SKILL, False, home, None, {})
    removed = remove.plan(catalog, SKILL, PROJECT_SKILL, False, home, None, {}, False, CLAUDE)
    assert added.code == removed.code == errors.NO_PROJECT


def test_d7_the_refusal_mentions_home_and_the_flag(catalog, effective, home):
    removal = remove.plan(catalog, SKILL, PROJECT_SKILL, False, home, None, {}, False, CLAUDE)
    assert "$HOME" in removal.message
    assert "--global" in removal.message


# --- D15: --no-cascade ------------------------------------------------------


def test_d15_no_cascade_removes_only_the_named_artifact(catalog, effective, home, project):
    plan_ = install(catalog, effective, SKILL, MIXED_PARENT, home, project)
    provenance = add.provenance_entries(plan_)

    removal = remove.plan(
        catalog, SKILL, MIXED_PARENT, False, home, project, provenance,
        no_cascade=True, claude=CLAUDE,
    )
    assert removal.cascaded == []
    remove.apply(removal, project)

    assert not (project / ".claude" / "skills" / MIXED_PARENT).exists()
    for dep in MIXED_PROJECT_DEPS:
        assert (project / ".claude" / "skills" / dep).is_symlink()


# --- D16, D17: provenance cleanup -------------------------------------------


def test_d16_provenance_is_dropped_for_everything_removed(catalog, effective, home, project):
    install(catalog, effective, SKILL, MIXED_PARENT, home, project)
    provenance = state.read(project)
    assert (SKILL, MIXED_PARENT) in provenance

    removal = remove.plan(
        catalog, SKILL, MIXED_PARENT, False, home, project, provenance, False, CLAUDE
    )
    remove.apply(removal, project)

    left = state.read(project)
    assert (SKILL, MIXED_PARENT) not in left
    for dep in MIXED_PROJECT_DEPS:
        assert (SKILL, dep) not in left


def test_d17_the_state_file_goes_when_nothing_is_left(catalog, effective, home, project):
    install(catalog, effective, SKILL, PROJECT_SKILL, home, project)
    assert state.path_for(project).is_file()

    removal = remove.plan(
        catalog, SKILL, PROJECT_SKILL, False, home, project, state.read(project), False, CLAUDE
    )
    remove.apply(removal, project)
    assert not state.path_for(project).exists()


# --- --group ---------------------------------------------------------------


def test_a_group_expands_to_what_is_linked_here(catalog, effective, home, project):
    """Not installed is not an error, so expansion filters rather than refusing."""
    install(catalog, effective, SKILL, MIXED_TAG_MEMBER, home, project)

    members, absent = remove.expand_group(catalog, SKILL, MIXED_TAG, False, home, project)
    assert members == [MIXED_TAG_MEMBER]
    assert MIXED_TAG_MEMBER not in absent
    assert absent, "the rest of the tag is not installed"


def test_a_group_expansion_reads_the_scope_the_flag_selects(catalog, effective, home, project):
    install(catalog, effective, SKILL, MIXED_TAG_MEMBER, home, project)

    members, _ = remove.expand_group(catalog, SKILL, MIXED_TAG, True, home, project)
    assert MIXED_TAG_MEMBER not in members, "the project link is not a global one"


def test_a_group_expansion_ignores_a_real_directory(catalog, effective, home, project):
    """Only links claude-kit made are candidates, as the named path already holds."""
    (project / ".claude" / "skills" / MIXED_TAG_MEMBER).mkdir(parents=True)

    members, absent = remove.expand_group(catalog, SKILL, MIXED_TAG, False, home, project)
    assert MIXED_TAG_MEMBER in absent
    assert members == []


def test_end_to_end_a_group_remove_cascades_its_dependencies(kit, project):
    assert kit("add", "--type", "skill", "--group", MIXED_TAG, cwd=project).returncode == errors.OK
    skills = project / ".claude" / "skills"
    assert (skills / MIXED_PARENT).is_symlink()

    result = kit("remove", "--type", "skill", "--group", MIXED_TAG, cwd=project)
    assert result.returncode == errors.OK, result.stderr
    for dep in MIXED_PROJECT_DEPS:
        assert not (skills / dep).exists(), f"{dep} arrived as a dependency and should cascade"
    assert (kit.home / ".claude" / "skills" / MIXED_GLOBAL_DEP).is_symlink(), (
        "a global dependency is always kept: other projects may still need it"
    )


def test_end_to_end_no_cascade_composes_with_a_group(kit, project):
    kit("add", "--type", "skill", "--group", MIXED_TAG, cwd=project)
    result = kit("remove", "--type", "skill", "--group", MIXED_TAG, "--no-cascade", cwd=project)
    assert result.returncode == errors.OK, result.stderr
    for dep in MIXED_PROJECT_DEPS:
        assert (project / ".claude" / "skills" / dep).is_symlink()


def test_end_to_end_removing_a_group_twice_is_not_an_error(kit, project):
    kit("add", "--type", "skill", "--group", MIXED_TAG, cwd=project)
    assert kit("remove", "--type", "skill", "--group", MIXED_TAG, cwd=project).returncode == errors.OK

    again = kit("remove", "--type", "skill", "--group", MIXED_TAG, cwd=project)
    assert again.returncode == errors.OK
    assert "Removed 0 of" in again.stdout


def test_end_to_end_an_unknown_tag_is_not_found(kit, project):
    result = kit("remove", "--type", "skill", "--group", "no-such-tag", cwd=project)
    assert result.returncode == errors.NOT_FOUND


def test_end_to_end_a_group_and_names_together_are_refused(kit, project):
    kit("add", PROJECT_SKILL, "--type", "skill", cwd=project)
    result = kit("remove", PROJECT_SKILL, "--type", "skill", "--group", MIXED_TAG, cwd=project)
    assert result.returncode == errors.USAGE
    assert (project / ".claude" / "skills" / PROJECT_SKILL).is_symlink(), "nothing was removed"


def test_end_to_end_a_group_in_home_refuses_once(kit):
    """One refusal, not one per member: none of them is the thing at fault."""
    result = kit("remove", "--type", "skill", "--group", MIXED_TAG, cwd=kit.home)
    assert result.returncode == errors.NO_PROJECT
    assert result.stderr.count("✗") == 1


# --- end to end ------------------------------------------------------------


def test_end_to_end_the_documented_cascade_case(kit, project):
    """The manual verification from the plan, as a test.

    add tdd, add sdd, remove sdd. Expect tdd kept as direct, the other two project
    dependencies cascaded, and the global one left in ~/.claude.
    """
    tdd = MIXED_PROJECT_DEPS[1]
    assert kit("add", tdd, "--type", "skill", cwd=project).returncode == errors.OK
    assert kit("add", MIXED_PARENT, "--type", "skill", cwd=project).returncode == errors.OK

    result = kit("remove", MIXED_PARENT, "--type", "skill", cwd=project)
    assert result.returncode == errors.OK

    skills = project / ".claude" / "skills"
    assert (skills / tdd).is_symlink(), "named directly first, so it stays"
    assert not (skills / MIXED_PARENT).exists()
    for dep in MIXED_PROJECT_DEPS:
        if dep != tdd:
            assert not (skills / dep).exists(), f"{dep} should have cascaded"
    assert (kit.home / ".claude" / "skills" / MIXED_GLOBAL_DEP).is_symlink()
    assert "Kept" in result.stdout and tdd in result.stdout


def test_end_to_end_without_the_prior_direct_add_everything_cascades(kit, project):
    """History B: the same end state, but tdd was never named directly."""
    assert kit("add", MIXED_PARENT, "--type", "skill", cwd=project).returncode == errors.OK
    assert kit("remove", MIXED_PARENT, "--type", "skill", cwd=project).returncode == errors.OK

    skills = project / ".claude" / "skills"
    for dep in MIXED_PROJECT_DEPS:
        assert not (skills / dep).exists(), f"{dep} should have cascaded"


def test_end_to_end_a_plugin_and_its_skill_dependency(kit, project):
    assert kit("add", "product-team", "--type", "plugin", cwd=project).returncode == errors.OK
    skills = project / ".claude" / "skills"
    assert (skills / "product-team").is_symlink()
    assert (skills / "idea-refine").is_symlink()

    assert kit("remove", "product-team", "--type", "plugin", cwd=project).returncode == errors.OK
    assert not (skills / "product-team").exists()
    assert not (skills / "idea-refine").exists(), "the vendored dependency should cascade"


def test_end_to_end_removing_from_home_is_refused(kit):
    result = kit("remove", PROJECT_SKILL, "--type", "skill", cwd=kit.home)
    assert result.returncode == errors.NO_PROJECT


def test_end_to_end_removing_from_a_directory_outside_any_repo(kit, tmp_path):
    """The round trip in a plain directory, matching what `add` now allows there.

    Symmetry is the point: a scope you can install into must be one you can
    uninstall from, or the tool strands links it created.
    """
    plain = tmp_path / "loose"
    plain.mkdir()
    assert kit("add", PROJECT_SKILL, "--type", "skill", cwd=plain).returncode == errors.OK

    result = kit("remove", PROJECT_SKILL, "--type", "skill", cwd=plain)
    assert result.returncode == errors.OK, result.stderr
    assert not (plain / ".claude" / "skills" / PROJECT_SKILL).exists()
    # D17: the state file goes when it empties rather than lingering as {}.
    assert not (plain / ".claude" / "claude-kit.json").exists()


def test_end_to_end_batch_continues_past_a_failure(kit, project):
    kit("add", PROJECT_SKILL, "--type", "skill", cwd=project)
    result = kit("remove", "no-such-thing", PROJECT_SKILL, "--type", "skill", cwd=project)
    assert result.returncode == errors.NOT_FOUND
    assert not (project / ".claude" / "skills" / PROJECT_SKILL).exists(), (
        "the second name should still have been removed"
    )
