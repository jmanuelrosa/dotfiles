"""Shared fixtures and loaders for the dotfiles test suite."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
CLAUDE = REPO / "roles/ai/files/claude"
SKILLS_DIR = CLAUDE / "skills"
AGENTS_DIR = CLAUDE / "agents"
PLUGINS_DIR = CLAUDE / "plugins"
FISH_FUNCTIONS = REPO / "roles/shell/files/fish/functions"
KIT = REPO / "roles/ai/files/scripts/claude-kit"

# Mirrors the table at the top of bin/claude-kit. Tests assert on these rather
# than on message text, so refusals can be reworded without breaking the suite.
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_FOUND = 2
EXIT_DEPENDENCY_ONLY = 3
EXIT_NEEDS_GLOBAL = 4
EXIT_ALREADY_LOCAL = 5
EXIT_ALREADY_GLOBAL = 6
EXIT_NO_PROJECT = 7


def _load(path):
    return json.loads(path.read_text())


def skill_name(entry, repo_key):
    """Mirror dn() in _claude_skill_jqlib.fish: basename of upstream_path,
    falling back to the repo name when the path is empty, '.' or '/'."""
    if "name" in entry:
        return entry["name"]
    path = (entry.get("upstream_path") or "").rstrip("/")
    if path in ("", "."):
        return repo_key.split("/")[-1]
    return path.split("/")[-1]


@pytest.fixture(scope="session")
def skill_registry():
    return _load(CLAUDE / "skill-registry.json")


@pytest.fixture(scope="session")
def agent_registry():
    return _load(CLAUDE / "agent-registry.json")


@pytest.fixture(scope="session")
def skills(skill_registry):
    """Every skill entry as (name, entry, origin) where origin is a repo key or 'local'."""
    out = []
    for repo_key, repo in skill_registry.get("repos", {}).items():
        for entry in repo.get("skills", []):
            out.append((skill_name(entry, repo_key), entry, repo_key))
    for entry in skill_registry.get("local_skills", []):
        out.append((entry["name"], entry, "local"))
    return out


@pytest.fixture(scope="session")
def agents(agent_registry):
    out = []
    for repo_key, repo in agent_registry.get("repos", {}).items():
        for entry in repo.get("agents", []):
            out.append((skill_name(entry, repo_key), entry, repo_key))
    for entry in agent_registry.get("local_agents", []):
        out.append((entry["name"], entry, "local"))
    return out


@pytest.fixture(scope="session")
def plugins():
    """Every plugin dir on disk that carries a manifest, as (name, manifest)."""
    out = []
    for d in sorted(PLUGINS_DIR.iterdir()):
        manifest = d / ".claude-plugin/plugin.json"
        if d.is_dir() and manifest.is_file():
            out.append((d.name, _load(manifest)))
    return out


def frontmatter(md_path):
    """Parse the YAML frontmatter of a markdown file. Raises on malformed YAML."""
    text = md_path.read_text()
    if not text.startswith("---\n"):
        return None
    _, _, rest = text.partition("---\n")
    block, sep, _ = rest.partition("\n---")
    if not sep:
        return None
    return yaml.safe_load(block)


@pytest.fixture
def fish(tmp_path):
    """Run a fish snippet against a throwaway HOME with the repo's functions loaded.

    Returns a callable: fish(code, cwd=..., env=...) -> CompletedProcess.
    HOME and DOTFILES_DIR are the only seams the claude-* functions read, so
    pointing them at tmp_path fully isolates a run from the real machine.
    """
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)

    def run(code, cwd=None, dotfiles=REPO, extra_env=None):
        env = {
            **os.environ,
            "HOME": str(home),
            "DOTFILES_DIR": str(dotfiles),
            "TERM": "dumb",
        }
        env.pop("XDG_CONFIG_HOME", None)
        if extra_env:
            env.update(extra_env)
        preamble = f"set -g fish_function_path {FISH_FUNCTIONS} $fish_function_path\n"
        return subprocess.run(
            ["fish", "--no-config", "-c", preamble + code],
            cwd=str(cwd or home),
            env=env,
            capture_output=True,
            text=True,
        )

    run.home = home
    return run


@pytest.fixture
def git_project(tmp_path):
    """A throwaway git repo, so project-scoped installs have somewhere to land."""
    proj = tmp_path / "project"
    proj.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
    return proj


@pytest.fixture
def kit(tmp_path):
    """Run claude-kit against a throwaway HOME.

    HOME and DOTFILES_DIR are the CLI's only environmental inputs, so pointing
    them at tmp_path isolates a run completely from the real machine. Returns a
    callable: kit("add", "commit", cwd=...) -> CompletedProcess, with .home
    exposed for asserting on what landed.
    """
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)

    def run(*argv, cwd=None, extra_env=None):
        env = {**os.environ, "HOME": str(home), "DOTFILES_DIR": str(REPO)}
        env.pop("XDG_CONFIG_HOME", None)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(KIT), *argv],
            cwd=str(cwd or home),
            env=env,
            capture_output=True,
            text=True,
        )

    run.home = home
    return run


# Fixture artifacts, chosen once so the cases read concretely. The asserts below
# fail loudly if a registry edit invalidates the choice, which beats a test that
# silently starts exercising the wrong branch.
A_GLOBAL_SKILL = "commit"
A_PROJECT_SKILL = "coderabbit"
A_GLOBAL_AGENT = "cc-staff-reviewer"
A_PROJECT_PLUGIN = "backend"


@pytest.fixture(scope="session", autouse=True)
def _fixture_artifacts_still_valid(skills, agents):
    by_name = {name: entry for name, entry, _ in skills}
    assert "global" in by_name[A_GLOBAL_SKILL]["groups"]
    assert "global" not in by_name[A_PROJECT_SKILL]["groups"]
    # Membership is tag *plus* declared dependencies, so an untagged skill that
    # anything depends on would still resolve global and break these cases.
    depended_on = {
        dep
        for _, entry, _ in [*skills, *agents]
        for dep in entry.get("dependencies", []) or []
    }
    assert A_PROJECT_SKILL not in depended_on
    agent_groups = {name: entry.get("groups", []) for name, entry, _ in agents}
    assert "global" in agent_groups[A_GLOBAL_AGENT]
    manifest = _load(PLUGINS_DIR / A_PROJECT_PLUGIN / ".claude-plugin/plugin.json")
    assert "global" not in manifest.get("groups", [])
