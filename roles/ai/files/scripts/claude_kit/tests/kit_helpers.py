"""Helpers this suite shares, in a module no other directory can claim.

These cannot live in `dotkit.testing`: `subparsers` imports claude-kit's own CLI, and
`force_colour` is a monkeypatch helper, so both are this tool's business rather than
the repo's. They cannot live in `conftest.py` either, because a test module importing
them by that name is the collision `dotkit.testing` documents: every non-package
`conftest.py` is named `conftest`, so with more than one suite directory on `sys.path`
the name resolves to whichever loaded last.

The answer is a name that is unique across every suite. `test_suites.py` asserts that
no importable module under a suite directory shares a basename with another, which is
what keeps that true as suites are added.
"""

import sys
from pathlib import Path

from dotkit.testing import AI_SCRIPTS_DIR

# Derived from this file's own location, so it says where the suite actually sits.
PACKAGE = Path(__file__).resolve().parents[1]

# Derived from the repo anchor instead, deliberately. Two independent derivations are
# what let test_packaging assert the package is a sibling of the shim and have the
# assertion mean something; computing both from one constant made it tautological.
SCRIPTS = AI_SCRIPTS_DIR
SHIM = AI_SCRIPTS_DIR / "claude-kit"


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


def ensure_importable():
    """Put the package's directory on sys.path, exactly as the shim does.

    Called from conftest so it happens before any test module imports claude_kit.
    """
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
