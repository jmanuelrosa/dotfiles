"""Fixtures for the dotkit suite.

Only the colour toggles, because `ui` renders and touches nothing else. The helper
they wrap lives in `dotkit.testing` rather than here: two suites need it now that
test_ui sits beside the package instead of inside claude-kit's, and a fixture is the
one thing a `conftest.py` can own without a second directory being able to claim the
name. See dotkit/testing.py for why that matters.
"""

import pytest
from dotkit.testing import force_colour


@pytest.fixture
def coloured(monkeypatch):
    """Force colour on, as if stdout were a terminal."""
    force_colour(monkeypatch, True)


@pytest.fixture
def plain(monkeypatch):
    """Force colour off, whatever the surrounding environment says."""
    force_colour(monkeypatch, False)
