"""Project-owned Pi extensions are documented directories with explicit activation."""

import yaml
from dotkit.testing import PI, REPO

EXTENSIONS = PI / "extensions"
DEFAULTS = REPO / "roles" / "ai" / "defaults" / "main.yml"
TASKS = REPO / "roles" / "ai" / "tasks" / "main.yml"
DISABLED = {"claude-ui"}


def task(name):
    return next(item for item in yaml.safe_load(TASKS.read_text()) if item.get("name") == name)


def test_every_extension_has_code_and_documentation():
    directories = {path for path in EXTENSIONS.iterdir() if path.is_dir()}

    assert directories
    for directory in directories:
        assert (directory / "index.ts").is_file(), str(directory)
        assert (directory / "README.md").is_file(), str(directory)
        assert (directory / "README.md").read_text().startswith(f"# "), str(directory)


def test_manifest_activates_every_extension_except_the_parked_experiment():
    configured = set(yaml.safe_load(DEFAULTS.read_text())["PI_EXTENSIONS"])
    present = {path.name for path in EXTENSIONS.iterdir() if path.is_dir()}

    assert configured == present - DISABLED
    assert configured.isdisjoint(DISABLED)


def test_role_does_not_provision_pi_extensions():
    names = {item.get("name") for item in yaml.safe_load(TASKS.read_text())}
    assert "Symlink pi extensions" not in names
    assert "Check for superseded pi extension links" not in names
