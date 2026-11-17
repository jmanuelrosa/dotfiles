"""Execute only Helium's tasks, with synthetic profiles and a stub process check."""

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
    task = next(task for task in tasks if task.get("ansible.builtin.import_tasks") == "helium.yml")
    assert task["tags"] == ["helium"]
    defaults = yaml.safe_load((APPS / "defaults/main.yml").read_text())
    assert defaults["HELIUM_PROFILE_DIR"] == "{{ HOME }}/Library/Application Support/net.imput.helium/Default"
    assert defaults["HELIUM_SHORTCUT_PREFS"] == {"helium": {
        "settings": {"behavior": {"vertical_collapse_shortcut": False}},
        "browser": {"custom_accelerators": {"34061": {"added": ["Meta+KeyB"]}}},
    }}


@pytest.fixture
def helium(tmp_path):
    if not shutil.which("ansible-playbook"):
        pytest.skip("Ansible not installed")
    profile = tmp_path / "Library/Application Support/net.imput.helium/Default"
    profile.mkdir(parents=True)
    prefs = profile / "Preferences"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    pgrep = bindir / "pgrep"
    pgrep.write_text('#!/bin/sh\n[ "$*" = "-x Helium" ] || exit 99\nexit "$TEST_PGREP_RC"\n')
    pgrep.chmod(0o755)
    play = tmp_path / "play.yml"
    play.write_text(yaml.safe_dump([{
        "hosts": "localhost", "connection": "local", "gather_facts": False,
        "vars_files": [str(APPS / "defaults/main.yml")],
        "vars": {"HOME": str(tmp_path), "ansible_python_interpreter": sys.executable,
                 "ansible_remote_tmp": str(tmp_path / "remote")},
        "environment": {"PATH": f"{bindir}:{os.environ['PATH']}"},
        "tasks": [{"ansible.builtin.import_tasks": str(APPS / "tasks/helium.yml")}],
    }]))

    def run(rc=1, check=False):
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(play), *(["--check"] if check else [])],
            env={**os.environ, "TEST_PGREP_RC": str(rc), "ANSIBLE_LOCAL_TEMP": str(tmp_path),
                 "ANSIBLE_LOG_PATH": str(tmp_path / "ansible.log"), "ANSIBLE_NOCOLOR": "1"},
            capture_output=True, text=True, timeout=60,
        )

    return prefs, run


def test_merge_preserves_profile_and_is_idempotent(helium):
    prefs, run = helium
    original = {"unrelated": [1, "private-marker"], "helium": {"browser": {
        "custom_accelerators": {"34061": {"added": ["Alt+KeyB"]},
                                "35000": {"added": ["Meta+KeyY"]}}}}}
    prefs.write_text(json.dumps(original))
    result = run(check=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(prefs.read_text()) == original
    assert not list(prefs.parent.glob("Preferences.*"))
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    expected = json.loads(json.dumps(original))
    expected["helium"]["settings"] = {"behavior": {"vertical_collapse_shortcut": False}}
    expected["helium"]["browser"]["custom_accelerators"]["34061"]["added"].append("Meta+KeyB")
    assert json.loads(prefs.read_text()) == expected
    assert prefs.stat().st_mode & 0o777 == 0o600
    backups = list(prefs.parent.glob("Preferences.*"))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == original
    before = prefs.stat().st_mtime_ns
    result = run()
    assert result.returncode == 0 and "changed=0" in result.stdout, result.stdout + result.stderr
    assert prefs.stat().st_mtime_ns == before
    assert list(prefs.parent.glob("Preferences.*")) == backups
    assert "private-marker" not in result.stdout + result.stderr


@pytest.mark.parametrize("rc", [0, 2, 3])
def test_refuses_running_or_unreadable_process_state(helium, rc):
    prefs, run = helium
    prefs.write_text('{"unrelated": "private-marker"}')
    before = prefs.read_bytes()
    result = run(rc)
    assert result.returncode != 0
    assert "Require Helium to be quit" in result.stdout, result.stdout + result.stderr
    assert "failed=1" in result.stdout
    assert prefs.read_bytes() == before
    assert not list(prefs.parent.glob("Preferences.*"))
    assert "private-marker" not in result.stdout + result.stderr


def test_missing_profile_is_skipped_without_process_access(helium):
    prefs, run = helium
    result = run(3)
    assert result.returncode == 0 and "changed=0" in result.stdout, result.stdout + result.stderr
    assert not prefs.exists()


@pytest.mark.parametrize("command, delta", [
    ("35000", {"added": ["Meta+KeyB"]}),
    ("34061", {"added": ["Meta+KeyS"]}),
    ("34090", {"removed": ["Meta+KeyS"]}),
])
def test_conflicts_are_refused_without_overwriting(helium, command, delta):
    prefs, run = helium
    prefs.write_text(json.dumps({"helium": {"browser": {"custom_accelerators": {command: delta}}}}))
    before = prefs.read_bytes()
    result = run()
    assert result.returncode != 0
    assert "Require Cmd+B unclaimed and Cmd+S unchanged" in result.stdout, result.stdout + result.stderr
    assert "failed=1" in result.stdout
    assert prefs.read_bytes() == before
    assert not list(prefs.parent.glob("Preferences.*"))
