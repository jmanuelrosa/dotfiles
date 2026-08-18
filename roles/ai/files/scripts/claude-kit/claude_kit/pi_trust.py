"""pi's own workspace trust, which is a different question from Claude Code's.

`claude-kit trust` reads and writes `~/.claude.json`, and none of that applies here.
pi keeps its own store and derives its key differently, so the same project has two
answers and neither tool can speak for the other. Separate module for that reason: the
derivations in `workspace.py` are Claude Code's and are documented as not ours to
choose, and these are pi's on exactly the same terms. Both were read out of the
installed 0.84.x `dist/core/trust-manager.js`.

Three differences, and every one of them changes the answer:

- **The key is the cwd, not the repo root.** Claude Code stores trust against the git
  repo root, and for a linked worktree against the main checkout, so every worktree of
  a repo shares one entry. pi stores it against the directory it was started in, so a
  subdirectory is its own workspace.
- **The key is realpathed.** `canonicalizePath` is `realpathSync`, where Claude Code's
  `normalise` deliberately is not. So a path reached through a symlink produces
  different keys in the two stores by design on both sides.
- **The nearest entry wins, including a denial.** Claude Code's gate looks for a
  granting entry and keeps walking past anything else; pi stops at the first ancestor
  with a boolean and takes it. So a `false` on a parent is not merely the absence of
  trust, it is a decision that shadows a `true` further up.

Why this is read at all: `claude-kit add` creates `<project>/.agents/skills`, and pi
treats the presence of that directory as a reason to ask about trusting the project. So
the tool's own work is what causes the prompt, which makes "will pi ask me here, and
what does its store already say" a question this tool owes an answer to.

Nothing here writes. pi guards the file with `proper-lockfile` and it is pi's to own;
accepting pi's prompt once is a safe, one-time act that records the same decision, and
`locked` exists only so a reader is told when the file is being written underneath them.
"""

import json
import os
from pathlib import Path

FILENAME = "trust.json"
LOCK_SUFFIX = ".lock"


def store_path(home):
    """Where pi keeps its trust decisions."""
    return Path(home) / ".pi" / "agent" / FILENAME


def normalise(path):
    """pi's `canonicalizePath`: absolute, and through symlinks.

    `realpathSync` in pi, so `Path.resolve()` rather than `workspace.normalise`. The
    difference is the whole reason this function exists twice in this package: a key
    computed the other way names a directory whose entry pi never consults.
    """
    try:
        return str(Path(path).resolve())
    except OSError:
        return os.path.normpath(os.path.abspath(str(path)))


def key_for(path):
    """The trust.json key pi stores this directory's decision under.

    The directory itself. No git call, and deliberately no repo-root walk: pi has no
    notion of a repository here, so a subdirectory of a trusted repo is a workspace pi
    has never been told about.
    """
    return normalise(path)


def read(path):
    """The store as a flat {path: bool} mapping, or {} when there is nothing to read.

    A missing file is the normal state of a machine where pi has not asked yet, and an
    unparseable one is pi's to complain about, so both read as "nothing recorded". This
    is a report, and refusing to print one because a file is malformed would be the
    least useful moment to stop.
    """
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: value for key, value in data.items() if isinstance(value, bool)}


def ancestors(path):
    """`path` and every directory above it, up to the filesystem root."""
    current = normalise(path)
    chain = [current]
    while True:
        parent = os.path.dirname(current)
        if parent == current:
            return chain
        chain.append(parent)
        current = parent


def decided_by(store, cwd):
    """(path, decision) for the nearest ancestor with an entry, or (None, None).

    `findNearestTrustEntry`, which stops at the first boolean it finds rather than
    looking for a `true`. Returning the decision alongside the path is what lets a
    caller distinguish the three states pi actually has: trusted here, refused here,
    and never asked.
    """
    for candidate in ancestors(cwd):
        if candidate in store:
            return candidate, store[candidate]
    return None, None


def locked(path):
    """True while pi holds its lock on the store.

    `proper-lockfile` takes `<file>.lock` beside the file, so its presence means a pi
    process is writing. Only worth reporting: nothing here writes, so this cannot
    change what the caller may do, only what they are told.
    """
    return Path(str(path) + LOCK_SUFFIX).exists()


def prompt_reason(store, cwd, project):
    """Why pi would ask about this project on its next session, or None.

    The two conditions pi applies, in its order: something in the project makes trust
    relevant, and no ancestor has already decided. The reason is returned rather than a
    bool because the two triggers call for different readings. `.agents/skills` is one
    this tool creates, so the prompt is a consequence of running `add` here; `.pi` is
    the user's own, so it is not.
    """
    if project is None:
        return None
    if (Path(project) / ".agents" / "skills").exists():
        trigger = "claude-kit linked .agents/skills here"
    elif (Path(project) / ".pi").is_dir():
        trigger = "this project has a .pi directory"
    else:
        return None
    path, _ = decided_by(store, cwd)
    return trigger if path is None else None
