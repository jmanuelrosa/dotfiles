"""Group H: `adopt`, reconstructing a lost claude-kit.json.

Inference is a function of (registry, installed set, existing provenance)
returning records, so most of this is unit tests over literal dicts. Only the
link classification and the write itself need a filesystem.

The test that matters most is test_h2, which feeds the inferred records straight
into remove.cascade: the point of the command is not the file it writes but the
cascade the file restores.
"""

import pytest

from claude_kit import catalog as cat
from claude_kit import checks, errors, scope, state
from claude_kit.commands import adopt, listing, remove
from conftest import CLAUDE

SKILL = cat.SKILL
AGENT = cat.AGENT
PLUGIN = cat.PLUGIN


def synth(**deps):
    """A catalog of skills with the given dependency edges. Mirrors test_remove."""
    return {
        (SKILL, name): cat.Artifact(name=name, type=SKILL, dependencies=tuple(needs))
        for name, needs in deps.items()
    }


def keys(*names):
    return {(SKILL, n) for n in names}


def link(directory, name, target):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).symlink_to(target)


# --- H1: what nothing declares is deliberate --------------------------------


def test_h1_a_skill_nothing_declares_is_recorded_direct():
    catalog = synth(alone=[])
    assert adopt.infer(catalog, keys("alone"), {}) == {(SKILL, "alone"): state.DIRECT}


def test_h1_a_parent_is_recorded_direct_even_though_it_has_dependencies():
    """Declaring dependencies says nothing about how the parent itself arrived."""
    catalog = synth(parent=["dep"], dep=[])
    entries = adopt.infer(catalog, keys("parent", "dep"), {})
    assert entries[(SKILL, "parent")] == state.DIRECT


def test_h1_a_declared_dependency_that_is_not_installed_is_not_recorded():
    """Provenance describes links, so an absent skill must not acquire a row or
    doctor would immediately report it as stale-provenance."""
    catalog = synth(parent=["dep"], dep=[])
    assert adopt.infer(catalog, keys("parent"), {}) == {(SKILL, "parent"): state.DIRECT}


def test_h1_an_artifact_outside_the_registry_is_still_recorded():
    """A link whose registry row was removed upstream is real and installed. Calling
    it direct keeps the cascade from ever deleting something we cannot reason about."""
    assert adopt.infer({}, keys("vanished"), {}) == {(SKILL, "vanished"): state.DIRECT}


# --- H2: what something declares is a dependency ----------------------------


def test_h2_a_declared_skill_is_recorded_as_a_dependency():
    catalog = synth(parent=["dep"], dep=[])
    entries = adopt.infer(catalog, keys("parent", "dep"), {})
    assert entries[(SKILL, "dep")] == state.dep_of("parent")


def test_h2_the_inferred_records_restore_the_cascade():
    """The whole point of the command.

    Without a file, remove takes the "no record, so keep it" branch and the project
    keeps a dependency nothing needs. Adoption has to produce exactly what a clean
    `add parent` would have written, judged by the cascade rather than by the JSON.
    """
    catalog = synth(parent=["dep"], dep=[])
    installed = keys("parent", "dep")

    without = remove.cascade(catalog, installed, {}, {(SKILL, "parent")})
    assert without == ([], [("dep", ["not tracked by claude-kit"])]), "the bug being fixed"

    adopted = adopt.infer(catalog, installed, {})
    doomed, kept = remove.cascade(catalog, installed, adopted, {(SKILL, "parent")})
    assert doomed == [(SKILL, "dep")]
    assert kept == []


def test_h2_a_transitive_chain_records_the_immediate_parent():
    """add records the parent it walked through, not the root of the closure."""
    catalog = synth(root=["middle"], middle=["leaf"], leaf=[])
    entries = adopt.infer(catalog, keys("root", "middle", "leaf"), {})
    assert entries[(SKILL, "middle")] == state.dep_of("root")
    assert entries[(SKILL, "leaf")] == state.dep_of("middle")


def test_h2_a_diamond_picks_the_alphabetically_first_parent():
    """Two installed dependants and no way to know which one pulled it in.

    The choice is deliberately arbitrary because it cannot matter: remove.cascade
    recomputes dependants from the registry and reads the record only through
    is_direct, so the stored name reaches `list` and doctor's wording and nothing
    else. Pinned so the file does not churn between runs.
    """
    catalog = synth(zebra=["shared"], apple=["shared"], shared=[])
    entries = adopt.infer(catalog, keys("zebra", "apple", "shared"), {})
    assert entries[(SKILL, "shared")] == state.dep_of("apple")


def test_h2_a_dependency_cycle_terminates():
    """Not in the registry today, but inference must not hang if one appears."""
    catalog = synth(a=["b"], b=["a"])
    entries = adopt.infer(catalog, keys("a", "b"), {})
    assert entries == {(SKILL, "a"): state.dep_of("b"), (SKILL, "b"): state.dep_of("a")}


def test_h2_only_skills_can_be_recorded_as_dependencies(catalog):
    """Every dependency edge names a skill, so an agent or plugin is always direct.

    Checked against the real registries rather than a synthetic pair, since this is
    a claim about the vocabulary rather than about the algorithm.
    """
    installed = {(AGENT, "architect"), (PLUGIN, "backend")}
    entries = adopt.infer(catalog, installed, {})
    assert entries == {(AGENT, "architect"): state.DIRECT, (PLUGIN, "backend"): state.DIRECT}


def test_h2_an_agent_counts_as_a_parent_of_its_declared_skill(catalog):
    """A cross-type edge: `architect` declares planning-and-task-breakdown."""
    parent = cat.get(catalog, AGENT, "architect")
    dep = parent.dependencies[0]
    entries = adopt.infer(catalog, {(AGENT, "architect"), (SKILL, dep)}, {})
    assert entries[(SKILL, dep)] == state.dep_of("architect")


def test_h2_a_dependency_only_skill_needs_no_special_case(catalog):
    """It cannot have been added directly, but nothing extra is required: its parent
    being installed is already what makes it a dependency."""
    entries = adopt.infer(catalog, {(SKILL, "grill-me"), (SKILL, "grilling")}, {})
    assert entries[(SKILL, "grilling")] == state.dep_of("grill-me")
    assert entries[(SKILL, "grill-me")] == state.DIRECT


# --- H3: existing records are never touched ---------------------------------


def test_h3_a_recorded_direct_survives_becoming_a_declared_dependency():
    """History A. The user named this skill, so re-running adopt after installing a
    parent must not arm the cascade against it."""
    catalog = synth(parent=["dep"], dep=[])
    provenance = {(SKILL, "dep"): state.DIRECT}
    assert (SKILL, "dep") not in adopt.infer(catalog, keys("parent", "dep"), provenance)


def test_h3_a_recorded_dependency_is_left_alone():
    catalog = synth(parent=["dep"], dep=[])
    provenance = {(SKILL, "dep"): state.dep_of("someone-else")}
    assert (SKILL, "dep") not in adopt.infer(catalog, keys("parent", "dep"), provenance)


def test_h3_a_partially_recorded_project_is_topped_up():
    """The fish-era project that later had one skill added through claude-kit."""
    catalog = synth(parent=["dep"], dep=[], other=[])
    provenance = {(SKILL, "other"): state.DIRECT}
    entries = adopt.infer(catalog, keys("parent", "dep", "other"), provenance)
    assert set(entries) == {(SKILL, "parent"), (SKILL, "dep")}


def test_h3_nothing_installed_yields_no_records():
    """An empty result is what keeps D17 intact: write() would delete the file."""
    assert adopt.infer(synth(a=[]), set(), {}) == {}


# --- H4: --type narrows the output, never the inputs ------------------------


def test_h4_type_narrows_the_recorded_entries(catalog):
    installed = {(AGENT, "architect"), (PLUGIN, "backend")}
    assert set(adopt.infer(catalog, installed, {}, AGENT)) == {(AGENT, "architect")}


def test_h4_a_filtered_out_parent_still_decides_its_dependency(catalog):
    """The distinction doctor.collect draws, and the one that is easy to get wrong.

    Narrowing the *inputs* would hide the agent, leaving its skill looking like
    nothing declared it, and adopt --type skill would then record a dependency as
    direct. Filtering the output keeps the answer identical to an unnarrowed run.
    """
    parent = cat.get(catalog, AGENT, "architect")
    dep = parent.dependencies[0]
    installed = {(AGENT, "architect"), (SKILL, dep)}
    entries = adopt.infer(catalog, installed, {}, SKILL)
    assert entries == {(SKILL, dep): state.dep_of("architect")}


# --- H5: reading the project off disk ---------------------------------------


def test_h5_only_links_into_our_store_are_adopted(catalog, tmp_path, home):
    """A hand-authored directory and a link pointing elsewhere are not ours."""
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    link(skills, "coderabbit", CLAUDE / "skills" / "coderabbit")
    (skills / "hand-written").mkdir()
    link(skills, "foreign", tmp_path / "somewhere-else")

    assert scope.installed_pairs(project, CLAUDE) == {(SKILL, "coderabbit")}


def test_h5_a_skill_and_a_plugin_sharing_a_name_are_told_apart(catalog, tmp_path):
    """Both live in .claude/skills/, so only the store they resolve into decides."""
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    link(skills, "backend", CLAUDE / "plugins" / "backend")
    link(skills, "coderabbit", CLAUDE / "skills" / "coderabbit")

    assert scope.installed_pairs(project, CLAUDE) == {
        (PLUGIN, "backend"),
        (SKILL, "coderabbit"),
    }


def test_h5_agents_are_adopted_from_their_own_leaf(catalog, tmp_path):
    project = tmp_path / "project"
    link(project / ".claude" / "agents", "architect.md", CLAUDE / "agents" / "architect.md")
    assert scope.installed_pairs(project, CLAUDE) == {(AGENT, "architect")}


def test_h5_adoption_silences_the_untracked_install_notes(catalog, tmp_path):
    """Closes the loop with doctor: G13 names this command, so running it must make
    the notes go away rather than merely change their wording."""
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    for name in ("spec-driven-development", "context-engineering"):
        link(skills, name, CLAUDE / "skills" / name)

    before = checks.provenance_drift(catalog, {}, project, CLAUDE)
    assert [f for f in before if f.check == "untracked-install"]

    entries = adopt.infer(catalog, scope.installed_pairs(project, CLAUDE), {})
    state.record(project, entries)

    after = checks.provenance_drift(catalog, state.read(project), project, CLAUDE)
    assert [f for f in after if f.check == "untracked-install"] == []
    assert [f for f in after if f.is_problem] == []


def test_h5_adoption_restores_the_parent_annotation_in_list(catalog, tmp_path, home):
    """The other consumer of the record. `list` reads `parent` for its (needs:)
    annotation, so a recovered manifest has to show up there too."""
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    for name in ("spec-driven-development", "context-engineering"):
        link(skills, name, CLAUDE / "skills" / name)

    state.record(project, adopt.infer(catalog, scope.installed_pairs(project, CLAUDE), {}))
    rows = listing.rows(
        catalog,
        SKILL,
        scope.global_set(catalog),
        home,
        project,
        state.read(project),
        claude=CLAUDE,
    )

    by_name = {row["name"]: row for row in rows}
    assert by_name["context-engineering"]["parent"] == "spec-driven-development"
    assert by_name["spec-driven-development"]["parent"] is None


# --- H6: the report ---------------------------------------------------------


def collect(entries, kind=None, dry_run=False, project=None):
    lines = []
    code = adopt.report(entries, kind, dry_run, project, emit=lines.append)
    return code, "\n".join(lines)


def test_h6_an_empty_result_is_success_not_a_refusal(tmp_path):
    code, text = collect({}, project=tmp_path)
    assert code == errors.OK
    assert "Nothing to adopt" in text


def test_h6_the_report_names_every_entry_and_its_reason(tmp_path):
    entries = {
        (SKILL, "parent"): state.DIRECT,
        (SKILL, "dep"): state.dep_of("parent"),
    }
    code, text = collect(entries, project=tmp_path)
    assert code == errors.OK
    assert "skill 'dep'" in text and state.dep_of("parent") in text
    assert "2 skill(s)." in text
    assert "--dry-run" not in text


def test_h6_a_dry_run_says_so(tmp_path):
    code, text = collect({(SKILL, "a"): state.DIRECT}, dry_run=True, project=tmp_path)
    assert code == errors.OK
    assert "Would record" in text
    assert "Nothing written (--dry-run)." in text


# --- H7: end to end through the shim ---------------------------------------


def test_h7_adopt_in_home_refuses_without_writing(kit):
    """~/.claude carries no provenance, so there is nothing to adopt there."""
    result = kit("adopt")
    assert result.returncode == errors.NO_PROJECT
    assert not (kit.home / ".claude" / state.FILENAME).exists()


def test_h7_a_dry_run_writes_nothing(kit, project):
    link(project / ".claude" / "skills", "coderabbit", CLAUDE / "skills" / "coderabbit")

    result = kit("adopt", "--dry-run", cwd=project)
    assert result.returncode == errors.OK
    assert "coderabbit" in result.stdout
    assert not state.path_for(project).exists()


def test_h7_adopt_then_remove_cascades(kit, project):
    """The request in full: a project with links and no manifest, made removable."""
    skills = project / ".claude" / "skills"
    for name in ("spec-driven-development", "context-engineering"):
        link(skills, name, CLAUDE / "skills" / name)

    assert kit("adopt", cwd=project).returncode == errors.OK
    assert state.read(project)[(SKILL, "context-engineering")] == state.dep_of(
        "spec-driven-development"
    )

    result = kit("remove", "spec-driven-development", "--type", "skill", cwd=project)
    assert result.returncode == errors.OK
    assert not (skills / "context-engineering").is_symlink(), result.stdout
    # D17: the last record going takes the file with it.
    assert not state.path_for(project).exists()


def test_h7_adopt_is_idempotent(kit, project):
    link(project / ".claude" / "skills", "coderabbit", CLAUDE / "skills" / "coderabbit")

    assert kit("adopt", cwd=project).returncode == errors.OK
    first = state.path_for(project).read_text()

    second = kit("adopt", cwd=project)
    assert second.returncode == errors.OK
    assert "Nothing to adopt" in second.stdout
    assert state.path_for(project).read_text() == first
