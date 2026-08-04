"""Provenance: why each project-scoped artifact is installed.

Lives at <project>/.claude/claude-kit.json, beside the links it describes, so
deleting or moving a repo takes its record along and there is nothing to
reconcile.

Why a file exists at all: two histories can leave byte-identical directories yet
demand opposite answers from the cascade.

    History A                          History B
    add test-driven-development        add spec-driven-development
    add spec-driven-development          (pulls all four)

Both end with the same four links. On `remove spec-driven-development`, A must
keep test-driven-development and B must remove it. The distinguishing fact is
history, not state, so scanning the directory cannot recover it. Eight of the ten
dependency edges in the registry point at ordinary addable skills, so this
ambiguity is the common case rather than an edge one.

Deliberately not recorded:

  pins             an untagged artifact in ~/.claude can only have arrived via
                   --global, since the effective global set is known. The symlink
                   is the record.
  global reasons   global dependencies never cascade, so nothing needs to know
                   why one is there.
  a project index  a correct cross-scope cascade would need every project that
                   installed something, and that goes stale the moment a checkout
                   moves. The cascade stays inside one project instead.
"""

import json

from . import catalog as cat

FILENAME = "claude-kit.json"
DIRECT = "direct"
DEP_PREFIX = "dep-of:"


class Malformed(Exception):
    """The file exists but does not parse, or is not the shape this module writes.

    Raised by read_strict and swallowed by read, the way workspace.py separates a
    missing ~/.claude.json from an unreadable one. Every reader but one wants the
    forgiving behaviour, because provenance is an optimisation over keeping things.
    `restore` is the exception: there, "nothing was recorded" and "your manifest is
    unparseable" call for opposite answers, and reading the second as the first
    would install nothing and report success.
    """

# The on-disk shape nests by collection, matching the registries.
COLLECTIONS = {cat.SKILL: "skills", cat.AGENT: "agents", cat.PLUGIN: "plugins"}
BY_COLLECTION = {v: k for k, v in COLLECTIONS.items()}


def path_for(project):
    return project / ".claude" / FILENAME


def dep_of(parent_name):
    return f"{DEP_PREFIX}{parent_name}"


def is_direct(reason):
    """Anything not recorded as a dependency counts as deliberate.

    Erring this way matters: an unrecognised reason must never make something
    cascade-eligible, because a wrong keep costs one stale link while a wrong
    delete loses something the user chose.
    """
    return not str(reason).startswith(DEP_PREFIX)


def parent_of(reason):
    """The recorded parent name, or None for a direct install."""
    text = str(reason)
    return text[len(DEP_PREFIX):] if text.startswith(DEP_PREFIX) else None


def read_strict(project):
    """Provenance as {(type, name): reason}, raising Malformed on a bad file.

    Empty is still the answer when there is no file at all: absence is not a defect,
    and only the caller standing in the project knows whether it matters.

    "Malformed" includes valid JSON of the wrong shape, which is not the same class
    of mistake as invalid JSON and used to slip past the except below. A file holding
    `[]` or `null` parses fine, then fails on .get() and takes `list`, `doctor` and
    `remove` down with a traceback, which is the worst possible moment for it: doctor
    is the command you reach for to find out what is wrong.

    An OSError is left to propagate: cli.main turns it into a usage error naming the
    file, which says more than "malformed" would about a permission or an I/O fault.
    """
    if project is None:
        return {}
    path = path_for(project)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError as exc:
        raise Malformed(str(exc)) from exc
    if not isinstance(data, dict):
        raise Malformed("the top level is not an object")
    out = {}
    for collection, entries in (data.get("installed") or {}).items():
        kind = BY_COLLECTION.get(collection)
        if kind is None or not isinstance(entries, dict):
            continue
        for name, reason in entries.items():
            out[(kind, name)] = reason
    return out


def read(project):
    """Provenance as {(type, name): reason}. Empty when the file is absent or bad.

    A malformed or unreadable file reads as empty rather than raising: provenance
    is an optimisation over conservative behaviour, and D14 already requires that
    a missing record never causes a deletion.
    """
    try:
        return read_strict(project)
    except (Malformed, OSError):
        return {}


def write(project, records):
    """Persist {(type, name): reason}, deleting the file when nothing is left.

    An empty object on disk is indistinguishable from a stale one to a reader, so
    the absence of the file is the honest representation of "nothing tracked".
    """
    path = path_for(project)
    if not records:
        if path.is_file():
            path.unlink()
        return None
    nested = {}
    for (kind, name), reason in sorted(records.items()):
        nested.setdefault(COLLECTIONS[kind], {})[name] = reason
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"installed": nested}, indent=2) + "\n")
    return path


def record(project, entries):
    """Merge entries in, upgrading a dependency to direct but never the reverse.

    The upgrade is what makes History A work: naming something already present as
    a dependency is how you say you want it in its own right, even though no new
    symlink is made.
    """
    records = read(project)
    for key, reason in entries.items():
        if records.get(key) == DIRECT and reason != DIRECT:
            continue
        records[key] = reason
    write(project, records)
    return records


def forget(project, keys):
    records = read(project)
    for key in keys:
        records.pop(key, None)
    write(project, records)
    return records
