"""Shared instructions scope Fish syntax to user-terminal snippets and document aliases."""

import re
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
REPO = HARNESS.parents[3]
ALIASES = REPO / "roles/shell/files/fish/conf.d/aliases/aliases.fish"
AGENTS = HARNESS / "AGENTS.md"
SECTION = "## Commands for the user's terminal"
SYSTEM_DIRS = [Path(d) for d in ("/bin", "/usr/bin", "/sbin", "/usr/sbin")]


def shadowing_aliases():
    names = re.findall(r"^alias\s+([^=\s]+)=", ALIASES.read_text(), flags=re.MULTILINE)
    return sorted(n for n in names if any((d / n).is_file() for d in SYSTEM_DIRS))


def terminal_section():
    text = AGENTS.read_text()
    start = text.index(SECTION)
    end = text.find("\n## ", start + len(SECTION))
    return text[start:end if end != -1 else None]


def test_some_alias_shadows_a_system_tool():
    assert "grep" in shadowing_aliases()


def test_every_shadowing_alias_is_documented():
    section = terminal_section()
    missing = [n for n in shadowing_aliases() if f"`{n}`" not in section]
    assert missing == [], f"add {missing} to the '{SECTION}' section of {AGENTS.name}"


def test_fish_syntax_is_for_user_terminal_snippets():
    section = terminal_section()
    for requirement in (
        "The user's interactive shell is fish 4",
        "commands for the user to paste into their terminal",
        "use syntax compatible with their shell unless they explicitly request another shell",
        "terminal snippets and manual handoffs, not to the agent's tool execution",
    ):
        assert requirement in section, f"missing user-terminal boundary: {requirement}"


def test_plain_commands_need_no_wrappers_or_scripts():
    section = terminal_section()
    assert "Plain CLI commands that already work in Fish need no changes, wrapper, or script file" in section
    assert "Do not create Fish scripts or introduce a Fish dependency merely because the user runs Fish" in section
    assert "`fish --no-config -c '<fish code>'`" not in section
    assert "Temporary machine-local shell scripts must" not in section


def test_project_artifacts_follow_the_target_environment():
    section = terminal_section()
    assert "follow the project's conventions and target environment, not the user's login shell" in section
    assert "Existing repository and vendor scripts keep their declared interpreter" in section


def test_agent_tools_use_their_execution_shell():
    section = terminal_section()
    assert "Agent tool calls use the tool's execution shell" in section
    assert "do not wrap commands in Fish merely because the user's terminal runs Fish" in section
