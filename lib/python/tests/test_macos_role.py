import yaml
from dotkit.testing import REPO

MACOS = REPO / "roles/macos"
DEFAULTS = yaml.safe_load((MACOS / "defaults/main.yml").read_text())
TASKS = yaml.safe_load((MACOS / "tasks/main.yml").read_text())


def test_gatekeeper_quarantine_is_restored_rather_than_disabled():
    quarantine = [entry for entry in DEFAULTS["OSX_DEFAULTS"] if entry["key"] == "LSQuarantine"]
    assert quarantine == [
        {"domain": "com.apple.LaunchServices", "key": "LSQuarantine", "type": "bool", "state": "absent"}
    ]


def test_defaults_without_a_value_reach_the_module_as_omitted():
    apply = next(task for task in TASKS if task["name"] == "Apply macOS user defaults")
    assert apply["community.general.osx_defaults"]["value"] == "{{ item.value | default(omit) }}"
