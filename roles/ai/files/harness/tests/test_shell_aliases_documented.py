"""Shared instructions require fish code and document aliases that shadow system tools."""

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


def test_fish_covers_internal_execution_and_sandbox_handoffs():
    section = terminal_section()
    for context in ("internal shell tool calls", "temporary helper scripts", "sandbox handoffs"):
        assert context in section, f"fish policy must cover {context}"


def test_generated_scripts_require_fish_and_syntax_checks():
    section = terminal_section()
    for requirement in ("`.fish`", "`#!/usr/bin/env fish`", "`fish --no-execute", "Never generate Bash or Zsh"):
        assert requirement in section, f"missing generated-script rule: {requirement}"


def test_fish_execution_preserves_sandbox_and_existing_interpreters():
    section = terminal_section()
    for requirement in ("`fish -c '<fish code>'`", "standalone CLI calls direct", "declared interpreter"):
        assert requirement in section, f"missing shell-host boundary: {requirement}"
