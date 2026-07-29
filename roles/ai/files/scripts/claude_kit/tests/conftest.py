"""Fixtures for the claude-kit suite.

Three altitudes, in order of how many tests should live at each:

  pure         import claude_kit.* and call functions on literal data. No I/O.
  filesystem   `home` + `project` fixtures, real symlinks under tmp_path.
  subprocess   the `kit` fixture, running the shim end to end. A handful only.

HOME and DOTFILES_DIR are the tool's only environmental inputs, so pointing them
at tmp_path isolates a run completely from the real machine.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPTS = PACKAGE.parent
FILES = SCRIPTS.parent
REPO = FILES.parents[2]  # roles/ai/files -> the dotfiles checkout
CLAUDE = FILES / "claude"
SHIM = SCRIPTS / "claude-kit"
# claude-skill / claude-agent are kept as reference implementations. test_list_format
# runs claude-skill for real and diffs its output against ours.
FISH_FUNCTIONS = REPO / "roles/shell/files/fish/functions"

# Make the package importable for the pure altitude. Mirrors what the shim does.
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A throwaway HOME with ~/.claude present, exported so the tool sees it."""
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("DOTFILES_DIR", str(REPO))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return h


@pytest.fixture
def project(tmp_path):
    """A throwaway project, which is to say a directory.

    A bare mkdir is faithful: project_root() takes cwd at face value, so there is
    nothing to initialise. This used to `git init` because the project was the git
    top level.
    """
    p = tmp_path / "project"
    p.mkdir()
    return p


@pytest.fixture
def kit(tmp_path):
    """Run the shim as a subprocess against a throwaway HOME.

    Returns kit("add", "commit", cwd=...) -> CompletedProcess, with .home exposed
    for asserting on what landed. Reserved for end-to-end wiring checks; anything
    testable by import belongs at the pure altitude instead.
    """
    h = tmp_path / "kit-home"
    (h / ".claude").mkdir(parents=True)

    def run(*argv, cwd=None, extra_env=None):
        env = {**os.environ, "HOME": str(h), "DOTFILES_DIR": str(REPO)}
        env.pop("XDG_CONFIG_HOME", None)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(SHIM), *argv],
            cwd=str(cwd or h),
            env=env,
            capture_output=True,
            text=True,
        )

    run.home = h
    return run


def force_colour(monkeypatch, on):
    """Turn colour on or off for an in-process render.

    colors.enabled reads the environment per call, so this is all a test needs to make
    a non-tty stdout behave like a terminal, or the reverse.
    """
    if on:
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
    else:
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.setenv("NO_COLOR", "1")


@pytest.fixture
def coloured(monkeypatch):
    """Force colour on, as if stdout were a terminal."""
    force_colour(monkeypatch, True)


@pytest.fixture
def plain(monkeypatch):
    """Force colour off, whatever the surrounding environment says."""
    force_colour(monkeypatch, False)


def subparsers():
    """The CLI's subcommand parsers, by name.

    argparse exposes them only as the one action whose `choices` is a dict, so the
    lookup is written here rather than in each module that needs it.
    """
    from claude_kit.cli import build_parser

    action = next(
        a for a in build_parser()._actions if hasattr(a, "choices") and isinstance(a.choices, dict)
    )
    return action.choices


@pytest.fixture(scope="session")
def catalog():
    """The real catalog, built once for the whole run.

    Seven modules each declared this and its `effective` companion at module scope,
    which re-parsed both registries and re-scanned files/claude/plugins/ per module.
    Both are read-only, so one session-scoped build serves every test.
    """
    from claude_kit import catalog as cat

    return cat.build_catalog(CLAUDE)


@pytest.fixture(scope="session")
def effective(catalog):
    from claude_kit import scope

    return scope.global_set(catalog)
