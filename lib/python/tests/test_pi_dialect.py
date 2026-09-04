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
import re
import sys

import pytest
import yaml
from dotkit.testing import AGENTS, AI_SCRIPTS_DIR, PI, PLUGINS, REPO, SKILLS

# The tool's own directory, exactly as its shim and its own suite's conftest insert
# it. Idempotent, and the same path claude-kit's tests use, so the two suites share
# one claude_kit in sys.modules rather than racing for the name.
if str(AI_SCRIPTS_DIR / "claude-kit") not in sys.path:
    sys.path.insert(0, str(AI_SCRIPTS_DIR / "claude-kit"))

from claude_kit import pi  # noqa: E402

AI_TASKS = REPO / "roles/ai/tasks/main.yml"
PI_SETTINGS = PI / "settings.json"
PI_MCP_SETTINGS = PI / "mcp.json"

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
    """Every agent that pins a depth for Claude, which must pin the same one for pi.

    The invariant is `effort:`, not a filename: an agent carrying Claude's key and
    not pi's runs at two different depths depending on who spawned it. So the set is
    derived from the frontmatter rather than from a glob, because a glob is a guess
    about where such agents live and it was wrong twice over. `*-staff-engineer.md`
    missed the seven product-team agents, and a `tools:` filter then dropped them
    again along with the security advisor.

    That filter was the subtler half. `tools:` is a same-key dialect collision, both
    harnesses read that name and the values are Claude tool names, so an agent
    carrying one stays Claude-only for *tool* purposes. That says nothing about its
    depth pin, and using it to skip the effort check silenced eight files that could
    carry `thinking:` today. The two concerns are independent, so `tools_unbridged`
    records the collision separately and no longer suppresses anything.
    """
    for path in agent_files():
        if "effort" in frontmatter_of(path):
            yield path


def tools_unbridged():
    """The agents whose `tools:` allowlist is Claude-only, listed rather than inferred.

    Read-only advisors and the product-team bench. Their values are Claude tool names,
    which pi would misread, so the key is not bridged. Naming them keeps the exemption
    visible instead of hiding it in a predicate that also governs the depth pin.
    """
    return sorted(path for path in agent_files() if "tools" in frontmatter_of(path))


# --- the frontmatter dialect --------------------------------------------------


@pytest.mark.parametrize("path", list(dual_keyed()), ids=lambda p: p.name)
def test_every_agent_pinning_a_depth_carries_both_keys_equal(path):
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


def test_every_agent_pinning_effort_is_in_the_dual_keyed_set():
    """The parametrize above passes vacuously if the set stops matching anything.

    Stated as an identity against the whole agent population rather than as a floor,
    so a file that gains `effort:` is covered the moment it does, and one that loses
    it drops out without anybody editing a number here.
    """
    found = set(dual_keyed())
    expected = {path for path in agent_files() if "effort" in frontmatter_of(path)}
    assert found == expected
    assert len(found) >= 22, (
        f"expected the architect, ux-shaper, the 15 seats and the product-team bench, "
        f"found {len(found)}"
    )


def test_the_unbridged_tools_exemption_does_not_hide_a_depth_pin():
    """The regression this module missed for as long as it globbed on a filename.

    Every agent carrying `tools:` is Claude-only for tools and still obliged to pin
    both depth keys, so the two sets are allowed to overlap freely. Asserting the
    overlap is non-empty is what proves the exemption no longer excuses a missing
    `thinking:`.
    """
    unbridged = set(tools_unbridged())
    assert unbridged, "no agent carries tools:, so this exemption is stale"
    assert unbridged & set(dual_keyed()), (
        "every tools:-carrying agent dropped out of the depth check, which is the "
        "exact hole that let eight agents run at pi's session default"
    )


@pytest.mark.parametrize("path", list(agent_files()), ids=lambda p: p.name)
def test_the_two_dialects_never_disagree_where_both_are_spoken(path):
    """Wherever an agent carries both keys of a pair, the values are equal.

    Equality only, not presence: `disallowedTools:` is carried by two agents and
    required of none, and presence of the depth pair is the first test's business.
    What no file may do is answer the same question differently per harness."""
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


def test_pi_mcp_adapter_imports_existing_host_configs_from_a_linked_config():
    """The package and its host imports survive a fresh role apply together."""
    packages = json.loads(PI_SETTINGS.read_text())["packages"]
    assert "npm:pi-mcp-adapter" in packages

    config = json.loads(PI_MCP_SETTINGS.read_text())
    assert config == {
        "mcpServers": {},
        "imports": [],
    }

    tasks = yaml.safe_load(AI_TASKS.read_text())
    link_task = next(task for task in tasks if task.get("name") == "Symlink pi agent config")
    assert "pi/mcp.json" in link_task["loop"]


def test_the_role_installs_herdr_for_pi_as_well_as_claude():
    """herdr ships a pi integration, and one status call gates both.

    The claude half has always been installed by the play and the pi half was left to
    whoever remembered, so a fresh machine reported claude state and nothing else. Both
    read the same register, so a second `herdr integration status` call here would be a
    second source of truth for the same question.
    """
    tasks = AI_TASKS.read_text()
    assert "herdr integration install pi" in tasks, "a fresh machine gets no pi telemetry"
    assert "'pi: current' not in herdr_integration.stdout" in tasks, "the pi install is ungated"
    # Command lines only. Counting occurrences in the file would count the prose above
    # them, which is how this assertion first failed against a comment.
    invocations = [
        line
        for line in tasks.splitlines()
        if line.strip().startswith("ansible.builtin.command:") and "herdr integration status" in line
    ]
    assert len(invocations) == 1, f"{len(invocations)} status calls for one question"


def test_the_settings_pi_loads_are_parseable():
    """A trailing comma here costs every setting, silently.

    Pi reads settings.json with JSON.parse and, on failure, loads no settings at all:
    no `packages`, no model pins, no theme. That is how the copy in the previous
    checkout disabled pi-subagents for weeks while the file looked fine to the eye.
    The assertion above happens to parse it, but that is a side effect of asking for
    one key, so the guarantee is stated here in its own right.
    """
    assert isinstance(json.loads(PI_SETTINGS.read_text()), dict)


def test_the_repo_root_agents_md_is_the_claude_md_pi_would_otherwise_miss():
    """pi prefers AGENTS.md over CLAUDE.md per directory, so two files means drift.

    Context files are discovered per directory as `AGENTS.md` *or* `CLAUDE.md`, so a
    repo shipping both hands pi the former and Claude Code the latter. A parallel
    summary is what that produced here: the root AGENTS.md kept describing a layout
    two restructures out of date while CLAUDE.md moved on. One file, reached under
    both names, is the only arrangement that cannot drift.

    Relative on purpose, as the dotkit links are: an absolute target would bake this
    checkout's path into every clone.
    """
    link = REPO / "AGENTS.md"
    assert link.is_symlink(), "root AGENTS.md must be a link, or it drifts from CLAUDE.md"
    target = link.readlink()
    assert not target.is_absolute(), f"AGENTS.md points at {target}, which breaks other clones"
    assert target.name == "CLAUDE.md"
    assert link.resolve() == (REPO / "CLAUDE.md").resolve()


# --- the keys pi ignores on a skill -------------------------------------------
#
# Agents are dual-keyed above because pi-subagents reads agent frontmatter. Skills are
# not, and cannot be: pi's own loader (dist/core/skills.js in 0.84.x) reads exactly
# three fields from a SKILL.md, `name`, `description` and `disable-model-invocation`,
# and ignores everything else.
#
# So `allowed-tools:`, `model:` and `effort:` on a skill are Claude-only, silently. The
# consequence worth stating is the first one: a skill Claude Code restricts to a handful
# of tools runs with pi's full tool set. Enforcing it here was considered and rejected,
# because the values are Claude permission specifiers with argument patterns
# (`Bash(git status *)`), so 17 of the 20 skills that carry the key qualify their Bash;
# a tool-name-level gate would have allowed an unrestricted shell for those 17 while
# reading like enforcement. What covers that surface instead is pi-sandbox, configured
# from the same Claude settings (see test_pi_sandbox.py), which confines what any command
# may touch rather than which skill may run it.
#
# The set is frozen so the limitation cannot quietly widen. A skill added here is a
# decision to make, not a line to update: either the restriction does not matter under
# pi, or the surface it guards belongs in the sandbox config.
#
# `cloudflare` took the first branch. Its `allowed-tools` lists only read-only commands
# and omits every mutating one, so what Claude gets from the key is a skipped prompt on
# the safe calls, not a gate on the dangerous ones. Under pi the writes prompt like any
# other command, which is the same outcome the key buys under Claude. The sandbox is not
# the answer for the rest of that surface either: a Cloudflare write leaves over the
# network and touches no path pi-sandbox can confine, so the confirmation that actually
# protects the account is the skill's own "Before any write" section, which both
# harnesses read as prose.

SKILL_KEYS_PI_IGNORES = ("allowed-tools", "model", "effort")

CLAUDE_ONLY_SKILL_FRONTMATTER = {
    "ac", "agent-writer", "apollo-client", "cloudflare", "coderabbit", "commit",
    "graphql-operations", "humanizer", "jira", "pr", "product-lead", "research",
    "setup-review",
    "0-refine-idea", "1-research", "2-write-prd", "3-red-team", "4-tech-shape",
    "5-decompose", "6-verify", "7-push-to-board", "8-living-spec", "setup-strategy",
}


def skill_files():
    """Every SKILL.md either harness could load, local and plugin-bundled."""
    yield from sorted(SKILLS.glob("*/SKILL.md"))
    yield from sorted(PLUGINS.glob("*/skills/*/SKILL.md"))


def skills_with_claude_only_keys():
    found = set()
    for path in skill_files():
        text = path.read_text()
        if not text.startswith("---\n"):
            continue
        block = text.split("---\n", 2)[1]
        if any(re.search(rf"^{key}:", block, re.M) for key in SKILL_KEYS_PI_IGNORES):
            found.add(path.parent.name)
    return found


def test_the_set_of_skills_pi_reads_differently_has_not_widened():
    """A frozen set, because the drift is silent in both directions.

    pi reports nothing when it ignores a key, and Claude reports nothing when a skill
    gains one, so neither harness would ever mention that a new skill joined this list.
    """
    assert skills_with_claude_only_keys() == CLAUDE_ONLY_SKILL_FRONTMATTER


def test_no_skill_pretends_to_speak_pis_dialect():
    """`thinking:` on a SKILL.md would read as a pin pi honours, and pi reads no such key.

    Dual-keying an agent is correct and dual-keying a skill is theatre, so the mistake
    worth catching is someone copying the agent convention one directory over.
    """
    for path in skill_files():
        text = path.read_text()
        if not text.startswith("---\n"):
            continue
        block = text.split("---\n", 2)[1]
        assert not re.search(r"^thinking:", block, re.M), (
            f"{path.parent.name}/SKILL.md carries `thinking:`, which pi's skill loader "
            f"never reads; only agent frontmatter is dual-keyed"
        )
