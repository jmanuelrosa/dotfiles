"""Claude Code's workspace trust, as recorded in ~/.claude.json.

Trust is the gate on project-scope plugins: a seat linked into `<project>/.claude/skills/`
loads only in a trusted workspace, so every plugin `add` in this tool is one step of a
two-step install and this module is the other step's rules.

Nothing here is claude-kit's own invention. It reads and writes a file Claude Code owns,
so the two derivations below mirror the ones in the 2.1.220 binary rather than choosing
something reasonable; a key we compute differently from the way Claude Code computes it
is a key Claude Code never reads.

    the key is the repo root      not the cwd, and for a linked worktree not the
                                  worktree either but the main checkout, because the
                                  key is derived through .git/commondir
    trust is inherited            the gate probes the key, then walks the cwd's
                                  ancestors to /, so trusting one directory trusts
                                  every project beneath it

The second one is why `granted_by` returns *which* path granted trust rather than a
bool. A project whose own entry reads false can still be trusted, and clearing its flag
then changes nothing observable: without the grantor's name that reads as the tool
having failed.
"""

import json
import os
import tempfile
from pathlib import Path

TRUSTED = "hasTrustDialogAccepted"

# The entry Claude Code creates when it first trusts a directory. Matched field for
# field so a key this tool creates is indistinguishable from one the trust dialog wrote,
# rather than a single-field object Claude Code then has to fill in around.
DEFAULT_ENTRY = {
    "allowedTools": [],
    "mcpContextUris": [],
    "mcpServers": {},
    "enabledMcpjsonServers": [],
    "disabledMcpjsonServers": [],
    TRUSTED: False,
    "projectOnboardingSeenCount": 0,
    "hasClaudeMdExternalIncludesApproved": False,
    "hasClaudeMdExternalIncludesWarningShown": False,
}


class Unreadable(Exception):
    """~/.claude.json is not JSON we should write back over.

    Deliberately not state.py's "read as empty and carry on". That file is ours and a
    corrupt one is worth discarding; this one holds the user's whole Claude
    configuration, so failing to understand it has to stop a write rather than start
    one from a blank slate.
    """


class Missing(Unreadable):
    """There is no ~/.claude.json at all.

    Separate from a corrupt one because the two answer differently. Nothing is trusted
    on a machine where Claude Code has never run, which is a report this tool can make;
    creating that file from scratch is not something it should do.
    """


def config_path(home):
    return Path(home) / ".claude.json"


def normalise(path):
    """Absolute and normalised, the way node's path.resolve + path.normalize are.

    Emphatically not Path.resolve(): that follows symlinks, and Claude Code does not.
    A key derived through a symlinked path would name a directory whose entry Claude
    Code never looks at, so the tool would report on, and write, the wrong workspace.
    """
    return os.path.normpath(os.path.abspath(str(path)))


def _main_checkout(directory):
    """The main checkout behind a linked worktree, or `directory` unchanged.

    A linked worktree's `.git` is a file holding `gitdir: <main>/.git/worktrees/<name>`,
    and the main checkout is reached from there through `commondir`. Every consistency
    check the binary makes is made here too, and each failure returns `directory`: a
    half-recognised worktree has to fall back to a key that at least exists, because
    guessing past a broken layout would silently trust some other directory.
    """
    marker = Path(directory) / ".git"
    try:
        if not marker.is_file():
            return directory
        pointer = marker.read_text().strip()
        if not pointer.startswith("gitdir:"):
            return directory
        gitdir = Path(normalise(Path(directory) / pointer[len("gitdir:") :].strip()))
        commondir = gitdir / "commondir"
        if not commondir.is_file():
            return directory
        common = Path(normalise(gitdir / commondir.read_text().strip()))
        # <main>/.git/worktrees/<name> is the only shape this resolution is valid for.
        if normalise(gitdir.parent) != normalise(common / "worktrees"):
            return directory
        if common.name != ".git":
            return directory
        return str(common.parent)
    except OSError:
        return directory


def repo_dir(start):
    """The nearest directory at or above `start` holding a `.git`, or None.

    Walks up looking for the entry rather than running git, exactly as the binary does.
    That keeps the tool free of a subprocess on its most common path and lets the
    worktree cases be tested against a fabricated layout in tmp_path.

    Stops *before* worktree resolution, which is what lets a caller tell "the key is the
    repo root above me" from "the key is a different checkout entirely".
    """
    current = Path(normalise(start))
    while True:
        if (current / ".git").exists():
            return str(current)
        parent = current.parent
        if parent == current:
            return None
        current = parent


def git_root(start):
    """The repo root whose trust key covers `start`, or None outside a repo."""
    found = repo_dir(start)
    return None if found is None else _main_checkout(found)


def key_for(path):
    """The ~/.claude.json key Claude Code stores this directory's trust under."""
    root = git_root(path)
    return normalise(root if root is not None else path)


def ancestors(path):
    """`path` and every directory above it, up to the filesystem root.

    The chain the gate walks. It starts from the cwd, not from the key, which for a
    worktree is a different lineage: the worktree sits under its own parents while its
    key sits under the main checkout's.
    """
    current = normalise(path)
    chain = [current]
    while True:
        parent = os.path.dirname(current)
        if parent == current:
            return chain
        chain.append(parent)
        current = parent


def projects(config):
    """The `projects` map, or an empty one. Never raises on a surprising shape."""
    found = config.get("projects")
    return found if isinstance(found, dict) else {}


def stored(config, key):
    """This key's own flag: True, False, or None when it has no entry at all.

    Three-valued because the three cases read differently to a user. An absent entry
    means Claude Code has never been run here, which is not the same statement as a
    directory that was offered the trust dialog and declined.
    """
    entry = projects(config).get(key)
    if not isinstance(entry, dict) or TRUSTED not in entry:
        return None
    return entry[TRUSTED] is True


def granted_by(config, key, cwd):
    """The path whose entry grants trust here, or None. Mirrors the gate's order.

    The key is probed first and the cwd's ancestors after, so the returned path is the
    one Claude Code would have stopped at. Returning the path rather than a bool is the
    whole point: "trusted" and "trusted because ~ is" need different advice.
    """
    entries = projects(config)

    def trusts(candidate):
        entry = entries.get(candidate)
        return isinstance(entry, dict) and entry.get(TRUSTED) is True

    if trusts(key):
        return key
    for candidate in ancestors(cwd):
        if trusts(candidate):
            return candidate
    return None


def descendant_keys(config, key):
    """Existing project keys strictly beneath `key`.

    Trusting a directory trusts all of these too, which is worth saying out loud before
    it happens. Matched at a path-segment boundary so /a/bc is not read as under /a/b.
    """
    prefix = key.rstrip(os.sep) + os.sep
    return sorted(other for other in projects(config) if other.startswith(prefix))


def read(path):
    """The whole config as a dict, or raise Missing / Unreadable."""
    try:
        text = Path(path).read_text()
    except FileNotFoundError:
        raise Missing(f"{path} does not exist yet") from None
    except OSError as exc:
        raise Unreadable(f"{path}: {exc.strerror or exc}") from None
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise Unreadable(f"{path} is not valid JSON ({exc})") from None
    if not isinstance(data, dict):
        raise Unreadable(f"{path} does not hold a JSON object")
    return data


def dump(config):
    """The bytes Claude Code itself would write.

    `JSON.stringify(config, null, 2)` with no trailing newline, and ensure_ascii off
    because JavaScript does not escape non-ASCII. Both matter for the same reason: this
    is a 76 KB file the user did not ask us to reformat, and json.load preserves key
    order, so getting these right keeps a trust toggle to a one-line diff.
    """
    return json.dumps(config, indent=2, ensure_ascii=False)


def apply(config, key, value):
    """Set one key's flag, in place, preserving everything else. Returns the config.

    An existing entry keeps its other fields, which is not defensive politeness: those
    entries run to 34 fields and hold the project's MCP servers, its allowed tools and
    its session history. A missing one is created from DEFAULT_ENTRY.
    """
    entries = config.setdefault("projects", {})
    if not isinstance(entries, dict):
        entries = {}
        config["projects"] = entries
    entry = entries.get(key)
    if not isinstance(entry, dict):
        entry = dict(DEFAULT_ENTRY)
        entries[key] = entry
    entry[TRUSTED] = value
    return config


def write(path, config):
    """Replace the config atomically, keeping its mode.

    Written to a sibling temp file and renamed, so a crash mid-write cannot leave the
    user without a Claude configuration. The mode is carried over deliberately: this
    file holds an oauth account, and a fresh temp file would take whatever the umask
    says, which on most machines is world-readable.
    """
    path = Path(path)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=".claude.json.")
    try:
        with os.fdopen(handle, "w") as stream:
            stream.write(dump(config))
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        # A failed write leaves the original in place rather than a stray temp file
        # beside it, which the next run would have no way to tell from a live one.
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
    return path
