"""Fetching, comparing and replacing upstream skill trees.

`fetch` is the seam. It is the only function here that touches the network, and it
takes the URL and a destination and nothing else, so a test replaces it with one
that unpacks a tarball built in tmp_path. Everything downstream (strip-components
semantics, the exclude set, the comparison, the atomic swap) then runs for real
against real bytes rather than being mocked away.
"""

import http.client
import os
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Never carried into a skill directory: repo furniture and installed packages.
EXCLUDE = {".git", ".github", "node_modules"}

TARBALL_URL = "https://github.com/{repo}/archive/{branch}.tar.gz"


class FetchError(Exception):
    """Upstream could not be reached, or what came back was not a tarball."""


def tarball_url(repo, branch):
    return TARBALL_URL.format(repo=repo, branch=branch)


def _safe_members(archive, strip):
    """Yield members with `strip` leading path components removed.

    GitHub wraps everything in a single <repo>-<ref>/ directory, which is what
    strip=1 discards. Members escaping the destination via .. or an absolute path
    are dropped: a tarball is remote input, and extracting one is the classic path
    traversal.
    """
    for member in archive.getmembers():
        parts = Path(member.name).parts
        if len(parts) <= strip:
            continue
        relative = Path(*parts[strip:])
        if relative.is_absolute() or ".." in relative.parts:
            continue
        member.name = str(relative)
        yield member


def extract(tar_path, destination, strip=1):
    """Unpack a tarball into destination, stripping leading components."""
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as archive:
        members = list(_safe_members(archive, strip))
        # filter="data" is required from Python 3.14, where the default changed to
        # error rather than warn. It also drops device nodes and unsafe modes.
        archive.extractall(destination, members=members, filter="data")
    return destination


def fetch(repo, branch, destination):
    """Download and unpack an upstream repo. The only networked function here.

    Tests replace this wholesale, which is why it does nothing but I/O: no
    decisions live in it that a test would then be unable to exercise.
    """
    url = tarball_url(repo, branch)
    handle = None
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            handle, tmp = tempfile.mkstemp(suffix=".tar.gz")
            with os.fdopen(handle, "wb") as out:
                handle = None
                shutil.copyfileobj(response, out)
    # HTTPException is not an OSError: a truncated chunked response raises
    # IncompleteRead mid-copy, which escaped as a traceback and abandoned every repo
    # still to check, when it is exactly the "could not be reached" case above.
    except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
        raise FetchError(f"could not fetch {url}: {exc}") from exc
    try:
        return extract(Path(tmp), destination)
    except (tarfile.TarError, OSError) as exc:
        raise FetchError(f"{url} is not a readable tarball: {exc}") from exc
    finally:
        os.unlink(tmp)


def subtree(root, upstream_path):
    """Where a skill lives inside a fetched repo.

    An empty path, "." or "/" means the repo root is itself the skill, which is how
    a single-skill repo is tracked.
    """
    cleaned = (upstream_path or "").strip().rstrip("/")
    if cleaned in ("", "."):
        return root
    return root / cleaned


def _relevant(directory):
    """Every path under directory, relative, with excluded subtrees pruned."""
    found = set()
    for current, dirnames, filenames in os.walk(directory):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE)
        base = Path(current).relative_to(directory)
        for name in dirnames:
            found.add(base / name)
        for name in filenames:
            if name in EXCLUDE:
                continue
            found.add(base / name)
    return found


def differs(source, destination):
    """True if the two trees differ in structure or file contents.

    Compares bytes, not stat metadata. filecmp.dircmp defaults to a shallow
    comparison that calls two files equal when size and mtime match, which would
    call an edited-and-restored file unchanged and silently skip a real update.
    """
    if not destination.is_dir():
        return True
    # Walked once: _relevant is a full os.walk, and a second call here would repeat it
    # for every up-to-date skill, which is most of them on a bare run.
    paths = _relevant(source)
    if paths != _relevant(destination):
        return True
    for relative in paths:
        left, right = source / relative, destination / relative
        if left.is_dir() != right.is_dir():
            return True
        if left.is_dir():
            continue
        if left.read_bytes() != right.read_bytes():
            return True
    return False


def copy_tree(source, destination):
    """Copy source over destination atomically enough to survive a crash.

    Builds a sibling directory first and swaps it in, so an interruption leaves
    either the old tree or the new one. The fish implementation this replaces did
    `rm -rf` then rsync, which destroyed the skill if the copy failed halfway.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".{destination.name}.incoming"
    retired = destination.parent / f".{destination.name}.previous"
    for leftover in (staging, retired):
        if leftover.exists():
            shutil.rmtree(leftover)

    shutil.copytree(source, staging, ignore=shutil.ignore_patterns(*EXCLUDE), symlinks=True)
    try:
        if destination.exists():
            os.replace(destination, retired)
        os.replace(staging, destination)
    finally:
        for leftover in (staging, retired):
            if leftover.exists():
                shutil.rmtree(leftover, ignore_errors=True)
    return destination


def stamp():
    """An ISO8601-Z timestamp, matching what the registries already carry."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
