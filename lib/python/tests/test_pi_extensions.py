"""Project-owned Pi extensions are documented directories with explicit activation."""

import yaml
from dotkit.testing import PI, REPO

EXTENSIONS = PI / "extensions"
DEFAULTS = REPO / "roles" / "ai" / "defaults" / "main.yml"
TASKS = REPO / "roles" / "ai" / "tasks" / "main.yml"
DISABLED = {"claude-ui"}


def task(name):
    return next(item for item in yaml.safe_load(TASKS.read_text()) if item.get("name") == name)


def extension_directories(root):
    return {
        path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")
    }


def test_extension_discovery_ignores_hidden_directories(tmp_path):
    (tmp_path / ".claude").mkdir()
    extension = tmp_path / "extension"
    extension.mkdir()

    assert extension_directories(tmp_path) == {extension}


def test_every_extension_has_code_and_documentation():
    directories = extension_directories(EXTENSIONS)

    assert directories
    for directory in directories:
        assert (directory / "index.ts").is_file(), str(directory)
        assert (directory / "README.md").is_file(), str(directory)
        assert (directory / "README.md").read_text().startswith(f"# "), str(directory)


def test_manifest_activates_every_extension_except_the_parked_experiment():
    configured = set(yaml.safe_load(DEFAULTS.read_text())["PI_EXTENSIONS"])
    present = {path.name for path in extension_directories(EXTENSIONS)}

    assert configured == present - DISABLED
    assert configured.isdisjoint(DISABLED)


def test_role_links_documented_extension_directories():
    link = task("Link pi extensions")

    assert link["loop"] == "{{ PI_EXTENSIONS }}"
    assert link["when"] == "'pi' in HARNESS_ENABLED"
    assert link["ansible.builtin.file"] == {
        "src": "{{ HARNESS_DIR }}/adapters/pi/extensions/{{ item }}",
        "dest": "{{ HOME }}/.pi/agent/extensions/{{ item }}",
        "state": "link",
        "force": True,
    }

