"""The frontmatter and path assumptions that let pi run the staff-engineer fleet.

Two harnesses read one payload, and each reads its own frontmatter dialect while
ignoring the other's. Claude Code reads `effort:` and `disallowedTools:`; pi's
pi-subagents extension reads `thinking:` and `disallowed_tools:`. Nothing enforces
agreement at load time in either harness: a seat whose `thinking:` drifts from its
`effort:` simply runs at two different depths depending on who spawned it, with no
error anywhere. Equality here is the only guard.

The paths are the same shape of assumption, living in someone else's loader.
pi-subagents discovers agents from exactly three places and never from `.claude/`:

  .pi/agents/           pi's own project namespace; not used here, because nothing
                        of ours is pi-specific and a second location would be a
                        second install to converge
  .agents/agents/       the harness-neutral project location, so `claude_kit.pi`
                        converges each installed plugin's agents/*.md into it as
                        per-file links (no single directory holds every agent the
                        installed plugins ship, so one directory link cannot do it)
  ~/.pi/agent/agents/   the global location, which the ai role links wholesale at
                        ~/.claude/agents, the directory `claude-kit sync` already
                        converges from the `global` tag

A renamed constant in pi.py, a retargeted role task, or a dropped `packages` entry
would each break the fleet under pi while every Claude-side test stays green and
`add` still reports success. That silence is what this module exists to end.
"""

import json
import sys

import pytest
import yaml
from dotkit.testing import AGENTS, AI_SCRIPTS_DIR, PI, PLUGINS, REPO

# The tool's own directory, exactly as its shim and its own suite's conftest insert
# it. Idempotent, and the same path claude-kit's tests use, so the two suites share
# one claude_kit in sys.modules rather than racing for the name.
if str(AI_SCRIPTS_DIR / "claude-kit") not in sys.path:
    sys.path.insert(0, str(AI_SCRIPTS_DIR / "claude-kit"))

from claude_kit import pi  # noqa: E402

AI_TASKS = REPO / "roles/ai/tasks/main.yml"
PI_SETTINGS = PI / "settings.json"

DIRS_TASK = "Ensure AI config directories exist"
AGENTS_LINK_TASK = "Point pi at the global claude agents"

# Claude's key first, pi's second. One row per fact the two harnesses must agree on.
DUAL_KEYS = (("effort", "thinking"), ("disallowedTools", "disallowed_tools"))


def frontmatter_of(path):
    """The frontmatter block, parsed. PyYAML is the oracle here as everywhere in tests."""
    text = path.read_text()
    assert text.startswith("---\n"), f"{path.name} has no frontmatter block"
    return yaml.safe_load(text.split("---\n", 2)[1])


def agent_files():
    """Every agent definition either harness could load: registry agents and seat agents."""
    yield from sorted(AGENTS.glob("*.md"))
    yield from sorted(PLUGINS.glob("*/agents/*.md"))


def dual_keyed():
    """The files required to speak both dialects: architect plus every implementer seat.

    An implementer seat is a seat agent without a `tools:` allowlist, the same split
    test_catalog.py pins. The advisor is exempt rather than forbidden: its `tools:`
    key is a same-key dialect collision (both harnesses read that name, and the
    values are Claude tool names), so it stays Claude-only until that is bridged,
    and nothing here asserts it must stay that way.
    """
    yield AGENTS / "architect.md"
    for path in sorted(PLUGINS.glob("*/agents/*-staff-engineer.md")):
        if "tools" not in frontmatter_of(path):
            yield path


# --- the frontmatter dialect --------------------------------------------------


@pytest.mark.parametrize("path", list(dual_keyed()), ids=lambda p: p.name)
def test_every_implementer_agent_carries_both_effort_keys_equal(path):
    """`effort:` is Claude's dial and `thinking:` is pi's, and each harness ignores
    the other's key. A seat carrying only one runs at the pinned depth under one
    harness and at the session default under the other, which is exactly the drift
    the pins in the seat anatomy exist to prevent."""
    fm = frontmatter_of(path)
    assert "effort" in fm, f"{path.name} lost its Claude effort pin"
    assert "thinking" in fm, f"{path.name} carries no pi counterpart for effort"
    assert fm["effort"] == fm["thinking"], (
        f"{path.name} pins effort={fm['effort']} but thinking={fm['thinking']}, "
        "so the two harnesses run this seat at different depths"
    )


def test_the_dual_keyed_set_is_the_architect_plus_the_implementer_bench():
    """The parametrize above passes vacuously if the seat glob stops matching."""
    found = list(dual_keyed())
    assert len(found) >= 15, f"expected architect plus 14 implementer seats, found {len(found)}"


@pytest.mark.parametrize("path", list(agent_files()), ids=lambda p: p.name)
def test_the_two_dialects_never_disagree_where_both_are_spoken(path):
    """Wherever an agent carries both keys of a pair, the values are equal.

    Equality only, not presence: an agent outside the fleet (`ux-shaper`, the
    advisor) legitimately carries `effort:` alone today, and required presence for
    the fleet is the first test's business. What no file may do is answer the same
    question differently per harness."""
    fm = frontmatter_of(path)
    for claude_key, pi_key in DUAL_KEYS:
        if claude_key in fm and pi_key in fm:
            assert fm[claude_key] == fm[pi_key], (
                f"{path.name}: {claude_key}={fm[claude_key]} but {pi_key}={fm[pi_key]}"
            )


@pytest.mark.parametrize("path", list(agent_files()), ids=lambda p: p.name)
def test_a_disallow_in_one_dialect_is_a_disallow_in_both(path):
    """Both directions, unlike the effort pair: a constraint is not a preference.

    `disallowedTools:` without `disallowed_tools:` means pi ignores a ban Claude
    enforces (architect's Agent ban is load-bearing: orchestration stays with the
    caller), and the reverse means Claude does. There is no agent for which one
    harness should enforce what the other waives."""
    fm = frontmatter_of(path)
    claude_key, pi_key = "disallowedTools", "disallowed_tools"
    if claude_key in fm or pi_key in fm:
        assert claude_key in fm and pi_key in fm, (
            f"{path.name} carries {claude_key if claude_key in fm else pi_key}: "
            "without its counterpart, so one harness silently ignores the ban"
        )


def test_architect_bans_the_agent_tool_in_both_dialects():
    """The one place the disallow pair is load-bearing today: orchestration stays
    with the caller under either harness."""
    fm = frontmatter_of(AGENTS / "architect.md")
    assert fm["disallowedTools"] == "Agent"
    assert fm["disallowed_tools"] == "Agent"


# --- the discovery paths ------------------------------------------------------


def test_claude_kit_writes_agent_links_where_pi_subagents_reads():
    """`.agents/agents` is pi-subagents' harness-neutral project location, read out
    of the extension rather than chosen here. The literal is the contract: a renamed
    constant in pi.py leaves `add` linking into a directory nothing reads, with every
    behavioural test in test_pi.py still green because they only ever ask pi.py where
    it wrote."""
    assert pi.PARENT == ".agents"
    assert pi.AGENTS_LEAF == "agents"
    project = REPO / "somewhere"
    assert pi.agents_path(project) == project / ".agents" / "agents"


def test_the_ai_role_links_pis_global_agents_at_claudes():
    """The third discovery location, ~/.pi/agent/agents/, is one directory link at
    ~/.claude/agents, so the global set is derived, linked and pruned by `sync` alone."""
    tasks = yaml.safe_load(AI_TASKS.read_text())
    matching = [t for t in tasks if t.get("name") == AGENTS_LINK_TASK]
    assert len(matching) == 1, f"expected exactly one '{AGENTS_LINK_TASK}' task in the ai role"
    spec = matching[0]["ansible.builtin.file"]
    assert spec["state"] == "link"
    assert spec["src"] == "{{ HOME }}/.claude/agents"
    assert spec["dest"] == "{{ HOME }}/.pi/agent/agents"
    assert spec["force"] is True, "without force a pre-existing entry fails the play"


def test_the_link_target_is_created_before_the_link():
    """`state: link` with force writes a dangling link happily, so ~/.claude/agents
    must be in the directories task or a first run points pi at nothing."""
    tasks = yaml.safe_load(AI_TASKS.read_text())
    dirs = next(t for t in tasks if t.get("name") == DIRS_TASK)
    assert "{{ HOME }}/.claude/agents" in dirs["loop"]


def test_pi_subagents_is_declared_in_the_settings_pi_actually_loads():
    """The extension is the reason any of the above matters: without the package
    entry, pi ships no Agent tool and every path here is a directory nothing reads."""
    packages = json.loads(PI_SETTINGS.read_text())["packages"]
    assert "npm:@tintinweb/pi-subagents" in packages
