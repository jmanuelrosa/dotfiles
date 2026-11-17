"""Execute only Bruno's tasks, with synthetic preferences and a stub process check."""

import json
import os
import shutil
import subprocess
import sys

import pytest
import yaml
from dotkit.testing import REPO

APPS = REPO / "roles/apps"


def test_shortcuts_are_statically_imported_with_a_dedicated_tag():
    tasks = yaml.safe_load((APPS / "tasks/main.yml").read_text())
    task = next(task for task in tasks if task.get("ansible.builtin.import_tasks") == "bruno.yml")
    assert task["tags"] == ["bruno"]
    defaults = yaml.safe_load((APPS / "defaults/main.yml").read_text())
    assert defaults["BRUNO_PREFERENCES_PATH"] == "{{ HOME }}/Library/Application Support/bruno/preferences.json"
    assert defaults["BRUNO_SHORTCUT_PREFS"] == {"preferences": {"keyBindings": {
        "switchToNextTab": {"mac": "ctrl+bind+tab"},
        "switchToPreviousTab": {"mac": "ctrl+bind+shift+bind+tab"},
    }}}


@pytest.fixture
def bruno(tmp_path):
    if not shutil.which("ansible-playbook"):
        pytest.skip("Ansible not installed")
    profile = tmp_path / "Library/Application Support/bruno"
    profile.mkdir(parents=True)
    prefs = profile / "preferences.json"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    pgrep = bindir / "pgrep"
    pgrep.write_text('#!/bin/sh\n[ "$*" = "-x Bruno" ] || exit 99\nexit "$TEST_PGREP_RC"\n')
    pgrep.chmod(0o755)
    play = tmp_path / "play.yml"
    play.write_text(yaml.safe_dump([{
        "hosts": "localhost", "connection": "local", "gather_facts": False,
        "vars_files": [str(APPS / "defaults/main.yml")],
        "vars": {"HOME": str(tmp_path), "ansible_python_interpreter": sys.executable,
                 "ansible_remote_tmp": str(tmp_path / "remote")},
        "environment": {"PATH": f"{bindir}:{os.environ['PATH']}"},
        "tasks": [{"ansible.builtin.import_tasks": str(APPS / "tasks/bruno.yml")}],
    }]))

    def run(rc=1, check=False):
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(play), *(["--check"] if check else [])],
            env={**os.environ, "TEST_PGREP_RC": str(rc), "ANSIBLE_LOCAL_TEMP": str(tmp_path),
                 "ANSIBLE_LOG_PATH": str(tmp_path / "ansible.log"), "ANSIBLE_NOCOLOR": "1"},
            capture_output=True, text=True, timeout=60,
        )

    return prefs, run


def test_empty_preferences_receive_only_the_managed_schema(bruno):
    prefs, run = bruno
    prefs.write_text("{}")
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(prefs.read_text()) == {"preferences": {"keyBindings": {
        "switchToNextTab": {"mac": "ctrl+bind+tab"},
        "switchToPreviousTab": {"mac": "ctrl+bind+shift+bind+tab"},
    }}}


@pytest.mark.parametrize("enabled", [None, True])
def test_merge_preserves_other_bindings_and_is_idempotent(bruno, enabled):
    prefs, run = bruno
    original = {"unrelated": [1, "private-marker"], "preferences": {"keyBindings": {
        "switchToNextTab": {"mac": "command+bind+]", "windows": "ctrl+bind+pageup", "name": "Next"},
        "switchToPreviousTab": {"mac": "command+bind+[", "windows": "ctrl+bind+pagedown"},
        "save": {"mac": "command+bind+s", "windows": "ctrl+bind+tab"},
    }, "display": {"zoomPercentage": 110}}}
    if enabled is not None:
        original["preferences"]["keybindingsEnabled"] = enabled
    prefs.write_text(json.dumps(original))
    result = run(check=True)
    assert result.returncode == 0 and "changed=1" in result.stdout, result.stdout + result.stderr
    assert json.loads(prefs.read_text()) == original
    assert not list(prefs.parent.glob("preferences.json.*"))
    assert "private-marker" not in result.stdout + result.stderr
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    expected = json.loads(json.dumps(original))
    expected["preferences"]["keyBindings"]["switchToNextTab"]["mac"] = "ctrl+bind+tab"
    expected["preferences"]["keyBindings"]["switchToPreviousTab"]["mac"] = "ctrl+bind+shift+bind+tab"
    assert json.loads(prefs.read_text()) == expected
    assert prefs.stat().st_mode & 0o777 == 0o600
    backups = list(prefs.parent.glob("preferences.json.*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == original
    assert "private-marker" not in result.stdout + result.stderr
    before = prefs.stat().st_mtime_ns
    result = run()
    assert result.returncode == 0 and "changed=0" in result.stdout, result.stdout + result.stderr
    assert prefs.stat().st_mtime_ns == before
    assert list(prefs.parent.glob("preferences.json.*")) == backups
    assert "private-marker" not in result.stdout + result.stderr


@pytest.mark.parametrize("check", [False, True])
@pytest.mark.parametrize("rc", [0, 2, 3])
def test_refuses_running_or_unreadable_process_state(bruno, rc, check):
    prefs, run = bruno
    prefs.write_text('{"unrelated": "private-marker"}')
    before = prefs.read_bytes()
    result = run(rc, check=check)
    assert result.returncode != 0
    assert "Require Bruno to be quit" in result.stdout, result.stdout + result.stderr
    assert "failed=1" in result.stdout
    assert prefs.read_bytes() == before
    assert not list(prefs.parent.glob("preferences.json.*"))
    assert "private-marker" not in result.stdout + result.stderr


def test_missing_profile_is_skipped_without_process_access(bruno):
    prefs, run = bruno
    result = run(3)
    assert result.returncode == 0 and "changed=0" in result.stdout, result.stdout + result.stderr
    assert not prefs.exists()


@pytest.mark.parametrize("chord", ["ctrl+bind+tab", "ctrl+bind+shift+bind+tab", "SHIFT+bind+TAB+bind+CTRL"])
def test_conflicting_mac_bindings_are_refused_without_overwriting(bruno, chord):
    prefs, run = bruno
    prefs.write_text(json.dumps({"preferences": {"keyBindings": {"save": {"mac": chord}}}}))
    before = prefs.read_bytes()
    result = run()
    assert result.returncode != 0
    assert "Require Bruno tab shortcuts unclaimed by other custom Mac bindings" in result.stdout, result.stdout + result.stderr
    assert "failed=1" in result.stdout
    assert prefs.read_bytes() == before
    assert not list(prefs.parent.glob("preferences.json.*"))


def test_disabled_keybindings_are_refused_without_reenabling(bruno):
    prefs, run = bruno
    prefs.write_text('{"preferences": {"keybindingsEnabled": false}}')
    before = prefs.read_bytes()
    result = run()
    assert result.returncode != 0
    assert "Require Bruno keybindings to be enabled" in result.stdout, result.stdout + result.stderr
    assert "failed=1" in result.stdout
    assert prefs.read_bytes() == before
    assert not list(prefs.parent.glob("preferences.json.*"))


def test_invalid_json_is_refused_without_overwriting(bruno):
    prefs, run = bruno
    prefs.write_text("{private-marker")
    before = prefs.read_bytes()
    result = run()
    assert result.returncode != 0
    assert "Parse local Bruno preferences privately" in result.stdout, result.stdout + result.stderr
    assert "failed=1" in result.stdout
    assert prefs.read_bytes() == before
    assert not list(prefs.parent.glob("preferences.json.*"))
    assert "private-marker" not in result.stdout + result.stderr
