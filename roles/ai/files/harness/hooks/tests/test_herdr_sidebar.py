"""The herdr sidebar reporter: which tokens reach herdr, and how rarely.

herdr-sidebar.sh runs on every Claude turn through the status line and on Claude's
PermissionRequest, Notification and Stop hooks, so the two failures that matter are a herdr
spawn on every turn and a token that silently stops being reported. A fake `herdr` on PATH
records every call, which is what each test asserts against.
"""

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[2]
HOOK = HARNESS / "hooks" / "herdr-sidebar.sh"
STATUSLINE = HARNESS / "adapters" / "claude" / "statusline.sh"
VOCAB = json.loads((HARNESS / "statusline.json").read_text())
HERDR = VOCAB["herdr"]
TOKENS = HERDR["tokens"]
PANE = "w1:p1"
WORKSPACE = "w1"


def branch(name):
    return f"{TOKENS['branch']}={HERDR['branchGlyph']} {name}"

FAKE = f"""#!{sys.executable}
import json, os, sys
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps([os.path.basename(sys.argv[0]), *sys.argv[1:]]) + "\\n")
reply = os.environ.get("FAKE_GH_REPLY")
if os.path.basename(sys.argv[0]) == "gh" and reply:
    print(reply)
"""


def load_module():
    loader = importlib.machinery.SourceFileLoader("herdr_sidebar_under_test", str(HOOK))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


def git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        check=True, capture_output=True,
    )


@pytest.fixture
def env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("herdr", "gh"):
        fake = bin_dir / name
        fake.write_text(FAKE)
        fake.chmod(0o755)
    socket = tmp_path / "herdr.sock"
    socket.write_text("")
    repo = tmp_path / "repo"
    git(tmp_path, "init", "-q", "-b", "main", str(repo))
    git(repo, "commit", "-q", "--allow-empty", "-m", "init")
    base = {k: v for k, v in os.environ.items() if not k.startswith(("HERDR_", "XDG_CACHE_HOME"))}
    base.update(
        PATH=f"{bin_dir}{os.pathsep}{base.get('PATH', '')}",
        XDG_CACHE_HOME=str(tmp_path / "cache"),
        FAKE_LOG=str(tmp_path / "calls.log"),
        HERDR_ENV="1",
        HERDR_PANE_ID=PANE,
        HERDR_WORKSPACE_ID=WORKSPACE,
        HERDR_SOCKET_PATH=str(socket),
    )
    return {"env": base, "repo": repo, "socket": socket, "log": tmp_path / "calls.log", "tmp": tmp_path}


def calls(env, program="herdr"):
    log = env["log"]
    lines = log.read_text().splitlines() if log.exists() else []
    return [call[1:] for call in map(json.loads, lines) if call[0] == program]


def statusline(env, cwd=None, pct=None, inside=True, rate_limits=None):
    environ = dict(env["env"])
    if not inside:
        environ = {k: v for k, v in environ.items() if not k.startswith("HERDR_")}
    payload = {"workspace": {"current_dir": str(cwd or env["repo"])}}
    if pct is not None:
        payload["context_window"] = {"used_percentage": pct, "context_window_size": 200_000}
    if rate_limits is not None:
        payload["rate_limits"] = rate_limits
    done = subprocess.run(
        [sys.executable, str(STATUSLINE)], input=json.dumps(payload),
        capture_output=True, text=True, env=environ, check=False,
    )
    assert done.returncode == 0, done.stderr


def hook(env, payload):
    done = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(payload),
        capture_output=True, text=True, env=env["env"], check=False,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout == "", "a PermissionRequest hook's stdout is read as a decision"


def pane_tokens(env):
    return [call for call in calls(env) if call[:3] == ["pane", "report-metadata", PANE] and "--token" in call]


def test_the_branch_is_reported_once_per_branch(env):
    statusline(env)
    statusline(env)
    assert pane_tokens(env) == [
        ["pane", "report-metadata", PANE, "--source", HERDR["source"], "--token", branch("main")],
    ]


def test_a_new_branch_is_reported_again(env):
    statusline(env)
    git(env["repo"], "switch", "-q", "-c", "fix/other")
    statusline(env)
    assert [call[-1] for call in pane_tokens(env)] == [branch("main"), branch("fix/other")]


def test_a_restarted_herdr_server_gets_its_tokens_again(env):
    statusline(env)
    # Created beside the old one before replacing it, so the new socket cannot reuse its inode.
    replacement = env["socket"].with_name("herdr.sock.new")
    replacement.write_text("")
    replacement.replace(env["socket"])
    statusline(env)
    assert len(pane_tokens(env)) == 2


def test_nothing_is_reported_outside_herdr(env):
    statusline(env, inside=False, pct=50)
    assert calls(env) == []


def test_a_linked_worktree_leaves_the_branch_to_its_workspace_label(env):
    linked = env["tmp"] / "linked"
    git(env["repo"], "worktree", "add", "-q", "-b", "feature/PROJ-7-linked", str(linked))
    statusline(env, cwd=linked)
    assert not any(f"{TOKENS['branch']}=" in arg for call in calls(env) for arg in call)
    # The ticket proves the worktree's branch was read, so the missing branch is a decision.
    assert any(f"{TOKENS['ticket']}=PROJ-7" in call for call in calls(env))


def test_context_is_reported_per_step_and_handoff_past_the_threshold(env):
    step, handoff = HERDR["contextStepPct"], VOCAB["handoffPct"]
    below = handoff - step
    statusline(env, pct=below)
    statusline(env, pct=below + 1)
    statusline(env, pct=handoff + 1)
    reported = [arg for call in pane_tokens(env) for arg in call if arg.startswith(f"{TOKENS['context']}=")]
    assert reported == [f"{TOKENS['context']}={below // step * step}%", f"{TOKENS['context']}={(handoff + 1) // step * step}%"]
    assert f"{TOKENS['handoff']}={VOCAB['labels']['handoff']}" in pane_tokens(env)[-1]


def test_a_ticket_branch_reports_its_key_and_recorded_title(env):
    branch = "feature/PROJ-42-sidebar"
    git(env["repo"], "switch", "-q", "-c", branch)
    git(env["repo"], "config", f"branch.{branch}.description", "Make the sidebar useful")
    statusline(env)
    workspace = [call for call in calls(env) if call[:3] == ["workspace", "report-metadata", WORKSPACE]]
    assert workspace == [
        ["workspace", "report-metadata", WORKSPACE, "--source", HERDR["source"], "--token", f"{TOKENS['ticket']}=PROJ-42 Make the sidebar useful"],
    ]


def test_the_pr_poll_reports_a_summary_with_a_ttl(env):
    git(env["repo"], "remote", "add", "origin", "https://github.com/acme/app.git")
    env["env"]["FAKE_GH_REPLY"] = json.dumps({
        "number": 7, "state": "OPEN", "reviewDecision": "APPROVED",
        "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
    })
    statusline(env)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not any("--ttl-ms" in call for call in calls(env)):
        time.sleep(0.1)
    expected = f"{TOKENS['pr']}=#7 {HERDR['prGlyphs']['pass']} {HERDR['prLabels']['APPROVED']}"
    reported = [call for call in calls(env) if "--ttl-ms" in call]
    assert reported and expected in reported[0]
    assert reported[0][reported[0].index("--ttl-ms") + 1] == str(HERDR["prTtlSeconds"] * 1000)
    statusline(env)
    time.sleep(0.5)
    assert len(calls(env, "gh")) == 1, "a second turn inside the refresh window must not poll again"


def test_a_permission_prompt_names_the_tool_and_stop_clears_it_once(env):
    hook(env, {"hook_event_name": "PermissionRequest", "tool_name": "Bash"})
    hook(env, {"hook_event_name": "Stop"})
    hook(env, {"hook_event_name": "Stop"})
    label = f"blocked={HERDR['waiting']['prefix']}: Bash"
    assert [call[-1] for call in calls(env)] == [label, "--clear-state-labels"]


def test_a_question_reads_as_waiting_for_input_and_other_notifications_do_nothing(env):
    hook(env, {"hook_event_name": "Notification", "notification_type": "idle_prompt"})
    hook(env, {"hook_event_name": "Notification", "notification_type": "permission_prompt"})
    hook(env, {"hook_event_name": "Notification", "notification_type": "elicitation_dialog"})
    assert [call[-1] for call in calls(env)] == [f"blocked={HERDR['waiting']['prefix']}: {HERDR['waiting']['input']}"]


def test_usage_shows_live_windows_and_drops_a_reset_one(env, monkeypatch):
    for name, value in env["env"].items():
        monkeypatch.setenv(name, value)
    module = load_module()
    now = time.time()
    module.record_usage({
        "five_hour": {"used_percentage": 9.4, "resets_at": now + 600},
        "seven_day": {"used_percentage": 1, "resets_at": now - 1},
    })
    assert module.usage_text(now) == "usage 5h 9%"
    assert module.usage_text(now + 601) == ""


@pytest.mark.parametrize(("data", "expected"), [
    ({"number": 3, "state": "OPEN", "reviewDecision": "CHANGES_REQUESTED",
      "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}, {"state": "FAILURE"}]},
     ["#3", "fail", "CHANGES_REQUESTED"]),
    ({"number": 4, "state": "OPEN", "reviewDecision": "REVIEW_REQUIRED",
      "statusCheckRollup": [{"status": "IN_PROGRESS", "conclusion": ""}]},
     ["#4", "pending", "REVIEW_REQUIRED"]),
    ({"number": 5, "state": "MERGED", "statusCheckRollup": []}, ["#5", "MERGED"]),
    ({"number": 6, "state": "OPEN", "reviewDecision": "", "statusCheckRollup": []}, ["#6"]),
])
def test_github_summaries(data, expected):
    words = {**HERDR["prGlyphs"], **HERDR["prLabels"]}
    assert load_module().summarize_github(data) == " ".join(words.get(part, part) for part in expected)


def test_gitlab_summaries():
    module = load_module()
    running = {"iid": 9, "state": "opened", "head_pipeline": {"status": "running"}, "detailed_merge_status": "not_approved"}
    assert module.summarize_gitlab(running) == f"!9 {HERDR['prGlyphs']['pending']} {HERDR['prLabels']['REVIEW_REQUIRED']}"
    assert module.summarize_gitlab({"iid": 2, "state": "merged"}) == f"!2 {HERDR['prLabels']['MERGED']}"
