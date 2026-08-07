"""Catalog construction and the effective global set.

Pure altitude: build_catalog reads the real registries once per session, then
every rule is exercised on the resulting data or on literal fixtures. No symlinks,
no subprocesses.
"""

import json

import pytest

from claude_kit import catalog as cat
from claude_kit import frontmatter
from claude_kit import scope
from dotkit.testing import AGENTS, CLAUDE

# --- fixtures over the real repo --------------------------------------------


def art(catalog, kind, name):
    found = cat.get(catalog, kind, name)
    assert found is not None, f"{kind} '{name}' missing from the catalog"
    return found


# --- name derivation, B7 ----------------------------------------------------


@pytest.mark.parametrize(
    "entry,repo_key,expected",
    [
        ({"upstream_path": "plugins/frontend-design/skills/frontend-design"}, "a/b", "frontend-design"),
        ({"upstream_path": "skills/commit"}, "a/b", "commit"),
        # A skill living at a repo root has no meaningful basename, so it takes
        # the repo's name instead.
        ({"upstream_path": "."}, "addyosmani/agent-skills", "agent-skills"),
        ({"upstream_path": ""}, "addyosmani/agent-skills", "agent-skills"),
        ({"upstream_path": "skills/trailing/"}, "a/b", "trailing"),
        # An explicit name always wins, which is how local entries work.
        ({"name": "explicit", "upstream_path": "ignored/path"}, "a/b", "explicit"),
        ({}, "owner/reponame", "reponame"),
    ],
)
def test_b7_entry_name_derivation(entry, repo_key, expected):
    assert cat.entry_name(entry, repo_key) == expected


def test_b7_no_catalog_name_is_a_path(catalog):
    """A derivation bug would surface as a name containing a slash or a dot."""
    for (_, name) in catalog:
        assert "/" not in name and name not in (".", ""), f"bad derived name {name!r}"


# --- catalog shape ----------------------------------------------------------


def test_catalog_covers_all_three_types(catalog):
    for kind in (cat.SKILL, cat.AGENT, cat.PLUGIN):
        assert cat.of_type(catalog, kind), f"no {kind}s in the catalog"


def test_b2_plugins_come_from_manifests_not_a_registry(catalog):
    """Every plugins/* directory carrying a manifest is present, and only those."""
    on_disk = {
        d.name
        for d in (CLAUDE / "plugins").iterdir()
        if (d / cat.PLUGIN_MANIFEST).is_file()
    }
    assert {a.name for a in cat.of_type(catalog, cat.PLUGIN)} == on_disk


def test_b2_a_directory_without_a_manifest_is_skipped(tmp_path):
    """Given a plugins dir with no manifest, Then it is silently omitted."""
    claude = tmp_path / "claude"
    (claude / "plugins" / "real" / ".claude-plugin").mkdir(parents=True)
    (claude / "plugins" / "real" / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "real", "description": "d", "version": "1.0.0"})
    )
    (claude / "plugins" / "bare").mkdir(parents=True)
    for kind in (cat.SKILL, cat.AGENT):
        (claude / cat.REGISTRY_FILE[kind]).write_text(json.dumps({"version": 2, "repos": {}}))

    catalog = cat.build_catalog(claude)
    assert {a.name for a in cat.of_type(catalog, cat.PLUGIN)} == {"real"}


def test_plugins_use_skilldependencies_not_the_reserved_key(catalog):
    """`dependencies` in a manifest makes a plugin ship nothing, silently, so the
    catalog must read skillDependencies and no plugin may carry the reserved key."""
    for plugin in cat.of_type(catalog, cat.PLUGIN):
        assert cat.PLUGIN_RESERVED_KEY not in plugin.manifest_keys, (
            f"plugin '{plugin.name}' uses the reserved '{cat.PLUGIN_RESERVED_KEY}' key; "
            f"Claude Code would register none of its artifacts"
        )


def test_product_team_declares_idea_refine(catalog):
    """The live skillDependencies case, pinned so a manifest edit is visible."""
    assert "idea-refine" in art(catalog, cat.PLUGIN, "product-team").dependencies


def test_leaf_and_basename_per_type(catalog):
    """Plugins share the skills leaf because that is how Claude Code loads one."""
    assert art(catalog, cat.SKILL, "commit").leaf == "skills"
    assert art(catalog, cat.AGENT, "architect").leaf == "agents"
    assert art(catalog, cat.PLUGIN, "backend").leaf == "skills"
    assert art(catalog, cat.SKILL, "commit").basename == "commit"
    assert art(catalog, cat.AGENT, "architect").basename == "architect.md"
    assert art(catalog, cat.PLUGIN, "backend").basename == "backend"


def test_a5_types_are_keyed_separately(tmp_path):
    """Given one name used by two types, Then both survive in the catalog.

    Keying by name alone would let one silently shadow the other, which is the
    mis-install --type exists to prevent.
    """
    claude = tmp_path / "claude"
    claude.mkdir()
    (claude / "skill-registry.json").write_text(
        json.dumps({"version": 2, "repos": {}, "local_skills": [{"name": "review", "groups": []}]})
    )
    (claude / "agent-registry.json").write_text(
        json.dumps({"version": 2, "repos": {}, "local_agents": [{"name": "review", "groups": []}]})
    )
    catalog = cat.build_catalog(claude)
    assert cat.get(catalog, cat.SKILL, "review").type == cat.SKILL
    assert cat.get(catalog, cat.AGENT, "review").type == cat.AGENT
    assert cat.duplicate_names(catalog) == {"review": [cat.AGENT, cat.SKILL]}


def test_no_duplicate_names_in_the_real_repo_today(catalog):
    """Overlap is legal now that --type disambiguates, so this is informational.

    Kept as a test so an overlap becomes a visible, deliberate decision rather
    than a surprise, and so doctor's G9 note has a known baseline.
    """
    assert cat.duplicate_names(catalog) == {}


# --- upstream metadata ------------------------------------------------------


def test_only_repo_tracked_skills_have_an_upstream(catalog):
    for skill in cat.of_type(catalog, cat.SKILL):
        if skill.origin == "local":
            assert not skill.has_upstream
        else:
            assert skill.has_upstream
            assert skill.upstream_branch, f"{skill.name} has no branch"


def test_agents_and_plugins_have_no_upstream(catalog):
    """agent-registry.json has no repos and plugins are authored here, which is
    why `update --type agent|plugin` is refused."""
    for kind in (cat.AGENT, cat.PLUGIN):
        assert not any(a.has_upstream for a in cat.of_type(catalog, kind))


# --- the effective global set ----------------------------------------------


def test_global_set_holds_skills_only(catalog, effective):
    """Agents and plugins are global by tag alone, so they are absent from the set.

    Including them would let a skill inherit globalness from an identically-named
    agent, the shadowing explicit --type exists to prevent.
    """
    skills = cat.skills(catalog)
    assert effective <= set(skills)
    tagged_agents = {a.name for a in cat.of_type(catalog, cat.AGENT) if a.tagged_global}
    assert tagged_agents, "no global agents left to make this case meaningful"
    assert not (tagged_agents & effective) or tagged_agents <= set(skills)


def test_global_set_includes_every_tagged_skill(catalog, effective):
    for skill in cat.of_type(catalog, cat.SKILL):
        if skill.tagged_global:
            assert skill.name in effective


def test_belongs_global_uses_the_tag_for_agents_and_plugins(catalog, effective):
    """A tagged agent belongs in ~/.claude even though it is not in the skill set."""
    architect = art(catalog, cat.AGENT, "architect")
    assert architect.tagged_global
    assert architect.name not in effective
    assert scope.belongs_global(architect, effective)


def test_belongs_global_does_not_leak_across_types():
    """Given an agent named X is global, When a *skill* named X is not, Then the
    skill stays project-scoped."""
    catalog = {
        (cat.AGENT, "X"): cat.Artifact(name="X", type=cat.AGENT, groups=("global",)),
        (cat.SKILL, "X"): cat.Artifact(name="X", type=cat.SKILL),
    }
    effective = scope.global_set(catalog)
    assert scope.belongs_global(catalog[(cat.AGENT, "X")], effective) is True
    assert scope.belongs_global(catalog[(cat.SKILL, "X")], effective) is False


@pytest.mark.parametrize(
    "name,parent",
    [
        # Reached only as a dependency of a global skill.
        ("grilling", "grill-me"),
        ("jira", "research"),
        # Reached only as a dependency of a global *agent*.
        ("documentation-and-adrs", "architect"),
        ("domain-modeling", "architect"),
        ("planning-and-task-breakdown", "architect"),
    ],
)
def test_global_set_expands_one_dependency_level(catalog, effective, name, parent):
    """Tag membership alone is not enough: a global artifact's dependencies reach
    ~/.claude too, or it would load with a dependency missing."""
    skill = cat.get(catalog, cat.SKILL, name)
    assert skill is not None
    assert not skill.tagged_global, f"{name} now carries the tag; this case is moot"
    assert name in effective, f"{name} should be global via {parent}"


def test_global_set_holds_exactly_the_documented_membership(catalog, effective):
    """Pinned so a registry retag shows up as a failing test rather than as a silent
    change to what lands in ~/.claude.

    This used to be pinned against a fish helper that derived the same set for the
    Television picker. That helper is gone: the cables read `claude-kit list --json`, so
    this function is the only implementation and there is nothing left to diverge from.
    """
    assert effective == {
        "ac",
        "agent-audit",
        "agent-writer",
        "cc-review",
        "commit",
        "documentation-and-adrs",
        "domain-modeling",
        "feature-team",
        "grill-me",
        "grill-with-docs",
        "grilling",
        "handoff",
        "humanizer",
        "jira",
        "planning-and-task-breakdown",
        "pr",
        "product-lead",
        "research",
        "skill-writer",
    }


def test_agent_dependencies_expand_a_second_level():
    """A global agent's skill dependencies expand one level further, because those
    skills may declare others the agent needs at runtime."""
    skills = {
        "top": cat.Artifact(name="top", type=cat.SKILL, dependencies=("mid",)),
        "mid": cat.Artifact(name="mid", type=cat.SKILL, dependencies=("leaf",)),
        "leaf": cat.Artifact(name="leaf", type=cat.SKILL),
    }
    catalog = {(cat.SKILL, n): a for n, a in skills.items()}

    catalog[(cat.SKILL, "g")] = cat.Artifact(
        name="g", type=cat.SKILL, groups=("global",), dependencies=("top",)
    )
    assert "mid" not in scope.global_set(catalog), "a skill expands one level only"

    del catalog[(cat.SKILL, "g")]
    catalog[(cat.AGENT, "a")] = cat.Artifact(
        name="a", type=cat.AGENT, groups=("global",), dependencies=("top",)
    )
    reached = scope.global_set(catalog)
    assert {"top", "mid"} <= reached
    assert "leaf" not in reached, "an agent expands two levels, not the whole closure"


def test_unknown_dependency_names_are_ignored_when_expanding():
    """A dangling edge must not crash resolution; doctor reports it instead."""
    catalog = {
        (cat.SKILL, "g"): cat.Artifact(
            name="g", type=cat.SKILL, groups=("global",), dependencies=("nope",)
        )
    }
    assert scope.global_set(catalog) == {"g"}


def test_dependency_edges_all_name_known_skills(catalog):
    """Every dependency edge names a skill, so a dangling one is a real defect."""
    skills = cat.skills(catalog)
    for art_ in catalog.values():
        for dep in art_.dependencies:
            assert dep in skills, f"{art_.type} '{art_.name}' depends on unknown skill '{dep}'"


def test_dependency_only_skills_are_actually_depended_on(catalog):
    """A dependency_only skill nothing needs can never be installed at all."""
    needed = {d for a in catalog.values() for d in a.dependencies}
    for skill in cat.of_type(catalog, cat.SKILL):
        if skill.dependency_only:
            assert skill.name in needed, f"'{skill.name}' is dependency_only but orphaned"


# --- the views the group flags read ----------------------------------------


def test_visible_drops_the_dependency_only_skills(catalog):
    names = {a.name for a in cat.visible(catalog, cat.SKILL)}
    hidden = {a.name for a in cat.of_type(catalog, cat.SKILL) if a.dependency_only}
    assert hidden, "the fixture needs at least one dependency_only skill"
    assert not (names & hidden)


def test_in_group_is_exact_membership():
    catalog = {
        (cat.SKILL, "a"): cat.Artifact(name="a", type=cat.SKILL, groups=("frontend", "ui")),
        (cat.SKILL, "b"): cat.Artifact(name="b", type=cat.SKILL, groups=("Frontend",)),
        (cat.SKILL, "c"): cat.Artifact(name="c", type=cat.SKILL, groups=("frontend-design",)),
    }
    assert [a.name for a in cat.in_group(catalog, cat.SKILL, "frontend")] == ["a"]


def test_in_group_tolerates_a_tag_with_a_space(catalog):
    """`prompt engineering` is a real tag, so no caller may split on whitespace."""
    assert cat.in_group(catalog, cat.SKILL, "prompt engineering")


def test_in_group_never_offers_a_dependency_only_member(catalog):
    """A hidden skill carries tags but cannot be added, so it is not a member.

    It still arrives through its parent's dependency closure, which is the only way
    it is ever meant to.
    """
    hidden = [a for a in cat.of_type(catalog, cat.SKILL) if a.dependency_only and a.groups]
    assert hidden, "the fixture needs a tagged dependency_only skill"
    for art_ in hidden:
        for tag in art_.groups:
            assert art_ not in cat.in_group(catalog, cat.SKILL, tag)


def test_in_group_is_empty_for_a_tag_nothing_carries(catalog):
    assert cat.in_group(catalog, cat.SKILL, "no-such-tag") == []


def test_in_group_is_name_ordered(catalog):
    members = [a.name for a in cat.in_group(catalog, cat.SKILL, "engineering")]
    assert members == sorted(members)


def test_every_catalog_source_exists_on_disk(catalog):
    for art_ in catalog.values():
        assert art_.source.exists(), f"{art_.type} '{art_.name}' missing at {art_.source}"


# --- seat routing, held against architect.md --------------------------------


def seat_agents(catalog):
    """Every staff-engineer agent shipped by a seat plugin, with its frontmatter keys."""
    for plugin in cat.of_type(catalog, cat.PLUGIN):
        for path in sorted((plugin.source / "agents").glob("*-staff-engineer.md")):
            yield path, frontmatter.keys(path.read_text()) or ()


def test_implementer_seats_are_the_ones_without_a_tools_allowlist(catalog):
    """The advisor/implementer split is readable from frontmatter alone.

    `tools:` is what makes a seat read-only, and a read-only seat owns no slice. Pinned
    so the next advisor seat is a deliberate addition here rather than a silent
    disappearance from architect's routing.
    """
    advisors = {p.stem for p, keys in seat_agents(catalog) if "tools" in keys}
    assert advisors == {"security-staff-engineer"}


def test_architect_routes_to_every_implementer_seat(catalog):
    """A seat architect never names is a seat it never assigns work to.

    This list rotted from twelve seats to seven without anyone noticing: design,
    mobile, desktop, dx and gtm each shipped without reaching `architect.md`, so
    architect silently defaulted their work to the frontend and backend seats. The
    symptom was invisible, because defaulting is indistinguishable from routing.
    """
    routing = (AGENTS / "architect.md").read_text()
    missing = sorted(
        path.stem
        for path, keys in seat_agents(catalog)
        if "tools" not in keys and path.stem.removesuffix("-staff-engineer") not in routing
    )
    assert missing == [], (
        f"seats absent from architect.md's enumeration: {', '.join(missing)}. "
        f"Architect cannot assign a slice to a seat it does not name."
    )
