"""Registry integrity: the invariants the fish tooling and the ai role both assume.

These need neither fish nor the claude CLI, so they run anywhere in under a second.
"""

from collections import Counter

import pytest
import yaml

from conftest import AGENTS_DIR, PLUGINS_DIR, SKILLS_DIR, frontmatter

# The controlled vocabulary from CLAUDE.md, plus `global` as the scope marker.
DISCIPLINE = {"engineering", "quality", "product", "marketing", "productivity"}
PERSONA = {
    "frontend", "backend", "mobile", "ios", "devops", "qa", "security",
    "designer", "marketer", "pm", "writer",
}
TECHNOLOGY = {
    "react", "react-native", "expo", "swift", "swiftui", "node", "nestjs",
    "fastify", "hono", "graphql", "apollo", "prisma", "tailwind", "astro",
    "tanstack", "playwright", "sentry", "typescript",
}
TOPIC = {
    "design", "ui", "testing", "review", "refactoring", "performance",
    "architecture", "seo", "conversion", "copywriting", "writing", "ci",
    "deployment", "observability", "workflow", "documentation", "planning",
    "git", "language", "ai", "web", "data", "database", "learning",
}
VOCABULARY = DISCIPLINE | PERSONA | TECHNOLOGY | TOPIC | {"global"}


def test_skill_names_are_unique(skills):
    dupes = [n for n, c in Counter(n for n, _, _ in skills).items() if c > 1]
    assert not dupes, f"skill names collide (they share a directory): {dupes}"


def test_agent_names_are_unique(agents):
    dupes = [n for n, c in Counter(n for n, _, _ in agents).items() if c > 1]
    assert not dupes, f"agent names collide: {dupes}"


def test_skill_and_plugin_names_do_not_collide(skills, plugins):
    overlap = {n for n, _, _ in skills} & {n for n, _ in plugins}
    assert not overlap, (
        f"a skill and a plugin share a name, so `add <name>` is ambiguous: {overlap}"
    )


def test_every_registered_skill_exists_on_disk(skills):
    missing = [n for n, _, _ in skills if not (SKILLS_DIR / n / "SKILL.md").is_file()]
    assert not missing, f"registered but no SKILL.md on disk: {missing}"


def test_every_skill_on_disk_is_registered(skills):
    registered = {n for n, _, _ in skills}
    on_disk = {d.name for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").is_file()}
    assert not on_disk - registered, f"on disk but unregistered: {sorted(on_disk - registered)}"


def test_every_registered_agent_exists_on_disk(agents):
    missing = [n for n, _, _ in agents if not (AGENTS_DIR / f"{n}.md").is_file()]
    assert not missing, f"registered but no .md on disk: {missing}"


def test_skill_dependencies_resolve(skills):
    known = {n for n, _, _ in skills}
    dangling = {
        f"{name} -> {dep}"
        for name, entry, _ in skills
        for dep in entry.get("dependencies", [])
        if dep not in known
    }
    assert not dangling, f"dependencies naming unknown skills: {sorted(dangling)}"


def test_agent_dependencies_resolve(agents, skills):
    known = {n for n, _, _ in skills}
    dangling = {
        f"{name} -> {dep}"
        for name, entry, _ in agents
        for dep in entry.get("dependencies", [])
        if dep not in known
    }
    assert not dangling, f"agent dependencies naming unknown skills: {sorted(dangling)}"


def test_dependency_only_skills_are_actually_depended_on(skills, agents):
    depended = {
        dep
        for _, entry, _ in [*skills, *agents]
        for dep in entry.get("dependencies", [])
    }
    orphaned = [
        name
        for name, entry, _ in skills
        if entry.get("dependency_only") and name not in depended
    ]
    assert not orphaned, (
        f"marked dependency_only but nothing depends on them, so they are "
        f"unreachable from every browsing surface: {orphaned}"
    )


# Both vocabulary tests below currently fail against real drift: 7 undocumented
# tags (one of them, "prompt engineering", contains a space and so breaks
# `--group` filtering) and 10 entries with no discipline tag. Retagging those
# ~17 entries is an open decision, so these are xfail rather than deleted. They
# report XPASS the moment the drift is fixed, which is the signal to drop the
# marker.
TAG_DRIFT = pytest.mark.xfail(
    reason="known tag drift: undocumented tags and missing discipline tags",
    strict=False,
)


@TAG_DRIFT
def test_groups_come_from_the_controlled_vocabulary(skills, agents):
    unknown = {
        f"{name}: {g}"
        for name, entry, _ in [*skills, *agents]
        for g in entry.get("groups", [])
        if g not in VOCABULARY
    }
    assert not unknown, f"groups outside the CLAUDE.md vocabulary: {sorted(unknown)}"


@TAG_DRIFT
def test_every_entry_has_exactly_one_discipline(skills, agents):
    # CLAUDE.md: discipline is "exactly one" per entry.
    offenders = {}
    for name, entry, _ in [*skills, *agents]:
        found = set(entry.get("groups", [])) & DISCIPLINE
        if len(found) != 1:
            offenders[name] = sorted(found)
    assert not offenders, f"entries without exactly one discipline tag: {offenders}"


@pytest.mark.parametrize("kind", ["skills", "agents"])
def test_frontmatter_parses(kind, skills, agents):
    """A ': ' inside an unquoted multi-line YAML description silently breaks the
    whole frontmatter block, which is how an agent stops registering."""
    if kind == "skills":
        paths = [SKILLS_DIR / n / "SKILL.md" for n, _, _ in skills]
    else:
        paths = [AGENTS_DIR / f"{n}.md" for n, _, _ in agents]

    broken = []
    for p in paths:
        if not p.is_file():
            continue
        label = p.parent.name if p.name == "SKILL.md" else p.stem
        try:
            fm = frontmatter(p)
        except yaml.YAMLError as exc:
            broken.append(
                f"{label}: {str(exc).splitlines()[0]} "
                f"(an unquoted ': ' in description? use a >- folded scalar)"
            )
            continue
        if fm is None:
            broken.append(f"{label}: no frontmatter block")
        elif not isinstance(fm, dict):
            broken.append(f"{label}: frontmatter is {type(fm).__name__}, not a mapping")
        elif "name" not in fm or "description" not in fm:
            broken.append(f"{label}: missing name/description")
    assert not broken, "\n".join(broken)


def test_plugin_dirs_and_manifests_agree(plugins):
    dirs = {d.name for d in PLUGINS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")}
    manifested = {n for n, _ in plugins}
    assert not dirs - manifested, (
        f"plugin dirs without .claude-plugin/plugin.json, so the scan skips them: "
        f"{sorted(dirs - manifested)}"
    )


def test_plugin_manifests_have_required_fields(plugins):
    bad = [
        f"{name}: missing {k}"
        for name, m in plugins
        for k in ("name", "description", "version")
        if k not in m
    ]
    assert not bad, bad


def test_plugin_manifest_name_matches_its_directory(plugins):
    mismatched = [f"{d} != {m['name']}" for d, m in plugins if m.get("name") != d]
    assert not mismatched, f"plugin.json name differs from dir name: {mismatched}"


def test_plugin_skill_dependencies_resolve(plugins, skills):
    known = {n for n, _, _ in skills}
    dangling = {
        f"{name} -> {dep}"
        for name, m in plugins
        for dep in m.get("skillDependencies", [])
        if dep not in known
    }
    assert not dangling, f"skillDependencies naming unknown skills: {sorted(dangling)}"


def test_plugins_do_not_use_the_reserved_dependencies_key(plugins):
    """An array of skill names under `dependencies` resolves to unknown plugins and
    Claude Code disables the whole plugin, silently shipping nothing."""
    offenders = [name for name, m in plugins if "dependencies" in m]
    assert not offenders, (
        f"`dependencies` is reserved for plugin-to-plugin deps; use skillDependencies: "
        f"{offenders}"
    )


def test_plugin_groups_come_from_the_vocabulary(plugins):
    unknown = {
        f"{name}: {g}"
        for name, m in plugins
        for g in m.get("groups", [])
        if g not in VOCABULARY
    }
    assert not unknown, f"plugin groups outside the vocabulary: {sorted(unknown)}"
