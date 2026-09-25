"""harness-build: write every harness's rendered files, or report where they drifted."""

import argparse
import json

from harnessgen import emit_claude, emit_pi, manifest, merge


def whole_file_text(document):
    return json.dumps(document, indent=2) + "\n"


def settings_text(settings):
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def drift(policy):
    """Each file or owned key whose content no longer matches the policy, as `path` or `path: key`."""
    found = []
    for relative, document in emit_pi.files(policy).items():
        path = policy.root / relative
        if not path.is_file() or json.loads(path.read_text()) != document:
            found.append(relative)
    settings = json.loads((policy.root / emit_claude.SETTINGS).read_text())
    for key, value in emit_claude.owned(policy).items():
        if merge.get(settings, key) != value:
            found.append(f"{emit_claude.SETTINGS}: {key}")
    return found


def check(root=None):
    return drift(manifest.load(root))


def build(root=None):
    """Write whatever differs and return the relative paths written.

    A file that already matches is left alone, so a build with nothing to do never
    touches Claude's settings, which a running session also writes.
    """
    policy = manifest.load(root)
    written = []
    for relative, document in emit_pi.files(policy).items():
        path = policy.root / relative
        text = whole_file_text(document)
        if not path.is_file() or path.read_text() != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            written.append(relative)

    path = policy.root / emit_claude.SETTINGS
    current = path.read_text()
    settings = json.loads(current)
    for key, value in emit_claude.owned(policy).items():
        merge.put(settings, key, value)
    if settings_text(settings) != current:
        path.write_text(settings_text(settings))
        written.append(emit_claude.SETTINGS)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(prog="harness-build", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_command = commands.add_parser("build", help="render every harness's files from policy/")
    build_command.add_argument("--check", action="store_true", help="write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    if args.check:
        drifted = check()
        for entry in drifted:
            print(f"drifted: {entry}")
        print(f"{len(drifted)} drifted" if drifted else "up to date")
        return 1 if drifted else 0

    written = build()
    for relative in written:
        print(f"wrote: {relative}")
    print(f"{len(written)} written" if written else "up to date")
    return 0
