"""How lns reaches this machine after replacing the Fish function."""

import re

import yaml
from dotkit.testing import REPO

SHELL_DEFAULTS = REPO / "roles/shell/defaults/main.yml"
SHELL_TASKS = REPO / "roles/shell/tasks/main.yml"
MAKEFILE = REPO / "Makefile"

INSTALL_TASK = "Install the pinned standalone tools"


def role_task(name):
    tasks = yaml.safe_load(SHELL_TASKS.read_text())
    matching = [task for task in tasks if task.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the shell role"
    return matching[0]


def test_lns_release_is_pinned_to_an_exact_checksum():
    lns = yaml.safe_load(SHELL_DEFAULTS.read_text())["LNS"]
    assert lns == {
        "repository": "https://github.com/jmanuelrosa/lns",
        "release": "v0.1.0",
        "checksum": "sha256:ce88ce79923e1589873aa91b37d8be41a22c433ba743ce1daced3bde3df963f0",
    }
    assert re.fullmatch(r"v\d+\.\d+\.\d+", lns["release"])


def test_shell_downloads_lns_as_the_command_file():
    task = role_task(INSTALL_TASK)
    assert task["ansible.builtin.get_url"] == {
        "url": "{{ item.value.repository }}/releases/download/{{ item.value.release }}/{{ item.key }}",
        "dest": "{{ HOME }}/.local/bin/{{ item.key }}",
        "checksum": "{{ item.value.checksum }}",
        "mode": "0755",
    }
    assert "'lns': LNS" in task["loop"]


def test_verify_smokes_the_lns_release_asset():
    source = MAKEFILE.read_text()
    assert re.search(r"for cmd in [^;]*\blns\b", source)
    assert "[ -f $$HOME/.local/bin/lns ] && [ ! -L $$HOME/.local/bin/lns ]" in source


def test_lns_implementation_source_is_retired_but_shared_helpers_remain():
    functions = REPO / "roles/shell/files/fish/functions"
    assert not (functions / "lns.fish").exists()
    assert not (functions / "_lns_usage.fish").exists()
    assert not (functions / "_lns_target.fish").exists()
    assert (functions / "ui/_ui.fish").is_file()
    assert (functions / "clean_ai/_clean_claude_excludes.fish").is_file()
    assert (functions / "clean_ai/_clean_claude_confirm.fish").is_file()
