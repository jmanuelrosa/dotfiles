import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml
from dotkit.testing import REPO

APPS = REPO / "roles/apps"


def test_managed_bindings_use_physical_control_and_window_tab_commands():
    tasks = yaml.safe_load((APPS / "tasks/main.yml").read_text())
    task = next(task for task in tasks if task.get("ansible.builtin.import_tasks") == "dbeaver.yml")
    assert task["tags"] == ["dbeaver"]
    line = (APPS / "files/dbeaver/keybindings.prefs").read_text().strip()
    key, value = line.split("=", 1)
    assert key == "org.eclipse.ui.commands"
    root = ET.fromstring(value.replace("\\=", "=").replace("\\n", "\n"))
    assert root.tag == "org.eclipse.ui.commands"
    bindings = root.findall("keyBinding")
    assert {binding.attrib["keySequence"]: binding.attrib["commandId"] for binding in bindings} == {
        "CTRL+TAB": "org.eclipse.ui.navigate.nextTab",
        "CTRL+SHIFT+TAB": "org.eclipse.ui.navigate.previousTab",
    }
    assert len(bindings) == 2
    assert all(binding.attrib["contextId"] == "org.eclipse.ui.contexts.window" for binding in bindings)
    assert all(binding.attrib["keyConfigurationId"] == "org.jkiss.dbeaver.defaultKeyScheme" for binding in bindings)


@pytest.fixture
def dbeaver(tmp_path):
    if not shutil.which("ansible-playbook"):
        pytest.skip("Ansible not installed")
    prefs = tmp_path / "workspace/org.eclipse.ui.workbench.prefs"
    prefs.parent.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    pgrep = bindir / "pgrep"
    pgrep.write_text('#!/bin/sh\n[ "$*" = "-x dbeaver" ] || exit 99\nexit "$TEST_PGREP_RC"\n')
    pgrep.chmod(0o755)
    play = tmp_path / "play.yml"
    play.write_text(yaml.safe_dump([{
        "hosts": "localhost", "connection": "local", "gather_facts": False,
        "vars": {"DBEAVER_PREFERENCES_PATH": str(prefs), "role_path": str(APPS),
                 "ansible_python_interpreter": sys.executable,
                 "ansible_remote_tmp": str(tmp_path / "remote")},
        "environment": {"PATH": f"{bindir}:{os.environ['PATH']}"},
        "tasks": [{"ansible.builtin.import_tasks": str(APPS / "tasks/dbeaver.yml")}],
    }]))

    def run(rc=1, check=False):
        return subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(play), *(["--check"] if check else [])],
            env={**os.environ, "TEST_PGREP_RC": str(rc), "ANSIBLE_LOCAL_TEMP": str(tmp_path),
                 "ANSIBLE_LOG_PATH": str(tmp_path / "ansible.log"), "ANSIBLE_NOCOLOR": "1"},
            capture_output=True, text=True, timeout=60,
        )

    return prefs, run


def test_only_keybinding_property_changes_and_reruns_are_idempotent(dbeaver):
    prefs, run = dbeaver
    original = "eclipse.preferences.version=1\nother.setting=private-marker\n"
    prefs.write_text(original)
    result = run(check=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert prefs.read_text() == original
    assert not list(prefs.parent.glob("org.eclipse.ui.workbench.prefs.*"))
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    managed = (APPS / "files/dbeaver/keybindings.prefs").read_text().strip()
    assert prefs.read_text() == original + managed + "\n"
    assert prefs.stat().st_mode & 0o777 == 0o600
    backups = list(prefs.parent.glob("org.eclipse.ui.workbench.prefs.*"))
    assert len(backups) == 1 and backups[0].read_text() == original
    before = prefs.stat().st_mtime_ns
    result = run()
    assert result.returncode == 0 and "changed=0" in result.stdout, result.stdout + result.stderr
    assert prefs.stat().st_mtime_ns == before
    assert list(prefs.parent.glob("org.eclipse.ui.workbench.prefs.*")) == backups
    assert "private-marker" not in result.stdout + result.stderr


def test_existing_keybinding_property_is_restored_without_duplicate_properties(dbeaver):
    prefs, run = dbeaver
    prefs.write_text("other.setting=private-marker\norg.eclipse.ui.commands=<org.eclipse.ui.commands/>\n")
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    managed = (APPS / "files/dbeaver/keybindings.prefs").read_text().strip()
    assert prefs.read_text() == "other.setting=private-marker\n" + managed + "\n"
    assert "private-marker" not in result.stdout + result.stderr


@pytest.mark.parametrize("rc", [0, 2, 3])
def test_refuses_running_or_unknown_process_state_without_writing(dbeaver, rc):
    prefs, run = dbeaver
    prefs.write_text("other.setting=private-marker\n")
    before = prefs.read_bytes()
    result = run(rc)
    assert result.returncode != 0
    assert "Require DBeaver to be quit" in result.stdout and "failed=1" in result.stdout
    assert prefs.read_bytes() == before
    assert not list(prefs.parent.glob("org.eclipse.ui.workbench.prefs.*"))
    assert "private-marker" not in result.stdout + result.stderr


def test_missing_preferences_are_skipped_without_process_access(dbeaver):
    prefs, run = dbeaver
    result = run(3)
    assert result.returncode == 0 and "changed=0" in result.stdout, result.stdout + result.stderr
    assert not prefs.exists()
