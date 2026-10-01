"""The rendered files are the policy, and a build is the only thing that changes them.

policy/*.toml is the one statement of what an agent may do. Every harness file below is
rendered from it, so a hand edit to one of them is drift: it holds until the next
`make harness` silently reverts it, or it never reaches the other harnesses at all.
"""

import json
import shutil
import subprocess
import sys

import pytest
from harnessgen import cli, emit_claude, emit_codex, emit_pi, manifest

ROOT = manifest.find_root()
RENDERED = [emit_claude.SETTINGS, *cli.whole_files(manifest.load(ROOT))]
ADAPTERS = [str(p.relative_to(ROOT)) for p in ROOT.glob("adapters/*/adapter.toml")]


@pytest.fixture
def harness(tmp_path):
    """The inputs and outputs of one build, copied somewhere a test may write."""
    for relative in ["harness.toml", "policy", "mcp.json", "adapters/pi/mcp.json", *ADAPTERS, *RENDERED]:
        source, target = ROOT / relative, tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if source.is_dir() else shutil.copy)(source, target)
    return tmp_path


def test_every_rendered_file_matches_the_policy():
    assert cli.check(ROOT) == [], "run `make harness`"


def test_the_cli_exits_clean_on_this_checkout():
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin/harness-build"), "build", "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_second_build_writes_nothing(harness):
    cli.build(harness)
    assert cli.build(harness) == []


def test_pi_sandbox_reads_prompt_limits_and_extra_paths_from_its_adapter(harness):
    (harness / "adapters/pi/adapter.toml").write_text(
        "[sandbox]\npermissionPromptTimeoutSeconds = 30\npermissionPromptMaxAttempts = 1\n"
        '[sandbox.filesystem]\nallowRead = ["~/package-skills"]\n'
    )
    policy = manifest.load(harness)
    config = emit_pi.sandbox(policy)
    assert config["permissionPromptTimeoutSeconds"] == 30
    assert config["permissionPromptMaxAttempts"] == 1
    assert config["filesystem"]["allowRead"] == [
        *policy.sandbox["filesystem"]["allow_read"], "~/package-skills",
    ]


def test_a_hand_edit_to_pi_mcp_config_is_named(harness):
    cli.build(harness)
    path = harness / emit_pi.MCP
    document = json.loads(path.read_text())
    document["mcpServers"]["slack"]["url"] = "https://example.invalid/mcp"
    path.write_text(json.dumps(document))
    assert cli.check(harness) == [emit_pi.MCP]


def test_a_hand_edit_to_a_whole_rendered_file_is_named(harness):
    cli.build(harness)
    path = harness / emit_pi.SANDBOX
    document = json.loads(path.read_text())
    document["network"]["allowedDomains"].append("example.com")
    path.write_text(json.dumps(document))
    assert cli.check(harness) == [emit_pi.SANDBOX]


def test_a_hand_edit_to_an_owned_settings_key_is_named(harness):
    cli.build(harness)
    path = harness / emit_claude.SETTINGS
    settings = json.loads(path.read_text())
    settings["permissions"]["allow"].append("Bash(curl:*)")
    path.write_text(json.dumps(settings))
    assert cli.check(harness) == [f"{emit_claude.SETTINGS}: permissions"]


def test_keys_the_generator_does_not_own_are_left_alone(harness):
    """Claude writes `model` itself on /model, and herdr appends its own hooks."""
    cli.build(harness)
    path = harness / emit_claude.SETTINGS
    settings = json.loads(path.read_text())
    settings["model"] = "a-model-picked-at-runtime"
    path.write_text(json.dumps(settings, indent=2) + "\n")
    assert cli.check(harness) == []
    cli.build(harness)
    assert json.loads(path.read_text())["model"] == "a-model-picked-at-runtime"


def test_a_hand_edited_managed_hook_is_named(harness):
    cli.build(harness)
    path = harness / emit_claude.SETTINGS
    settings = json.loads(path.read_text())
    settings["hooks"]["PreToolUse"][0]["hooks"].pop(0)
    path.write_text(json.dumps(settings))
    assert cli.check(harness) == [f"{emit_claude.SETTINGS}: hooks"]


def test_a_hook_herdr_appends_survives_a_build(harness):
    cli.build(harness)
    path = harness / emit_claude.SETTINGS
    settings = json.loads(path.read_text())
    appended = {"matcher": "^startup$", "hooks": [{"type": "command", "command": "bash '/x/herdr.sh' session"}]}
    settings["hooks"]["SessionStart"].append(appended)
    path.write_text(json.dumps(settings, indent=2) + "\n")
    assert cli.check(harness) == []
    cli.build(harness)
    assert appended in json.loads(path.read_text())["hooks"]["SessionStart"]


def test_a_hand_edit_to_a_rendered_text_file_is_named(harness):
    """The rules file is Starlark, not JSON, so it is compared as text."""
    cli.build(harness)
    path = harness / emit_codex.RULES
    path.write_text(path.read_text().replace('"forbidden"', '"prompt"', 1))
    assert cli.check(harness) == [emit_codex.RULES]
