"""herdr-remote opens the tunnel only behind a running Ovis, and off leaves nothing to restart."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "herdr-remote"
UI = Path(__file__).resolve().parents[5] / "shell/files/fish/functions/ui/_ui.fish"

FAKE_HERDR = """#!/bin/sh
printf 'herdr %s socket=%s\\n' "$*" "${HERDR_SOCKET_PATH-unset}" >>"$CALLS"
case "$*" in
  *.start*) [ -z "$FAIL_START" ] ;;
esac
"""

FAKE_LAUNCHCTL = """#!/bin/sh
printf 'launchctl %s\\n' "$*" >>"$CALLS"
case "$1" in
  print) [ -e "$LOADED" ] ;;
  bootstrap) touch "$LOADED" ;;
  bootout) rm -f "$LOADED" ;;
esac
"""


@pytest.fixture
def run(tmp_path):
    if shutil.which("fish") is None:
        pytest.skip("Fish is required for herdr-remote tests")
    home = tmp_path / "home"
    functions = home / ".config/fish/functions"
    functions.mkdir(parents=True)
    (functions / "_ui.fish").symlink_to(UI)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("herdr", FAKE_HERDR), ("launchctl", FAKE_LAUNCHCTL)):
        fake = bin_dir / name
        fake.write_text(body)
        fake.chmod(0o755)

    config = home / ".config/herdr-remote/config"
    config.parent.mkdir(parents=True)
    plist = tmp_path / "tunnel.plist"
    socket = tmp_path / "work/herdr.sock"
    config.write_text(
        f"label test.tunnel\nplist {plist}\nplugin test.ovis\nurl https://example.test\nsocket {socket}\n"
    )

    calls = tmp_path / "calls"
    loaded = tmp_path / "loaded"

    def invoke(*args, loaded_before=False, fail_start=False):
        calls.write_text("")
        if loaded_before:
            loaded.touch()
        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "CALLS": str(calls),
            "LOADED": str(loaded),
            "NO_COLOR": "1",
        }
        env.pop("XDG_CONFIG_HOME", None)
        env.pop("HERDR_SOCKET_PATH", None)
        if fail_start:
            env["FAIL_START"] = "1"
        result = subprocess.run(
            [str(SCRIPT), *args], env=env, capture_output=True, text=True
        )
        return result, calls.read_text().splitlines(), loaded.exists()

    invoke.uid = os.getuid()
    invoke.plist = plist
    invoke.socket = socket
    invoke.config = config
    return invoke


def test_on_starts_ovis_in_its_session_before_opening_the_tunnel(run):
    result, calls, loaded = run("on")

    assert result.returncode == 0, result.stderr
    assert calls == [
        f"herdr plugin enable test.ovis socket={run.socket}",
        f"herdr plugin action invoke test.ovis.start socket={run.socket}",
        "launchctl print gui/%d/test.tunnel" % run.uid,
        f"launchctl bootstrap gui/{run.uid} {run.plist}",
    ]
    assert loaded


def test_on_keeps_the_tunnel_closed_when_ovis_does_not_start(run):
    result, calls, loaded = run("on", fail_start=True)

    assert result.returncode == 1
    assert not any(call.startswith("launchctl bootstrap") for call in calls)
    assert calls[-1] == f"herdr plugin disable test.ovis socket={run.socket}"
    assert not loaded


def test_on_leaves_an_open_tunnel_alone(run):
    result, calls, loaded = run("on", loaded_before=True)

    assert result.returncode == 0, result.stderr
    assert not any(call.startswith("launchctl bootstrap") for call in calls)
    assert loaded


def test_off_closes_the_tunnel_then_stops_and_disables_ovis(run):
    result, calls, loaded = run("off", loaded_before=True)

    assert result.returncode == 0, result.stderr
    assert calls == [
        "launchctl print gui/%d/test.tunnel" % run.uid,
        f"launchctl bootout gui/{run.uid}/test.tunnel",
        f"herdr plugin action invoke test.ovis.stop socket={run.socket}",
        f"herdr plugin disable test.ovis socket={run.socket}",
    ]
    assert not loaded


def test_refuses_without_a_config(run):
    run.config.unlink()

    result, calls, _ = run("on")

    assert result.returncode == 1
    assert "herdr-remote config" in result.stderr
    assert calls == []


def test_rejects_an_unknown_command(run):
    result, calls, _ = run("start")

    assert result.returncode == 1
    assert "Usage: herdr-remote" in result.stderr
    assert calls == []
