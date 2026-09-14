"""How lns reaches this machine after replacing the Fish function."""

import re

import yaml
from dotkit.testing import REPO

SHELL_DEFAULTS = REPO / "roles/shell/defaults/main.yml"
SHELL_TASKS = REPO / "roles/shell/tasks/main.yml"
MAKEFILE = REPO / "Makefile"

LNS_FUNCTION_INSPECT_TASK = "Inspect the autoloaded lns function link"
LNS_FUNCTION_REFUSE_TASK = "Refuse to replace an unexpected lns function override"
LNS_FUNCTION_REMOVE_TASK = "Remove the legacy lns function symlink"
LNS_USAGE_INSPECT_TASK = "Inspect the legacy lns usage function link"
LNS_USAGE_REFUSE_TASK = "Refuse to replace an unexpected lns usage function override"
LNS_USAGE_REMOVE_TASK = "Remove the legacy lns usage function symlink"
LNS_TARGET_INSPECT_TASK = "Inspect the legacy lns target function link"
LNS_TARGET_REFUSE_TASK = "Refuse to replace an unexpected lns target function override"
LNS_TARGET_REMOVE_TASK = "Remove the legacy lns target function symlink"
LNS_COMMAND_INSPECT_TASK = "Inspect the installed lns command"
LNS_COMMAND_REFUSE_TASK = "Refuse to replace an unexpected lns command"
LNS_INSTALL_TASK = "Install the pinned lns release"
FISH_LINK_TASK = "Symlink fish functions"


def role_task(name):
    tasks = yaml.safe_load(SHELL_TASKS.read_text())
    matching = [task for task in tasks if task.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the shell role"
    return matching[0]


def task_names():
    return [task["name"] for task in yaml.safe_load(SHELL_TASKS.read_text())]


def test_lns_release_is_pinned_to_an_exact_checksum():
    lns = yaml.safe_load(SHELL_DEFAULTS.read_text())["LNS"]
    assert lns == {
        "repository": "https://github.com/jmanuelrosa/lns",
        "release": "v0.1.0",
        "checksum": "sha256:ce88ce79923e1589873aa91b37d8be41a22c433ba743ce1daced3bde3df963f0",
    }
    assert re.fullmatch(r"v\d+\.\d+\.\d+", lns["release"])


def test_shell_downloads_lns_as_the_command_file():
    body = role_task(LNS_INSTALL_TASK)["ansible.builtin.get_url"]
    assert body == {
        "url": "{{ LNS.repository }}/releases/download/{{ LNS.release }}/lns",
        "dest": "{{ HOME }}/.local/bin/lns",
        "checksum": "{{ LNS.checksum }}",
        "mode": "0755",
    }


def test_shell_refuses_non_regular_objects_at_the_lns_destination():
    inspect = role_task(LNS_COMMAND_INSPECT_TASK)["ansible.builtin.stat"]
    assert inspect == {"path": "{{ HOME }}/.local/bin/lns", "follow": False}

    refuse = role_task(LNS_COMMAND_REFUSE_TASK)
    assert refuse["ansible.builtin.assert"]["that"] == [
        "lns_command.stat.isreg | default(false)"
    ]
    assert refuse["when"] == "lns_command.stat.exists | default(false)"


def test_shell_removes_only_role_owned_lns_function_links():
    functions = (
        (
            "lns",
            "lns_function",
            LNS_FUNCTION_INSPECT_TASK,
            LNS_FUNCTION_REFUSE_TASK,
            LNS_FUNCTION_REMOVE_TASK,
        ),
        (
            "_lns_usage",
            "lns_usage_function",
            LNS_USAGE_INSPECT_TASK,
            LNS_USAGE_REFUSE_TASK,
            LNS_USAGE_REMOVE_TASK,
        ),
        (
            "_lns_target",
            "lns_target_function",
            LNS_TARGET_INSPECT_TASK,
            LNS_TARGET_REFUSE_TASK,
            LNS_TARGET_REMOVE_TASK,
        ),
    )

    for function, register, inspect_name, refuse_name, remove_name in functions:
        path = f"{{{{ HOME }}}}/.config/fish/functions/{function}.fish"
        source_match = (
            f'{register}.stat.lnk_source is match('
            f'".*/roles/shell/files/fish/functions/{function}[.]fish$"'
            ")"
        )

        inspect = role_task(inspect_name)["ansible.builtin.stat"]
        assert inspect == {"path": path, "follow": False}

        refuse = role_task(refuse_name)
        assert refuse["ansible.builtin.assert"]["that"] == [
            f"{register}.stat.islnk | default(false)",
            source_match,
        ]
        assert refuse["when"] == f"{register}.stat.exists | default(false)"

        remove = role_task(remove_name)
        assert remove["ansible.builtin.file"] == {"path": path, "state": "absent"}
        assert remove["when"] == [
            f"{register}.stat.islnk | default(false)",
            source_match,
        ]


def test_lns_is_installed_before_legacy_links_are_removed_or_functions_are_linked():
    names = task_names()
    for refuse in (
        LNS_FUNCTION_REFUSE_TASK,
        LNS_USAGE_REFUSE_TASK,
        LNS_TARGET_REFUSE_TASK,
        LNS_COMMAND_REFUSE_TASK,
    ):
        assert names.index(refuse) < names.index(LNS_INSTALL_TASK)
    for remove in (
        LNS_FUNCTION_REMOVE_TASK,
        LNS_USAGE_REMOVE_TASK,
        LNS_TARGET_REMOVE_TASK,
    ):
        assert names.index(LNS_INSTALL_TASK) < names.index(remove)
        assert names.index(remove) < names.index(FISH_LINK_TASK)


def test_verify_smokes_the_lns_release_asset():
    source = MAKEFILE.read_text()
    assert re.search(r"for cmd in [^;]*\blns\b", source)
    assert "[ -f $$HOME/.local/bin/lns ] && [ ! -L $$HOME/.local/bin/lns ]" in source


def test_lns_implementation_source_is_retired_but_shared_helpers_remain():
    functions = REPO / "roles/shell/files/fish/functions"
    assert not (functions / "lns.fish").exists()
    assert not (functions / "_lns_usage.fish").exists()
    assert not (functions / "_lns_target.fish").exists()
    assert (functions / "_ui.fish").is_file()
    assert (functions / "_clean_claude_excludes.fish").is_file()
    assert (functions / "_clean_claude_confirm.fish").is_file()
