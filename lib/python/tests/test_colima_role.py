import yaml
from dotkit.testing import REPO

APPS = REPO / "roles/apps"
CONFIG = APPS / "files/colima/colima.yaml"
DEFAULTS = yaml.safe_load((APPS / "defaults/main.yml").read_text())


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
    assert config["mountType"] == "sshfs"
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


def test_colima_config_is_linked_into_the_default_profile():
    assert "{{ HOME }}/.colima/default" in DEFAULTS["APPS_DIRS"]
    assert {
        "src": "colima/colima.yaml",
        "dest": "{{ HOME }}/.colima/default/colima.yaml",
    } in DEFAULTS["APPS_LINKS"]
