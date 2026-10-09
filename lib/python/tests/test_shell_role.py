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
