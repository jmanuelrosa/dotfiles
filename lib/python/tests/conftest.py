"""Fixtures for the dotkit suite.

The colour toggles, because `ui` renders and touches nothing else. The helper
they wrap lives in `dotkit.testing` rather than here: it was shared with the kura
CLI's suite while that suite still lived in this checkout, and a fixture is the one
thing a `conftest.py` can own without a second directory being able to claim the
name. See dotkit/testing.py for why that matters.

And the catalog skip: a module that imports one of the catalog paths reads the
agent-catalog clone, so on a machine without one it is not collected, and the run
says so. Decided from the import statement rather than by importing the module,
because several of them list the catalog while building their parameters.
"""

import ast

import pytest
from dotkit import testing
from dotkit.testing import force_colour

CATALOG_LESS = []


def imports_the_catalog(path):
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "dotkit.testing"
        and {alias.name for alias in node.names} & set(testing.CATALOG_NAMES)
        for node in ast.parse(path.read_text()).body
    )


def pytest_ignore_collect(collection_path):
    if testing.CATALOG.is_dir() or collection_path.suffix != ".py":
        return None
    if collection_path.name.startswith("test_") and imports_the_catalog(collection_path):
        CATALOG_LESS.append(collection_path.name)
        return True
    return None


def pytest_terminal_summary(terminalreporter):
    if CATALOG_LESS:
        terminalreporter.write_line(
            f"not collected, no agent catalog at {testing.CATALOG}: {', '.join(sorted(CATALOG_LESS))}"
        )


@pytest.fixture
def coloured(monkeypatch):
    """Force colour on, as if stdout were a terminal."""
    force_colour(monkeypatch, True)


@pytest.fixture
def plain(monkeypatch):
    """Force colour off, whatever the surrounding environment says."""
    force_colour(monkeypatch, False)
