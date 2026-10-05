import yaml
from dotkit.testing import REPO

APPS = REPO / "roles/apps"
CONFIG = APPS / "files/colima/colima.yaml"
TASKS = yaml.safe_load((APPS / "tasks/infrastructure.yml").read_text())


def role_task(name):
    matching = [task for task in TASKS if task.get("name") == name]
    assert len(matching) == 1
    return matching[0]


def test_colima_profile_uses_native_virtualization_and_balanced_resources():
    config = yaml.safe_load(CONFIG.read_text())
    assert {key: config[key] for key in ("cpu", "memory", "disk")} == {
        "cpu": 6,
        "memory": 8,
        "disk": 30,
    }
    assert config["arch"] == "aarch64"
    assert config["runtime"] == "docker"
    assert config["vmType"] == "vz"
    assert config["mountType"] == "virtiofs"
    assert config["mountInotify"] is False
    assert config["portForwarder"] == "grpc"
    assert config["network"]["address"] is True
    assert config["docker"]["builder"]["gc"]["enabled"] is True
    assert config["provision"][0]["mode"] == "system"
    assert config["rosetta"] is False
    assert config["binfmt"] is True
    assert config["kubernetes"]["enabled"] is False


def test_colima_profile_retains_commented_configuration_examples():
    source = CONFIG.read_text()
    for example in (
        "# dns: [8.8.8.8, 1.1.1.1]",
        "# dnsHosts:",
        "# EXAMPLE - disable buildkit",
        "# EXAMPLE - add insecure registries",
        "# EXAMPLE - script executed as root",
        "# EXAMPLE - script executed as user",
        "# EXAMPLE - script executed after VM boot, before container runtimes start",
        "# EXAMPLE - script executed after VM and container runtimes are ready",
        "# mounts:",
        "# env:",
    ):
        assert example in source


def test_colima_config_and_backup_paths_keep_the_existing_profile_location():
    defaults = yaml.safe_load((APPS / "defaults/main.yml").read_text())
    assert defaults["COLIMA_CONFIG_PATH"] == "{{ HOME }}/.colima/default/colima.yaml"
    assert defaults["COLIMA_CONFIG_BACKUP_PATH"] == (
        "{{ CURRENT_DIR }}/backups/.colima/default/colima.yaml"
    )
    directories = role_task("Ensure Colima config and backup directories exist")
    assert directories["ansible.builtin.file"]["state"] == "directory"
    assert directories["loop"] == [
        "{{ COLIMA_CONFIG_PATH | dirname }}",
        "{{ COLIMA_CONFIG_BACKUP_PATH | dirname }}",
    ]


def test_colima_backup_preserves_original_and_skips_the_managed_symlink():
    inspect = role_task("Inspect existing Colima config")
    assert inspect["ansible.builtin.stat"] == {
        "path": "{{ COLIMA_CONFIG_PATH }}",
        "follow": False,
    }
    assert inspect["register"] == "colima_config"
    backup = role_task("Back up existing Colima config")
    assert backup["ansible.builtin.copy"] == {
        "src": "{{ COLIMA_CONFIG_PATH }}",
        "dest": "{{ COLIMA_CONFIG_BACKUP_PATH }}",
        "remote_src": True,
        "force": False,
        "mode": "0644",
    }
    assert backup["when"] == [
        "colima_config.stat.exists",
        "colima_config.stat.lnk_source | default('') != role_path ~ '/files/colima/colima.yaml'",
    ]


def test_colima_symlink_is_created_only_after_inspection_and_backup():
    names = [task["name"] for task in TASKS]
    assert (
        names.index("Ensure Colima config and backup directories exist")
        < names.index("Inspect existing Colima config")
        < names.index("Back up existing Colima config")
        < names.index("Symlink Colima config")
    )
    assert role_task("Symlink Colima config")["ansible.builtin.file"] == {
        "src": "{{ role_path }}/files/colima/colima.yaml",
        "dest": "{{ COLIMA_CONFIG_PATH }}",
        "state": "link",
        "force": True,
    }
