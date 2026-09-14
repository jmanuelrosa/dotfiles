"""How shoo reaches this machine after replacing the port Fish function."""

import re

import yaml
from dotkit.testing import REPO

SHELL_DEFAULTS = REPO / "roles/shell/defaults/main.yml"
SHELL_TASKS = REPO / "roles/shell/tasks/main.yml"
MAKEFILE = REPO / "Makefile"

LEGACY_FUNCTION_INSPECT_TASK = "Inspect the autoloaded port function link"
LEGACY_FUNCTION_REFUSE_TASK = "Refuse to replace an unexpected port function override"
LEGACY_FUNCTION_REMOVE_TASK = "Remove the legacy port function symlink"
LEGACY_USAGE_INSPECT_TASK = "Inspect the legacy port usage function link"
LEGACY_USAGE_REFUSE_TASK = "Refuse to replace an unexpected port usage function override"
LEGACY_USAGE_REMOVE_TASK = "Remove the legacy port usage function symlink"
LEGACY_COMMAND_INSPECT_TASK = "Inspect the legacy port command"
LEGACY_COMMAND_REFUSE_TASK = "Refuse to remove an unexpected port command"
LEGACY_COMMAND_REMOVE_TASK = "Remove the legacy port command"
SHOO_INSPECT_TASK = "Inspect the installed shoo command"
SHOO_REFUSE_TASK = "Refuse to replace an unexpected shoo command"
SHOO_INSTALL_TASK = "Install the pinned shoo release"
FISH_LINK_TASK = "Symlink fish functions"


def role_task(name):
    tasks = yaml.safe_load(SHELL_TASKS.read_text())
    matching = [task for task in tasks if task.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the shell role"
    return matching[0]


def task_names():
    return [task["name"] for task in yaml.safe_load(SHELL_TASKS.read_text())]


def test_shoo_release_and_legacy_port_are_pinned_to_checksums():
    shoo = yaml.safe_load(SHELL_DEFAULTS.read_text())["SHOO"]
    assert shoo == {
        "repository": "https://github.com/jmanuelrosa/shoo",
        "release": "v0.2.0",
        "checksum": "sha256:f3a8bca655b7e68ff2b1e40547dcd05c6447b23feaa3eac3ad00d1a8c3e0af70",
        "legacy_port_checksum": "14ff0cad83dc4c48442b63fc0a0d36c81a2c9a085ebebf63b93478e14c974335",
    }
    assert re.fullmatch(r"v\d+\.\d+\.\d+", shoo["release"])


def test_shell_downloads_shoo_as_the_command_file():
    body = role_task(SHOO_INSTALL_TASK)["ansible.builtin.get_url"]
    assert body == {
        "url": "{{ SHOO.repository }}/releases/download/{{ SHOO.release }}/shoo",
        "dest": "{{ HOME }}/.local/bin/shoo",
        "checksum": "{{ SHOO.checksum }}",
        "mode": "0755",
    }


def test_shell_inspects_the_port_function_without_following_it():
    body = role_task(LEGACY_FUNCTION_INSPECT_TASK)["ansible.builtin.stat"]
    assert body["path"] == "{{ HOME }}/.config/fish/functions/port.fish"
    assert body["follow"] is False


def test_shell_checks_for_a_function_override_before_linking_functions():
    names = task_names()
    assert names.index(LEGACY_FUNCTION_INSPECT_TASK) < names.index(FISH_LINK_TASK)
    assert names.index(LEGACY_FUNCTION_REFUSE_TASK) < names.index(FISH_LINK_TASK)


def test_shell_refuses_an_unexpected_port_function_override():
    task = role_task(LEGACY_FUNCTION_REFUSE_TASK)
    assert task["ansible.builtin.assert"]["that"] == [
        "port_function.stat.islnk | default(false)",
        'port_function.stat.lnk_source is match(".*/roles/shell/files/fish/functions/port[.]fish$")',
    ]
    assert "Refusing to replace" in task["ansible.builtin.assert"]["fail_msg"]
    assert task["when"] == "port_function.stat.exists | default(false)"


def test_shell_removes_only_a_role_owned_port_function():
    task = role_task(LEGACY_FUNCTION_REMOVE_TASK)
    assert task["ansible.builtin.file"] == {
        "path": "{{ HOME }}/.config/fish/functions/port.fish",
        "state": "absent",
    }
    assert task["when"] == [
        "port_function.stat.islnk | default(false)",
        'port_function.stat.lnk_source is match(".*/roles/shell/files/fish/functions/port[.]fish$")',
    ]


def test_shell_removes_only_a_role_owned_port_usage_function():
    inspect = role_task(LEGACY_USAGE_INSPECT_TASK)["ansible.builtin.stat"]
    assert inspect == {
        "path": "{{ HOME }}/.config/fish/functions/_port_usage.fish",
        "follow": False,
    }

    refuse = role_task(LEGACY_USAGE_REFUSE_TASK)
    assert refuse["ansible.builtin.assert"]["that"] == [
        "port_usage_function.stat.islnk | default(false)",
        'port_usage_function.stat.lnk_source is match(".*/roles/shell/files/fish/functions/_port_usage[.]fish$")',
    ]
    assert refuse["when"] == "port_usage_function.stat.exists | default(false)"

    remove = role_task(LEGACY_USAGE_REMOVE_TASK)
    assert remove["ansible.builtin.file"] == {
        "path": "{{ HOME }}/.config/fish/functions/_port_usage.fish",
        "state": "absent",
    }
    assert remove["when"] == [
        "port_usage_function.stat.islnk | default(false)",
        'port_usage_function.stat.lnk_source is match(".*/roles/shell/files/fish/functions/_port_usage[.]fish$")',
    ]


def test_shell_inspects_the_legacy_port_command_checksum():
    body = role_task(LEGACY_COMMAND_INSPECT_TASK)["ansible.builtin.stat"]
    assert body == {
        "path": "{{ HOME }}/.local/bin/port",
        "follow": False,
        "checksum_algorithm": "sha256",
    }


def test_shell_refuses_to_remove_an_unexpected_port_command():
    task = role_task(LEGACY_COMMAND_REFUSE_TASK)
    assert task["ansible.builtin.assert"]["that"] == [
        "legacy_port_command.stat.isreg | default(false)",
        "legacy_port_command.stat.checksum | default('') == SHOO.legacy_port_checksum",
    ]
    assert "Refusing to remove" in task["ansible.builtin.assert"]["fail_msg"]
    assert task["when"] == "legacy_port_command.stat.exists | default(false)"


def test_shell_removes_only_the_pinned_legacy_port_command():
    task = role_task(LEGACY_COMMAND_REMOVE_TASK)
    assert task["ansible.builtin.file"] == {
        "path": "{{ HOME }}/.local/bin/port",
        "state": "absent",
    }
    assert task["when"] == [
        "legacy_port_command.stat.isreg | default(false)",
        "legacy_port_command.stat.checksum | default('') == SHOO.legacy_port_checksum",
    ]


def test_shell_refuses_non_regular_objects_at_the_shoo_destination():
    inspect = role_task(SHOO_INSPECT_TASK)["ansible.builtin.stat"]
    assert inspect == {"path": "{{ HOME }}/.local/bin/shoo", "follow": False}

    refuse = role_task(SHOO_REFUSE_TASK)
    assert refuse["ansible.builtin.assert"]["that"] == [
        "shoo_command.stat.isreg | default(false)"
    ]
    assert refuse["when"] == "shoo_command.stat.exists | default(false)"


def test_shoo_is_installed_before_legacy_commands_are_removed():
    names = task_names()
    assert names.index(LEGACY_FUNCTION_REFUSE_TASK) < names.index(SHOO_INSTALL_TASK)
    assert names.index(LEGACY_USAGE_REFUSE_TASK) < names.index(SHOO_INSTALL_TASK)
    assert names.index(LEGACY_COMMAND_REFUSE_TASK) < names.index(SHOO_INSTALL_TASK)
    assert names.index(SHOO_REFUSE_TASK) < names.index(SHOO_INSTALL_TASK)
    assert names.index(SHOO_INSTALL_TASK) < names.index(LEGACY_FUNCTION_REMOVE_TASK)
    assert names.index(SHOO_INSTALL_TASK) < names.index(LEGACY_USAGE_REMOVE_TASK)
    assert names.index(SHOO_INSTALL_TASK) < names.index(LEGACY_COMMAND_REMOVE_TASK)


def test_the_function_link_loop_needs_no_port_exception_after_retirement():
    assert "when" not in role_task(FISH_LINK_TASK)


def test_verify_smokes_the_shoo_release_asset():
    source = MAKEFILE.read_text()
    assert re.search(r"for cmd in [^;]*\bshoo\b", source)
    assert "[ -f $$HOME/.local/bin/shoo ] && [ ! -L $$HOME/.local/bin/shoo ]" in source


def test_port_implementation_source_is_retired():
    assert not (REPO / "roles/shell/files/fish/functions/port.fish").exists()
    assert not (REPO / "roles/shell/files/fish/functions/_port_usage.fish").exists()
