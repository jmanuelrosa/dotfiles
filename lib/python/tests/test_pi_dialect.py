"""The agent paths and settings that let Pi run the shared global agents.

Kura manages standalone agents and bundle-owned ones in native Claude and Pi roots.
The AI role removes its old links. The frontmatter dialect those agents and skills
speak is the catalog's, asserted in agent-catalog's tests/test_pi_dialect.py.
"""

import json

import yaml
from dotkit.testing import (
    PI,
    REPO,
    harness_dirs,
    harness_links,
)

AI_TASKS = REPO / "roles/ai/tasks/main.yml"
PI_SETTINGS = PI / "settings.json"


# --- the discovery paths ------------------------------------------------------


def test_kura_owns_pis_global_agent_root():
    """pi-subagents reads global agents from ~/.pi/agent/agents, which `kura sync` creates
    and fills, so the link table neither creates nor links it."""
    assert "~/.pi/agent/agents" not in harness_dirs()
    assert "~/.pi/agent/agents" not in harness_links()


def test_the_link_parent_is_created_before_the_link():
    """`state: link` with force writes a link into a missing parent as an error, so
    ~/.pi/agent must be in the directories the role creates first."""
    assert "~/.pi/agent" in harness_dirs()


def test_pi_subagents_is_declared_in_the_settings_pi_actually_loads():
    """The extension is the reason any of the above matters: without the package
    entry, pi ships no Agent tool and every path here is a directory nothing reads."""
    packages = json.loads(PI_SETTINGS.read_text())["packages"]
    assert "npm:@tintinweb/pi-subagents" in packages
    assert "npm:pi-subagents" not in packages


def test_old_subagent_overrides_are_removed_and_mentions_start_directly():
    settings = json.loads(PI_SETTINGS.read_text())
    assert "subagents" not in settings
    assert not any("npm:pi-subagents" in key for key in settings["extensionChangelogVersions"])
    config = json.loads((PI / "subagents.json").read_text())
    assert config["agentMentions"] == "direct"
    assert config["worktreeIsolation"] is False


def test_the_role_installs_herdr_for_pi_as_well_as_claude():
    """herdr ships a pi integration, and one status call gates both.

    The claude half has always been installed by the play and the pi half was left to
    whoever remembered, so a fresh machine reported claude state and nothing else. Both
    read the same register, so a second `herdr integration status` call here would be a
    second source of truth for the same question.
    """
    install = next(
        task for task in yaml.safe_load(AI_TASKS.read_text())
        if task.get("name") == "Install the herdr integrations"
    )
    assert install["ansible.builtin.command"] == "herdr integration install {{ item }}"
    assert install["loop"] == "{{ HARNESS_ENABLED | intersect(['claude', 'pi']) }}", (
        "a fresh machine gets no pi telemetry"
    )
    assert install["when"] == "(item ~ ': current') not in herdr_integration.stdout", (
        "the install is ungated"
    )
    tasks = AI_TASKS.read_text()
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


def test_the_repo_root_claude_md_imports_the_shared_agents_md():
    agents = REPO / "AGENTS.md"
    assert agents.is_file() and not agents.is_symlink(), "root AGENTS.md must be a real file"
    assert (REPO / "CLAUDE.md").read_text().strip() == "@AGENTS.md"
    assert not (REPO / ".claude" / "CLAUDE.md").exists() or \
           (REPO / ".claude" / "CLAUDE.md").is_symlink(), \
           ".claude/CLAUDE.md must be a link (to ~/.claude/CLAUDE.md), not a file"
