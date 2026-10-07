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
