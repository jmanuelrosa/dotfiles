"""What a project is made of, as group tags with the evidence for each.

`scout` reads the catalogue from the project's end. Every other command starts
from a name; this one starts from a directory and asks which tags it earns, then
offers the artifacts carrying them.

Every rule here is a heuristic over files, so a tag never travels alone: it is
paired with the evidence string that produced it, and the report prints that
verbatim. A recommendation nobody can check is one nobody should act on.

Two grades of evidence, and the difference is what splits the report in two:

    direct     something in the project says so — a declared dependency, a marker
               file, or the absence of one where its presence is the norm.
    implied    a neighbour of a direct hit. Plausible, never asserted.

Probing is deliberately narrow. package.json, the Swift markers and the desktop
markers are read because the registries carry artifacts for those ecosystems;
Cargo.toml, go.mod and pyproject.toml are read by nothing here, because a hit there
implies nothing installable and would only add noise the reader has to discount.
A stack the catalogue does not cover falls through to `fallback` instead.

Pure apart from reading the project directory. Nothing here touches the registry:
tags are matched as opaque strings, so retagging the catalogue needs no edit here.
"""

import json
import os
import re

# Tags a large part of the catalogue carries. Matching on them ranks everything as
# relevant, which says exactly as much as ranking nothing.
#
# `observability` is here for that reason and not because it is vague: fourteen of the
# fifteen seat plugins carry it as boilerplate, so one @sentry/* dependency used to
# make the data, design and gtm seats strong matches for a React API. The
# discriminating tag over the same territory is `sentry`, which only the artifacts
# actually about it carry.
#
# rank() exempts whatever `--focus` names, so asking for a broad tag still works.
BROAD_TAGS = frozenset({"engineering", "global", "observability"})

# Tags naming a specific framework, library or platform. A skill carrying one is
# only ever relevant if the project actually uses it, which is what keeps an Astro
# or Apollo skill out of a plain React project's report. Persona tags like
# `frontend` are shared by every framework's artifacts, so without this rule one
# implied `frontend` hit drags in the whole front-end shelf.
#
# This is a *gate*, and rank() satisfies it from `direct` alone, so membership here
# carries an obligation: a tag in this set that read() cannot produce as direct
# evidence silently hides every artifact carrying it, in every project, for ever.
# Nothing reports that; the artifact simply never appears.
#
# Two consequences worth keeping in mind when editing the tables below.
#   - An IMPLIED_TAGS entry pointing at a member of this set is inert. `node` used to
#     reach a Fastify project only that way, so `node` and `nodejs-backend-patterns`
#     were invisible there while a NestJS project got both, purely because @nestjs/
#     happens to emit `node` directly.
#   - A tag naming a technology no probe can detect does not belong here at all. It
#     is not a gate we can honour, so it can only ever subtract.
# test_scout.py's G1 and G2 assert both halves of this.
TECH_TAGS = frozenset(
    {
        "apollo",
        "astro",
        "database",
        "desktop",
        "electron",
        "expo",
        "fastify",
        "graphql",
        "hono",
        "ios",
        "mobile",
        "nestjs",
        "node",
        "playwright",
        "prisma",
        "react",
        "react-native",
        "react-router",
        "sentry",
        "swift",
        "tailwind",
        "tanstack",
        "tauri",
        "typescript",
    }
)

# Dependency name to tag, for the ecosystems the catalogue actually has artifacts
# for. An entry that maps to a tag nothing carries is harmless but pointless.
# A dependency names its own technology *and* the platform that technology implies,
# because both are facts about the project rather than guesses. Expo is React Native,
# Fastify is Node: putting those in IMPLIED_TAGS instead looked tidier and was wrong,
# since a gate tag reached only by implication can never satisfy the gate.
DEP_TAGS = {
    "react": ("react",),
    "react-dom": ("react",),
    "react-native": ("react-native", "mobile"),
    "react-router": ("react-router",),
    "react-router-dom": ("react-router",),
    "expo": ("expo", "mobile"),
    "astro": ("astro",),
    "tailwindcss": ("tailwind",),
    "typescript": ("typescript",),
    "graphql": ("graphql",),
    "fastify": ("fastify", "node"),
    "hono": ("hono", "node"),
    "prisma": ("prisma", "database"),
    "playwright": ("playwright", "testing"),
    "vitest": ("testing",),
    "jest": ("testing",),
    "electron": ("electron", "desktop"),
    "electron-builder": ("electron", "desktop"),
}

# Scoped families, matched by prefix so a new member of one needs no entry.
DEP_PREFIX_TAGS = {
    "@nestjs/": ("nestjs", "node"),
    "@apollo/": ("apollo", "graphql"),
    "@prisma/": ("prisma", "database"),
    "@playwright/": ("playwright", "testing"),
    "@tanstack/": ("tanstack",),
    "@sentry/": ("sentry", "observability"),
    "@expo/": ("expo", "mobile"),
    "@electron/": ("electron", "desktop"),
    "@tauri-apps/": ("tauri", "desktop"),
}

# A direct hit makes its neighbours plausible, which is the whole of the second
# tier: these are the tags scout is willing to guess at, and nothing else.
#
# Every value here should be a *persona* or *topic* tag. A TECH_TAGS member in this
# position is inert, because rank() only ever satisfies the gate from direct evidence,
# so stating `fastify implies node` here achieved nothing at all. Where the
# implication is a fact rather than a guess it now lives in DEP_TAGS; where it is a
# guess about a technology, it cannot be expressed and should not be.
IMPLIED_TAGS = {
    "react": ("frontend", "ui"),
    "react-router": ("frontend",),
    "tanstack": ("frontend",),
    "astro": ("frontend",),
    "tailwind": ("frontend", "designer", "design", "ui"),
    "nestjs": ("backend",),
    "fastify": ("backend",),
    "hono": ("backend",),
    "graphql": ("backend", "frontend"),
    "database": ("backend",),
    "electron": ("frontend", "ui"),
    "tauri": ("frontend", "ui"),
    "sentry": ("observability", "devops"),
    "playwright": ("testing",),
    "ci": ("devops",),
}

# Read only when nothing in the project maps to a tech tag, so a Rust, Go, Python
# or Ruby codebase still gets an answer rather than an empty report.
AGNOSTIC_TAGS = (
    "workflow",
    "review",
    "testing",
    "git",
    "planning",
    "productivity",
    "documentation",
    "refactoring",
)

# Evidence of absence. Real evidence, and it ranks strongly, but it says nothing
# about which ecosystem this is — so it does not count towards "the catalogue
# covers this stack" and never suppresses the fallback above.
GAP_TAGS = frozenset({"testing", "ci", "documentation"})

# A coarse stand-in for reading a project's prose. It recovers the common cases and
# nothing subtler: a script cannot infer intent, it can only match words.
INTENT_KEYWORDS = {
    "domain-driven": ("architecture",),
    "domain model": ("architecture",),
    "ddd": ("architecture",),
    "tdd": ("testing",),
    "test-driven": ("testing",),
    "adr": ("documentation",),
}

INTENT_FILES = ("CLAUDE.md", "README.md")

SWIFT_FILES = ("Package.swift", "Podfile")
SWIFT_GLOBS = ("*.xcodeproj", "*.xcworkspace")
# Named rather than inlined at the call site so the set of tags read() can produce is
# derivable from these tables alone, which is what lets test_scout.py check the
# TECH_TAGS obligation without restating the emitters and drifting from them.
#
# `mobile` is asserted here rather than implied from `swift`, for the same reason Expo
# names it: implying a gate tag achieves nothing, and it was costing every Swift
# project the `mobile` seat. It claims no more than the `ios` beside it already does.
SWIFT_TAGS = ("swift", "ios", "mobile")

# A Tauri app is Rust-first, so package.json can be absent entirely and the @tauri-apps/
# prefix above never fires. The directory is the marker the CLI itself scaffolds.
TAURI_DIR = "src-tauri"
TAURI_TAGS = ("tauri", "desktop")

# Read out of the pbxproj because nothing cheaper distinguishes a Mac app from an iPhone
# app: both carry an .xcodeproj and Package.swift, so SWIFT_TAGS alone hands every Mac
# app to the mobile seat. Additive on purpose, since a project can ship both targets.
PBXPROJ = "project.pbxproj"
MACOS_SDKROOT = "SDKROOT = macosx"
MACOS_TAGS = ("swift", "desktop")

TEST_DIRS = ("tests", "test", "__tests__", "spec")
TEST_FILE = re.compile(r"\.(test|spec)\.[jt]sx?$|Tests?\.swift$|^test_.+\.py$")
# Pruned from the test-file walk: a dependency's own tests say nothing about
# whether *this* project is tested, and node_modules alone makes the walk unbounded.
NOISE_DIRS = frozenset({"node_modules", "dist", "build", "vendor", "target", ".git"})

MANIFEST = "package.json"
# npm ranges are noise in an evidence string; the version is there to be recognised,
# not to be resolved.
RANGE_CHARS = "^~>=< "


def _read_json(path):
    """The parsed object, or {} for anything this cannot use.

    A manifest is a mapping by definition, so valid JSON of any other shape is as
    useless here as invalid JSON and is treated the same way. Catching only ValueError
    left `[]`, `null`, a bare string and a bare number to reach .get() in _declared and
    raise, which turned a junk package.json into a traceback instead of a scout run
    that finds nothing in it.
    """
    try:
        data = json.loads(path.read_text(errors="replace"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _mentions(path, needle):
    """Whether a readable text file contains needle, False for anything unreadable.

    A missing or unreadable file is simply not evidence, the same way a malformed
    package.json is not: probing must never turn a junk checkout into a traceback.
    """
    try:
        return needle in path.read_text(errors="replace")
    except OSError:
        return False


def _declared(project):
    """Every dependency package.json declares, runtime and dev together.

    devDependencies count: a project's test runner and its type checker live there,
    and they are exactly the facts scout wants.
    """
    package = _read_json(project / MANIFEST) if (project / MANIFEST).is_file() else {}
    return {
        **(package.get("dependencies") or {}),
        **(package.get("devDependencies") or {}),
    }


def has_tests(project):
    """Whether anything in the project looks like a test.

    Directory first, since that answers most projects without a walk. The walk
    stops at the first hit and prunes NOISE_DIRS and dotfiles, so the cost is
    bounded by how far it has to look rather than by the size of the checkout.
    """
    if any((project / name).is_dir() for name in TEST_DIRS):
        return True
    for _, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in NOISE_DIRS and not d.startswith(".")]
        if any(TEST_FILE.search(name) for name in files):
            return True
    return False


def read(project):
    """Tags with direct evidence in the project, as {tag: evidence}.

    First evidence for a tag wins, so the reason printed is the most specific one
    found rather than the last one checked.
    """
    direct = {}

    def note(tags, evidence):
        for tag in tags:
            direct.setdefault(tag, evidence)

    declared = _declared(project)
    for name in sorted(declared):
        version = str(declared[name]).lstrip(RANGE_CHARS)
        evidence = f"{name}@{version} in {MANIFEST}"
        if name in DEP_TAGS:
            note(DEP_TAGS[name], evidence)
        for prefix, tags in DEP_PREFIX_TAGS.items():
            if name.startswith(prefix):
                note(tags, evidence)

    markers = [name for name in SWIFT_FILES if (project / name).is_file()]
    projects = sorted(path for pattern in SWIFT_GLOBS for path in project.glob(pattern))
    markers += [path.name for path in projects]
    if markers:
        note(SWIFT_TAGS, f"{markers[0]} in the project root")
    for bundle in projects:
        if _mentions(bundle / PBXPROJ, MACOS_SDKROOT):
            note(MACOS_TAGS, f"{bundle.name} declares a macOS SDK target")
            break

    if (project / TAURI_DIR).is_dir():
        note(TAURI_TAGS, f"{TAURI_DIR}/ in the project root")

    # Absence, which is evidence too. Each of these is a gap an artifact fills, so
    # a project without tests wants a testing skill more than a tested one does.
    if not has_tests(project):
        note(("testing",), "no test directory and no test files")
    if not (project / ".github" / "workflows").is_dir():
        note(("ci",), "no .github/workflows")
    if not (project / "docs").is_dir():
        note(("documentation",), "no docs/ directory")

    for filename in INTENT_FILES:
        document = project / filename
        if not document.is_file():
            continue
        try:
            text = document.read_text(errors="replace").lower()
        except OSError:
            continue
        for keyword, tags in INTENT_KEYWORDS.items():
            if keyword in text:
                note(tags, f"{filename} mentions '{keyword}'")

    return direct


def implied(direct):
    """Neighbours of the directly-evidenced tags, minus anything already direct.

    A tag that has direct evidence must never be downgraded by also being implied,
    which is why this subtracts rather than merging.
    """
    indirect = {}
    for tag, evidence in direct.items():
        for neighbour in IMPLIED_TAGS.get(tag, ()):
            if neighbour not in direct:
                indirect.setdefault(neighbour, f"implied by {tag} ({evidence})")
    return indirect


def covered(direct):
    """Whether any direct evidence identifies the stack.

    The gap tags are excluded because every project earns some of them and none of
    them names an ecosystem. Without that subtraction a Rust repo with no tests
    would read as covered and never reach the fallback.
    """
    return bool(set(direct) - GAP_TAGS)


def fallback(direct):
    """Stack-agnostic tags to consider when the catalogue does not cover the stack.

    Guesses rather than evidence, so the caller folds these into the *implied* map:
    inflating them to strong matches would make every unrecognised project look
    like a confident recommendation.
    """
    return {
        tag: f"no catalogue tech detected, {tag} is stack-agnostic"
        for tag in AGNOSTIC_TAGS
        if tag not in direct
    }
