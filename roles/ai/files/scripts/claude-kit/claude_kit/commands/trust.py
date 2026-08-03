"""`claude-kit trust`: show or change whether this workspace is trusted.

The other half of a plugin install. `add` links a seat into `<project>/.claude/skills/`
and Claude Code loads it only in a trusted workspace, so until now the second step was a
prose hint pointing at a hand edit of ~/.claude.json. That hint was also wrong twice
over, in the two ways workspace.py exists to get right: the key is the repo root (the
*main* checkout, for a worktree), and trust is inherited from any trusted ancestor.

The report is built around the second one. Answering "are you trusted" with a bool would
be technically correct and useless, because the interesting states are "trusted on your
own key" and "trusted only because ~ is", and they call for opposite advice. So every
line names the path it is talking about.

Writes touch exactly one field of one key. Nothing here creates ~/.claude.json: that
file is Claude Code's, and a machine that has none has no trust to change.
"""

from dataclasses import dataclass
from pathlib import Path

from .. import errors, paths, workspace as ws
from dotkit import ui
from ..cli import fail


@dataclass(frozen=True)
class State:
    """Everything the report needs, resolved once. Pure data."""

    cwd: str
    key: str
    #: The nearest directory holding a .git, before worktree resolution. None outside a
    #: repo, in which case the key is the cwd itself.
    repo: str
    #: The key belongs to a different checkout than the repo the cwd sits in, which only
    #: happens for a linked worktree and is the surprise worth naming.
    worktree: bool
    #: True, False, or None when the key has no entry at all.
    stored: bool
    #: The path whose entry grants trust, or None. May be the key, an ancestor, or None.
    granted: str
    #: Existing project keys beneath the key, which trusting it would also trust.
    beneath: tuple

    @property
    def trusted(self):
        return self.granted is not None

    @property
    def inherited(self):
        return self.trusted and self.granted != self.key


def resolve(config, cwd):
    """The State for `cwd` against an already-loaded config. No I/O beyond the repo walk."""
    repo = ws.repo_dir(cwd)
    key = ws.key_for(cwd)
    return State(
        cwd=ws.normalise(cwd),
        key=key,
        repo=repo,
        worktree=repo is not None and ws.normalise(repo) != key,
        stored=ws.stored(config, key),
        granted=ws.granted_by(config, key, cwd),
        beneath=tuple(ws.descendant_keys(config, key)),
    )


FLAGS = {True: "true", False: "false", None: "no entry yet"}


def header(state, emit):
    """Where we are, what key that maps to, and what the file says about it."""
    emit(ui.render("title", "🔐 Workspace trust"))
    emit(ui.render("item", f"Workspace: {ui.path(state.cwd)}"))
    emit(ui.render("item", f"Trust key: {ui.path(state.key)}"))
    if state.worktree:
        emit(
            ui.render(
                "note",
                "Linked worktree: Claude Code keys trust on the main checkout, so every "
                "worktree of this repo shares one answer.",
                indent=4,
            )
        )
    elif state.repo is None:
        emit(ui.render("note", "Not a git repository, so the key is the directory itself.", indent=4))
    emit(ui.render("item", f"{ws.TRUSTED}: {FLAGS[state.stored]}"))


def verdict(state, emit):
    """The one line that answers the question, plus what to do about it."""
    if state.inherited:
        emit(ui.render("ok", f"Trusted, inherited from {ui.path(state.granted)}."))
        emit(
            ui.render(
                "note",
                f"{ui.path(state.granted)} grants trust to every directory beneath it, "
                f"so this workspace is trusted whatever its own flag says.",
            )
        )
    elif state.trusted:
        emit(ui.render("ok", "Trusted on its own key."))
        emit(
            ui.render(
                "note",
                f"Project-scope plugins load here, after Claude Code is restarted from "
                f"{ui.path(state.key)}.",
            )
        )
    else:
        emit(ui.render("warn", "Not trusted. Project-scope plugins will not load here."))
        emit(ui.render("note", "claude-kit trust --on"))


def show(state, missing, emit=print):
    """Read-only. Exits DRIFT when untrusted, as doctor does for a problem it found."""
    header(state, emit)
    if missing:
        emit(
            ui.render(
                "note",
                "No ~/.claude.json yet, so nothing on this machine is trusted. Run "
                "Claude Code once to create it.",
                indent=4,
            )
        )
    verdict(state, emit)
    return errors.OK if state.trusted else errors.DRIFT


def changed(state, value, emit=print):
    """Report a write that has already happened. Always OK.

    An `--off` under a trusted ancestor is the case this has to be honest about: the
    flag is now false and the workspace is still trusted. It warns, names the ancestor
    and prints the command that would clear it, and still exits OK, because the write
    the user asked for did happen.
    """
    header(state, emit)
    if value:
        emit(ui.render("ok", f"Trusted {ui.path(state.key)}."))
        if state.beneath:
            emit(
                ui.render(
                    "warn",
                    f"This also grants trust to {len(state.beneath)} project(s) beneath it.",
                )
            )
            for other in state.beneath:
                emit(ui.render("item", ui.path(other), indent=4))
    else:
        emit(ui.render("ok", f"Cleared {ws.TRUSTED} for {ui.path(state.key)}."))
        if state.granted is not None:
            emit(
                ui.render(
                    "warn",
                    f"Still trusted: {ui.path(state.granted)} grants trust to every "
                    f"directory beneath it.",
                )
            )
            emit(ui.render("note", f"claude-kit trust --off {ui.path(state.granted)}"))

    emit(ui.render("done", "Restart Claude Code for this to take effect."))
    emit(
        ui.render(
            "note",
            "A live session for this project rewrites ~/.claude.json from memory when it "
            "exits, which would undo this. Close it first.",
        )
    )
    return errors.OK


def run(args):
    target = args.path or Path.cwd()
    config_path = ws.config_path(paths.home())
    value = True if args.turn_on else False if args.turn_off else None

    try:
        config = ws.read(config_path)
        missing = False
    except ws.Missing as exc:
        if value is not None:
            return fail(
                errors.USAGE,
                f"{exc}, and this is Claude Code's own file to create.\n"
                "  Run Claude Code once, then set trust here.",
            )
        config, missing = {}, True
    except ws.Unreadable as exc:
        return fail(errors.USAGE, f"{exc}\n  Refusing to write over a file we cannot read.")

    state = resolve(config, target)

    if value is None:
        return show(state, missing)

    # `--off` is already satisfied by a false flag *and* by no entry at all: both leave
    # the key granting nothing, and writing a default entry to say so would be a change
    # to the file with no change in behaviour.
    already = state.stored is True if value else state.stored is not True
    if already:
        where = "already trusted" if value else "already not trusted"
        return fail(
            errors.ALREADY,
            f"{ui.path(state.key)} is {where} on its own key."
            + (
                f"\n  It is trusted through {ui.path(state.granted)}; clear that instead."
                if not value and state.granted is not None
                else ""
            ),
        )

    ws.write(config_path, ws.apply(config, state.key, value))
    # Re-resolved against the written config so the report reads the flag it just set
    # rather than describing an intention.
    return changed(resolve(config, target), value)
