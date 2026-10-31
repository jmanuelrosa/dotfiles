"""ui.py and colors.py are copies from the dotkit repository, pinned in dotkit.json.

Change them in dotkit and run its `bin/dotkit-vendor` against this checkout, so every
tool that prints through the vocabulary receives the same edit.
"""

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LOCK = json.loads((ROOT / "dotkit.json").read_text())


@pytest.mark.parametrize("name", sorted(LOCK["files"]))
def test_the_vendored_copy_is_unedited(name):
    copy = ROOT / LOCK["target"] / name
    actual = hashlib.sha256(copy.read_bytes()).hexdigest()
    assert actual == LOCK["files"][name], f"{copy.relative_to(ROOT)} differs from dotkit {LOCK['rev'][:12]}"
