"""The neutral policy and each adapter's own knobs, as plain data."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

MARKER = "harness.toml"
HARNESS_PLACEHOLDER = "{harness}"


def find_root(start=None):
    start = Path(start or __file__).resolve()
    for directory in (start, *start.parents):
        if (directory / MARKER).is_file():
            return directory
    raise FileNotFoundError(f"no {MARKER} at or above {start}")


def home_relative(path):
    """`~/...` when under $HOME, which every harness here expands, so no username is written."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def expand(value, root):
    if isinstance(value, str):
        return value.replace(HARNESS_PLACEHOLDER, home_relative(root))
    if isinstance(value, list):
        return [expand(item, root) for item in value]
    if isinstance(value, dict):
        return {key: expand(item, root) for key, item in value.items()}
    return value


def read(path, root):
    with path.open("rb") as handle:
        return expand(tomllib.load(handle), root)


@dataclass(frozen=True)
class Manifest:
    root: Path
    permissions: dict
    sandbox: dict

    def adapter(self, name):
        return read(self.root / "adapters" / name / "adapter.toml", self.root)


def load(root=None):
    root = Path(root) if root else find_root()
    policy = root / "policy"
    return Manifest(
        root=root,
        permissions=read(policy / "permissions.toml", root),
        sandbox=read(policy / "sandbox.toml", root),
    )
