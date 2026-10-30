#!/usr/bin/env python3
"""diagrams.py - find, check, lint and re-anchor the diagrams a repo's docs carry.

A diagram is a block in a Markdown file fenced by two HTML comments:

    <!-- diagram name=auth-flow kind=explanation sha=1a2b3c4 paths=src/auth/**,src/session.ts -->
    ```mermaid
    ...
    ```
    <!-- /diagram -->

or, for draw.io, the same markers around the exported image of a `.drawio` source:

    <!-- diagram name=auth-flow kind=explanation sha=1a2b3c4 paths=src/auth/** -->
    ![Auth flow](diagrams/auth-flow.drawio.svg)
    <!-- /diagram -->

`sha` is the commit the diagram was last verified against and `paths` are the
files it rests on, as git pathspecs relative to the repo root. `scan` names
every diagram and whether the anchored paths changed since `sha` (or since a
base ref, for a branch about to ship); `--lint` also checks that each Mermaid
block parses and each draw.io source and export exist and are readable.
`stamp` rewrites `sha` to the current HEAD after a diagram was redrawn or
confirmed current.

Self-contained on purpose: the skill is installed as a symlink into a global
skills root, far from any shared python package.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from xml.etree import ElementTree

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_A_REPO = 2
EXIT_STALE = 3
EXIT_LINT = 4

RUN_TIMEOUT = 60
LINT_OUTPUT_LINES = 20
LINTER = ("bunx", "@probelabs/maid@0.0.29", "-")
MAID_EXIT_DIAGNOSTICS = 1

OPEN_MARKER = re.compile(r"<!--\s*diagram\s+(?P<attrs>[^>]*?)\s*-->")
CLOSE_MARKER = re.compile(r"<!--\s*/diagram\s*-->")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
MERMAID_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*mermaid\b")
DRAWIO_EXPORT = re.compile(r"\]\((?P<target>[^)\s]+\.drawio\.(?:svg|png))\)")
ATTR = re.compile(r"(?P<key>[a-z]+)=(?P<value>\"[^\"]*\"|\S+)")
REQUIRED_ATTRS = ("name", "kind", "sha", "paths")
KINDS = ("use-case", "explanation", "reference", "how-to", "tutorial")
DRAWIO_ROOTS = ("mxfile", "mxGraphModel")
SKIPPED_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".teammate"}

STATUS_CURRENT = "current"
STATUS_STALE = "stale"
STATUS_INVALID = "invalid"
STATUS_UNKNOWN_SHA = "unknown-sha"
FORMAT_MERMAID = "mermaid"
FORMAT_DRAWIO = "drawio"
FORMAT_UNKNOWN = "unknown"
LINT_OK = "ok"
LINT_ERROR = "error"
LINT_UNAVAILABLE = "unavailable"


@dataclass
class Diagram:
    name: str
    kind: str
    sha: str
    paths: list
    file: str
    line: int
    status: str = STATUS_CURRENT
    format: str = FORMAT_UNKNOWN
    commits: list = field(default_factory=list)
    dirty: list = field(default_factory=list)
    problem: str = ""
    lint: str = ""
    lint_output: list = field(default_factory=list)
    body: list = field(default_factory=list, repr=False)


def run_git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT,
        check=False,
    )
    return result.returncode, result.stdout.strip("\n")


def repo_root(start):
    code, out = run_git(start, "rev-parse", "--show-toplevel")
    if code != 0:
        return None
    return Path(out)


def parse_attrs(raw):
    attrs = {}
    for match in ATTR.finditer(raw):
        attrs[match.group("key")] = match.group("value").strip('"')
    return attrs


def detect_format(body):
    if any(MERMAID_FENCE.match(line) for line in body):
        return FORMAT_MERMAID
    if any(DRAWIO_EXPORT.search(line) for line in body):
        return FORMAT_DRAWIO
    return FORMAT_UNKNOWN


def parse_markers(text, file):
    diagrams = []
    open_match = None
    fence = 0
    for number, line in enumerate(text.splitlines(), start=1):
        ticks = FENCE.match(line)
        if ticks and open_match is None:
            width = len(ticks.group(1))
            if fence == 0:
                fence = width
            elif width >= fence:
                fence = 0
            continue
        if fence:
            continue
        if open_match is None:
            open_match = OPEN_MARKER.search(line)
            if open_match is None:
                continue
            attrs = parse_attrs(open_match.group("attrs"))
            missing = [key for key in REQUIRED_ATTRS if not attrs.get(key)]
            diagram = Diagram(
                name=attrs.get("name", ""),
                kind=attrs.get("kind", ""),
                sha=attrs.get("sha", ""),
                paths=[p for p in attrs.get("paths", "").split(",") if p],
                file=file,
                line=number,
            )
            if missing:
                diagram.status = STATUS_INVALID
                diagram.problem = "missing " + ", ".join(missing)
            elif diagram.kind not in KINDS:
                diagram.status = STATUS_INVALID
                diagram.problem = f"unknown kind {diagram.kind!r}"
            diagrams.append(diagram)
            continue
        if CLOSE_MARKER.search(line):
            diagrams[-1].format = detect_format(diagrams[-1].body)
            open_match = None
            continue
        diagrams[-1].body.append(line)
    if open_match is not None and diagrams:
        last = diagrams[-1]
        last.status = STATUS_INVALID
        last.problem = "no closing <!-- /diagram --> marker"
    return diagrams


def markdown_files(root):
    _, listed = run_git(
        root, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.md"
    )
    for name in sorted(filter(None, listed.split("\0"))):
        path = root / name
        if any(part in SKIPPED_DIRS for part in Path(name).parts):
            continue
        if not path.is_file():
            continue
        yield path


def collect(root):
    diagrams = []
    for path in markdown_files(root):
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        if "<!-- diagram" not in text:
            continue
        diagrams.extend(parse_markers(text, str(path.relative_to(root))))
    return diagrams


def pathspecs(paths):
    return [f":(glob){p}" if any(ch in p for ch in "*?[") else p for p in paths]


def check_since_sha(root, diagram):
    code, _ = run_git(root, "cat-file", "-e", f"{diagram.sha}^{{commit}}")
    if code != 0:
        diagram.status = STATUS_UNKNOWN_SHA
        diagram.problem = f"sha {diagram.sha} is not a commit in this repo"
        return
    _, out = run_git(
        root, "log", "--oneline", f"{diagram.sha}..HEAD", "--", *pathspecs(diagram.paths)
    )
    diagram.commits = out.splitlines()
    _, dirty = run_git(root, "status", "--porcelain", "--", *pathspecs(diagram.paths))
    diagram.dirty = [line[3:] for line in dirty.splitlines()]
    if diagram.commits or diagram.dirty:
        diagram.status = STATUS_STALE


def check_since_ref(root, diagram, ref):
    _, out = run_git(root, "diff", "--name-only", f"{ref}...HEAD", "--", *pathspecs(diagram.paths))
    diagram.commits = out.splitlines()
    _, dirty = run_git(root, "status", "--porcelain", "--", *pathspecs(diagram.paths))
    diagram.dirty = [line[3:] for line in dirty.splitlines()]
    if diagram.commits or diagram.dirty:
        diagram.status = STATUS_STALE


def mermaid_source(body):
    lines = iter(body)
    for line in lines:
        opening = MERMAID_FENCE.match(line)
        if opening:
            fence = opening.group(1)
            break
    else:
        return ""
    source = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) >= len(fence) and set(stripped) == {fence[0]}:
            break
        source.append(line)
    return "\n".join(source) + "\n"


def lint_mermaid(diagram):
    try:
        result = subprocess.run(
            LINTER,
            input=mermaid_source(diagram.body),
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return LINT_UNAVAILABLE, [f"{' '.join(LINTER)}: {error}"]
    output = (result.stdout + result.stderr).strip().splitlines()[:LINT_OUTPUT_LINES]
    if result.returncode == EXIT_OK:
        return LINT_OK, []
    if result.returncode == MAID_EXIT_DIAGNOSTICS:
        return LINT_ERROR, output
    return LINT_UNAVAILABLE, output


def drawio_problem(source):
    try:
        document = ElementTree.parse(source).getroot()
    except ElementTree.ParseError as error:
        return f"not valid XML: {error}"
    if document.tag not in DRAWIO_ROOTS:
        return f"root element is <{document.tag}>, expected <mxfile> or <mxGraphModel>"
    if any((page.text or "").strip() for page in document.iter("diagram")):
        return "compressed; save it uncompressed so it diffs"
    return ""


def lint_drawio(root, diagram):
    page_dir = (root / diagram.file).parent
    problems = []
    for line in diagram.body:
        for match in DRAWIO_EXPORT.finditer(line):
            export = (page_dir / match.group("target")).resolve()
            source = export.with_suffix("")
            shown = source.relative_to(root) if source.is_relative_to(root) else source
            if not source.is_file():
                problems.append(f"missing source {shown}")
            else:
                problem = drawio_problem(source)
                if problem:
                    problems.append(f"{shown}: {problem}")
            if not export.is_file():
                problems.append(f"missing export {match.group('target')}")
    return (LINT_ERROR, problems) if problems else (LINT_OK, [])


def lint(root, diagram):
    if diagram.format == FORMAT_MERMAID:
        return lint_mermaid(diagram)
    if diagram.format == FORMAT_DRAWIO:
        return lint_drawio(root, diagram)
    return LINT_ERROR, ["no mermaid block or .drawio.svg/.drawio.png export between the markers"]


def scan(root, since, run_lint=False, only=None):
    diagrams = collect(root)
    if only:
        diagrams = [d for d in diagrams if d.name in only]
    for diagram in diagrams:
        if diagram.status == STATUS_INVALID:
            continue
        if since:
            check_since_ref(root, diagram, since)
        else:
            check_since_sha(root, diagram)
        if run_lint:
            diagram.lint, diagram.lint_output = lint(root, diagram)
    return diagrams


def print_scan(diagrams, since, run_lint):
    print(f"DIAGRAMS={len(diagrams)}")
    if not diagrams:
        return
    print(f"STALE={sum(1 for d in diagrams if d.status == STATUS_STALE)}")
    if run_lint:
        print(f"LINT_ERRORS={sum(1 for d in diagrams if d.lint == LINT_ERROR)}")
    print(f"SINCE={since or 'anchor'}")
    for diagram in diagrams:
        print()
        print(f"== {diagram.name} ==")
        print(f"FILE={diagram.file}:{diagram.line}")
        print(f"KIND={diagram.kind}")
        print(f"FORMAT={diagram.format}")
        print(f"SHA={diagram.sha}")
        print(f"PATHS={','.join(diagram.paths)}")
        print(f"STATUS={diagram.status}")
        if diagram.problem:
            print(f"PROBLEM={diagram.problem}")
        if diagram.lint:
            print(f"LINT={diagram.lint}")
        label = "changed files" if since else "commits"
        for entry in diagram.commits:
            print(f"{label}: {entry}")
        for entry in diagram.dirty:
            print(f"working tree: {entry}")
        for entry in diagram.lint_output:
            print(f"lint: {entry}")


def stamp(root, names, everything):
    _, head = run_git(root, "rev-parse", "--short", "HEAD")
    diagrams = collect(root)
    wanted = {d.name for d in diagrams} if everything else set(names)
    unknown = sorted(wanted - {d.name for d in diagrams})
    if unknown:
        print(f"error: no diagram named {', '.join(unknown)}", file=sys.stderr)
        return EXIT_USAGE
    by_file = {}
    for diagram in diagrams:
        if diagram.name in wanted and diagram.status != STATUS_INVALID:
            by_file.setdefault(diagram.file, []).append(diagram)
    for file, entries in by_file.items():
        path = root / file
        lines = path.read_text(encoding="utf-8", errors="surrogateescape").splitlines(keepends=True)
        for diagram in entries:
            index = diagram.line - 1
            lines[index] = re.sub(r"sha=\S+", f"sha={head}", lines[index], count=1)
            print(f"STAMPED={diagram.name} sha={head} file={file}:{diagram.line}")
        path.write_text("".join(lines), encoding="utf-8", errors="surrogateescape")
    return EXIT_OK


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="any path inside the repo (default: cwd)")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_cmd = sub.add_parser("scan", help="list diagrams and whether their anchored paths changed")
    scan_cmd.add_argument(
        "--since",
        metavar="REF",
        help="compare against REF...HEAD plus the working tree instead of each diagram's sha",
    )
    scan_cmd.add_argument(
        "--lint",
        action="store_true",
        help="also parse each Mermaid block and check each draw.io source and export",
    )
    scan_cmd.add_argument(
        "--only", metavar="NAMES", help="comma-separated diagram names to limit the scan to"
    )
    scan_cmd.add_argument("--json", action="store_true", help="emit a JSON list instead of text")

    stamp_cmd = sub.add_parser("stamp", help="set sha to the current HEAD on the named diagrams")
    stamp_cmd.add_argument("names", nargs="*", help="diagram names")
    stamp_cmd.add_argument("--all", action="store_true", help="every diagram in the repo")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = repo_root(Path(args.root))
    if root is None:
        print(f"error: {args.root} is not inside a git repository", file=sys.stderr)
        return EXIT_NOT_A_REPO
    if args.command == "stamp":
        if not args.names and not args.all:
            print("error: name at least one diagram or pass --all", file=sys.stderr)
            return EXIT_USAGE
        return stamp(root, args.names, args.all)
    only = {name for name in (args.only or "").split(",") if name}
    diagrams = scan(root, args.since, args.lint, only)
    if args.json:
        print(json.dumps([{k: v for k, v in asdict(d).items() if k != "body"} for d in diagrams], indent=2))
    else:
        print_scan(diagrams, args.since, args.lint)
    if any(d.lint == LINT_ERROR for d in diagrams):
        return EXIT_LINT
    if any(d.status == STATUS_STALE for d in diagrams):
        return EXIT_STALE
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
