"""Codex's spelling of the policy, the TOML writer it needs, and the merge into a file Codex owns."""

import json
import os
import shutil
import stat
import subprocess
import tomllib

import pytest
from harnessgen import cli, emit_codex, manifest, tomlw

ROOT = manifest.find_root()

# Shaped like a real ~/.codex/config.toml: quoted-key tables, a table holding only
# tables, an empty one, nested env tables, a literal string with JSON in it, hyphenated
# keys, the hook-trust tables Codex writes after /hooks, and an array of tables.
CODEX_CONFIG = r'''
model = "some-model"
personality = "pragmatic"
notify = ["/Applications/Some App.app/Contents/MacOS/client", "turn-ended"]

[marketplaces.bundled]
source_type = "local"
source = "/Users/someone/.codex/.tmp/bundled"

[plugins."browser@openai-bundled"]
enabled = true

[plugins."slack@openai-curated"]
enabled = false

[features]
js_repl = false

[mcp_servers.node_repl]
args = []
command = "/Applications/Some App.app/node_repl"
startup_timeout_sec = 120

[mcp_servers.node_repl.env]
SERVICES = '{"browser":"/x/browser-service.mjs","sky":"@oai/sky/service"}'
EMPTY = ""

[shell_environment_policy.set]
SHA = "9230e2bd"

[desktop]
ambient-suggestions-enabled = false
followUpQueueMode = "queue"

[projects."/Users/someone"]
trust_level = "trusted"

[hooks.state."/Users/someone/.codex/hooks.json:pre_tool_use:0:0"]
enabled = true
trusted_hash = "abc123"

[empty_table]

[[profiles_list]]
name = "first"
ratio = 0.5

[[profiles_list]]
name = "second \"quoted\" \\ tab\t"
nested = { a = 1, b = [1, 2] }
'''


def roundtrip(document):
    return tomllib.loads(tomlw.dumps(document))


# --- the TOML writer ----------------------------------------------------------


def test_a_real_shaped_config_survives_the_round_trip():
    document = tomllib.loads(CODEX_CONFIG)
    assert roundtrip(document) == document


@pytest.mark.parametrize("text", ["", "\x01", "\x7f", "é ☃", 'a"b', "a\\b", "line\nbreak"])
def test_every_string_survives_the_round_trip(text):
    assert roundtrip({"k": text, text or "empty": 1}) == {"k": text, text or "empty": 1}


def test_numbers_and_booleans_survive_the_round_trip():
    document = {"i": -3, "f": 1.5, "big": 10**18, "t": True, "no": False, "inf": float("inf")}
    assert roundtrip(document) == document


def test_a_table_of_only_tables_gets_no_header_of_its_own():
    text = tomlw.dumps({"plugins": {"a@b": {"enabled": True}}})
    assert "[plugins]" not in text and '[plugins."a@b"]' in text


def test_an_empty_table_keeps_its_header():
    assert "[empty]" in tomlw.dumps({"empty": {}})


def test_a_value_toml_cannot_spell_is_refused():
    with pytest.raises(TypeError):
        tomlw.dumps({"k": object()})


# --- the rendered files -------------------------------------------------------


def test_a_pure_prefix_translates_and_a_glob_inside_a_token_does_not():
    assert emit_codex.prefix("git push --force *") == ["git", "push", "--force"]
    assert emit_codex.prefix("git push origin main") == ["git", "push", "origin", "main"]
    assert emit_codex.prefix("git push --force*") is None
    assert emit_codex.prefix("*") is None


def test_every_command_deny_is_a_rule_or_reported():
    policy = manifest.load(ROOT)
    rules = emit_codex.rules(policy)
    reported = emit_codex.untranslatable(policy)
    for pattern in policy.permissions["commands"]["deny"]:
        tokens = emit_codex.prefix(pattern)
        if tokens is None:
            assert f"commands.deny: {pattern}" in reported
        else:
            assert f"pattern = {json.dumps(tokens)}," in rules


def test_a_pattern_and_its_trailing_star_form_are_one_rule():
    policy = manifest.load(ROOT)
    assert emit_codex.rules(policy).count('pattern = ["lazygit"],') == 1


def test_the_sandbox_writes_only_what_codex_can_read_as_a_root():
    """`.` would resolve against ~/.codex, and a `$VAR` is taken literally."""
    policy = manifest.load(ROOT)
    roots = emit_codex.workspace_write(policy.sandbox)["writable_roots"]
    assert "." not in roots and not any(root.startswith("$") for root in roots)
    assert "~/.cache/uv" in roots


def test_the_network_is_off_and_every_domain_is_reported():
    policy = manifest.load(ROOT)
    assert emit_codex.workspace_write(policy.sandbox)["network_access"] is False
    reported = emit_codex.untranslatable(policy)
    assert all(f"network.allow_domains: {d}" in reported for d in policy.sandbox["network"]["allow_domains"])


def test_codex_is_given_only_the_hooks_its_harness_list_names():
    policy = manifest.load(ROOT)
    commands = [h["command"] for g in emit_codex.hooks(policy)["hooks"]["PreToolUse"] for h in g["hooks"]]
    listed = [h["script"] for h in policy.hooks if emit_codex.NAME in h["harnesses"]]
    assert commands == [f"~/.codex/hooks/{script}" for script in listed]


def test_a_hook_matcher_is_anchored_to_the_one_tool():
    """Codex matches a regex, so a bare `Bash` would also match any tool containing it."""
    policy = manifest.load(ROOT)
    assert {g["matcher"] for g in emit_codex.hooks(policy)["hooks"]["PreToolUse"]} == {"^Bash$"}


@pytest.mark.skipif(shutil.which("codex") is None, reason="codex is not installed")
def test_codex_itself_forbids_what_the_rules_forbid(tmp_path):
    rules = tmp_path / "dotfiles.rules"
    rules.write_text(emit_codex.rules(manifest.load(ROOT)))

    def decision(*argv):
        result = subprocess.run(
            ["codex", "execpolicy", "check", "--rules", str(rules), "--", *argv],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout).get("decision")

    assert decision("git", "push", "--force", "origin", "x") == "forbidden"
    assert decision("sudo", "ls") == "forbidden"
    assert decision("git", "push", "origin", "feature") is None


# --- apply --------------------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def config_of(home):
    return home / ".codex" / "config.toml"


def test_apply_replaces_the_owned_keys_and_keeps_every_other(home):
    config_of(home).parent.mkdir()
    config_of(home).write_text(CODEX_CONFIG)
    cli.apply_codex(ROOT)
    merged = tomllib.loads(config_of(home).read_text())
    owned = emit_codex.owned(manifest.load(ROOT))
    assert {key: merged[key] for key in owned} == owned
    original = tomllib.loads(CODEX_CONFIG)
    assert {k: merged[k] for k in original if k not in owned} == {k: v for k, v in original.items() if k not in owned}


def test_a_second_apply_changes_nothing(home):
    cli.apply_codex(ROOT)
    assert cli.apply_codex(ROOT) == []
    assert cli.apply_codex(ROOT, check_only=True) == []


def test_apply_check_writes_nothing(home):
    assert cli.apply_codex(ROOT, check_only=True)
    assert not (home / ".codex").exists()


def test_the_untouched_config_is_kept_once(home):
    config_of(home).parent.mkdir()
    config_of(home).write_text(CODEX_CONFIG)
    cli.apply_codex(ROOT)
    backup = config_of(home).with_name("config.toml" + cli.BACKUP_SUFFIX)
    assert backup.read_text() == CODEX_CONFIG
    config_of(home).write_text('model = "picked-later"\n')
    cli.apply_codex(ROOT)
    assert backup.read_text() == CODEX_CONFIG


def test_a_new_config_is_private(home):
    """Codex keeps its config owner-only, and it can hold MCP credentials."""
    cli.apply_codex(ROOT)
    assert stat.S_IMODE(os.stat(config_of(home)).st_mode) == 0o600


def test_the_rules_land_as_a_real_file(home):
    cli.apply_codex(ROOT)
    rules = home / ".codex" / "rules" / "dotfiles.rules"
    assert rules.is_file() and not rules.is_symlink()
    assert rules.read_text() == emit_codex.rules(manifest.load(ROOT))
