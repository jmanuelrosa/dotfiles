"""Drift checks, as pure functions returning findings.

Each check takes already-loaded data and returns a list of Finding. Keeping them
free of I/O is what lets `doctor` be tested on literal catalogs rather than by
constructing a broken repo on disk.

Severity matters here. PROBLEM means something is actually wrong; NOTE means the
situation is legal but worth seeing. Overlapping names across types is the case
that has to be a NOTE: explicit --type makes it harmless, and reporting it as a
failure would train the reader to ignore doctor.
"""

from dataclasses import dataclass

from . import catalog as cat
from . import frontmatter, pi, scope, state, workspace

PROBLEM = "problem"
NOTE = "note"


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    subject: str
    detail: str
    # Which artifact type this concerns, so `doctor --type X` can narrow without
    # matching on message text. None means it spans types and cannot be narrowed.
    kind: str = None

    @property
    def is_problem(self):
        return self.severity == PROBLEM


def missing_sources(catalog):
    """G2: a registry entry whose artifact is not on disk."""
    return [
        Finding(
            "missing-source",
            PROBLEM,
            f"{art.type} '{art.name}'",
            f"registered but absent from {art.source}",
            art.type,
        )
        for art in sorted(catalog.values(), key=lambda a: (a.type, a.name))
        if art.source is not None and not art.source.exists()
    ]


def untracked_on_disk(catalog, claude):
    """G3: an artifact directory or file on disk that no registry mentions.

    Plugins are exempt: their manifest *is* their registration, so a plugin
    directory can never be untracked.
    """
    findings = []
    for kind in (cat.SKILL, cat.AGENT):
        want_suffix = cat.SUFFIX[kind]
        directory = claude / cat.STORE[kind]
        if not directory.is_dir():
            continue
        known = {art.name for art in cat.of_type(catalog, kind)}
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith("."):
                continue
            if want_suffix and not entry.name.endswith(want_suffix):
                continue
            name = entry.name[: -len(want_suffix)] if want_suffix else entry.name
            if name not in known:
                findings.append(
                    Finding("untracked", PROBLEM, f"{kind} '{name}'", f"on disk at {entry} but in no registry", kind)
                )
    return findings


def dangling_dependencies(catalog):
    """G4: a dependency edge naming something that does not exist.

    Cross-type by nature: every edge names a skill, but the declaring artifact may
    be a skill, an agent or a plugin.
    """
    skills = cat.skills(catalog)
    findings = []
    for art in sorted(catalog.values(), key=lambda a: (a.type, a.name)):
        for dep in art.dependencies:
            if dep not in skills:
                key = cat.PLUGIN_DEPS_KEY if art.type == cat.PLUGIN else "dependencies"
                findings.append(
                    Finding(
                        "dangling-dependency",
                        PROBLEM,
                        f"{art.type} '{art.name}'",
                        f"{key} names '{dep}', which is not a known skill",
                    )
                )
    return findings


def orphaned_dependency_only(catalog):
    """G5: a dependency_only skill nothing declares, so it can never install."""
    needed = {dep for art in catalog.values() for dep in art.dependencies}
    return [
        Finding(
            "orphaned-dependency-only",
            PROBLEM,
            f"skill '{skill.name}'",
            "marked dependency_only but nothing depends on it, so it can never be installed",
            cat.SKILL,
        )
        for skill in cat.of_type(catalog, cat.SKILL)
        if skill.dependency_only and skill.name not in needed
    ]


def plugin_manifests(catalog):
    """G6 and G7: required keys, and the reserved-key trap.

    G7 is the highest-value check in the suite. An array of skill names under
    `dependencies` makes Claude Code register none of the plugin's agents or
    skills, while `claude plugin details` still lists them all, so the manifest
    looks healthy. Nothing else surfaces it.
    """
    findings = []
    for plugin in cat.of_type(catalog, cat.PLUGIN):
        missing = [k for k in cat.PLUGIN_REQUIRED_KEYS if k not in plugin.manifest_keys]
        if missing:
            findings.append(
                Finding(
                    "plugin-missing-keys",
                    PROBLEM,
                    f"plugin '{plugin.name}'",
                    f"manifest lacks {', '.join(missing)}",
                    cat.PLUGIN,
                )
            )
        if cat.PLUGIN_RESERVED_KEY in plugin.manifest_keys:
            findings.append(
                Finding(
                    "plugin-reserved-key",
                    PROBLEM,
                    f"plugin '{plugin.name}'",
                    f"manifest uses the reserved '{cat.PLUGIN_RESERVED_KEY}' key. Claude Code "
                    f"will register none of its artifacts while still listing them. "
                    f"Rename it to '{cat.PLUGIN_DEPS_KEY}'.",
                    cat.PLUGIN,
                )
            )
    return findings


def frontmatter_parses(catalog, kinds=(cat.SKILL, cat.AGENT)):
    """G8: malformed YAML frontmatter.

    An unquoted ": " in a description makes YAML read the value as a nested
    mapping, so the whole block fails to parse and the artifact does not load.

    Validated by `frontmatter`, which scans the dialect these artifacts write
    rather than parsing YAML in general, so the check runs on a machine with only
    python3 instead of reporting that it did not run. It reports a subset of what
    a real parser would; that module is where the subset is described.
    """
    findings = []
    for kind in kinds:
        for art in cat.of_type(catalog, kind):
            path = art.source if kind == cat.AGENT else art.source / "SKILL.md"
            if not path.is_file():
                continue
            try:
                parsed = frontmatter.keys(path.read_text())
            except frontmatter.Malformed as exc:
                findings.append(
                    Finding("bad-frontmatter", PROBLEM, f"{kind} '{art.name}'", f"{path}: {exc}", kind)
                )
                continue
            if parsed is None:
                findings.append(
                    Finding("bad-frontmatter", PROBLEM, f"{kind} '{art.name}'", f"{path}: no frontmatter block", kind)
                )
            elif "name" not in parsed:
                findings.append(
                    Finding(
                        "bad-frontmatter",
                        PROBLEM,
                        f"{kind} '{art.name}'",
                        f"{path}: frontmatter has no name",
                        kind,
                    )
                )
    return findings


def name_overlaps(catalog):
    """G9: one name used by more than one type. A NOTE, not a problem.

    Legal since --type is always explicit. Reported so an overlap is a visible
    decision rather than a surprise.
    """
    return [
        Finding(
            "name-overlap",
            NOTE,
            f"'{name}'",
            f"used by {' and '.join(kinds)}; commands need --type to pick one",
        )
        for name, kinds in sorted(cat.duplicate_names(catalog).items())
    ]


def broken_links(claude, home, project):
    """G1: a symlink under either .claude that no longer resolves.

    Deliberately type-agnostic. A broken link cannot always be classified, and one
    pointing outside our store still needs reporting, so this walks the leaves
    rather than asking per type.
    """
    findings = []
    for label, root in (("~/.claude", home), ("the project", project)):
        if root is None:
            continue
        for leaf, name, path in scope.all_links(root):
            if not path.exists():
                findings.append(
                    Finding("broken-link", PROBLEM, f"{name} in {label}", f"{path} points nowhere", None)
                )
    return findings


def wrong_scope(catalog, effective, home, project, claude):
    """G10 and G11.

    G10 is a problem: a global-tagged artifact linked inside a project belongs in
    ~/.claude, and its presence in a project means it is missing everywhere else.

    G11 is only a note: an untagged artifact in ~/.claude is exactly what --global
    produces. With no pin file there is nothing further to verify, and flagging it
    would fire on every deliberate override.
    """
    findings = []
    for kind in (cat.SKILL, cat.AGENT, cat.PLUGIN):
        for name in scope.installed_names(project, kind, claude):
            art = cat.get(catalog, kind, name)
            if art is not None and scope.belongs_global(art, effective):
                findings.append(
                    Finding(
                        "wrong-scope",
                        PROBLEM,
                        f"{kind} '{name}'",
                        "is global but linked in this project; it belongs in ~/.claude",
                        kind,
                    )
                )
        for name in scope.installed_names(home, kind, claude):
            art = cat.get(catalog, kind, name)
            if art is not None and not scope.belongs_global(art, effective):
                findings.append(
                    Finding(
                        "global-override",
                        NOTE,
                        f"{kind} '{name}'",
                        "is in ~/.claude without the global tag, so it was added with --global",
                        kind,
                    )
                )
    return findings


def untrusted_workspace(config, project, claude):
    """G18: a plugin is linked here but Claude Code will not load it.

    The one check about Claude Code's own configuration rather than ours, and it earns
    its place because the failure is completely silent: the link is correct, `add`
    reported success, `claude plugin details` still lists the bundle's agents, and none
    of them register. That cost a full debugging session once.

    Gated on a plugin actually being linked. Trust is Claude Code's business until
    something claude-kit installed depends on it, and a project with no plugins would
    otherwise collect a problem it has no reason to act on, which is how a report earns
    being skipped.
    """
    if project is None:
        return []
    if not scope.installed_names(project, cat.PLUGIN, claude):
        return []
    key = workspace.key_for(project)
    if workspace.granted_by(config, key, project) is not None:
        return []
    return [
        Finding(
            "untrusted-workspace",
            PROBLEM,
            f"workspace {key}",
            "has plugins linked but is not trusted, so none of them load. "
            "Run: claude-kit trust --on",
            cat.PLUGIN,
        )
    ]


def pi_skills_unreachable(project):
    """G19: this project's skills are linked, but pi cannot see them.

    The same shape of failure as G18 and it earns its place for the same reason: nothing
    reports it. Pi reads `.agents/skills/`, never `.claude/`, so without the link every
    `/skill:` in the project is simply absent, with no warning at either end. `add`
    converges the link itself, so this fires for a project set up before that existed,
    one whose link was deleted by hand, or one where something else already occupies
    the path.

    A note rather than a problem: nothing about Claude Code is broken, and a machine
    that does not use pi has nothing to act on.
    """
    if project is None or not pi.wanted(project):
        return []
    if pi.is_ours(project):
        return []
    link = pi.link_path(project)
    detail = (
        f"{link} exists but is not the link to {pi.source_path(project)}, so pi reads "
        f"something else here"
        if link.is_symlink() or link.exists()
        else f"pi reads {link}, which is missing, so none of them load in pi. "
        f"Run: claude-kit add or claude-kit restore"
    )
    return [Finding("pi-unreachable", NOTE, "this project's skills", detail, cat.SKILL)]


def pi_agents_unreachable(project):
    """G20: this project's plugin agents are installed, but pi cannot see them.

    G19 one directory over, and it needs its own check because the two halves of pi's
    view are converged separately and fail separately. Skills reach pi through a single
    directory link, so one answer covers all of them; agents cannot, because a seat keeps
    its agent inside its own plugin and no single directory holds them all. `add` and
    `remove` therefore write per-file links, and report what they did at the moment they
    do it and never again.

    That is the gap. A link pruned by hand, a `.agents/agents` path occupied by something
    else, or a project set up before those links existed all leave the pi-subagents
    extension discovering nothing, while `claude-kit list` still shows every plugin
    installed and Claude Code loads them normally.

    A note rather than a problem, for G19's reason: nothing about Claude Code is broken,
    and a machine that does not use pi has nothing to act on. Silent when the project has
    no plugins, since there is then no agent for pi to be missing.
    """
    if project is None:
        return []
    wanted = pi.desired_agents(project)
    if not wanted:
        return []
    path = pi.agents_path(project)
    if path.exists() and not path.is_dir():
        return [
            Finding(
                "pi-agents-unreachable",
                NOTE,
                "this project's plugin agents",
                f"{path} exists and is not a directory, so pi reads no agents here. "
                f"Move it aside, then run: claude-kit add or claude-kit restore",
                cat.PLUGIN,
            )
        ]
    missing = sorted(name for name in wanted if not scope.links_to(path / name, wanted[name]))
    if not missing:
        return []
    return [
        Finding(
            "pi-agents-unreachable",
            NOTE,
            "this project's plugin agents",
            f"pi reads {path}, where {len(missing)} of {len(wanted)} agent link(s) "
            f"are missing ({', '.join(missing)}), so those never load in pi. "
            f"Run: claude-kit add or claude-kit restore",
            cat.PLUGIN,
        )
    ]


def provenance_drift(catalog, provenance, project, claude):
    """G12, G13 and G14: the state file against what is actually linked."""
    if project is None:
        return []
    findings = []
    installed = scope.installed_pairs(project, claude)

    for (kind, name) in sorted(provenance):
        if (kind, name) not in installed:
            findings.append(
                Finding(
                    "stale-provenance",
                    PROBLEM,
                    f"{kind} '{name}'",
                    "recorded in claude-kit.json but not linked. Run: claude-kit restore",
                    kind,
                )
            )

    for (kind, name) in sorted(installed):
        if (kind, name) not in provenance:
            findings.append(
                Finding(
                    "untracked-install",
                    NOTE,
                    f"{kind} '{name}'",
                    "linked but not recorded, so the cascade will keep it rather than guess. "
                    "Run: claude-kit adopt",
                    kind,
                )
            )

    # G14: the safety valve. D10 and D14 both err toward keeping things, so
    # without this a project accumulates dependencies nothing needs and no command
    # ever mentions them.
    declared = set()
    for (kind, name) in installed:
        art = cat.get(catalog, kind, name)
        if art is not None:
            declared.update(art.dependencies)
    for (kind, name) in sorted(installed):
        if kind != cat.SKILL or name in declared:
            continue
        reason = provenance.get((kind, name))
        if reason is not None and not state.is_direct(reason):
            findings.append(
                Finding(
                    "removable",
                    NOTE,
                    f"skill '{name}'",
                    f"installed for {state.parent_of(reason)}, which nothing installed needs now. "
                    f"Remove with: claude-kit remove {name} --type skill",
                    cat.SKILL,
                )
            )
    return findings
