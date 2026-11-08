import os
import shutil
import subprocess

import pytest
import yaml
from dotkit.testing import REPO

SHELL_TASKS = REPO / "roles/shell/tasks/main.yml"


def role_task(name):
    tasks = yaml.safe_load(SHELL_TASKS.read_text())
    matching = [task for task in tasks if task.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the shell role"
    return matching[0]


def test_television_config_is_linked_before_television_runs():
    tasks = yaml.safe_load(SHELL_TASKS.read_text())
    task_names = [task["name"] for task in tasks]

    configs = role_task("Symlink shell configs")["loop"]
    assert {"src": "television/config.toml", "dest": "television/config.toml"} in configs
    assert task_names.index("Symlink shell configs") < task_names.index(
        "Sync upstream television channels"
    )


def test_every_fish_plugin_is_pinned_to_a_ref():
    defaults = yaml.safe_load((REPO / "roles/shell/defaults/main.yml").read_text())
    for plugin in defaults["FISH_PLUGINS"]:
        repo, _, ref = plugin.partition("@")
        assert repo.count("/") == 1 and ref, f"{plugin} must be pinned as owner/repo@ref"



def test_fish_plugins_install_only_when_the_pinned_ref_is_missing():
    tasks = yaml.safe_load(SHELL_TASKS.read_text())
    task_names = [task["name"] for task in tasks]
    listing = role_task("List installed fish plugins")
    install = role_task("Install fish plugins at their pinned ref")

    assert listing["changed_when"] is False and listing["check_mode"] is False
    assert install["loop"] == "{{ FISH_PLUGINS }}"
    assert install["when"] == "(item | lower) not in (fisher_installed.stdout_lines | default([]))"
    assert task_names.index("List installed fish plugins") < task_names.index(
        "Install fish plugins at their pinned ref"
    )


def test_a_stale_ref_of_the_same_repo_is_removed_right_before_the_pin_installs():
    install = role_task("Install fish plugins at their pinned ref")
    script = install["ansible.builtin.shell"].splitlines()

    assert install["vars"]["plugin_repo"] == "{{ item | lower | split('@') | first | regex_escape }}"
    assert script == [
        "for stale in (fisher list '^{{ plugin_repo }}(@.*)?$')",
        "    fisher remove $stale",
        "end",
        "fisher install {{ item }}",
    ]


def test_the_ssh_agent_guard_is_applied_after_plugin_installation():
    tasks = yaml.safe_load(SHELL_TASKS.read_text())
    install = role_task("Install fish plugins at their pinned ref")
    guard = role_task("Initialize the SSH agent only in interactive fish")
    assert tasks.index(install) < tasks.index(guard)
    assert guard["ansible.builtin.lineinfile"] == {
        "path": "{{ HOME }}/.config/fish/conf.d/fish-ssh-agent.fish",
        "insertbefore": "BOF",
        "line": "status is-interactive; or return",
        "mode": "0644",
    }


@pytest.mark.parametrize("interactive", [False, True])
def test_the_ssh_agent_guard_preserves_interactive_startup(tmp_path, interactive):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("Fish is required for startup tests")
    guard = role_task("Initialize the SSH agent only in interactive fish")
    snippet = tmp_path / "ssh-agent.fish"
    snippet.write_text(
        "#!/usr/bin/env fish\n"
        + guard["ansible.builtin.lineinfile"]["line"]
        + '\nprintf "agent-initialized\\n"\n'
    )
    env = {**os.environ, "HOME": str(tmp_path), "SSH_AGENT_SNIPPET": str(snippet)}
    subprocess.run([fish, "--no-execute", str(snippet)], check=True, env=env)
    result = subprocess.run(
        [fish, "--no-config", *(["--interactive"] if interactive else []), "--command",
         'source "$SSH_AGENT_SNIPPET"; printf "command-reached\\n"'],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    expected = "agent-initialized\ncommand-reached\n" if interactive else "command-reached\n"
    assert result.stdout == expected
