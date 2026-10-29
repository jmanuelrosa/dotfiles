import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

FUNCTIONS = Path(__file__).resolve().parents[1]
CABLE = tomllib.loads(
    (FUNCTIONS.parents[1] / "television/cable/kura-skills.toml").read_text()
)
SELECTION = r"{split:\n:..|map:{split: :0}|join: }"


@pytest.fixture
def picker(tmp_path):
    fish = shutil.which("fish")
    if fish is None or shutil.which("jq") is None:
        pytest.skip("Fish and jq are required for picker tests")
    rows = [
        {"name": "existing", "groups": ["frontend"], "state": "linked", "global": False},
        {"name": "ui", "groups": ["frontend"], "state": "available", "global": False},
        {"name": "shared", "groups": ["frontend", "gcp"], "state": "missing", "global": False},
        {"name": "cloud", "groups": ["gcp"], "state": "available", "global": True},
        {"name": "global", "groups": ["frontend"], "state": "linked", "global": True},
        {"name": "server", "groups": ["backend"], "state": "available", "global": False},
    ]
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.jsonl"
    stub = bin_dir / "kura"
    stub.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "with open(os.environ['TEST_CALLS'], 'a') as log:\n"
        "    log.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "if sys.argv[1] == 'list':\n"
        "    if os.environ.get('TEST_LIST_FAIL'):\n"
        "        sys.exit(7)\n"
        "    print(os.environ['TEST_ROWS'])\n"
    )
    stub.chmod(0o755)
    (bin_dir / "editor").symlink_to(stub)
    (bin_dir / "bat").symlink_to(stub)

    def run(action, *names, linked=False, list_fail=False, color=False, no_color=False):
        if linked:
            for row in rows:
                row["state"] = "linked"
        env = {
            **os.environ,
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "PATH": os.pathsep.join((str(bin_dir), os.environ["PATH"])),
            "EDITOR": "editor",
            "DOTFILES_DIR": str(tmp_path),
            "TEST_CALLS": str(calls),
            "TEST_ROWS": json.dumps(rows),
            "TEST_LIST_FAIL": "1" if list_fail else "",
            "NO_COLOR": "1" if no_color or not color else "",
            "FORCE_COLOR": "1" if color else "",
        }
        if action == "list":
            command = "fish -c '_tv_kura_list skill'"
        elif action == "categories":
            source = next(
                (s for s in CABLE["source"]["command"] if s["name"] == "Categories"),
                None,
            )
            assert source is not None, "kura-skills needs a Categories source"
            command = source["run"]
        elif action == "preview":
            command = CABLE["preview"]["command"].replace("{split: :0}", names[0])
        else:
            template = CABLE["actions"][action]["command"]
            assert SELECTION in template
            command = template.replace(SELECTION, " ".join(names))
        setup = (
            f'set -g fish_function_path "{FUNCTIONS / "kura"}" '
            f'"{FUNCTIONS / "ui"}" $fish_function_path; '
        )
        script = setup + command.replace("fish -c '", "fish --no-config -c '" + setup)
        result = subprocess.run(
            [fish, "--no-config", "--command", script],
            cwd=home,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        recorded = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
        return result, recorded

    return run


def test_categories_are_unique_with_skill_and_link_counts(picker):
    result, calls = picker("categories")
    assert result.returncode == 0, result.stderr
    assert [" ".join(line.split()) for line in result.stdout.splitlines()] == [
        "@backend [0/1 linked] skills: 1",
        "@frontend [2/4 linked] skills: 4",
        "@gcp [0/2 linked] skills: 2",
    ]
    assert calls == [["list", "--type", "skill", "--json"]]


def test_picker_rows_show_status_before_searchable_groups(picker):
    result, _ = picker("list")
    assert result.returncode == 0, result.stderr
    assert "\x1b" not in result.stdout
    assert [" ".join(line.split()) for line in result.stdout.splitlines()] == [
        "cloud [available] gcp",
        "existing [linked] frontend",
        "global [linked] frontend",
        "server [available] backend",
        "shared [not downloaded] frontend, gcp",
        "ui [available] frontend",
    ]


def test_picker_columns_fit_the_current_rows(picker):
    result, _ = picker("list")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    name_width = max(len(line.split(" ")[0]) for line in lines)
    assert {line.index("[") for line in lines} == {name_width + 2}
    assert {line.index("frontend") for line in lines if "frontend" in line} == {
        name_width + len("[not downloaded]") + 4
    }


@pytest.mark.parametrize(
    ("name", "state", "colour", "groups"),
    [
        ("existing", "linked", 32, "frontend"),
        ("cloud", "available", 36, "gcp"),
        ("shared", "not downloaded", 33, "frontend, gcp"),
    ],
)
def test_picker_colours_status_and_groups_without_changing_action_ids(
    picker, name, state, colour, groups
):
    result, _ = picker("list", color=True)
    assert result.returncode == 0, result.stderr
    line = next(line for line in result.stdout.splitlines() if line.startswith(name + " "))
    assert line.split(" ")[0] == name
    assert f"\x1b[{colour}m[{state}]" in line
    assert re.search(r"\x1b\[[0-9;]*m" + re.escape(groups) + r"\x1b\[[0-9;]*m$", line)


def test_picker_respects_no_color_even_when_the_cable_forces_color(picker):
    result, _ = picker("list", color=True, no_color=True)
    assert result.returncode == 0, result.stderr
    assert "\x1b" not in result.stdout
    assert "[linked]" in result.stdout


def test_install_categories_deduplicates_and_preserves_linked_skills(picker):
    result, calls = picker("toggle", "@frontend", "@gcp")
    assert result.returncode == 0, result.stderr
    assert [call for call in calls if call[0] != "list"] == [
        ["add", "cloud", "--type", "skill", "--global"],
        ["add", "shared", "--type", "skill"],
        ["add", "ui", "--type", "skill"],
    ]


def test_fully_linked_category_does_not_remove_anything(picker):
    result, calls = picker("toggle", "@frontend", linked=True)
    assert result.returncode == 0, result.stderr
    assert all(call[0] == "list" for call in calls)


@pytest.mark.parametrize("action", ["outdated", "update"])
def test_category_maintenance_expands_all_members(picker, action):
    result, calls = picker(action, "@frontend", "@gcp")
    assert result.returncode == 0, result.stderr
    assert calls[-1] == [action, "--type", "skill", "cloud", "existing", "global", "shared", "ui"]


def test_edit_category_opens_member_skill_files(picker):
    result, calls = picker("edit", "@gcp")
    assert result.returncode == 0, result.stderr
    assert [Path(path).parts[-2:] for path in calls[-1]] == [
        ("cloud", "SKILL.md"), ("shared", "SKILL.md")
    ]


def test_category_preview_lists_its_skills(picker):
    result, calls = picker("preview", "@frontend")
    assert result.returncode == 0, result.stderr
    assert calls == [["list", "--type", "skill", "--group", "frontend"]]


def test_individual_skill_toggle_keeps_existing_scope_behavior(picker):
    result, calls = picker("toggle", "existing", "cloud")
    assert result.returncode == 0, result.stderr
    assert calls == [
        ["list", "--type", "skill", "--json"],
        ["remove", "existing", "--type", "skill"],
        ["add", "cloud", "--type", "skill", "--global"],
    ]


def test_individual_preview_still_opens_skill_markdown(picker):
    result, calls = picker("preview", "ui")
    assert result.returncode == 0, result.stderr
    assert calls[0][:3] == ["--color=always", "--plain", "--language=markdown"]
    assert Path(calls[0][-1]).parts[-2:] == ("ui", "SKILL.md")


@pytest.mark.parametrize("action", ["toggle", "outdated", "update", "edit"])
def test_stale_category_selection_does_not_run_unscoped_actions(picker, action):
    result, calls = picker(action, "@removed")
    assert result.returncode == 0, result.stderr
    assert calls == [["list", "--type", "skill", "--json"]]


def test_category_lookup_failure_stops_before_installing(picker):
    result, calls = picker("toggle", "@frontend", list_fail=True)
    assert result.returncode == 7
    assert calls == [["list", "--type", "skill", "--json"]]
