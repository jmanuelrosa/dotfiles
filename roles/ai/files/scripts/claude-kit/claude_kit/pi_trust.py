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
treats that directory, in the cwd or any ancestor of it, as a reason to ask about
trusting the project. So the tool's own work is what causes the prompt, which makes
"will pi ask me here, and what does its store already say" a question this tool owes an
answer to.

Nothing here writes. pi guards the file with `proper-lockfile` and it is pi's to own;
accepting pi's prompt once is a safe, one-time act that records the same decision, and
`locked` exists only so a reader is told when the file is being written underneath them.
"""

import json
import os
from pathlib import Path

from claude_kit import paths

FILENAME = "trust.json"
LOCK_SUFFIX = ".lock"
CONFIG_DIR = ".pi"
SKILLS_DIR = Path(".agents") / "skills"

TRUST_REQUIRING_CONFIG_ENTRIES = (
    "settings.json",
    "extensions",
    "skills",
    "prompts",
    "themes",
    "SYSTEM.md",
    "APPEND_SYSTEM.md",
)


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


def config_entries_requiring_trust(cwd):
    """The `.pi/` entries pi gates behind trust that this directory actually holds.

    `TRUST_REQUIRING_PROJECT_CONFIG_RESOURCES`, kept in pi's order because the report
    names them. The list is the whole point: pi does not ask about a `.pi` directory, it
    asks about these seven names inside one. A checkout whose `.pi/` holds only a
    `.gitkeep` is a directory pi never prompts over, and naming the directory would
    claim a prompt that never comes. `existsSync` in pi, so a plain file called `skills`
    counts too.
    """
    config = Path(normalise(cwd)) / CONFIG_DIR
    return [entry for entry in TRUST_REQUIRING_CONFIG_ENTRIES if (config / entry).exists()]


def skills_dir_requiring_trust(cwd, home):
    """The nearest `.agents/skills` at or above `cwd` that pi would gate on, or None.

    pi walks from the canonicalised cwd to the filesystem root, so a directory linked
    above this one prompts exactly as one here does, and `$HOME/.agents/skills` is
    skipped by name because it is the user's own store rather than any project's.
    Looking only at the project root both misses the first and, anywhere under $HOME,
    invents the second.
    """
    excluded = Path(normalise(home)) / SKILLS_DIR
    for candidate in ancestors(cwd):
        found = Path(candidate) / SKILLS_DIR
        if found != excluded and found.exists():
            return found
    return None


def prompt_reason(store, cwd, project, home=None):
    """Why pi would ask about this directory on its next session, or None.

    The two conditions pi applies, in its order: `hasTrustRequiringProjectResources`
    finds something trust would gate, and `findNearestTrustEntry` has nothing recorded
    for the cwd or an ancestor. Both are asked of the cwd, since that is the only path
    pi knows.

    The reason is returned rather than a bool because the triggers call for different
    readings. A `.agents/skills` at the project root is one `add` creates, so the prompt
    is a consequence of running this tool here; one further up, or a `.pi/` entry, is
    the user's own and must not be described as ours.
    """
    skills = skills_dir_requiring_trust(cwd, paths.home() if home is None else home)
    if skills is not None:
        ours = project is not None and skills == Path(normalise(project)) / SKILLS_DIR
        trigger = "claude-kit linked .agents/skills here" if ours else f"{skills} covers this directory"
    else:
        entries = config_entries_requiring_trust(cwd)
        if not entries:
            return None
        trigger = f"{CONFIG_DIR}/ here holds {', '.join(entries)}"
    path, _ = decided_by(store, cwd)
    return trigger if path is None else None
