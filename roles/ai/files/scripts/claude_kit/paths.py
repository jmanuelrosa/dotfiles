"""Locating the two roots the tool reads.

Two unrelated notions of "root" live here and conflating them is a real bug
source:

  repo_root()     the dotfiles checkout, where artifacts are stored
  project_root()  the user's cwd, where they get linked

project_root lives in scope.py, next to the rules that use it. This module only
finds the checkout.
"""

import os
import sys
from pathlib import Path

from dotkit import colors

# The playbook marks the repo root. Searching for it beats counting parent
# directories, which silently breaks whenever this file moves.
REPO_MARKER = "dotfiles.yml"
FILES_SUBDIR = "roles/ai/files"
CLAUDE_SUBDIR = f"{FILES_SUBDIR}/claude"


def repo_root():
    """The dotfiles checkout.

    DOTFILES_DIR wins when set, which is the seam that lets tests point at a
    fixture repo. Otherwise walk up from this file: resolve() follows the
    ~/.local/bin symlink back into the checkout, so this works whether
    claude-kit was invoked through PATH or in place.
    """
    override = os.environ.get("DOTFILES_DIR")
    if override:
        return Path(override)
    here = Path(__file__).resolve()
    for directory in here.parents:
        if (directory / REPO_MARKER).is_file():
            return directory
    raise SystemExit(
        f"{colors.cross(sys.stderr)} cannot locate the dotfiles repo from {here}. "
        "Set DOTFILES_DIR."
    )


def claude_dir(root=None):
    """Where skills, agents and plugins are stored."""
    return (root or repo_root()) / CLAUDE_SUBDIR


def home():
    """Read HOME through the environment rather than Path.home().

    Path.home() consults the password database on some platforms, which would
    ignore the HOME a test sets and let a run escape into the real ~/.claude.
    """
    return Path(os.environ.get("HOME") or Path.home())
