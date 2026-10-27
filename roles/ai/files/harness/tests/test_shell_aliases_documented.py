"""Every fish alias that shadows a system tool is named in the global instructions.

The agent's own shell runs without fish or its aliases, so a command it hands the user
to paste only works if the instructions say which names mean something else there.
"""

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
