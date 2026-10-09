import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

WT_FISH = Path(__file__).parent.parent / "wt/wt.fish"


@pytest.fixture
def worktree(tmp_path):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("Fish is required for shell behavior tests")

    source = tmp_path / "main checkout [test]"
    source.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    target = tmp_path / "feature checkout"
    converge_log = tmp_path / "converge.log"
    env = os.environ.copy()
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        XDG_DATA_HOME=str(home / ".local/share"),
        XDG_CACHE_HOME=str(home / ".cache"),
        GIT_CONFIG_NOSYSTEM="1",
        WT_TARGET=str(target),
        WT_CONVERGE_LOG=str(converge_log),
    )

    def git(*args):
        return subprocess.run(
            ["git", *args],
            cwd=source,
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

    git("init", "-b", "main")
    git("config", "user.name", "wt tests")
    git("config", "user.email", "wt@example.invalid")
    git("config", "commit.gpgsign", "false")
    (source / ".gitignore").write_text(".env*\nnode_modules/\n.venv/\nvenv/\nvendor/\n")
    git("add", ".gitignore")
    git("commit", "-m", "Initialize test repository")

    def add():
        commands = f"source {shlex.quote(str(WT_FISH))}\n" + r"""
function _ui
    if test "$argv[1]" = path
        printf '%s\n' "$argv[2]"
    end
end
function kura
    printf '%s\n' "$PWD" $argv > "$WT_CONVERGE_LOG"
end
wt add --branch feature/test "feature checkout"
"""
        result = subprocess.run(
            [fish, "--no-config", "--command", commands],
            cwd=source,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert "cp:" not in result.stderr, result.stderr
        return target, converge_log

    return source, git, add


def test_copies_root_and_nested_environment_files(worktree):
    source, _, add = worktree
    environment_files = (
        ".env.example",
        ".env.sample",
        "apps/web/.env.example",
        "packages/api server/.env.sample",
    )
    for relative in environment_files:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"SOURCE={relative}\n")

    target, _ = add()

    for relative in environment_files:
        assert (target / relative).read_text() == (source / relative).read_text()
    (target / ".env.example").write_text("SOURCE=worktree\n")
    assert (source / ".env.example").read_text() == "SOURCE=.env.example\n"


@pytest.mark.parametrize("directory", [".git", "node_modules", ".venv", "venv", "vendor"])
def test_skips_environment_files_in_metadata_and_dependencies(worktree, directory):
    source, _, add = worktree
    ignored = source / "apps/web" / directory / ".env.example"
    ignored.parent.mkdir(parents=True)
    ignored.write_text("SOURCE=dependency\n")
    environment = source / "apps/web/.env.example"
    environment.write_text("SOURCE=application\n")

    target, _ = add()

    assert (target / "apps/web/.env.example").read_text() == environment.read_text()
    assert not (target / "apps/web" / directory).exists()


def test_copies_symlinked_environment_file_as_independent_file(worktree):
    source, _, add = worktree
    shared = source.parent / "shared.env"
    shared.write_text("SOURCE=shared\n")
    (source / ".env.example").symlink_to(shared)

    target, _ = add()

    assert (target / ".env.example").read_text() == shared.read_text()
    assert not (target / ".env.example").is_symlink()


@pytest.mark.parametrize("directory", [".claude", ".agents"])
def test_copies_project_skills_and_converges_in_new_worktree(worktree, directory):
    source, _, add = worktree
    skill = source / directory / "skills/local/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Local skill\n")

    target, converge_log = add()

    assert (target / directory / "skills/local/SKILL.md").read_text() == skill.read_text()
    assert converge_log.read_text().splitlines() == [str(target), "converge", "--quiet"]


def test_excludes_claude_worktrees(worktree):
    source, _, add = worktree
    files = {
        ".claude/worktrees/old checkout/.env.example": "SOURCE=old-worktree\n",
        ".claude/worktrees/old checkout/.claude/settings.json": "{}\n",
        ".claude/settings.local.json": "{}\n",
        ".claude/.gitignore": "worktrees/\n",
        ".claude/skills/worktrees/SKILL.md": "# Worktree skill\n",
    }
    for relative, content in files.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    target, _ = add()

    assert not (target / ".claude/worktrees").exists()
    for relative, content in files.items():
        if not relative.startswith(".claude/worktrees/"):
            assert (target / relative).read_text() == content


def test_merges_local_configuration_into_tracked_directories(worktree):
    source, git, add = worktree
    directories = (".vscode", ".claude", ".agents")
    for directory in directories:
        config = source / directory / "tracked.json"
        config.parent.mkdir()
        config.write_text('{"source": "tracked"}\n')
        nested = source / directory / "nested/tracked.json"
        nested.parent.mkdir()
        nested.write_text('{"source": "tracked"}\n')
    git("add", *directories)
    git("commit", "-m", "Track project configuration")
    for directory in directories:
        (source / directory / "local.json").write_text('{"source": "local"}\n')
        (source / directory / "nested/local.json").write_text('{"source": "local"}\n')

    target, _ = add()

    for directory in directories:
        assert (target / directory / "tracked.json").read_text() == '{"source": "tracked"}\n'
        assert (target / directory / "local.json").read_text() == '{"source": "local"}\n'
        assert (target / directory / "nested/tracked.json").read_text() == '{"source": "tracked"}\n'
        assert (target / directory / "nested/local.json").read_text() == '{"source": "local"}\n'
        assert not (target / directory / directory).exists()


def test_preserves_relative_skill_bridge_and_catalog_links(worktree):
    source, _, add = worktree
    catalog = source.parent / "catalog"
    catalog.mkdir()
    (catalog / "SKILL.md").write_text("# Catalog skill\n")
    skills = source / ".claude/skills"
    skills.mkdir(parents=True)
    (skills / "catalog").symlink_to(catalog, target_is_directory=True)
    (source / ".agents").mkdir()
    (source / ".agents/skills").symlink_to("../.claude/skills", target_is_directory=True)

    target, _ = add()

    assert (target / ".agents/skills").readlink() == Path("../.claude/skills")
    assert (target / ".agents/skills/catalog").is_symlink()
    assert (target / ".agents/skills/catalog/SKILL.md").read_text() == "# Catalog skill\n"


def test_convergence_precedes_dependency_install():
    source = WT_FISH.read_text()
    assert source.index("kura converge --quiet") < source.index("if test -f pnpm-lock.yaml")
