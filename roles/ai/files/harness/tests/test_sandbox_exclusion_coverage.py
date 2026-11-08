"""Claude commands stay sandboxed even when a skill or command permission allows them."""

import fnmatch
import re

import pytest
from harnessgen import manifest

POLICY = manifest.load()
CLAUDE_RULE_RE = re.compile(r"^Bash\((.*)\)$")


def test_no_claude_command_bypasses_the_sandbox():
    sandbox = POLICY.adapter("claude")["sandbox"]
    assert sandbox["enabled"] is True
    assert sandbox["allowUnsandboxedCommands"] is False
    assert sandbox["excludedCommands"] == []


@pytest.mark.parametrize("probe", [
    f"{launcher}~/.claude/skills/{skill}/scripts/apply.py plan.json"
    for skill in ("commit", "pr", "ship")
    for launcher in ("python3 ", "python ", "bash ", "")
])
def test_every_spelling_of_a_skill_script_reaches_git_skill_gate_under_claude(probe):
    hook = next(h for h in POLICY.hooks_for("claude") if h["id"] == "git-skill-gate")
    rules = [CLAUDE_RULE_RE.match(rule).group(1) for rule in hook.get("claude_if", [])]
    assert not rules or any(fnmatch.fnmatchcase(probe, rule) for rule in rules)
