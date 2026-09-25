"""The neutral policy and each adapter's own knobs, as plain data."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

MARKER = "harness.toml"
HARNESS_PLACEHOLDER = "{harness}"
RENDER_ROOT_ENV = "HARNESS_RENDER_ROOT"


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


def render_root(root):
    """What `{harness}` expands to: this tree, unless the environment names the checkout.

    The rendered files are committed for the checkout they are linked from, so a clone
    elsewhere (CI) names that checkout to hold those files to the policy at all.
    """
    return os.environ.get(RENDER_ROOT_ENV) or home_relative(root)


def expand(value, root):
    if isinstance(value, str):
        return value.replace(HARNESS_PLACEHOLDER, render_root(root))
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
    hooks: list

    def adapter(self, name):
        return read(self.root / "adapters" / name / "adapter.toml", self.root)

    def hooks_for(self, harness):
        return [hook for hook in self.hooks if harness in hook["harnesses"]]


def load(root=None):
    root = Path(root) if root else find_root()
    policy = root / "policy"
    return Manifest(
        root=root,
        permissions=read(policy / "permissions.toml", root),
        sandbox=read(policy / "sandbox.toml", root),
        hooks=read(policy / "hooks.toml", root)["hook"],
    )
