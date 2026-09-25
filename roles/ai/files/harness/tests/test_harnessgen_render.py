"""How the neutral policy is spelled per harness, and how owned keys land in a shared file."""

from pathlib import Path

from harnessgen import emit_claude, emit_pi, manifest, merge

ROOT = manifest.find_root()


# --- the manifests ------------------------------------------------------------


def test_the_policy_never_names_where_the_harness_is_checked_out():
    """A literal checkout path is right on one machine; `{harness}` is right on all of them."""
    checkout = manifest.home_relative(ROOT)
    for path in (ROOT / "policy").glob("*.toml"):
        assert checkout not in path.read_text(), f"{path.name} names {checkout}; use {{harness}}"


def test_the_placeholder_expands_to_the_render_root():
    policy = manifest.load(ROOT)
    reads = policy.sandbox["filesystem"]["allow_read"]
    assert not any(manifest.HARNESS_PLACEHOLDER in p for p in reads)
    rendered = manifest.render_root(ROOT)
    harness_reads = [p for p in reads if p.startswith(rendered)]
    assert harness_reads, "the sandbox lost its reads of the harness's own trees"
    if rendered == manifest.home_relative(ROOT):
        assert all(Path(p).expanduser().exists() for p in harness_reads)


def test_the_placeholder_is_this_tree_unless_the_environment_names_another(monkeypatch):
    monkeypatch.delenv(manifest.RENDER_ROOT_ENV, raising=False)
    assert manifest.render_root(ROOT) == manifest.home_relative(ROOT)
    monkeypatch.setenv(manifest.RENDER_ROOT_ENV, "~/elsewhere/harness")
    assert manifest.render_root(ROOT) == "~/elsewhere/harness"
    assert manifest.expand("{harness}/hooks", ROOT) == "~/elsewhere/harness/hooks"


def test_the_root_is_found_from_anywhere_inside_it():
    assert manifest.find_root(ROOT / "adapters/claude") == ROOT


# --- Claude's spelling --------------------------------------------------------


def test_an_allowed_prefix_keeps_the_colon_spelling():
    assert emit_claude.allow_command_rule("rg *") == "Bash(rg:*)"
    assert emit_claude.allow_command_rule("git log") == "Bash(git log)"


def test_a_denied_command_is_written_as_the_policy_states_it():
    assert emit_claude.deny_command_rule("git push --force *") == "Bash(git push --force *)"


def test_a_path_denied_to_both_tools_is_one_adjacent_pair():
    assert emit_claude.path_denies(["~/.ssh/**", "~/.aws/**"], ["~/.ssh/**", "**/yarn.lock", "~/.aws/**"]) == [
        "Read(~/.ssh/**)", "Edit(~/.ssh/**)", "Edit(**/yarn.lock)", "Read(~/.aws/**)", "Edit(~/.aws/**)",
    ]


def test_a_read_only_deny_is_not_dropped():
    assert emit_claude.path_denies(["~/.netrc"], []) == ["Read(~/.netrc)"]


def test_the_owned_keys_are_the_ones_the_adapter_header_names():
    header = (ROOT / "adapters/claude/adapter.toml").read_text().split("\n\n", 1)[0]
    for key in emit_claude.owned(manifest.load(ROOT)):
        assert f"`{key}`" in header, f"adapter.toml does not say harness-build owns {key}"


# --- the merge ----------------------------------------------------------------


def test_the_merge_keeps_existing_key_order_and_appends_new_keys():
    assert list(merge.ordered_like({"b": 1, "a": 1}, {"a": 2, "c": 2, "b": 2})) == ["b", "a", "c"]


def test_the_merge_drops_a_key_the_render_no_longer_has():
    assert merge.ordered_like({"a": 1, "gone": 1}, {"a": 2}) == {"a": 2}


def test_the_merge_replaces_lists_whole():
    assert merge.ordered_like({"a": [1, 2]}, {"a": [3]}) == {"a": [3]}


def test_a_dotted_key_lands_in_place_without_touching_its_siblings():
    settings = {"pluginConfigs": {"other@x": {"on": True}}, "model": "opus"}
    merge.put(settings, "pluginConfigs.agents-md@builtin", {"options": {}})
    assert settings == {
        "pluginConfigs": {"other@x": {"on": True}, "agents-md@builtin": {"options": {}}},
        "model": "opus",
    }
    assert merge.get(settings, "pluginConfigs.agents-md@builtin") == {"options": {}}
    assert merge.get(settings, "pluginConfigs.missing") is None


# --- hooks --------------------------------------------------------------------


def test_the_adapter_header_says_the_generator_manages_hooks():
    header = (ROOT / "adapters/claude/adapter.toml").read_text().split("\n\n", 1)[0]
    assert "`hooks`" in header


def test_a_rewrite_hook_is_the_one_line_claude_has_always_run():
    hook = {"kind": "rewrite", "exec": ["rtk", "hook", "claude"], "requires_env": "RTK_ENABLE"}
    assert emit_claude.rewrite_command(hook) == (
        'if [ -n "$RTK_ENABLE" ] && command -v rtk >/dev/null 2>&1; then rtk hook claude || true; fi'
    )


def test_each_claude_if_rule_is_its_own_entry():
    hook = {"script": "gate.sh", "claude_if": ["Bash(git *)", "Bash(gh *)"], "timeout": 5}
    assert emit_claude.hook_entries(hook, "~/h") == [
        {"type": "command", "command": "~/h/gate.sh", "if": "Bash(git *)", "timeout": 5},
        {"type": "command", "command": "~/h/gate.sh", "if": "Bash(gh *)", "timeout": 5},
    ]


def ours(command, matcher="Bash"):
    return {"matcher": matcher, "hooks": [{"type": "command", "command": command}]}


def test_a_foreign_hook_sharing_a_matcher_joins_the_managed_group_after_it():
    block = {"SessionStart": [{"matcher": "*", "hooks": [{"command": "herdr"}, {"command": "kura"}]}]}
    rendered = {"SessionStart": [ours("kura", "*")]}
    assert emit_claude.merge_hooks(block, rendered) == {
        "SessionStart": [{"matcher": "*", "hooks": [{"type": "command", "command": "kura"}, {"command": "herdr"}]}],
    }


def test_a_foreign_group_is_kept_whole_after_the_managed_ones():
    foreign = {"matcher": "^startup$", "hooks": [{"command": "herdr"}]}
    block = {"SessionStart": [foreign, ours("kura", "*")]}
    rendered = {"SessionStart": [ours("kura", "*")]}
    assert emit_claude.merge_hooks(block, rendered)["SessionStart"] == [ours("kura", "*"), foreign]


def test_an_event_only_foreign_hooks_use_is_left_alone():
    block = {"Notification": [{"hooks": [{"command": "notify"}]}], "Stop": [{"hooks": [{"command": "old"}]}]}
    merged = emit_claude.merge_hooks(block, {"Stop": [{"hooks": [{"type": "command", "command": "recap"}]}]})
    assert list(merged) == ["Notification", "Stop"]
    assert merged["Notification"] == block["Notification"]


def test_a_managed_hook_dropped_from_the_policy_leaves_settings():
    """By command, so a hook is ours only while the policy renders it. One the policy stops
    rendering is then foreign, which is why removing a hook means removing its entry too."""
    block = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "a"}, {"command": "b"}]}]}
    merged = emit_claude.merge_hooks(block, {"PreToolUse": [ours("a")]})
    assert [h["command"] for h in merged["PreToolUse"][0]["hooks"]] == ["a", "b"]


def test_drift_ignores_foreign_hooks_and_sees_managed_order():
    rendered = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "a"}, {"command": "b"}]}]}
    commands = emit_claude.commands_in(rendered)
    with_foreign = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "a"}, {"command": "x"}, {"command": "b"}]}]}
    assert emit_claude.managed_view(with_foreign, commands) == rendered
    swapped = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "b"}, {"command": "a"}]}]}
    assert emit_claude.managed_view(swapped, commands) != rendered


def test_pi_is_given_only_the_hooks_its_harness_list_names():
    policy = manifest.load(ROOT)
    pi_ids = {entry["id"] for entries in emit_pi.hooks(policy).values() for entry in entries}
    assert pi_ids == {hook["id"] for hook in policy.hooks if "pi" in hook["harnesses"]}
    assert "plan-date-stamp" not in pi_ids


def test_every_script_the_policy_names_is_a_hook_that_ships():
    for hook in manifest.load(ROOT).hooks:
        if "script" in hook:
            assert (ROOT / "hooks" / hook["script"]).is_file(), f"{hook['id']} names a missing script"
