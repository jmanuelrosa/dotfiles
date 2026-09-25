"""How the neutral policy is spelled per harness, and how owned keys land in a shared file."""

from pathlib import Path

from harnessgen import emit_claude, manifest, merge

ROOT = manifest.find_root()


# --- the manifests ------------------------------------------------------------


def test_the_policy_never_names_where_the_harness_is_checked_out():
    """A literal checkout path is right on one machine; `{harness}` is right on all of them."""
    checkout = manifest.home_relative(ROOT)
    for path in (ROOT / "policy").glob("*.toml"):
        assert checkout not in path.read_text(), f"{path.name} names {checkout}; use {{harness}}"


def test_the_placeholder_expands_to_this_tree():
    policy = manifest.load(ROOT)
    reads = policy.sandbox["filesystem"]["allow_read"]
    assert not any(manifest.HARNESS_PLACEHOLDER in p for p in reads)
    harness_reads = [p for p in reads if p.startswith(manifest.home_relative(ROOT))]
    assert harness_reads, "the sandbox lost its reads of the harness's own trees"
    assert all(Path(p).expanduser().exists() for p in harness_reads)


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
