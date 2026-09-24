import json
import os
import subprocess
from pathlib import Path


FUNCTIONS = Path(__file__).resolve().parents[3] / "roles/shell/files/fish/functions"
ALIASES = FUNCTIONS.parent / "conf.d/aliases.fish"


def fish(command, home, cwd, reply=""):
    return subprocess.run(
        ["fish", "--no-config", "-c", f'set -p fish_function_path "{FUNCTIONS}"; {command}'],
        cwd=cwd,
        env={**os.environ, "HOME": str(home), "NO_COLOR": "1"},
        input=reply,
        capture_output=True,
        text=True,
        check=False,
    )


def session(home, name, cwd):
    file = home / ".pi/agent/sessions" / f"{name}.jsonl"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps({"type": "session", "cwd": str(cwd)}) + "\n")
    return file


def test_pi_project_only_removes_its_directories_and_sessions(tmp_path):
    home = tmp_path / "home"
    root = home / "code"
    nested = root / "packages/api"
    sibling = home / "code-other"
    for directory in (root / ".pi", root / ".agents", nested / ".pi", sibling / ".pi", home / ".pi/agent", home / ".agents/skills"):
        directory.mkdir(parents=True)
    (root / "node_modules/.pi").mkdir(parents=True)
    (home / ".pi/agent/auth.json").write_text("secret")
    selected = session(home, "selected", root)
    selected_nested = session(home, "nested", nested)
    retained = session(home, "other", sibling)

    preview = fish(f'clean_pi project "{root}" --dry-run', home, root)
    assert preview.returncode == 0, preview.stderr
    assert "~/.pi/agent/sessions/selected.jsonl" in preview.stdout
    assert "~/.pi/agent/sessions/other.jsonl" not in preview.stdout
    assert (root / ".pi").exists()

    result = fish(f'clean_pi project "{root}"', home, root, "y\n")
    assert result.returncode == 0, result.stderr
    assert not (root / ".pi").exists()
    assert not (root / ".agents").exists()
    assert not (nested / ".pi").exists()
    assert not selected.exists()
    assert not selected_nested.exists()
    assert retained.exists()
    assert (root / "node_modules/.pi").exists()
    assert (home / ".pi/agent/auth.json").exists()
    assert (home / ".agents/skills").exists()


def test_pi_project_unlinks_symlink_without_following_it(tmp_path):
    home = tmp_path / "home"
    root = home / "project"
    target = home / "elsewhere"
    root.mkdir(parents=True)
    target.mkdir(parents=True)
    (target / "keep.txt").write_text("keep")
    (root / ".agents").symlink_to(target, target_is_directory=True)

    result = fish(f'clean_pi project "{root}"', home, root, "y\n")
    assert result.returncode == 0, result.stderr
    assert not (root / ".agents").is_symlink()
    assert (target / "keep.txt").exists()


def test_pi_project_uses_configured_session_directory(tmp_path):
    home = tmp_path / "home"
    root = home / "project"
    (root / ".pi").mkdir(parents=True)
    (root / ".pi/settings.json").write_text(json.dumps({"sessionDir": ".sessions"}))
    selected = root / ".sessions/selected.jsonl"
    selected.parent.mkdir()
    selected.write_text(json.dumps({"type": "session", "cwd": str(root)}) + "\n")
    default = session(home, "default", root)

    result = fish(f'clean_pi project "{root}"', home, home, "y\n")
    assert result.returncode == 0, result.stderr
    assert not selected.exists()
    assert default.exists()


def test_pi_modes_preserve_shared_config_until_confirmed_purge(tmp_path):
    home = tmp_path / "home"
    root = home / "project"
    for directory in (root / ".pi/skills", root / ".agents/skills", root / ".pi/agents", root / ".agents/agents", home / ".pi/agent", home / ".agents/skills", home / ".agents/other"):
        directory.mkdir(parents=True)
    (home / ".pi/agent/auth.json").write_text("secret")

    skills = fish(f'clean_pi skills "{root}"', home, root, "y\n")
    assert skills.returncode == 0, skills.stderr
    assert not (root / ".pi/skills").exists()
    assert not (root / ".agents/skills").exists()
    assert (root / ".pi/agents").exists()
    assert (home / ".agents/skills").exists()

    rejected = fish(f'clean_pi purge "{root}"', home, root, "y\n")
    assert rejected.returncode != 0
    assert (home / ".pi/agent/auth.json").exists()
    assert (home / ".agents/skills").exists()

    purged = fish(f'clean_pi purge "{root}"', home, root, "purge\n")
    assert purged.returncode == 0, purged.stderr
    assert not (home / ".pi/agent").exists()
    assert not (home / ".agents/skills").exists()
    assert (home / ".agents/other").exists()


def test_claude_discovery_keeps_its_existing_scope(tmp_path):
    home = tmp_path / "home"
    root = home / "project"
    (root / ".claude/skills").mkdir(parents=True)
    (root / "node_modules/.claude").mkdir(parents=True)
    home.mkdir(exist_ok=True)

    result = fish(f'_clean_claude_find "{root}" node_modules', home, root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [str(root / ".claude")]


def test_shared_aliases_dispatch_modes_to_both_harnesses(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    command = (
        f'source "{ALIASES}"; '
        'function clean_claude; echo "claude $argv"; end; '
        'function clean_pi; echo "pi $argv"; end; '
        'clean:ai:skill --dry-run; clean:ai:agents --dry-run; '
        'clean:ai:purge --dry-run; clean:ai:agents --dry-run -w; clean:pi:skill --dry-run; '
        'clean:claude:skill --dry-run'
    )
    result = fish(command, home, home)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "claude skills --dry-run", "pi skills --dry-run",
        "claude agents --dry-run", "pi agents --dry-run",
        "claude purge --dry-run", "pi purge --dry-run",
        "claude agents --dry-run -w", "pi agents --dry-run -w",
        "pi skills --dry-run", "claude skills --dry-run",
    ]

    stopped = fish(
        f'source "{ALIASES}"; function clean_claude; return 1; end; '
        'function clean_pi; echo pi-ran; end; clean:ai --dry-run',
        home,
        home,
    )
    assert stopped.returncode == 1
    assert "pi-ran" not in stopped.stdout
