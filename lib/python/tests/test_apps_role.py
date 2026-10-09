import re

import yaml
from dotkit.testing import REPO

APPS = REPO / "roles/apps"
DEFAULTS = yaml.safe_load((APPS / "defaults/main.yml").read_text())
TASKS = yaml.safe_load((APPS / "tasks/main.yml").read_text())
EXACT_SEMVER = re.compile(r"\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?")


def role_task(name):
    matching = [task for task in TASKS if task.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the apps role"
    return matching[0]


def test_cf_cli_is_pinned_to_an_exact_version():
    version = DEFAULTS["CF_CLI"]["version"]
    assert EXACT_SEMVER.fullmatch(version), f"CF_CLI.version {version!r} must be an exact version, not a tag or range"


def test_cf_cli_reinstalls_when_the_installed_version_differs_from_the_pin():
    install = role_task("Install the pinned cf Cloudflare CLI")
    command = install["ansible.builtin.command"]

    assert "creates" not in command
    assert command["cmd"] == "bun add -g {{ CF_CLI.package }}@{{ CF_CLI.version }}"
    assert install["when"] == (
        "cf_cli_manifest.content is not defined or "
        "(cf_cli_manifest.content | b64decode | from_json).version != CF_CLI.version"
    )


def test_cf_cli_manifest_is_read_from_bun_global_dir_resolution():
    manifest = role_task("Read the installed cf Cloudflare CLI manifest")
    assert "BUN_INSTALL_GLOBAL_DIR" in manifest["vars"]["bun_global_dir"]
    assert "BUN_INSTALL" in manifest["vars"]["bun_install"]
    assert manifest["ansible.builtin.slurp"]["src"].startswith("{{ bun_global_dir }}/")


def test_every_gh_extension_is_pinned_to_a_release_tag():
    for extension in DEFAULTS["GH_EXTENSIONS"]:
        assert set(extension) == {"repository", "release"}
        assert extension["repository"].count("/") == 1
        assert extension["release"], f"{extension['repository']} must name a release tag"


def test_gh_extensions_install_only_when_the_pinned_release_is_missing():
    task_names = [task["name"] for task in TASKS]
    listing = role_task("List installed gh extensions")
    install = role_task("Install gh extensions at their pinned release")
    script = install["ansible.builtin.shell"]

    assert listing["changed_when"] is False and listing["check_mode"] is False
    assert "creates" not in install.get("args", {})
    assert "(item.repository | regex_escape)" in install["when"]
    assert "(item.release | regex_escape)" in install["when"]
    assert script.index("gh extension remove") < script.index(
        "gh extension install {{ item.repository }} --pin {{ item.release }}"
    )
    assert task_names.index("List installed gh extensions") < task_names.index(
        "Install gh extensions at their pinned release"
    )
