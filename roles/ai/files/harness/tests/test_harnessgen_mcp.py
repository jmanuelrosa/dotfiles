"""The shared inventory merges by name without adopting app-owned servers."""

import json
import shutil
import tomllib

import pytest
import yaml
from harnessgen import cli, manifest, mcp

ROOT = manifest.find_root()


@pytest.fixture
def harness(tmp_path, monkeypatch):
    for relative in ["harness.toml", "policy", "mcp.json", "adapters/claude/adapter.toml", "adapters/codex/adapter.toml"]:
        source, target = ROOT / relative, tmp_path / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if source.is_dir() else shutil.copy)(source, target)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return tmp_path / "source", tmp_path / "home"


def inventory(root, servers):
    (root / "mcp.json").write_text(json.dumps({"mcpServers": servers}))


def test_notion_is_the_initial_server_and_policy_still_denies_its_tools():
    assert mcp.load(ROOT) == {"notion": {"type": "http", "url": "https://mcp.notion.com/mcp"}}
    assert {"notion", "Notion"} <= set(manifest.load(ROOT).permissions["mcp"]["deny"])


def test_slack_is_pi_only_and_its_link_refuses_user_owned_overrides():
    pi_only = json.loads((ROOT / "adapters/pi/mcp.json").read_text())["mcpServers"]
    assert set(pi_only) == {"slack"}
    assert pi_only["slack"]["url"] == "https://mcp.slack.com/mcp"
    assert not (set(pi_only) & set(mcp.load(ROOT)))

    ai_role = ROOT.parents[1]
    links = yaml.safe_load((ai_role / "defaults/main.yml").read_text())["HARNESS_LINKS"]["pi"]["files"]
    assert {"src": "adapters/pi/mcp.json", "dest": "{{ HOME }}/.pi/agent/mcp.json"} in links
    tasks = yaml.safe_load((ai_role / "tasks/main.yml").read_text())
    assert any(task["name"] == "Refuse to replace a user-owned Pi MCP override" for task in tasks)
    assert any(task["name"] == "Refuse shared server names in the Pi-only inventory" for task in tasks)
    assert not any("mcp.json" in task.get("ansible.builtin.file", {}).get("path", "") and
                   task["ansible.builtin.file"].get("state") == "absent" for task in tasks)


def test_claude_adds_only_managed_names_and_does_not_rewrite_on_repeat(harness):
    root, home = harness
    config = home / ".claude.json"
    config.parent.mkdir(parents=True)
    original = {"numStartups": 4, "mcpServers": {"personal": {"command": "local"}}}
    config.write_text(json.dumps(original))
    assert cli.apply_claude(root, check_only=True) == ["mcp: notion"]
    assert json.loads(config.read_text()) == original
    assert cli.apply_claude(root) == ["mcp: notion"]
    assert json.loads(config.read_text()) == {**original, "mcpServers": {**original["mcpServers"], **mcp.load(root)}}
    assert json.loads((home / ".claude/.harness-mcp-owned.json").read_text()) == ["notion"]
    assert cli.apply_claude(root) == []
    assert json.loads((home / ".claude.json.harness-bak").read_text()) == original


def test_managed_server_is_replaced_without_touching_user_servers(harness):
    root, home = harness
    cli.apply_claude(root)
    config = home / ".claude.json"
    document = json.loads(config.read_text())
    document["mcpServers"]["notion"]["url"] = "https://edited.example.invalid/mcp"
    document["mcpServers"]["personal"] = {"command": "local"}
    config.write_text(json.dumps(document))
    assert cli.apply_claude(root) == ["mcp: notion"]
    assert json.loads(config.read_text())["mcpServers"] == {**mcp.load(root), "personal": {"command": "local"}}


def test_codex_preserves_app_server_and_existing_policy(harness):
    root, home = harness
    config = home / ".codex/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('[mcp_servers.node_repl]\ncommand = "app-owned"\n[projects."/workspace"]\ntrust_level = "trusted"\n')
    assert "mcp: notion" in cli.apply_codex(root, check_only=True)
    assert not (home / ".codex/.harness-mcp-owned.json").exists()
    assert "mcp: notion" in cli.apply_codex(root)
    servers = tomllib.loads(config.read_text())["mcp_servers"]
    assert servers == {"node_repl": {"command": "app-owned"}, "notion": {"url": mcp.load(root)["notion"]["url"]}}
    assert tomllib.loads(config.read_text())["projects"]["/workspace"]["trust_level"] == "trusted"
    assert cli.apply_codex(root) == []
    assert "node_repl" in (home / ".codex/config.toml.harness-bak").read_text()


@pytest.mark.parametrize("client,read", [("claude", json.loads), ("codex", tomllib.loads)])
def test_removal_only_deletes_managed_names_even_after_manual_edit(harness, client, read):
    root, home = harness
    config = home / (".claude.json" if client == "claude" else ".codex/config.toml")
    apply = cli.apply_claude if client == "claude" else cli.apply_codex
    apply(root)
    text = config.read_text().replace("https://mcp.notion.com/mcp", "https://edited.example.invalid/mcp")
    config.write_text(text)
    inventory(root, {})
    assert apply(root) == ["mcp: notion"]
    assert "notion" not in read(config.read_text())["mcpServers" if client == "claude" else "mcp_servers"]
    assert json.loads((home / (".claude" if client == "claude" else ".codex") / mcp.STATE_FILE).read_text()) == []
    assert apply(root) == []


@pytest.mark.parametrize("client", ["claude", "codex"])
def test_unmanaged_name_collision_refuses_before_writing(harness, client):
    root, home = harness
    config = home / (".claude.json" if client == "claude" else ".codex/config.toml")
    config.parent.mkdir(parents=True)
    content = '{"mcpServers":{"notion":{"url":"user"}}}' if client == "claude" else '[mcp_servers.notion]\nurl = "user"\n'
    config.write_text(content)
    with pytest.raises(ValueError, match="unmanaged MCP server name collision: notion"):
        (cli.apply_claude if client == "claude" else cli.apply_codex)(root)
    assert config.read_text() == content
    assert not (config.parent / mcp.STATE_FILE).exists()


def test_only_portable_stdio_env_and_http_fields_are_accepted(harness):
    root, _ = harness
    entry = {"command": "server", "args": [], "env": {"TOKEN": "${TOKEN}"}}
    inventory(root, {"local": entry})
    assert mcp.for_codex(mcp.load(root)["local"]) == {"command": "server", "args": [], "env_vars": ["TOKEN"]}
    assert mcp.for_claude(entry)["type"] == "stdio"
    inventory(root, {"local": {**entry, "env": {"TOKEN": "literal-secret"}}})
    with pytest.raises(ValueError, match="variable references"):
        mcp.load(root)
    inventory(root, {"notion": {"type": "http", "url": "https://mcp.notion.com/mcp", "headers": {"Authorization": "secret"}}})
    with pytest.raises(ValueError, match="unsupported HTTP fields"):
        mcp.load(root)


def test_stdio_env_renaming_is_not_supported(harness):
    root, _ = harness
    inventory(root, {"local": {"command": "server", "env": {"TOKEN": "${OTHER_TOKEN}"}}})
    with pytest.raises(ValueError, match="cannot rename"):
        cli.apply_codex(root, check_only=True)
