"""Group G: `doctor`.

Every check is a pure function over a catalog, so a broken repo is expressed as a
literal Artifact rather than constructed on disk. Only the link-inspecting checks
need real symlinks.
"""

import json

import pytest

from claude_kit import catalog as cat
from claude_kit import checks, errors, scope, state
from claude_kit.commands import add, doctor
from conftest import CLAUDE

SKILL = cat.SKILL
AGENT = cat.AGENT
PLUGIN = cat.PLUGIN

REAL_SKILL_SOURCE = CLAUDE / "skills" / "coderabbit"


def subjects(findings):
    return [f.subject for f in findings]


def by_check(findings, name):
    return [f for f in findings if f.check == name]


# --- G2: missing sources ----------------------------------------------------


def test_g2_a_registered_artifact_absent_from_disk_is_reported(tmp_path):
    ghost = cat.Artifact(name="ghost", type=SKILL, source=tmp_path / "nowhere")
    findings = checks.missing_sources({(SKILL, "ghost"): ghost})
    assert len(findings) == 1
    assert findings[0].is_problem
    assert findings[0].kind == SKILL


def test_g2_the_real_repo_has_no_missing_sources(catalog):
    assert checks.missing_sources(catalog) == []


# --- G3: untracked on disk --------------------------------------------------


def test_g3_a_directory_no_registry_mentions_is_reported(tmp_path):
    claude = tmp_path / "claude"
    (claude / "skills" / "orphan").mkdir(parents=True)
    (claude / "skills" / "known").mkdir()
    catalog = {(SKILL, "known"): cat.Artifact(name="known", type=SKILL)}
    findings = checks.untracked_on_disk(catalog, claude)
    assert subjects(findings) == ["skill 'orphan'"]


def test_g3_hidden_entries_are_ignored(tmp_path):
    claude = tmp_path / "claude"
    (claude / "skills" / ".DS_Store").mkdir(parents=True)
    assert checks.untracked_on_disk({}, claude) == []


def test_g3_a_non_md_file_in_agents_is_ignored(tmp_path):
    claude = tmp_path / "claude"
    (claude / "agents").mkdir(parents=True)
    (claude / "agents" / "README.txt").write_text("x")
    assert checks.untracked_on_disk({}, claude) == []


def test_g3_the_real_repo_has_nothing_untracked(catalog):
    assert checks.untracked_on_disk(catalog, CLAUDE) == []


# --- G4: dangling dependencies ---------------------------------------------


def test_g4_an_edge_naming_nothing_is_reported():
    catalog = {(SKILL, "parent"): cat.Artifact(name="parent", type=SKILL, dependencies=("nope",))}
    findings = checks.dangling_dependencies(catalog)
    assert len(findings) == 1
    assert "'nope'" in findings[0].detail


def test_g4_spans_types_so_it_cannot_be_narrowed():
    """An agent's or plugin's edge points at a skill, so the finding has no single
    type and must be dropped rather than misfiled when --type narrows."""
    catalog = {
        (PLUGIN, "bundle"): cat.Artifact(name="bundle", type=PLUGIN, dependencies=("nope",)),
    }
    findings = checks.dangling_dependencies(catalog)
    assert findings[0].kind is None
    assert cat.PLUGIN_DEPS_KEY in findings[0].detail, "a plugin edge should name skillDependencies"


def test_g4_a_skill_edge_names_the_plain_key():
    catalog = {(SKILL, "s"): cat.Artifact(name="s", type=SKILL, dependencies=("nope",))}
    assert "dependencies names" in checks.dangling_dependencies(catalog)[0].detail


def test_g4_the_real_repo_has_no_dangling_edges(catalog):
    assert checks.dangling_dependencies(catalog) == []


# --- G5: orphaned dependency_only ------------------------------------------


def test_g5_a_dependency_only_skill_nothing_needs_is_reported():
    catalog = {
        (SKILL, "lonely"): cat.Artifact(name="lonely", type=SKILL, dependency_only=True),
    }
    findings = checks.orphaned_dependency_only(catalog)
    assert subjects(findings) == ["skill 'lonely'"]
    assert "can never be installed" in findings[0].detail


def test_g5_one_that_is_depended_on_is_fine():
    catalog = {
        (SKILL, "needed"): cat.Artifact(name="needed", type=SKILL, dependency_only=True),
        (SKILL, "parent"): cat.Artifact(name="parent", type=SKILL, dependencies=("needed",)),
    }
    assert checks.orphaned_dependency_only(catalog) == []


def test_g5_the_real_repo_has_no_orphans(catalog):
    assert checks.orphaned_dependency_only(catalog) == []


# --- G6, G7: plugin manifests ----------------------------------------------


def test_g6_missing_required_keys_are_reported():
    plugin = cat.Artifact(name="p", type=PLUGIN, manifest_keys=("name",))
    findings = by_check(checks.plugin_manifests({(PLUGIN, "p"): plugin}), "plugin-missing-keys")
    assert len(findings) == 1
    assert "description" in findings[0].detail and "version" in findings[0].detail


def test_g7_the_reserved_dependencies_key_is_reported():
    """The highest-value check: this failure is invisible everywhere else.

    `claude plugin details` still lists every artifact while Claude Code registers
    none of them, so nothing but this check surfaces it.
    """
    plugin = cat.Artifact(
        name="p", type=PLUGIN, manifest_keys=("name", "description", "version", "dependencies")
    )
    findings = by_check(checks.plugin_manifests({(PLUGIN, "p"): plugin}), "plugin-reserved-key")
    assert len(findings) == 1
    assert findings[0].is_problem
    assert cat.PLUGIN_DEPS_KEY in findings[0].detail, "the fix should be named"


def test_g7_skilldependencies_is_not_flagged():
    plugin = cat.Artifact(
        name="p", type=PLUGIN, manifest_keys=("name", "description", "version", "skillDependencies")
    )
    assert by_check(checks.plugin_manifests({(PLUGIN, "p"): plugin}), "plugin-reserved-key") == []


def test_g6_g7_the_real_plugins_are_clean(catalog):
    assert checks.plugin_manifests(catalog) == []


# --- G8: frontmatter -------------------------------------------------------


def test_g8_malformed_yaml_is_reported(tmp_path):
    """An unquoted ': ' makes YAML read the value as a nested mapping, so the whole
    block fails and the artifact silently does not load."""
    source = tmp_path / "broken"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: x\ndescription: bad: value: here\n---\nbody\n")
    catalog = {(SKILL, "broken"): cat.Artifact(name="broken", type=SKILL, source=source)}
    findings = checks.frontmatter_parses(catalog, kinds=(SKILL,))
    assert len(findings) == 1
    assert findings[0].check == "bad-frontmatter"


def test_g8_a_missing_frontmatter_block_is_reported(tmp_path):
    source = tmp_path / "plain"
    source.mkdir()
    (source / "SKILL.md").write_text("no frontmatter at all\n")
    catalog = {(SKILL, "plain"): cat.Artifact(name="plain", type=SKILL, source=source)}
    assert "no frontmatter" in checks.frontmatter_parses(catalog, kinds=(SKILL,))[0].detail


def test_g8_frontmatter_without_a_name_is_reported(tmp_path):
    source = tmp_path / "nameless"
    source.mkdir()
    (source / "SKILL.md").write_text("---\ndescription: fine\n---\nbody\n")
    catalog = {(SKILL, "nameless"): cat.Artifact(name="nameless", type=SKILL, source=source)}
    assert "no name" in checks.frontmatter_parses(catalog, kinds=(SKILL,))[0].detail


def test_g8_valid_frontmatter_passes(tmp_path):
    source = tmp_path / "good"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: good\ndescription: >-\n  fine: even with a colon\n---\nbody\n")
    catalog = {(SKILL, "good"): cat.Artifact(name="good", type=SKILL, source=source)}
    assert checks.frontmatter_parses(catalog, kinds=(SKILL,)) == []


def test_g8_every_real_skill_and_agent_parses(catalog):
    assert checks.frontmatter_parses(catalog) == []


def test_g8_needs_no_third_party_parser(catalog):
    """The check has to run on a machine carrying only python3.

    It used to ask PyYAML, a test dependency, and reported that it had not run
    wherever PyYAML was absent, which is where it mattered most. The scanner that
    replaced it is stdlib-only; test_frontmatter.py holds it to PyYAML's verdicts.
    """
    assert not hasattr(checks, "yaml_parser"), "the seam is gone; nothing should reach for it"
    assert by_check(checks.frontmatter_parses(catalog), "frontmatter-unchecked") == []


def test_g8_reports_the_line_it_objects_to(tmp_path):
    """The detail is the whole value of the finding: 114 blocks is too many to bisect."""
    source = tmp_path / "broken"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: x\ndescription: bad: value\n---\nbody\n")
    catalog = {(SKILL, "broken"): cat.Artifact(name="broken", type=SKILL, source=source)}
    detail = checks.frontmatter_parses(catalog, kinds=(SKILL,))[0].detail
    assert "SKILL.md" in detail
    assert "line 2" in detail


# --- G9: name overlaps are a note, not a problem --------------------------


def test_g9_an_overlap_is_reported_as_a_note():
    catalog = {
        (SKILL, "review"): cat.Artifact(name="review", type=SKILL),
        (AGENT, "review"): cat.Artifact(name="review", type=AGENT),
    }
    findings = checks.name_overlaps(catalog)
    assert len(findings) == 1
    assert not findings[0].is_problem, "legal now that --type disambiguates"
    assert "--type" in findings[0].detail


def test_g9_spans_types_so_it_cannot_be_narrowed():
    catalog = {
        (SKILL, "review"): cat.Artifact(name="review", type=SKILL),
        (AGENT, "review"): cat.Artifact(name="review", type=AGENT),
    }
    assert checks.name_overlaps(catalog)[0].kind is None


def test_g9_the_real_repo_has_no_overlaps_today(catalog):
    assert checks.name_overlaps(catalog) == []


# --- G1: broken links ------------------------------------------------------


def test_g1_a_broken_symlink_is_reported(tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "gone").symlink_to(tmp_path / "nowhere")

    findings = checks.broken_links(CLAUDE, home, project)
    assert len(findings) == 1
    assert findings[0].check == "broken-link"
    assert "the project" in findings[0].subject


def test_g1_a_broken_link_in_home_is_reported(tmp_path):
    home = tmp_path / "home"
    skills = home / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "gone").symlink_to(tmp_path / "nowhere")
    findings = checks.broken_links(CLAUDE, home, None)
    assert "~/.claude" in findings[0].subject


def test_g1_a_healthy_link_is_not_reported(tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "fine").symlink_to(REAL_SKILL_SOURCE)
    assert checks.broken_links(CLAUDE, home, project) == []


# --- G10, G11: scope --------------------------------------------------------


def test_g10_a_global_artifact_in_a_project_is_a_problem(catalog, effective, tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    art = cat.get(catalog, SKILL, "commit")
    target = scope.link_path(art, scope.PROJECT, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(art.source)

    findings = by_check(checks.wrong_scope(catalog, effective, home, project, CLAUDE), "wrong-scope")
    assert len(findings) == 1
    assert findings[0].is_problem
    assert "belongs in ~/.claude" in findings[0].detail


def test_g11_an_untagged_artifact_in_home_is_only_a_note(catalog, effective, tmp_path):
    """This is exactly what --global produces. With no pin file there is nothing
    further to verify, so flagging it as a problem would fire on every deliberate
    override and train the reader to ignore doctor."""
    home, project = tmp_path / "home", tmp_path / "project"
    art = cat.get(catalog, SKILL, "coderabbit")
    target = scope.link_path(art, scope.GLOBAL, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(art.source)

    findings = by_check(checks.wrong_scope(catalog, effective, home, project, CLAUDE), "global-override")
    assert len(findings) == 1
    assert not findings[0].is_problem
    assert "--global" in findings[0].detail


def test_a_correctly_placed_pair_yields_nothing(catalog, effective, tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    global_art = cat.get(catalog, SKILL, "commit")
    project_art = cat.get(catalog, SKILL, "coderabbit")
    for art, where, root in ((global_art, scope.GLOBAL, home), (project_art, scope.PROJECT, project)):
        target = scope.link_path(art, where, home, project)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(art.source)
    assert checks.wrong_scope(catalog, effective, home, project, CLAUDE) == []


# --- G12, G13, G14: provenance drift ---------------------------------------


def test_g12_a_record_with_no_link_is_a_problem(catalog, tmp_path):
    project = tmp_path / "project"
    (project / ".claude" / "skills").mkdir(parents=True)
    provenance = {(SKILL, "coderabbit"): state.DIRECT}
    findings = by_check(checks.provenance_drift(catalog, provenance, project, CLAUDE), "stale-provenance")
    assert len(findings) == 1
    assert findings[0].is_problem


def test_g13_a_link_with_no_record_is_a_note(catalog, tmp_path):
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "coderabbit").symlink_to(REAL_SKILL_SOURCE)

    findings = by_check(checks.provenance_drift(catalog, {}, project, CLAUDE), "untracked-install")
    assert len(findings) == 1
    assert not findings[0].is_problem
    assert "cascade will keep it" in findings[0].detail
    assert "claude-kit adopt" in findings[0].detail, "the fix should be named"


def test_g14_a_dependency_nothing_needs_is_reported_as_removable(catalog, tmp_path):
    """The safety valve. D10 and D14 both err toward keeping, so without this a
    project silently accumulates dependencies nothing needs."""
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "test-driven-development").symlink_to(CLAUDE / "skills" / "test-driven-development")
    provenance = {(SKILL, "test-driven-development"): state.dep_of("spec-driven-development")}

    findings = by_check(checks.provenance_drift(catalog, provenance, project, CLAUDE), "removable")
    assert len(findings) == 1
    assert not findings[0].is_problem
    assert "claude-kit remove test-driven-development --type skill" in findings[0].detail


def test_g14_a_dependency_still_needed_is_not_reported(catalog, tmp_path):
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    for name in ("spec-driven-development", "test-driven-development"):
        (skills / name).symlink_to(CLAUDE / "skills" / name)
    provenance = {
        (SKILL, "spec-driven-development"): state.DIRECT,
        (SKILL, "test-driven-development"): state.dep_of("spec-driven-development"),
    }
    assert by_check(checks.provenance_drift(catalog, provenance, project, CLAUDE), "removable") == []


def test_g14_a_direct_install_is_never_removable(catalog, tmp_path):
    project = tmp_path / "project"
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "coderabbit").symlink_to(REAL_SKILL_SOURCE)
    provenance = {(SKILL, "coderabbit"): state.DIRECT}
    assert by_check(checks.provenance_drift(catalog, provenance, project, CLAUDE), "removable") == []


def test_provenance_drift_is_skipped_with_no_project(catalog):
    assert checks.provenance_drift(catalog, {(SKILL, "x"): state.DIRECT}, None, CLAUDE) == []


# --- G15: --type narrows ----------------------------------------------------


def test_g15_narrowing_keeps_only_that_types_findings(catalog, effective, tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    doctored = {
        **catalog,
        (PLUGIN, "broken"): cat.Artifact(
            name="broken", type=PLUGIN, manifest_keys=("name", "dependencies"), source=CLAUDE
        ),
        (SKILL, "ghost"): cat.Artifact(name="ghost", type=SKILL, source=tmp_path / "nowhere"),
    }
    plugin_only = doctor.collect(doctored, effective, CLAUDE, home, project, {}, kind=PLUGIN)
    assert {f.kind for f in plugin_only} == {PLUGIN}
    assert any(f.check == "plugin-reserved-key" for f in plugin_only)
    assert not any(f.check == "missing-source" for f in plugin_only)


def test_g15_cross_type_findings_are_dropped_when_narrowing(catalog, effective, tmp_path):
    """A dangling edge and a name overlap have no single type, so they belong only
    to an unnarrowed run."""
    home = tmp_path / "home"
    doctored = {
        **catalog,
        (SKILL, "dangler"): cat.Artifact(
            name="dangler", type=SKILL, dependencies=("nope",), source=REAL_SKILL_SOURCE
        ),
    }
    full = doctor.collect(doctored, effective, CLAUDE, home, None, {})
    narrowed = doctor.collect(doctored, effective, CLAUDE, home, None, {}, kind=SKILL)
    assert any(f.check == "dangling-dependency" for f in full)
    assert not any(f.check == "dangling-dependency" for f in narrowed)


def test_a6_an_unnarrowed_run_includes_all_three_types(catalog, effective, tmp_path):
    home = tmp_path / "home"
    doctored = {
        **catalog,
        (SKILL, "s"): cat.Artifact(name="s", type=SKILL, source=tmp_path / "no-s"),
        (AGENT, "a"): cat.Artifact(name="a", type=AGENT, source=tmp_path / "no-a"),
        (PLUGIN, "p"): cat.Artifact(name="p", type=PLUGIN, source=tmp_path / "no-p"),
    }
    findings = doctor.collect(doctored, effective, CLAUDE, home, None, {})
    assert {SKILL, AGENT, PLUGIN} <= {f.kind for f in findings if f.kind}


# --- G16, G17: exit codes and no-project tolerance -------------------------


def test_g17_a_clean_run_exits_ok(catalog, effective, tmp_path, capsys):
    home = tmp_path / "home"
    findings = doctor.collect(catalog, effective, CLAUDE, home, None, {})
    assert [f for f in findings if f.is_problem] == []
    assert doctor.report(findings, None, None) == errors.OK


def test_g17_any_problem_exits_drift(tmp_path):
    findings = [checks.Finding("x", checks.PROBLEM, "s", "d", SKILL)]
    assert doctor.report(findings, None, None) == errors.DRIFT


def test_g17_notes_alone_do_not_fail(tmp_path, capsys):
    findings = [checks.Finding("x", checks.NOTE, "s", "d", SKILL)]
    assert doctor.report(findings, None, None) == errors.OK


def test_g16_no_project_still_runs_registry_checks(catalog, effective, tmp_path, capsys):
    home = tmp_path / "home"
    findings = doctor.collect(catalog, effective, CLAUDE, home, None, {})
    doctor.report(findings, None, None)
    assert "project-scope checks were skipped" in capsys.readouterr().out


# --- end to end ------------------------------------------------------------


def test_end_to_end_the_real_repo_is_clean(kit, project):
    """The repo as committed should pass doctor. A failure here is a real defect,
    not a test problem."""
    result = kit("doctor", cwd=project)
    assert result.returncode == errors.OK, result.stdout + result.stderr
    assert "No drift found" in result.stdout


def test_end_to_end_no_type_is_accepted(kit, project):
    assert kit("doctor", cwd=project).returncode == errors.OK


@pytest.mark.parametrize("kind", [SKILL, AGENT, PLUGIN])
def test_end_to_end_narrowed_runs_are_accepted(kit, project, kind):
    result = kit("doctor", "--type", kind, cwd=project)
    assert result.returncode == errors.OK
    assert f"{kind}s" in result.stdout


def test_end_to_end_detects_a_wrong_scope_install(kit, project):
    """Force a global skill into a project by hand, then expect DRIFT."""
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "commit").symlink_to(CLAUDE / "skills" / "commit")

    result = kit("doctor", "--type", "skill", cwd=project)
    assert result.returncode == errors.DRIFT
    assert "wrong-scope" in result.stdout


def test_end_to_end_detects_a_broken_link(kit, project):
    skills = project / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "vanished").symlink_to(project / "nowhere")
    result = kit("doctor", cwd=project)
    assert result.returncode == errors.DRIFT
    assert "broken-link" in result.stdout


def test_end_to_end_reports_removable_after_a_no_cascade_remove(kit, project):
    """--no-cascade leaves dependencies behind on purpose, and G14 is how the user
    finds out they are there."""
    kit("add", "spec-driven-development", "--type", "skill", cwd=project)
    kit("remove", "spec-driven-development", "--type", "skill", "--no-cascade", cwd=project)
    result = kit("doctor", "--type", "skill", cwd=project)
    assert "removable" in result.stdout
