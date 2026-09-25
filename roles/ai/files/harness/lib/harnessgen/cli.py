"""harness-build: write every harness's rendered files, or report where they drifted."""

import argparse
import json
import shutil
import tomllib
from pathlib import Path

from harnessgen import emit_claude, emit_codex, emit_pi, manifest, merge, tomlw

WHOLE_FILE_EMITTERS = (emit_pi, emit_codex)
REPORTING_EMITTERS = (emit_codex,)
BACKUP_SUFFIX = ".harness-bak"


def whole_file_text(document):
    return document if isinstance(document, str) else json.dumps(document, indent=2) + "\n"


def settings_text(settings):
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def whole_files(policy):
    return {relative: doc for emitter in WHOLE_FILE_EMITTERS for relative, doc in emitter.files(policy).items()}


def matches(path, document):
    """A JSON file matches by content, so a reformat is not drift; anything else by text."""
    if not path.is_file():
        return False
    if isinstance(document, str):
        return path.read_text() == document
    return json.loads(path.read_text()) == document


def drift(policy):
    """Each file or owned key whose content no longer matches the policy, as `path` or `path: key`."""
    found = [relative for relative, document in whole_files(policy).items()
             if not matches(policy.root / relative, document)]
    settings = json.loads((policy.root / emit_claude.SETTINGS).read_text())
    found += [f"{emit_claude.SETTINGS}: {key}" for key in emit_claude.drifted(settings, policy)]
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
    for relative, document in whole_files(policy).items():
        path = policy.root / relative
        if not matches(path, document):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(whole_file_text(document))
            written.append(relative)

    path = policy.root / emit_claude.SETTINGS
    current = path.read_text()
    settings = emit_claude.apply(json.loads(current), policy)
    if settings_text(settings) != current:
        path.write_text(settings_text(settings))
        written.append(emit_claude.SETTINGS)
    return written


def apply_codex(root=None, check_only=False):
    """Merge the owned keys into Codex's config.toml and install its rules file.

    Returns what differed, as `config: key` or the rules path. Codex writes its config
    itself, so only the owned keys are compared, by value; the rules file is ours whole.
    The first write keeps the untouched file beside it, once.
    """
    policy = manifest.load(root)
    install = policy.adapter(emit_codex.NAME)["install"]
    config_path = Path(install["config"]).expanduser()
    rules_path = Path(install["rules"]).expanduser()

    config = tomllib.loads(config_path.read_text()) if config_path.is_file() else {}
    changes = [f"config: {key}" for key, value in emit_codex.owned(policy).items()
               if merge.get(config, key) != value]
    rules = emit_codex.rules(policy)
    if not matches(rules_path, rules):
        changes.append(install["rules"])
    if check_only or not changes:
        return changes

    if any(change.startswith("config: ") for change in changes):
        backup = config_path.with_name(config_path.name + BACKUP_SUFFIX)
        if config_path.is_file() and not backup.exists():
            shutil.copy2(config_path, backup)
        for key, value in emit_codex.owned(policy).items():
            merge.put(config, key, value)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch(mode=0o600, exist_ok=True)
        config_path.write_text(tomlw.dumps(config))
    if install["rules"] in changes:
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(rules)
    return changes


def report(root=None):
    policy = manifest.load(root)
    return {emitter.NAME: emitter.untranslatable(policy) for emitter in REPORTING_EMITTERS}


def summary(entries, verb, done):
    return f"{len(entries)} {verb}" if entries else done


def main(argv=None):
    parser = argparse.ArgumentParser(prog="harness-build", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_command = commands.add_parser("build", help="render every harness's files from policy/")
    build_command.add_argument("--check", action="store_true", help="write nothing; exit 1 on drift")
    apply_command = commands.add_parser("apply", help="merge the policy into a harness's own config")
    apply_command.add_argument("harness", choices=[emit_codex.NAME])
    apply_command.add_argument("--check", action="store_true", help="write nothing; exit 1 on changes")
    commands.add_parser("report", help="list the policy rules each harness cannot carry")
    args = parser.parse_args(argv)

    if args.command == "report":
        for harness, rules in report().items():
            print(f"{harness}: {len(rules)} untranslatable")
            for entry in rules:
                print(f"  {entry}")
        return 0

    if args.command == "apply":
        changes = apply_codex(check_only=args.check)
        for entry in changes:
            print(f"{'pending' if args.check else 'changed'}: {entry}")
        print(summary(changes, "changes", "up to date"))
        return 1 if args.check and changes else 0

    if args.check:
        drifted = check()
        for entry in drifted:
            print(f"drifted: {entry}")
        print(summary(drifted, "drifted", "up to date"))
        return 1 if drifted else 0

    written = build()
    for relative in written:
        print(f"wrote: {relative}")
    print(summary(written, "written", "up to date"))
    return 0
