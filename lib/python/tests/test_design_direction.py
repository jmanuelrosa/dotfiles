"""The design seat decides something, and nobody else quietly offers to decide it instead.

The seat was for a while a pure conformance engine: 52 pass/fail rules and not one asking
whether the result was any good. It passed its own gate on the median every time, because
correctness is a floor and a floor makes no choices. Step 2 is what changed that, and the
failures it can suffer are all silent ones, which is why they are pinned here rather than
noticed later in a screenshot.

Three classes of silence:

A trigger row naming a reference that does not exist reads exactly like a checklist that
fired and found nothing. That is not hypothetical: the seat routed error-and-empty-state
work to `errors-and-observability` for as long as the file on disk had been named
`errors-and-resilience.md`, so one of nine domains was unreachable and the agent reported
having consulted it. The check is generic across every seat, since nothing about that
mistake was specific to design.

An axis dropped from Step 2 costs exactly the decision it names. The nine are the whole
content of the step: "the framework default" is a failing answer only for an axis that is
still listed.

And `frontend-design` routed from a consuming seat is the gate's back door. Origination
behind a direction step and origination beside it are not the same offer, and leaving both
open widens the gap the gate was added to close rather than narrowing it.

Nothing here guards against `impeccable` returning to the registry, deliberately: no
automated path writes there (`update` only refreshes tracked entries, `add` and `scout`
never write at all), so re-adding it would be a human act by someone who had just read the
CLAUDE.md section saying why not, and a test they would delete in the same commit is not a
guard. What is checked is the attribution on the doctrine extracted from it, which is a
licence obligation rather than a preference.
"""

import json
import re

import pytest
from dotkit.testing import AGENT_REGISTRY, CLAUDE, PLUGINS, SKILL_REGISTRY

DESIGN = PLUGINS / "design"
DESIGN_AGENT = DESIGN / "agents/design-staff-engineer.md"
CRAFT = DESIGN / "skills/design-failure-modes/references/craft-and-distinctiveness.md"

# The consuming seats: feature UI that composes the direction rather than setting it.
CONSUMERS = ("frontend", "mobile", "desktop")

# Step 2's nine axes. Dropping one drops the decision it names.
AXES = (
    "Scale range",
    "Type",
    "Palette",
    "Material",
    "Bleed",
    "Grid",
    "Subject artifact",
    "Density",
    "Motion",
)

DIRECTION_DOC = "docs/design/direction.md"


def seat_agents():
    """Every seat agent that ships, paired with the plugin it belongs to."""
    return sorted(
        (plugin.name, path)
        for plugin in PLUGINS.iterdir()
        if plugin.is_dir()
        for path in (plugin / "agents").glob("*-staff-engineer.md")
    )


def routed_references(text):
    """Reference basenames named in a seat's failure-mode trigger table.

    The table's right-hand column holds a bare stem, never a path, so the seat reads as
    prose while the router owns the links. That is exactly what lets the two disagree
    without anything failing, so the scan is scoped to that one section and takes the
    last cell of every row that is neither the header nor the `|---|` separator.
    """
    # An implementer seat titles this "Step N: Open the failure-mode checklists"; the
    # advisor variant drops the numbered steps and titles it "Failure-mode checklists".
    section = re.split(r"^#+ .*[Ff]ailure-mode checklists.*$", text, flags=re.MULTILINE)[-1]
    section = section.split("\n## ")[0]
    stems = set()
    for line in section.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cell = line.strip().strip("|").rsplit("|", 1)[-1].strip()
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", cell):
            stems.add(cell)
    return stems


@pytest.mark.parametrize("plugin,path", seat_agents(), ids=lambda v: getattr(v, "name", v))
def test_every_reference_a_seat_routes_to_exists(plugin, path):
    """A trigger row pointing at nothing is indistinguishable from a clean checklist."""
    references = PLUGINS / plugin / "skills" / f"{plugin}-failure-modes" / "references"
    if not references.is_dir():
        pytest.skip(f"{plugin} bundles no failure-modes references")
    on_disk = {file.stem for file in references.glob("*.md")}
    named = routed_references(path.read_text())
    assert named, f"{path.name} routes to no reference at all; the scan found nothing"
    missing = sorted(named - on_disk)
    assert not missing, f"{path.name} routes to {missing}, absent from {references}"


def test_the_seat_commits_a_direction_before_it_builds():
    """Step 2 exists, and the operating loop reaches it before any edit."""
    text = DESIGN_AGENT.read_text()
    assert "## Step 2: Commit the direction" in text
    assert "**Commit the direction**" in text, "the operating loop must reach Step 2"
    detect = text.index("## Step 1: Detect the stack")
    direction = text.index("## Step 2: Commit the direction")
    assert detect < direction, (
        "direction follows detection: detection is what reveals whether a system exists"
    )


@pytest.mark.parametrize("axis", AXES)
def test_step_two_still_carries_every_axis(axis):
    """Nine axes are the content of the step; a dropped one is a decision nobody makes."""
    step = DESIGN_AGENT.read_text().split("## Step 2: Commit the direction")[1]
    step = step.split("## Step 3:")[0]
    assert f"**{axis}**" in step, f"Step 2 no longer takes a position on {axis}"


@pytest.mark.parametrize(
    "answer", ['"The framework default"', '"the system default"', '"none"']
)
def test_the_default_is_a_failing_answer(answer):
    """The step is worthless if 'whatever the framework does' satisfies it.

    Naming all three matters: an agent that reads "state a position on each axis" and
    writes "system default" has stated a position, and every screen this step exists to
    prevent was built exactly that way.
    """
    step = DESIGN_AGENT.read_text().split("## Step 2: Commit the direction")[1]
    step = step.split("## Step 3:")[0]
    assert answer in step, f"{answer} is no longer refused by Step 2"
    assert "is a failing answer" in step


def test_the_thesis_precedes_the_axes():
    """Levers chosen without a thesis produce noise; the order is the design."""
    step = DESIGN_AGENT.read_text().split("## Step 2: Commit the direction")[1]
    assert step.index("The thesis comes first") < step.index("Then state a move on each axis")


def test_the_craft_reference_ships_and_is_routed():
    """The one reference asking whether the design is good, not whether it is correct."""
    assert CRAFT.is_file()
    router = (DESIGN / "skills/design-failure-modes/SKILL.md").read_text()
    assert "craft-and-distinctiveness.md" in router
    assert "craft-and-distinctiveness" in DESIGN_AGENT.read_text()


def test_the_craft_reference_keeps_its_attribution():
    """Extracted doctrine, Apache-2.0. Dropping the credit makes it look authored here."""
    text = CRAFT.read_text()
    assert "pbakaus/impeccable" in text and "Apache-2.0" in text


def test_the_self_check_can_fail_a_design_that_decided_nothing():
    """A gate with eleven correctness boxes and no judgment box passes the median."""
    check = DESIGN_AGENT.read_text().split("## Pre-handoff self-check")[1]
    check = check.split("## Common rationalizations")[0]
    assert "signature element" in check
    assert "defended position" in check
    assert "redrawn to serve a different product" in check
    assert "screenshot" in check, "distinctiveness cannot be judged from source"


@pytest.mark.parametrize("seat", CONSUMERS)
def test_no_consuming_seat_routes_to_the_origination_skill(seat):
    """`frontend-design` behind a gate and beside it are not the same offer."""
    text = (PLUGINS / seat / "agents" / f"{seat}-staff-engineer.md").read_text()
    assert "to `frontend-design`" not in text, (
        f"{seat} routes to frontend-design, which bypasses the design seat's direction gate"
    )


@pytest.mark.parametrize("seat", CONSUMERS)
def test_every_consuming_seat_reads_the_direction(seat):
    """A direction nobody downstream opens stops at the seat boundary."""
    text = (PLUGINS / seat / "agents" / f"{seat}-staff-engineer.md").read_text()
    assert DIRECTION_DOC in text, f"{seat} never reads {DIRECTION_DOC}"


def test_the_design_seat_writes_the_direction_where_the_others_read_it():
    assert DIRECTION_DOC in DESIGN_AGENT.read_text()


def test_the_craft_skills_arrive_with_the_plugin():
    """Routing prose naming a skill nothing installs is decorative.

    The seat named `emil-design-eng` and `frontend-design` in its routing table for as
    long as the manifest declared neither, so a fresh project installed the design plugin
    and got a trigger table pointing at nothing.
    """
    manifest = json.loads((DESIGN / ".claude-plugin/plugin.json").read_text())
    declared = set(manifest.get("skillDependencies", ()))
    assert {"frontend-design", "emil-design-eng"} <= declared

    registry = json.loads(SKILL_REGISTRY.read_text())
    tracked = {
        skill["upstream_path"].rstrip("/").rsplit("/", 1)[-1]
        for repo in registry["repos"].values()
        for skill in repo["skills"]
    } | {skill["name"] for skill in registry.get("local_skills", ())}
    assert declared <= tracked, f"{sorted(declared - tracked)} is in no registry"


def test_the_dead_topic_tag_stays_dead():
    """`design` was a synonym of `ui` whose only holder carried both, so `--group design`
    silently returned an incomplete set while `designer` returned the whole family."""
    offenders = []
    registry = json.loads(SKILL_REGISTRY.read_text())
    for repo, body in registry["repos"].items():
        for skill in body["skills"]:
            if "design" in skill.get("groups", ()):
                offenders.append(f"{repo}:{skill['upstream_path']}")
    for skill in registry.get("local_skills", ()):
        if "design" in skill.get("groups", ()):
            offenders.append(skill["name"])
    agents = json.loads(AGENT_REGISTRY.read_text())
    for value in agents.values():
        if isinstance(value, list):
            offenders += [e["name"] for e in value if "design" in e.get("groups", ())]
    for manifest in PLUGINS.glob("*/.claude-plugin/plugin.json"):
        if "design" in json.loads(manifest.read_text()).get("groups", ()):
            offenders.append(manifest.parents[1].name)
    assert not offenders, f"`design` is not a topic tag; use `ui` or the `designer` persona: {offenders}"


def test_precedence_is_stated_once_and_pointed_at():
    """Four copies drift. The rule is cross-seat, so it lives in rules/ like the review policy."""
    rule = CLAUDE / "rules/skill-precedence.md"
    assert rule.is_file()
    text = rule.read_text()
    assert "no skill grants permission" in text.lower()
    for seat in ("design", *CONSUMERS):
        agent = (PLUGINS / seat / "agents" / f"{seat}-staff-engineer.md").read_text()
        assert "skill-precedence.md" in agent, f"{seat} resolves skill conflicts silently"


def test_the_voided_mandate_still_belongs_to_a_skill_that_ships():
    """The rule names emil by file, so a rename upstream must not leave the ban dangling."""
    rule = (CLAUDE / "rules/skill-precedence.md").read_text()
    named = re.findall(r"`([a-z0-9-]+)` carries both", rule)
    assert named, "the rule names no skill whose format mandates it voids"
    registry = json.loads(SKILL_REGISTRY.read_text())
    tracked = {
        skill["upstream_path"].rstrip("/").rsplit("/", 1)[-1]
        for repo in registry["repos"].values()
        for skill in repo["skills"]
    }
    assert set(named) <= tracked, f"{sorted(set(named) - tracked)} is named but not tracked"
