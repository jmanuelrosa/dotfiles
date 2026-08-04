"""Reading the three artifact sources into one uniform shape.

Skills and agents come from registries; plugins are discovered by scanning for a
manifest, because they carry no registry row. Everything below is pure apart from
build_catalog's reads, so the rules that matter are testable on literal data.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

SKILL = "skill"
AGENT = "agent"
PLUGIN = "plugin"

# Where each type INSTALLS. Plugins load as <name>@skills-dir, so they share the
# skills leaf with skills.
LEAF = {SKILL: "skills", AGENT: "agents", PLUGIN: "skills"}
# Where each type is STORED in the repo. Distinct from LEAF, and that distinction is
# load-bearing: since skills and plugins install into the same leaf, the store a
# symlink points into is the only thing that says which type it is.
STORE = {SKILL: "skills", AGENT: "agents", PLUGIN: "plugins"}

REGISTRY_FILE = {SKILL: "skill-registry.json", AGENT: "agent-registry.json"}
COLLECTION = {SKILL: "skills", AGENT: "agents"}
# Agents are single files; skills and plugins are directories.
SUFFIX = {SKILL: "", AGENT: ".md", PLUGIN: ""}

PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
# Claude Code reserves `dependencies` in a plugin manifest. An array of skill
# names there makes the plugin ship nothing at all, silently, while
# `claude plugin details` still lists every artifact. Verified on 2.1.220.
PLUGIN_DEPS_KEY = "skillDependencies"
PLUGIN_RESERVED_KEY = "dependencies"
PLUGIN_REQUIRED_KEYS = ("name", "description", "version")


@dataclass(frozen=True)
class Artifact:
    name: str
    type: str
    groups: tuple = ()
    dependencies: tuple = ()
    dependency_only: bool = False
    source: Path = None
    origin: str = "local"
    # Only repo-tracked skills have an upstream to sync from.
    upstream_repo: str = None
    upstream_path: str = None
    upstream_branch: str = None
    updated_at: str = None
    # Plugins only: keys present in the manifest, so doctor can flag the traps.
    manifest_keys: tuple = field(default=())

    @property
    def leaf(self):
        return LEAF[self.type]

    @property
    def basename(self):
        return f"{self.name}{SUFFIX[self.type]}"

    @property
    def tagged_global(self):
        return "global" in self.groups

    @property
    def has_upstream(self):
        return self.upstream_repo is not None


def entry_name(entry, repo_key):
    """A repo entry's directory name: the basename of upstream_path.

    Falls back to the repo name when the path is empty, "." or "/", which is how
    a skill living at a repo root is named.

    This is now the only implementation, and the Television cables depend on it being
    the name they get from `claude-kit list --json`: their preview and $EDITOR actions
    build a path under files/claude/skills/ from it.
    """
    if "name" in entry:
        return entry["name"]
    path = (entry.get("upstream_path") or "").rstrip("/")
    if path in ("", "."):
        return repo_key.split("/")[-1]
    return path.split("/")[-1]


def _read_json(path):
    return json.loads(path.read_text())


def registry_entries(registry, collection):
    """Yield (name, entry, repo_key) across a registry's repos and its local list.

    repo_key is None for local entries, which is what distinguishes a skill with
    an upstream from one authored here.
    """
    for repo_key, repo in (registry.get("repos") or {}).items():
        for entry in repo.get(collection) or []:
            yield entry_name(entry, repo_key), entry, repo_key
    for entry in registry.get(f"local_{collection}") or []:
        yield entry["name"], entry, None


def _from_registry(claude, kind):
    registry = _read_json(claude / REGISTRY_FILE[kind])
    collection = COLLECTION[kind]
    repos = registry.get("repos") or {}
    out = {}
    for name, entry, repo_key in registry_entries(registry, collection):
        out[name] = Artifact(
            name=name,
            type=kind,
            groups=tuple(entry.get("groups") or ()),
            dependencies=tuple(entry.get("dependencies") or ()),
            dependency_only=bool(entry.get("dependency_only")),
            source=claude / collection / f"{name}{SUFFIX[kind]}",
            origin=repo_key or "local",
            upstream_repo=repo_key,
            upstream_path=entry.get("upstream_path") if repo_key else None,
            upstream_branch=(repos.get(repo_key) or {}).get("branch") if repo_key else None,
            updated_at=entry.get("updated_at"),
        )
    return out


def _from_plugins(claude):
    out = {}
    root = claude / "plugins"
    if not root.is_dir():
        return out
    for directory in sorted(root.iterdir()):
        manifest = directory / PLUGIN_MANIFEST
        if not manifest.is_file():
            continue
        data = _read_json(manifest)
        # A plugin bundles only what it owns. A skill vendored from upstream stays
        # under skills/ and is named here, so `update` keeps syncing it by
        # upstream_path instead of it forking inside a plugin.
        out[directory.name] = Artifact(
            name=directory.name,
            type=PLUGIN,
            groups=tuple(data.get("groups") or ()),
            dependencies=tuple(data.get(PLUGIN_DEPS_KEY) or ()),
            source=directory,
            origin="local",
            manifest_keys=tuple(data.keys()),
        )
    return out


def build_catalog(claude):
    """Every artifact, keyed by (type, name).

    Keyed by pair rather than by name alone: because --type is always explicit,
    the three namespaces are allowed to overlap, and collapsing them would let
    one type silently shadow another.
    """
    catalog = {}
    for kind in (SKILL, AGENT):
        for name, art in _from_registry(claude, kind).items():
            catalog[(kind, name)] = art
    for name, art in _from_plugins(claude).items():
        catalog[(PLUGIN, name)] = art
    return catalog


def get(catalog, kind, name):
    return catalog.get((kind, name))


def of_type(catalog, kind):
    """Every artifact of one type, name-ordered."""
    return [art for (t, _), art in sorted(catalog.items()) if t == kind]


def skills(catalog):
    """Name-keyed skills. Every dependency edge names a skill, so resolvers want
    this view rather than the pair-keyed catalog."""
    return {art.name: art for (t, _), art in catalog.items() if t == SKILL}


def visible(catalog, kind):
    """Artifacts of `kind` that can be named directly, name-ordered.

    A dependency-only skill installs with whichever skill needs it and refuses to be
    added by name, so every surface that offers a choice starts here.
    """
    return [art for art in of_type(catalog, kind) if not art.dependency_only]


def in_group(catalog, kind, tag):
    """Visible artifacts of `kind` carrying `tag`, name-ordered.

    The tag is opaque: exact membership, no case folding and no normalisation, since
    the vocabulary is whatever the registries say and one tag has a space in it. A
    tag nothing carries is an empty list, which each caller reads its own way.
    """
    return [art for art in visible(catalog, kind) if tag in art.groups]


def duplicate_names(catalog):
    """Names used by more than one type, as {name: [types]}.

    Legal now that --type disambiguates, so doctor reports these as information
    rather than an error.
    """
    seen = {}
    for (kind, name) in catalog:
        seen.setdefault(name, []).append(kind)
    return {n: sorted(k) for n, k in seen.items() if len(k) > 1}
