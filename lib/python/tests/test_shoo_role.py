"""How shoo reaches this machine after replacing the port Fish function."""

import re

import yaml
from dotkit.testing import REPO

SHELL_DEFAULTS = REPO / "roles/shell/defaults/main.yml"
SHELL_TASKS = REPO / "roles/shell/tasks/main.yml"
MAKEFILE = REPO / "Makefile"

INSTALL_TASK = "Install the pinned standalone tools"
FISH_LINK_TASK = "Symlink fish functions"


def role_task(name):
    tasks = yaml.safe_load(SHELL_TASKS.read_text())
    matching = [task for task in tasks if task.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the shell role"
    return matching[0]


def test_shoo_release_is_pinned_to_a_checksum():
    shoo = yaml.safe_load(SHELL_DEFAULTS.read_text())["SHOO"]
    assert shoo == {
        "repository": "https://github.com/jmanuelrosa/shoo",
        "release": "v0.2.0",
        "checksum": "sha256:f3a8bca655b7e68ff2b1e40547dcd05c6447b23feaa3eac3ad00d1a8c3e0af70",
    }
    assert re.fullmatch(r"v\d+\.\d+\.\d+", shoo["release"])


def test_shell_downloads_shoo_as_the_command_file():
    task = role_task(INSTALL_TASK)
    assert task["ansible.builtin.get_url"] == {
        "url": "{{ item.value.repository }}/releases/download/{{ item.value.release }}/{{ item.key }}",
        "dest": "{{ HOME }}/.local/bin/{{ item.key }}",
        "checksum": "{{ item.value.checksum }}",
        "mode": "0755",
    }
    assert "'shoo': SHOO" in task["loop"]


def test_the_function_link_loop_needs_no_port_exception_after_retirement():
    assert "when" not in role_task(FISH_LINK_TASK)


def test_verify_smokes_the_shoo_release_asset():
    source = MAKEFILE.read_text()
    assert re.search(r"for cmd in [^;]*\bshoo\b", source)
    assert "[ -f $$HOME/.local/bin/shoo ] && [ ! -L $$HOME/.local/bin/shoo ]" in source


def test_port_implementation_source_is_retired():
    assert not (REPO / "roles/shell/files/fish/functions/port.fish").exists()
    assert not (REPO / "roles/shell/files/fish/functions/_port_usage.fish").exists()
