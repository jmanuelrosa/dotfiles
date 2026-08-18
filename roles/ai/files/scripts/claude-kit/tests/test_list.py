"""Group B: `list`.

The row-building function is pure, so filtering and annotation are tested on
literal data. Only the installed/uninstalled marks need real symlinks.
"""

import pytest

from claude_kit import catalog as cat
from claude_kit import scope, state
from claude_kit.commands import listing
from dotkit.testing import CLAUDE


def rows(catalog, kind, effective, home=None, project=None, provenance=None, group=None):
    return listing.rows(catalog, kind, effective, home, project, provenance or {}, group)


def names(result):
    return [row["name"] for row in result]


# --- B1: one type at a time -------------------------------------------------


@pytest.mark.parametrize("kind", [cat.SKILL, cat.AGENT, cat.PLUGIN])
def test_b1_only_the_requested_type_appears(catalog, effective, kind):
    listed = set(names(rows(catalog, kind, effective)))
    assert listed
    for other in (cat.SKILL, cat.AGENT, cat.PLUGIN):
        if other == kind:
            continue
        only_other = {
            a.name for a in cat.of_type(catalog, other) if not cat.get(catalog, kind, a.name)
        }
        assert not (listed & only_other), f"{kind} listing leaked {other}s"


def test_b1_skills_do_not_include_plugins(catalog, effective):
    """The sharpest case: both live in .claude/skills/, so a leak looks plausible."""
    assert "backend" not in names(rows(catalog, cat.SKILL, effective))
    assert "backend" in names(rows(catalog, cat.PLUGIN, effective))


# --- B2: plugins come from manifests ----------------------------------------


def test_b2_every_manifested_plugin_is_listed(catalog, effective):
    on_disk = {
        d.name for d in (CLAUDE / "plugins").iterdir() if (d / cat.PLUGIN_MANIFEST).is_file()
    }
    assert set(names(rows(catalog, cat.PLUGIN, effective))) == on_disk


# --- B3: dependency-only skills are hidden ----------------------------------


@pytest.mark.parametrize("hidden", ["grilling", "domain-modeling"])
def test_b3_dependency_only_skills_are_hidden(catalog, effective, hidden):
    """They cannot be added directly, so listing them invites a refusal."""
    assert cat.get(catalog, cat.SKILL, hidden).dependency_only
    assert hidden not in names(rows(catalog, cat.SKILL, effective))


def test_b3_their_parents_are_still_listed(catalog, effective):
    listed = names(rows(catalog, cat.SKILL, effective))
    assert "grill-me" in listed
    assert "grill-with-docs" in listed


# --- B4, B5: --group filtering ----------------------------------------------


def test_b4_group_filters_to_tagged_entries(catalog, effective):
    filtered = rows(catalog, cat.SKILL, effective, group="global")
    assert filtered
    for row in filtered:
        assert "global" in row["groups"]


def test_b4_group_is_an_opaque_tag(catalog, effective):
    """Filtering is set membership, so a new tag needs no code change."""
    filtered = rows(catalog, cat.SKILL, effective, group="testing")
    assert filtered
    for row in filtered:
        assert "testing" in row["groups"]


def test_b5_an_unmatched_group_is_empty_not_an_error(catalog, effective):
    assert rows(catalog, cat.SKILL, effective, group="no-such-tag") == []


# --- B6: installed marks ----------------------------------------------------


def test_b6_marks_a_project_link_as_installed(catalog, effective, tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    art = cat.get(catalog, cat.SKILL, "coderabbit")
    target = scope.link_path(art, scope.PROJECT, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(art.source)

    by_name = {row["name"]: row for row in rows(catalog, cat.SKILL, effective, home, project)}
    assert by_name["coderabbit"]["installed"] == scope.PROJECT
    assert by_name["frontend-design"]["installed"] is None


def test_b6_reads_only_the_two_scopes_not_a_parent_directory(catalog, effective, tmp_path):
    """A .claude above the project must not register as installed."""
    home = tmp_path / "home"
    project = tmp_path / "parent" / "project"
    project.mkdir(parents=True)
    art = cat.get(catalog, cat.SKILL, "coderabbit")
    stray = tmp_path / "parent" / ".claude" / "skills"
    stray.mkdir(parents=True)
    (stray / "coderabbit").symlink_to(art.source)

    by_name = {row["name"]: row for row in rows(catalog, cat.SKILL, effective, home, project)}
    assert by_name["coderabbit"]["installed"] is None


# --- B8: dependency annotation ----------------------------------------------


def test_b8_dependencies_are_annotated(catalog, effective):
    """Sorted and deduped, as the jq `unique` this inherited its ordering from was."""
    by_name = {row["name"]: row for row in rows(catalog, cat.SKILL, effective)}
    assert by_name["spec-driven-development"]["dependencies"] == (
        "context-engineering",
        "incremental-implementation",
        "planning-and-task-breakdown",
        "test-driven-development",
    )
    assert "needs:" in listing.format_row(by_name["spec-driven-development"])


def test_b8_plugin_skill_dependencies_are_annotated(catalog, effective):
    by_name = {row["name"]: row for row in rows(catalog, cat.PLUGIN, effective)}
    assert by_name["product-team"]["dependencies"] == ("idea-refine",)


# --- B9: global shown without any pin record --------------------------------


def test_b9_a_tagged_skill_is_shown_as_global(catalog, effective):
    by_name = {row["name"]: row for row in rows(catalog, cat.SKILL, effective)}
    assert by_name["commit"]["global"] is True
    assert cat.get(catalog, cat.SKILL, "commit").tagged_global, "the tag is what makes it global"
    assert by_name["coderabbit"]["global"] is False


def test_b9_an_untagged_skill_linked_in_home_is_shown_as_global(catalog, effective, tmp_path):
    """Given an untagged skill sits in ~/.claude, Then it reads as global.

    Derived from the symlink alone: nothing else can have put it there but
    --global, so no pin file is needed to know that.
    """
    home, project = tmp_path / "home", tmp_path / "project"
    art = cat.get(catalog, cat.SKILL, "coderabbit")
    assert not art.tagged_global
    target = scope.link_path(art, scope.GLOBAL, home, project)
    target.parent.mkdir(parents=True)
    target.symlink_to(art.source)

    by_name = {row["name"]: row for row in rows(catalog, cat.SKILL, effective, home, project)}
    assert by_name["coderabbit"]["global"] is True
    # No registry edge reaches it, so --global is the only story there is to tell and the
    # marker says just that.
    assert by_name["coderabbit"]["global_for"] == ()
    assert "(global)" in listing.format_row(by_name["coderabbit"])


def test_b9_a_skill_global_only_via_a_dependency_names_its_parent(catalog, effective):
    """The one scope question with no file behind it: `state` records nothing about
    ~/.claude, so the registry edge is what says why a skill nobody typed is there.
    """
    by_name = {row["name"]: row for row in rows(catalog, cat.SKILL, effective)}
    row = by_name["planning-and-task-breakdown"]
    assert not cat.get(catalog, cat.SKILL, row["name"]).tagged_global
    assert row["global"] is True
    assert row["global_for"] == ("architect",)
    assert "(global for architect)" in listing.format_row(row)


def test_b9_only_skills_carry_a_global_parent(catalog, effective):
    """Every dependency edge names a skill, so an agent or plugin is global by tag alone
    and has nothing to attribute."""
    for kind in (cat.AGENT, cat.PLUGIN):
        assert all(row["global_for"] == () for row in rows(catalog, kind, effective))


# --- B10: provenance annotation ---------------------------------------------


def test_b10_a_dependency_says_what_pulled_it_in(catalog, effective):
    provenance = {(cat.SKILL, "context-engineering"): state.dep_of("spec-driven-development")}
    by_name = {
        row["name"]: row
        for row in rows(catalog, cat.SKILL, effective, provenance=provenance)
    }
    row = by_name["context-engineering"]
    assert row["parent"] == "spec-driven-development"
    assert "installed for spec-driven-development" in listing.format_row(row)


def test_b10_a_direct_install_has_no_parent(catalog, effective):
    provenance = {(cat.SKILL, "coderabbit"): state.DIRECT}
    by_name = {
        row["name"]: row for row in rows(catalog, cat.SKILL, effective, provenance=provenance)
    }
    assert by_name["coderabbit"]["reason"] == state.DIRECT
    assert by_name["coderabbit"]["parent"] is None


def test_b10_provenance_is_keyed_by_type(catalog, effective):
    """A skill's record must not annotate an identically-named agent."""
    provenance = {(cat.AGENT, "architect"): state.dep_of("something")}
    skill_rows = rows(catalog, cat.SKILL, effective, provenance=provenance)
    assert all(row["parent"] is None for row in skill_rows)


# --- B11: read-only, so it never refuses ------------------------------------


def test_b11_works_with_no_project(catalog, effective, tmp_path):
    """Given cwd is $HOME, Then listing still reports global state."""
    listed = rows(catalog, cat.SKILL, effective, home=tmp_path / "home", project=None)
    assert listed
    assert all(row["installed"] in (None, scope.GLOBAL) for row in listed)


def test_b11_end_to_end_in_home_exits_ok(kit):
    """$HOME is the only place with no project state to show, and list never refuses."""
    result = kit("list", "--type", "skill", cwd=kit.home)
    assert result.returncode == 0
    assert "$HOME" in result.stdout


def test_b11_end_to_end_outside_a_repo_shows_project_state(kit, tmp_path):
    """A plain directory is a project, so listing must not disclaim project state.

    It used to print the no-project notice here, which would now be a lie: `add`
    installs into this directory quite happily.
    """
    plain = tmp_path / "plain"
    plain.mkdir()
    result = kit("list", "--type", "skill", cwd=plain)
    assert result.returncode == 0
    assert "$HOME" not in result.stdout


def test_b11_end_to_end_reports_a_count(kit, project):
    result = kit("list", "--type", "plugin", cwd=project)
    assert result.returncode == 0
    assert "plugins," in result.stdout
    assert "backend" in result.stdout


def test_group_summary_names_the_tag(kit, project):
    result = kit("list", "--type", "skill", "--group", "global", cwd=project)
    assert result.returncode == 0
    assert "tagged 'global'" in result.stdout
