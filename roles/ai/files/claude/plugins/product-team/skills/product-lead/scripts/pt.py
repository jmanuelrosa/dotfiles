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
SPEC_REQUIREMENT = re.compile(r"^### Requirement:\s*(.+?)\s*$")
SPEC_SCENARIO = re.compile(r"^#### Scenario:\s*(R\d+\.S\d+)\b")

# The metadata lines a `### R#:` block may carry at column zero. `Modifies:` and
# `Removes:` are how a later initiative changes what an earlier one merged into
# docs/specs/: a modify restates the whole requirement under its own heading (which is
# also how a rename happens), a removal carries no scenarios and must say why and what
# happens to whoever relied on it.
META = (
    ("capability", re.compile(r"^Capability:\s*([a-z0-9-]+)\s*$")),
    ("modifies", re.compile(r"^Modifies:\s*(.+?)\s*$")),
    ("removes", re.compile(r"^Removes:\s*(.+?)\s*$")),
    ("reason", re.compile(r"^Reason:\s*(.+?)\s*$")),
    ("migration", re.compile(r"^Migration:\s*(.+?)\s*$")),
)
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
        """Unsatisfied requirements; a tuple entry is alternatives, any one satisfies it."""
        absent = []
        for entry in self.requires:
            options = entry if isinstance(entry, tuple) else (entry,)
            if not any(_present(root / f) for f in options):
                absent.append(" or ".join(options))
        return absent


STAGES = (
    Stage("0-brief", ("00-brief.md",), (), "/product-team:0-refine-idea"),
    Stage("1-research", ("01-research/summary.md",), ("00-brief.md",), "/product-team:1-research"),
    Stage("2-prd", (PRD,), ("00-brief.md",), "/product-team:2-write-prd"),
    Stage("3-red-team", ("03-red-team-report.md",), (PRD,), "/product-team:3-red-team"),
    Stage("4-tech-shape", (UX_SPEC, "04-design-doc.md"), (PRD,), "/product-team:4-tech-shape"),
    Stage("5-decompose", (TASKS,), (PRD, "04-design-doc.md"), "/product-team:5-decompose", alt=(BACKLOG,)),
    # `(TASKS, BACKLOG)` for the same reason stage 5 carries `alt`: a legacy initiative
    # with stories and no task list must be verifiable, not blocked forever.
    Stage(
        "6-verify",
        ("06-dor-report.md",),
        ((TASKS, BACKLOG),),
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
    """Shipped requirements whose capability spec does not yet reflect them.

    Unapplied means: an upserted or modified requirement whose heading the spec does not
    hold, or a removal whose target is still there. Checking only that the spec file
    existed hid all three, so a shipped requirement missing from an existing file read as
    merged forever.

    `docs/specs/` is repo-level while an initiative is three directories down, so the
    repo is derived rather than passed: it keeps the stage table's predicates to one
    argument, which is the initiative every other one takes.
    """
    specs = root.parents[2] / SPECS
    unmerged = []
    for identifier, requirement in sorted(shipped(root).items()):
        if not requirement["capability"]:
            continue
        names = spec_requirements(specs / requirement["capability"] / "spec.md")
        if requirement["removes"]:
            applied = requirement["removes"] not in names
        else:
            applied = requirement["name"] in names
        if not applied:
            unmerged.append(identifier)
    return unmerged


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
            current = {"id": heading.group(1), "name": heading.group(2), "shall": "", "scenarios": {}}
            current.update({key: None for key, _ in META})
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
        stripped = line.strip()
        for key, pattern in META:
            matched = pattern.match(stripped)
            if matched:
                current[key] = matched.group(1)
                break
        else:
            if stripped and not current["shall"]:
                current["shall"] = stripped
    return found


def spec_requirements(spec_path):
    """`{name: scenario id set}` from a capability spec, empty when it does not exist."""
    found, current = {}, None
    for line in _lines(spec_path):
        heading = SPEC_REQUIREMENT.match(line)
        if heading:
            current = found.setdefault(heading.group(1), set())
            continue
        step = SPEC_SCENARIO.match(line)
        if step and current is not None:
            current.add(step.group(1))
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
    """Every mechanical DoR item. Returns `(errors, warnings, skipped)`, lists of strings.

    Errors are broken references and structural corruption, wrong at any point in the
    pipeline. Warnings are incompleteness that is the normal state mid-pipeline and only
    a defect at Definition of Ready time, which is what `--strict` is for: `6-verify`
    and the solo profile's decompose handoff fail on both.
    """
    errors, warnings, skipped = [], [], []
    repo = root.parents[2]
    defined = requirements(root)
    scenario_ids = {s for r in defined.values() for s in r["scenarios"]}
    listed = tasks(root)
    has_tasks = (root / TASKS).exists()

    if not defined:
        skipped.append(
            f"scenario coverage: {PRD} declares no `### R#:` requirement blocks"
            + (" (written before scenarios were requirements)" if legacy_prd(root) else "")
        )
    else:
        for requirement in defined.values():
            if not requirement["scenarios"] and not requirement["removes"]:
                errors.append(f"{PRD}: {requirement['id']} has no scenario, so nothing can claim or test it")
        claimed = claims(root)
        for unknown in sorted(set(claimed) - scenario_ids):
            errors.append(f"{', '.join(claimed[unknown])}: claims {unknown}, which {PRD} does not define")
        for uncovered in sorted(scenario_ids - set(claimed)):
            warnings.append(f"{PRD}: {uncovered} is claimed by no story and no task")
        if has_tasks:
            in_tasks = {found for _, _, _, text in listed for found in SCENARIO_ID.findall(text)}
            for story_only in sorted((set(claimed) & scenario_ids) - in_tasks):
                warnings.append(
                    f"{story_only} is claimed only by {', '.join(claimed[story_only])}; no task carries it, "
                    f"so it can never be reported shipped or merged into {SPECS}"
                )
        errors.extend(_delta_problems(repo, root, defined, listed, has_tasks))

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
            warnings.append(f"{name}: Size hint is not set to S, M or L")
        elif size.upper() == "L" and PLACEHOLDER.match(table.get("Split rationale", "")):
            warnings.append(f"{name}: size L with no split rationale")
        if has_ux and PLACEHOLDER.match(table.get("Needs design seat", "")):
            warnings.append(f"{name}: Needs design seat is blank")
        depends = table.get("Depends on", "")
        if PLACEHOLDER.match(depends):
            warnings.append(f"{name}: Depends on is blank; a story with none says `none`")
        graph[name] = [d for d in re.findall(r"story-\d+\.\d+\.md", depends)]

        if anchors:
            pointer = UX_ANCHOR.search(path.read_text(encoding="utf-8"))
            if not pointer:
                warnings.append(f"{name}: no resolvable {UX_SPEC} pointer in its Design / UX note")
            elif pointer.group(1) not in anchors:
                errors.append(f"{name}: Design / UX pointer #{pointer.group(1)} matches no heading in {UX_SPEC}")

    cycle = _cycle(graph)
    if cycle:
        errors.append("dependency cycle: " + " -> ".join(cycle))

    order = {name: index for index, name in enumerate(DEFERRABLE)}
    for artifact, identifier, question, resolver in deferrals(root):
        target = resolver.strip("`")
        if target not in order:
            errors.append(f"{artifact}: deferral {identifier} names {target!r}, which is not a pipeline artifact")
        elif order[target] <= order[artifact]:
            errors.append(f"{artifact}: deferral {identifier} points at {target}, which does not run after it")
        elif not (root / target).exists():
            warnings.append(f"{artifact}: deferral {identifier} waits on {target}, which does not exist yet")
        elif not re.search(rf"\b{re.escape(identifier)}\b", (root / target).read_text(encoding="utf-8")):
            # A word boundary, not a substring: D1 must not read as closed inside D10.
            errors.append(f"{target}: does not close deferral {identifier} ({question})")

    if not stories(root) and not has_tasks:
        skipped.append("story and task items: neither a backlog nor a task list exists yet")
    return errors, warnings, skipped


def _delta_problems(repo, root, defined, listed, has_tasks):
    """What is wrong with the PRD's `Modifies:` / `Removes:` blocks, all errors.

    A target that is absent because the merge already ran is not a problem: a modify is
    applied once its own heading is in the spec, and an applied removal is
    indistinguishable from one that never matched, so a misspelt removal target reads as
    fine. That is the same bias toward silence the rest of this script carries.
    """
    problems = []
    for requirement in defined.values():
        identifier = requirement["id"]
        if requirement["modifies"] and requirement["removes"]:
            problems.append(f"{PRD}: {identifier} carries both Modifies: and Removes:; a block does one or the other")
            continue
        target = requirement["removes"] or requirement["modifies"]
        capability = requirement["capability"]
        spec_path = repo / SPECS / capability / "spec.md" if capability else None
        if not target:
            if spec_path is not None and requirement["scenarios"]:
                held = spec_requirements(spec_path).get(requirement["name"], set())
                dropped = sorted(held - set(requirement["scenarios"]))
                if dropped:
                    problems.append(
                        f"{PRD}: {identifier} restates {requirement['name']!r} but drops {', '.join(dropped)}; "
                        f"write `Modifies: {requirement['name']}` if that is intended"
                    )
            continue
        verb = "removes" if requirement["removes"] else "modifies"
        if not capability:
            problems.append(f"{PRD}: {identifier} {verb} {target!r} but names no capability, so no spec can apply it")
            continue
        names = spec_requirements(spec_path)
        if not spec_path.exists():
            problems.append(f"{PRD}: {identifier} {verb} {target!r} but {SPECS / capability / 'spec.md'} does not exist")
        elif requirement["modifies"] and target not in names and requirement["name"] not in names:
            problems.append(f"{PRD}: {identifier} modifies {target!r}, which that spec does not hold")
        if requirement["removes"]:
            if requirement["scenarios"]:
                problems.append(f"{PRD}: {identifier} removes a requirement and may not carry scenarios")
            if not (requirement["reason"] and requirement["migration"]):
                problems.append(f"{PRD}: {identifier} removes {target!r} without both a Reason: and a Migration: line")
            cites = re.compile(rf"\b{identifier}\b(?!\.S)")
            if has_tasks and not any(cites.search(text) for _, _, _, text in listed):
                problems.append(
                    f"{PRD}: {identifier} removes {target!r} but no task cites {identifier}; "
                    "decommissioning is work, so the removal can never ship"
                )
    return problems


def shipped(root):
    """Requirements whose every claiming task is checked off, as `{R#: requirement}`.

    Task-driven on purpose: tasks are the only artifact with a repo-visible completion
    signal, while a story completes as a closed board issue the repo cannot see. A
    removal block has no scenarios, so it ships through tasks citing its bare id
    instead; decommissioning is work, and a removal no task cites never ships.
    """
    done, pending = {}, {}
    listed = tasks(root)
    for is_done, _, _, text in listed:
        for identifier in SCENARIO_ID.findall(text):
            (done if is_done else pending).setdefault(identifier.split(".")[0], True)
    result = {}
    for identifier, requirement in requirements(root).items():
        if requirement["removes"]:
            cites = re.compile(rf"\b{identifier}\b(?!\.S)")
            citing = [is_done for is_done, _, _, text in listed if cites.search(text)]
            if citing and all(citing):
                result[identifier] = requirement
        elif identifier in done and identifier not in pending:
            result[identifier] = requirement
    return result


def spec_body(requirement):
    lines = [f"### Requirement: {requirement['name']}", requirement["shall"], ""]
    for identifier, steps in requirement["scenarios"].items():
        lines.append(f"#### Scenario: {identifier}")
        lines.extend(steps)
        lines.append("")
    return lines


def _replace(existing, name, block):
    """The spec with `### Requirement: {name}`'s block replaced (or appended when absent)."""
    heading = f"### Requirement: {name}"
    start = next((i for i, line in enumerate(existing) if line.strip() == heading), None)
    if start is None:
        return existing + block
    end = start + 1
    while end < len(existing) and not existing[end].startswith("### "):
        end += 1
    return existing[:start] + block + existing[end:]


def merge(spec_path, requirement):
    """One requirement applied to a capability spec: `(lines, problem)`, one of them None.

    Rewriting the whole file from the PRD was the alternative and it is wrong: a
    capability accumulates requirements across initiatives, so a merge that starts from
    one initiative's PRD deletes every requirement the others added. The same reasoning
    is why a plain upsert that would drop a scenario the spec already holds is refused
    rather than applied: the scenario may be another initiative's, and losing it must be
    said with `Modifies:` rather than done by accident.

    Every path is idempotent: an applied removal (target absent) and an applied modify
    (its own heading present) both converge instead of failing the second run.
    """
    existing = _lines(spec_path) if spec_path.exists() else [
        f"# {spec_path.parent.name}",
        "",
        "## Purpose",
        "",
        "## Requirements",
        "",
    ]
    names = spec_requirements(spec_path)
    identifier = requirement["id"]
    if requirement["removes"]:
        if not spec_path.exists():
            return None, f"{identifier} removes {requirement['removes']!r} but {ui.path(spec_path)} does not exist"
        if requirement["removes"] not in names:
            return existing, None
        return _replace(existing, requirement["removes"], []), None
    if requirement["modifies"]:
        target = requirement["modifies"] if requirement["modifies"] in names else (
            requirement["name"] if requirement["name"] in names else None
        )
        if target is None:
            return None, f"{identifier} modifies {requirement['modifies']!r}, which {ui.path(spec_path)} does not hold"
        return _replace(existing, target, spec_body(requirement)), None
    dropped = sorted(names.get(requirement["name"], set()) - set(requirement["scenarios"]))
    if dropped:
        return None, (
            f"{identifier} would drop {', '.join(dropped)} from {requirement['name']!r}; "
            f"write `Modifies: {requirement['name']}` if that is intended"
        )
    return _replace(existing, requirement["name"], spec_body(requirement)), None


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

    # Two gate-table shapes exist on disk: the current template's
    # | Gate | Status | Decided by | Date | Reason | and the legacy
    # | Stage | Status | Gate PR | Decided by | Date | Notes |. Positions are taken from
    # the header row rather than hardcoded, because hardcoding either shape misreads the
    # other one column over and puts the date where the decider goes.
    gates, columns = [], {"decided by": 2, "date": 3, "reason": 4}
    for line in _lines(root / "STATUS.md"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        lowered = [c.lower() for c in cells]
        if "decided by" in lowered:
            columns = {"decided by": lowered.index("decided by"), "date": lowered.index("date") if "date" in lowered else 3}
            columns["reason"] = next((i for i, c in enumerate(lowered) if c.startswith(("reason", "notes"))), 4)
            continue
        label = next((g for g in GATES if len(cells) >= 2 and g in cells[0]), None)
        if label:
            padded = cells + [""] * max(columns.values())
            gates.append((label, cells[1], padded[columns["decided by"]], padded[columns["date"]], padded[columns["reason"]]))

    unmerged = _unmerged(root)

    if args.json:
        print(json.dumps({
            "initiative": root.name,
            "profile": profile,
            "gate_medium": settings.get("gate_medium", "session"),
            "stages": [{"stage": n, "state": s, "detail": d} for n, s, d in state],
            "gates": [{"gate": g, "status": s, "decided_by": w, "date": d, "reason": r} for g, s, w, d, r in gates],
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
        for label, status, decider, date, _ in gates:
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
    errors, warnings, skipped = check(root)
    failed = bool(errors) or (args.strict and bool(warnings))
    if args.json:
        print(json.dumps({
            "initiative": root.name,
            "errors": errors,
            "warnings": warnings,
            "skipped": skipped,
        }, indent=2))
        return FINDINGS if failed else OK

    ui.title(f"🔎 {root.name}: mechanical Definition of Ready")
    ui.blank()
    # Rows under a heading rather than one ✗ each, as claude-kit's doctor reports: `err`
    # writes to stderr, so a finding printed that way arrives out of order against the
    # heading above it, and a report whose lines interleave is a report nobody trusts.
    if errors:
        ui.title("Errors")
        for finding in errors:
            ui.item(finding)
        ui.blank()
    if warnings:
        ui.title("Warnings" + ("" if args.strict else " (failures under --strict)"))
        for finding in warnings:
            ui.item(finding)
        ui.blank()
    if skipped:
        ui.title("Not checked")
        for note in skipped:
            ui.item(note)
        ui.blank()
    if not errors and not warnings:
        ui.ok(f"{len(stories(root))} stories and {len(tasks(root))} tasks pass every item a script can decide")
    ui.note("scenario testability, slice verticality and requirement quality stay with /product-team:6-verify")
    ui.done(f"{len(errors)} errors, {len(warnings)} warnings, {len(skipped)} items not checked")
    return FINDINGS if failed else OK


def cmd_spec_merge(repo, root, args):
    ready = shipped(root)
    without = sorted(i for i, r in ready.items() if not r["capability"])
    written, problems = {}, []
    for identifier, requirement in sorted(ready.items()):
        if not requirement["capability"]:
            continue
        spec_path = repo / SPECS / requirement["capability"] / "spec.md"
        merged, problem = merge(spec_path, requirement)
        if problem:
            problems.append(problem)
            continue
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
    for problem in problems:
        ui.warn(problem)
    if not written and not without and not problems:
        ui.item("no requirement has all of its tasks checked off yet")
    ui.blank()
    ui.done(
        f"{'would write' if args.dry_run else 'wrote'} {len(written)} specs, "
        f"{len(without)} requirements skipped, {len(problems)} refused"
    )
    return FINDINGS if problems else OK


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
    parser.add_argument("--strict", action="store_true", help="check only: fail on warnings too")
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
