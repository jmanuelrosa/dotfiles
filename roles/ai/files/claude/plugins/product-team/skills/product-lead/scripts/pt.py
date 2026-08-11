#!/usr/bin/env python3
"""The Product Team pipeline's mechanical half: sequencing, checking, and the spec merge.

Three subcommands, and each replaces something a model used to spend Opus tokens on:

    pt.py status <slug>       which stage is done, ready or blocked, and the next command
    pt.py check <slug>        the Definition of Ready items a script can decide
    pt.py spec-merge <slug>   shipped requirements upserted into docs/specs/

`status` exists because a stage's position is a fact about which files are on disk, not
a table anyone has to maintain. The old STATUS.md carried an eight-row state machine that
every stage read, rewrote twice, and could disagree with reality about; what stays in that
file now is only what a file listing cannot hold, which is who decided a gate and why.

`check` exists because the two failures this pipeline actually keeps hitting are lexical.
An `L` story with no split rationale failed three initiatives in a row, and a requirement
no story claims is invisible to any amount of judgment: it is a set difference, so it
belongs here rather than in a prompt.

Both are deliberately incomplete and biased toward silence, in the same way
claude_kit/frontmatter.py is: a shape this script does not model reads as fine rather
than as broken. A false finding teaches the reader to skip the report, and the report is
worth nothing the moment that happens. What it cannot decide (is this scenario
testable, is this slice really vertical) stays with the model in `6-verify`.

An initiative written before requirements carried scenarios still passes: `check` says
which items it skipped and why instead of failing every story in an old backlog.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotkit import ui  # noqa: E402

OK = 0
FINDINGS = 1
USAGE = 2

INITIATIVES = Path("docs/initiatives")
CONFIG = Path("docs/strategy/product-team.yml")
SPECS = Path("docs/specs")

PRD = "02-prd.md"
UX_SPEC = "04-ux-spec.md"
TASKS = "05-tasks.md"
BACKLOG = "05-backlog"

# Every artifact that carries deferrals, in pipeline order. A deferral may only name a
# resolver that comes after the artifact holding it: pointing backwards or sideways is a
# hole with a label on it, since nothing will run again to close it.
DEFERRABLE = (PRD, UX_SPEC, "04-design-doc.md", TASKS)

REQUIREMENT = re.compile(r"^### (R\d+):\s*(.+?)\s*$")
SCENARIO = re.compile(r"^#### (R\d+\.S\d+)\b\s*(.*)$")
SCENARIO_ID = re.compile(r"\bR\d+\.S\d+\b")
LEGACY_REQUIREMENT = re.compile(r"^-\s+\*\*(R\d+)\*\*:")
CAPABILITY = re.compile(r"^Capability:\s*([a-z0-9-]+)\s*$")
TASK = re.compile(r"^\s*-\s+\[( |x|X)\]\s+(\d+)\.(\d+)\s+(.*)$")
UX_ANCHOR = re.compile(re.escape(UX_SPEC) + r"#([a-z0-9-]+)")
HEADING = re.compile(r"^#{2,4}\s+(.*?)\s*#*$")
STORY_FILE = re.compile(r"story-\d+\.\d+\.md")
PLACEHOLDER = re.compile(r"^(|-|n/a|na|tbd|pending|\{.*\})$", re.IGNORECASE)


class Stage:
    """One pipeline stage, complete when the files it generates are on disk.

    `alt` carries the shape an older initiative left behind: stage 5 used to produce a
    directory of stories and no task list, so an initiative that predates the task layer
    must still read as decomposed rather than as blocked forever.
    """

    def __init__(self, name, generates, requires, command, alt=(), profiles=("full", "solo"), done=None):
        self.name = name
        self.generates = generates
        self.requires = requires
        self.command = command
        self.alt = alt
        self.profiles = profiles
        self.done = done

    def state(self, root):
        """`(state, detail)` where state is done, partial, ready or blocked.

        `partial` is the state this pipeline's own history makes necessary. Two
        initiatives on disk predate `04-ux-spec.md` existing at all, so a stage judged
        only complete-or-not reported them as `ready` and told the reader to go and run
        stage 4 again, below two stages that already read done. Naming the gap says the
        true thing without inventing work.
        """
        if self.done is not None:
            return ("done", "every story carries a board issue") if self.done(root) else self._pending(root)
        present = [f for f in self.generates if _present(root / f)]
        absent = [f for f in self.generates if f not in present]
        if self.generates and not absent:
            return "done", ", ".join(present)
        if self.alt and all(_present(root / f) for f in self.alt):
            return "done", f"{', '.join(self.alt)}, and no {', '.join(absent)}: it predates that artifact"
        if present:
            return "partial", f"has {', '.join(present)}, missing {', '.join(absent)}"
        return self._pending(root)

    def _pending(self, root):
        missing = self.missing(root)
        if missing:
            return "blocked", "needs " + ", ".join(missing)
        return "ready", self.command

    def missing(self, root):
        return [f for f in self.requires if not _present(root / f)]


STAGES = (
    Stage("0-brief", ("00-brief.md",), (), "/product-team:0-refine-idea"),
    Stage("1-research", ("01-research/summary.md",), ("00-brief.md",), "/product-team:1-research"),
    Stage("2-prd", (PRD,), ("00-brief.md",), "/product-team:2-write-prd"),
    Stage("3-red-team", ("03-red-team-report.md",), (PRD,), "/product-team:3-red-team"),
    Stage("4-tech-shape", (UX_SPEC, "04-design-doc.md"), (PRD,), "/product-team:4-tech-shape"),
    Stage("5-decompose", (TASKS,), (PRD, "04-design-doc.md"), "/product-team:5-decompose", alt=(BACKLOG,)),
    Stage(
        "6-verify",
        ("06-dor-report.md",),
        (TASKS,),
        "/product-team:6-verify",
        profiles=("full",),
    ),
    Stage(
        "7-push-to-board",
        (),
        ("06-dor-report.md",),
        "/product-team:7-push-to-board",
        profiles=("full",),
        done=lambda root: _boarded(root),
    ),
)

# 8-living-spec is deliberately absent from the table above. Its trigger is ship time
# rather than a position in the pipeline, so it has no "ready" state to report: what
# `status` says instead is how many shipped requirements are missing from docs/specs/,
# which is the only form of this that cannot read done while work is outstanding.

GATES = ("Gate 0", "Gate 1")


def _present(path):
    """A file that exists, or a directory with something in it."""
    return path.is_file() or (path.is_dir() and any(path.iterdir()))


def _boarded(root):
    """Stage 7 is done when every story carries a real board issue rather than PENDING."""
    found = stories(root)
    return bool(found) and all(
        not PLACEHOLDER.match(value) and not value.upper().startswith("PENDING")
        for value in (fields(path).get("Board issue", "") for path in found)
    )


def _unmerged(root):
    """Shipped requirements whose capability spec does not exist yet.

    `docs/specs/` is repo-level while an initiative is three directories down, so the
    repo is derived rather than passed: it keeps the stage table's predicates to one
    argument, which is the initiative every other one takes.
    """
    specs = root.parents[2] / SPECS
    return sorted(
        identifier
        for identifier, requirement in shipped(root).items()
        if requirement["capability"] and not (specs / requirement["capability"] / "spec.md").exists()
    )


def _lines(path):
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []


def slug(text):
    """A GitHub-style heading anchor, which is what a Design/UX pointer names."""
    text = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[\s_]+", "-", text)


def config(repo):
    """The top-level scalars of docs/strategy/product-team.yml.

    Only column-zero `key: value` pairs, because they are all this script needs and a
    partial YAML parser that tried for more would be a second dialect to get wrong.
    `roster` and `gate_owners` are nested and are read by the stage skills, which have a
    real YAML reader in the model.
    """
    values = {}
    for line in _lines(repo / CONFIG):
        if line[:1].isspace() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.split("#")[0].strip().strip("\"'")
        if value:
            values[key.strip()] = value
    return values


def find(repo, slug_or_none):
    """The initiative directory, by name or by being the only one there."""
    root = repo / INITIATIVES
    if not root.is_dir():
        return None, f"no {INITIATIVES} in {ui.path(repo)}"
    if slug_or_none:
        target = root / slug_or_none
        return (target, None) if target.is_dir() else (None, f"no initiative {slug_or_none!r}")
    found = sorted(p for p in root.iterdir() if p.is_dir())
    if len(found) == 1:
        return found[0], None
    if not found:
        return None, "no initiatives yet"
    return None, f"name one of: {', '.join(p.name for p in found)}"


def requirements(root):
    """`{R#: {"name", "shall", "capability", "scenarios": {id: [lines]}}}` from the PRD.

    Empty for a PRD written before requirements carried scenarios; `legacy` below is how
    the caller tells that apart from a PRD with no requirements at all.
    """
    found, current, scenario = {}, None, None
    for line in _lines(root / PRD):
        heading = REQUIREMENT.match(line)
        if heading:
            current = {"id": heading.group(1), "name": heading.group(2), "shall": "", "capability": None, "scenarios": {}}
            found[heading.group(1)] = current
            scenario = None
            continue
        if current is None:
            continue
        step = SCENARIO.match(line)
        if step:
            scenario = current["scenarios"].setdefault(step.group(1), [])
            continue
        if line.startswith("#"):
            current, scenario = None, None
            continue
        if scenario is not None:
            if line.strip():
                scenario.append(line.rstrip())
            continue
        capability = CAPABILITY.match(line.strip())
        if capability:
            current["capability"] = capability.group(1)
        elif line.strip() and not current["shall"]:
            current["shall"] = line.strip()
    return found


def legacy_prd(root):
    """True when the PRD predates scenario ids but does declare requirements."""
    lines = _lines(root / PRD)
    return not any(REQUIREMENT.match(line) for line in lines) and any(
        LEGACY_REQUIREMENT.match(line) for line in lines
    )


def fields(path):
    """The `| Field | Value |` rows of an artifact's own table, as a dict."""
    values = {}
    for line in _lines(path):
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) == 2 and not set(cells[1]) <= set("- :"):
            values[cells[0]] = cells[1]
    return values


def stories(root):
    directory = root / BACKLOG
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if STORY_FILE.fullmatch(p.name))


def tasks(root):
    """`[(done, group, number, text)]` from the task list."""
    found = []
    for line in _lines(root / TASKS):
        match = TASK.match(line)
        if match:
            found.append((match.group(1).lower() == "x", match.group(2), match.group(3), match.group(4)))
    return found


def claims(root):
    """Every scenario id claimed anywhere, mapped to what claimed it."""
    claimed = {}
    for path in stories(root):
        declared = fields(path).get("Scenarios", "")
        for found in SCENARIO_ID.findall(declared):
            claimed.setdefault(found, []).append(path.name)
    for _, group, number, text in tasks(root):
        for found in SCENARIO_ID.findall(text):
            claimed.setdefault(found, []).append(f"{TASKS}:{group}.{number}")
    return claimed


def deferrals(root):
    """`[(artifact, id, question, resolver)]` from every `## Deferrals` table."""
    found = []
    for name in DEFERRABLE:
        inside = False
        for line in _lines(root / name):
            if line.startswith("## "):
                inside = line.strip().lower() == "## deferrals"
                continue
            if not inside or not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and not set("".join(cells)) <= set("- :") and cells[0].lower() != "id":
                found.append((name, cells[0], cells[1], cells[2]))
    return found


def _cycle(graph):
    """The first dependency cycle in `{story: [depends on]}`, or None."""
    state = {}

    def walk(node, trail):
        if state.get(node) == "done":
            return None
        if state.get(node) == "open":
            return trail[trail.index(node):] + [node]
        state[node] = "open"
        for neighbour in graph.get(node, ()):
            if neighbour in graph:
                found = walk(neighbour, trail + [node])
                if found:
                    return found
        state[node] = "done"
        return None

    for node in sorted(graph):
        found = walk(node, [])
        if found:
            return found
    return None


def check(root):
    """Every mechanical DoR item. Returns `(findings, skipped)`, both lists of strings."""
    findings, skipped = [], []
    defined = requirements(root)
    scenario_ids = {s for r in defined.values() for s in r["scenarios"]}

    if not defined:
        skipped.append(
            f"scenario coverage: {PRD} declares no `### R#:` requirement blocks"
            + (" (written before scenarios were requirements)" if legacy_prd(root) else "")
        )
    else:
        for requirement in defined.values():
            if not requirement["scenarios"]:
                findings.append(f"{PRD}: {requirement['id']} has no scenario, so nothing can claim or test it")
        claimed = claims(root)
        for unknown in sorted(set(claimed) - scenario_ids):
            findings.append(f"{', '.join(claimed[unknown])}: claims {unknown}, which {PRD} does not define")
        for uncovered in sorted(scenario_ids - set(claimed)):
            findings.append(f"{PRD}: {uncovered} is claimed by no story and no task")

    # Both the Design / UX pointer and the design-seat flag are copied out of the UX
    # spec, so an initiative that predates that artifact can be judged on neither. Firing
    # per story instead reported ten findings against `game-finder`, none of which named
    # anything its author could have done, which is how a report teaches its reader to
    # stop opening it.
    has_ux = _present(root / UX_SPEC)
    anchors = {slug(m.group(1)) for line in _lines(root / UX_SPEC) if (m := HEADING.match(line))}
    if not has_ux:
        skipped.append(f"Design / UX pointers and the design-seat flag: no {UX_SPEC} to judge them against")
    elif not anchors:
        skipped.append(f"Design / UX pointers: {UX_SPEC} has no headings to anchor at")
    graph = {}

    for path in stories(root):
        table = fields(path)
        name = path.name
        size = table.get("Size hint", "")
        if PLACEHOLDER.match(size):
            findings.append(f"{name}: Size hint is not set to S, M or L")
        elif size.upper() == "L" and PLACEHOLDER.match(table.get("Split rationale", "")):
            findings.append(f"{name}: size L with no split rationale")
        if has_ux and PLACEHOLDER.match(table.get("Needs design seat", "")):
            findings.append(f"{name}: Needs design seat is blank")
        depends = table.get("Depends on", "")
        if PLACEHOLDER.match(depends):
            findings.append(f"{name}: Depends on is blank; a story with none says `none`")
        graph[name] = [d for d in re.findall(r"story-\d+\.\d+\.md", depends)]

        if anchors:
            pointer = UX_ANCHOR.search(path.read_text(encoding="utf-8"))
            if not pointer:
                findings.append(f"{name}: no resolvable {UX_SPEC} pointer in its Design / UX note")
            elif pointer.group(1) not in anchors:
                findings.append(f"{name}: Design / UX pointer #{pointer.group(1)} matches no heading in {UX_SPEC}")

    cycle = _cycle(graph)
    if cycle:
        findings.append("dependency cycle: " + " -> ".join(cycle))

    order = {name: index for index, name in enumerate(DEFERRABLE)}
    for artifact, identifier, question, resolver in deferrals(root):
        target = resolver.strip("`")
        if target not in order:
            findings.append(f"{artifact}: deferral {identifier} names {target!r}, which is not a pipeline artifact")
        elif order[target] <= order[artifact]:
            findings.append(f"{artifact}: deferral {identifier} points at {target}, which does not run after it")
        elif not (root / target).exists():
            findings.append(f"{artifact}: deferral {identifier} waits on {target}, which does not exist yet")
        elif identifier not in (root / target).read_text(encoding="utf-8"):
            findings.append(f"{target}: does not close deferral {identifier} ({question})")

    if not stories(root) and not (root / TASKS).exists():
        skipped.append("story and task items: neither a backlog nor a task list exists yet")
    return findings, skipped


def shipped(root):
    """Requirements whose every claiming task is checked off, as `{R#: requirement}`."""
    done, pending = {}, {}
    for is_done, _, _, text in tasks(root):
        for identifier in SCENARIO_ID.findall(text):
            (done if is_done else pending).setdefault(identifier.split(".")[0], True)
    return {
        identifier: requirement
        for identifier, requirement in requirements(root).items()
        if identifier in done and identifier not in pending
    }


def spec_body(requirement):
    lines = [f"### Requirement: {requirement['name']}", requirement["shall"], ""]
    for identifier, steps in requirement["scenarios"].items():
        lines.append(f"#### Scenario: {identifier}")
        lines.extend(steps)
        lines.append("")
    return lines


def merge(spec_path, requirement):
    """Upsert one requirement into a capability spec, preserving everything else.

    Rewriting the whole file from the PRD was the alternative and it is wrong: a
    capability accumulates requirements across initiatives, so a merge that starts from
    one initiative's PRD deletes every requirement the others added.
    """
    heading = f"### Requirement: {requirement['name']}"
    existing = _lines(spec_path) if spec_path.exists() else [
        f"# {spec_path.parent.name}",
        "",
        "## Purpose",
        "",
        "## Requirements",
        "",
    ]
    block = spec_body(requirement)
    start = next((i for i, line in enumerate(existing) if line.strip() == heading), None)
    if start is None:
        return existing + block
    end = start + 1
    while end < len(existing) and not existing[end].startswith("### "):
        end += 1
    return existing[:start] + block + existing[end:]


def cmd_status(repo, root, args):
    settings = config(repo)
    profile = settings.get("profile", "full")
    state, following = [], None
    for stage in STAGES:
        if profile not in stage.profiles:
            state.append((stage.name, "n/a", f"not in the {profile} profile"))
            continue
        current, detail = stage.state(root)
        state.append((stage.name, current, detail))
        if current == "ready" and following is None:
            following = stage.command

    gates = []
    for line in _lines(root / "STATUS.md"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        label = next((g for g in GATES if len(cells) >= 2 and g in cells[0]), None)
        if label:
            gates.append((label, cells[1], cells[3] if len(cells) > 3 else "", cells[4] if len(cells) > 4 else ""))

    unmerged = _unmerged(root)

    if args.json:
        print(json.dumps({
            "initiative": root.name,
            "profile": profile,
            "gate_medium": settings.get("gate_medium", "session"),
            "stages": [{"stage": n, "state": s, "detail": d} for n, s, d in state],
            "gates": [{"gate": g, "status": s, "decided_by": w, "date": d} for g, s, w, d in gates],
            "next": following,
            "unmerged_requirements": unmerged,
        }, indent=2))
        return OK

    ui.title(f"📋 {root.name}")
    ui.note(f"profile {profile}, gates {settings.get('gate_medium', 'session')}")
    ui.blank()
    glyphs = {"done": ui.ok, "ready": ui.step, "partial": ui.warn, "blocked": ui.item, "n/a": ui.item}
    for name, current, detail in state:
        # indent=0 on every row: `item` indents by 2 by default, which would step the
        # blocked rows out of the column the other glyphs share and stop this being a table.
        glyphs[current](f"{name:<16} {detail}", indent=0)
    if gates:
        ui.blank()
        ui.title("Gates")
        for label, status, decider, date in gates:
            line = f"{label:<8} {status:<12} {decider} {date}".rstrip()
            (ui.ok if status == "approved" else ui.warn)(line)
    if unmerged:
        ui.blank()
        ui.warn(f"{len(unmerged)} shipped requirements are not in {SPECS}: {', '.join(unmerged)}")
        ui.note(f"close it with pt.py spec-merge {root.name}")
    ui.blank()
    ui.done(f"next: {following}" if following else "every stage in this profile is done")
    return OK


def cmd_check(repo, root, args):
    findings, skipped = check(root)
    if args.json:
        print(json.dumps({"initiative": root.name, "findings": findings, "skipped": skipped}, indent=2))
        return FINDINGS if findings else OK

    ui.title(f"🔎 {root.name}: mechanical Definition of Ready")
    ui.blank()
    # Rows under a heading rather than one ✗ each, as claude-kit's doctor reports: `err`
    # writes to stderr, so a finding printed that way arrives out of order against the
    # heading above it, and a report whose lines interleave is a report nobody trusts.
    if findings:
        ui.title("Findings")
        for finding in findings:
            ui.item(finding)
        ui.blank()
    if skipped:
        ui.title("Not checked")
        for note in skipped:
            ui.item(note)
        ui.blank()
    if not findings:
        ui.ok(f"{len(stories(root))} stories and {len(tasks(root))} tasks pass every item a script can decide")
    ui.note("scenario testability, slice verticality and requirement quality stay with /product-team:6-verify")
    ui.done(f"{len(findings)} findings, {len(skipped)} items not checked")
    return FINDINGS if findings else OK


def cmd_spec_merge(repo, root, args):
    ready = shipped(root)
    without = sorted(i for i, r in ready.items() if not r["capability"])
    written, skipped_ids = {}, []
    for identifier, requirement in sorted(ready.items()):
        if not requirement["capability"]:
            continue
        spec_path = repo / SPECS / requirement["capability"] / "spec.md"
        merged = merge(spec_path, requirement)
        if not args.dry_run:
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text("\n".join(merged).rstrip() + "\n", encoding="utf-8")
        written.setdefault(spec_path, []).append(identifier)

    ui.title(f"📚 {root.name}: living capability specs")
    ui.blank()
    for spec_path, identifiers in sorted(written.items()):
        ui.ok(f"{ui.path(spec_path)}  {', '.join(identifiers)}")
    for identifier in without:
        ui.warn(f"{identifier} is shipped but names no capability, so it has no spec to merge into")
        skipped_ids.append(identifier)
    if not written and not without:
        ui.item("no requirement has all of its tasks checked off yet")
    ui.blank()
    ui.done(
        f"{'would write' if args.dry_run else 'wrote'} {len(written)} specs, "
        f"{len(skipped_ids)} requirements skipped"
    )
    return OK


COMMANDS = {"status": cmd_status, "check": cmd_check, "spec-merge": cmd_spec_merge}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pt.py",
        description="The Product Team pipeline's sequencing, checking and spec merge.",
    )
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("slug", nargs="?", help="initiative slug; inferred when the repo has exactly one")
    parser.add_argument("--repo", default=".", help="repository root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output (status, check)")
    parser.add_argument("--dry-run", action="store_true", help="spec-merge only: report without writing")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    root, problem = find(repo, args.slug)
    if problem:
        ui.err(problem)
        return USAGE
    return COMMANDS[args.command](repo, root, args)


if __name__ == "__main__":
    sys.exit(main())
