"""`pt.py`: the Product Team pipeline's sequencing, its DoR checks, and the spec merge.

Most cases build a whole initiative under `tmp_path` from literal markdown, because every
one of these functions reads files and the parsing is the part that breaks. Three cases
run the script as a subprocess to pin the exit codes a stage skill branches on.

Two of them are regressions against bugs the real initiatives on disk exposed while this
was being written, and both are the same failure: a check firing on an initiative that
predates the field it checks. `game-finder` collected ten findings for a design-seat flag
that did not exist when it ran, and stage 4 read `ready` on two initiatives that had
completed it before `04-ux-spec.md` was an artifact at all. A report that cannot be acted
on is worse than no report, so those two shapes are asserted silent.
"""

import importlib.util
import json
import subprocess
import sys

from pathlib import Path

import pytest

# Beside the subject it exercises, located relatively so moving the skill moves these.
SCRIPT = Path(__file__).resolve().parents[1] / "pt.py"


def _load():
    cached = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("pt_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = cached


pt = _load()


PRD = """---
initiative: "demo"
---

# PRD: Demo

## Capabilities

- data-export

## Requirements

### R1: Export a report
The system SHALL export any report the user can see as a CSV file.
Capability: data-export

#### R1.S1
- **WHEN** a report with no rows is exported
- **THEN** the file contains the header row and nothing else

#### R1.S2
- **WHEN** a cell begins with `=`
- **THEN** it is prefixed so no spreadsheet evaluates it

### R2: Export history
The system SHALL record when each export ran.
Capability: data-export

#### R2.S1
- **WHEN** an export completes
- **THEN** its timestamp is stored against the account
"""

STORY = """---
initiative: "demo"
---

# Story 1.1: Export a report

| Field | Value |
|---|---|
| Epic | epic-1.md |
| Scenarios | R1.S1, R1.S2 |
| Size hint | M |
| Depends on | none |
| Needs design seat | no |
| Board issue | PENDING (filled by /product-team:7-push-to-board) |

## Design / UX note

04-ux-spec.md#export-a-report
"""

UX = """# UX spec: Demo

## Flows

### Export a report

Nothing to see here.
"""

TASKS = """## 1. Toolchain

- [x] 1.1 Initialise the project

## 2. Export

- [x] 2.1 Write the CSV encoder covering R1.S1 and R1.S2
- [ ] 2.2 Store the export timestamp (R2.S1)
"""


def initiative(tmp_path, slug="demo", **files):
    """A repo with one initiative, holding exactly the files a case names."""
    root = tmp_path / "docs" / "initiatives" / slug
    root.mkdir(parents=True)
    for name, body in files.items():
        target = root / name.replace("__", "/").replace("_md", ".md").replace("_", "-")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def write(root, name, body):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def build(tmp_path, **named):
    """`(repo, initiative_root)` with each `name.md` written verbatim."""
    root = tmp_path / "docs" / "initiatives" / "demo"
    root.mkdir(parents=True)
    for name, body in named.items():
        write(root, name.replace("_", "-").replace("-md", ".md"), body)
    return tmp_path, root


# --- parsing -----------------------------------------------------------------


def test_slug_matches_a_github_heading_anchor():
    assert pt.slug("Export a report") == "export-a-report"
    assert pt.slug("R1: the note, unbounded") == "r1-the-note-unbounded"


def test_requirements_carry_their_shall_scenarios_and_capability(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD})
    found = pt.requirements(root)
    assert sorted(found) == ["R1", "R2"]
    assert found["R1"]["name"] == "Export a report"
    assert found["R1"]["shall"].startswith("The system SHALL export")
    assert found["R1"]["capability"] == "data-export"
    assert sorted(found["R1"]["scenarios"]) == ["R1.S1", "R1.S2"]
    assert found["R1"]["scenarios"]["R1.S1"] == [
        "- **WHEN** a report with no rows is exported",
        "- **THEN** the file contains the header row and nothing else",
    ]


def test_a_prd_written_before_scenarios_is_recognised_rather_than_failed(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": "## Requirements\n\n- **R1**: it exports.\n- **R2**: it logs.\n"})
    assert pt.requirements(root) == {}
    assert pt.legacy_prd(root) is True


def test_a_prd_with_no_requirements_at_all_is_not_called_legacy(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": "# PRD\n\nNothing yet.\n"})
    assert pt.legacy_prd(root) is False


def test_claims_come_from_both_stories_and_tasks(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY)
    claimed = pt.claims(root)
    assert claimed["R1.S1"] == ["story-1.1.md", "05-tasks.md:2.1"]
    assert claimed["R2.S1"] == ["05-tasks.md:2.2"]


def test_config_reads_top_level_scalars_and_ignores_the_nested_roster(tmp_path):
    (tmp_path / "docs" / "strategy").mkdir(parents=True)
    (tmp_path / "docs/strategy/product-team.yml").write_text(
        "profile: solo\n"
        "gate_medium: pr   # a comment\n"
        "roster:\n"
        "  research: [competitive-researcher]\n"
        "github_repo: UNSET\n",
        encoding="utf-8",
    )
    settings = pt.config(tmp_path)
    assert settings == {"profile": "solo", "gate_medium": "pr", "github_repo": "UNSET"}


# --- the DAG -----------------------------------------------------------------


def stage(name):
    return next(s for s in pt.STAGES if s.name == name)


def test_a_stage_is_done_when_its_artifacts_exist(tmp_path):
    _, root = build(tmp_path, **{"00-brief.md": "brief", "02-prd.md": PRD})
    assert stage("2-prd").state(root)[0] == "done"


def test_a_stage_is_blocked_by_what_it_reads(tmp_path):
    _, root = build(tmp_path, **{"00-brief.md": "brief"})
    state, detail = stage("3-red-team").state(root)
    assert state == "blocked"
    assert "02-prd.md" in detail


def test_a_stage_with_its_inputs_and_no_output_is_ready(tmp_path):
    _, root = build(tmp_path, **{"00-brief.md": "brief", "02-prd.md": PRD})
    state, detail = stage("3-red-team").state(root)
    assert state == "ready"
    assert detail == "/product-team:3-red-team"


def test_a_stage_half_finished_is_partial_not_ready(tmp_path):
    """The `game-finder` bug: stage 4 predates 04-ux-spec.md, so it read `ready`.

    Which told the reader to run it again, below two stages that already read done.
    """
    _, root = build(tmp_path, **{"00-brief.md": "b", "02-prd.md": PRD, "04-design-doc.md": "design"})
    state, detail = stage("4-tech-shape").state(root)
    assert state == "partial"
    assert "04-ux-spec.md" in detail


def test_a_legacy_backlog_counts_as_decomposed(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-design-doc.md": "design"})
    write(root, "05-backlog/story-1.1.md", STORY)
    state, detail = stage("5-decompose").state(root)
    assert state == "done"
    assert "predates" in detail


def test_a_legacy_backlog_unblocks_stage_six(tmp_path):
    """The migration promise: an initiative that predates 05-tasks.md is verifiable."""
    _, root = build(tmp_path, **{"02-prd.md": PRD})
    write(root, "05-backlog/story-1.1.md", STORY)
    state, detail = stage("6-verify").state(root)
    assert state == "ready", detail

    _, root_bare = build(tmp_path / "other", **{"02-prd.md": PRD})
    state, detail = stage("6-verify").state(root_bare)
    assert state == "blocked"
    assert "05-tasks.md or 05-backlog" in detail


def test_the_board_stage_is_done_only_once_every_story_has_an_issue(tmp_path):
    _, root = build(tmp_path, **{"06-dor-report.md": "ALL PASS"})
    write(root, "05-backlog/story-1.1.md", STORY)
    assert stage("7-push-to-board").state(root)[0] == "ready"
    write(root, "05-backlog/story-1.1.md", STORY.replace("PENDING (filled by /product-team:7-push-to-board)", "#12"))
    assert stage("7-push-to-board").state(root)[0] == "done"


# --- check -------------------------------------------------------------------


def test_a_complete_initiative_reports_nothing(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY)
    errors, warnings, skipped = pt.check(root)
    assert errors == []
    assert warnings == []
    assert skipped == []


def test_a_scenario_nobody_claims_is_a_warning(tmp_path):
    """Mid-pipeline that is the normal state, so it fails only under --strict."""
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX})
    write(root, "05-backlog/story-1.1.md", STORY)
    errors, warnings, _ = pt.check(root)
    assert not any("R2.S1" in f for f in errors)
    assert any("R2.S1 is claimed by no story and no task" in f for f in warnings)


def test_claiming_a_scenario_the_prd_does_not_define_is_an_error(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY.replace("R1.S1, R1.S2", "R1.S1, R9.S4"))
    errors, _, _ = pt.check(root)
    assert any("claims R9.S4" in f for f in errors)


def test_a_requirement_with_no_scenario_is_an_error(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD + "\n### R3: Bare\nThe system SHALL do something.\n"})
    errors, _, _ = pt.check(root)
    assert any("R3 has no scenario" in f for f in errors)


def test_a_scenario_claimed_only_by_a_story_is_named_as_unshippable(tmp_path):
    """A story completes as a closed board issue the repo cannot see, so a story-only
    claim satisfies coverage while making the requirement invisible to `shipped`."""
    thin = TASKS.replace("covering R1.S1 and R1.S2", "covering R1.S1")
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX, "05-tasks.md": thin})
    write(root, "05-backlog/story-1.1.md", STORY)
    errors, warnings, _ = pt.check(root)
    assert any("R1.S2 is claimed only by story-1.1.md" in f for f in warnings)
    assert not any("R1.S2" in f for f in errors)
    assert sorted(pt.shipped(root)) == ["R1"], "shipping stays task-driven"


def test_size_l_needs_a_split_rationale(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY.replace("| Size hint | M |", "| Size hint | L |"))
    _, warnings, _ = pt.check(root)
    assert any("size L with no split rationale" in f for f in warnings)

    write(
        root,
        "05-backlog/story-1.1.md",
        STORY.replace("| Size hint | M |", "| Size hint | L |\n| Split rationale | the encoder cannot be halved |"),
    )
    _, warnings, _ = pt.check(root)
    assert not any("split rationale" in f for f in warnings)


def test_the_ux_derived_items_are_skipped_when_there_is_no_ux_spec(tmp_path):
    """The `game-finder` bug: ten findings naming a field that did not exist yet."""
    _, root = build(tmp_path, **{"02-prd.md": PRD, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY.replace("| Needs design seat | no |", "| Needs design seat |  |"))
    errors, warnings, skipped = pt.check(root)
    assert errors == []
    assert warnings == []
    assert any("no 04-ux-spec.md" in note for note in skipped)


def test_a_blank_design_seat_is_a_warning_once_a_ux_spec_exists(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY.replace("| Needs design seat | no |", "| Needs design seat |  |"))
    _, warnings, _ = pt.check(root)
    assert any("Needs design seat is blank" in f for f in warnings)


def test_a_dangling_ux_anchor_is_an_error(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY.replace("#export-a-report", "#export-a-spreadsheet"))
    errors, _, _ = pt.check(root)
    assert any("matches no heading" in f for f in errors)


def test_a_dependency_cycle_is_an_error(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY.replace("| Depends on | none |", "| Depends on | story-1.2.md |"))
    write(
        root,
        "05-backlog/story-1.2.md",
        STORY.replace("Story 1.1", "Story 1.2")
        .replace("| Depends on | none |", "| Depends on | story-1.1.md |")
        .replace("R1.S1, R1.S2", "R2.S1"),
    )
    errors, _, _ = pt.check(root)
    assert any("dependency cycle" in f for f in errors)


DEFERRED = """## Deferrals

| id | Question | Resolved by |
|---|---|---|
| D1 | Which encoder handles the locale | 04-design-doc.md |
"""


def test_a_deferral_the_resolver_never_mentions_is_an_error(tmp_path):
    _, root = build(
        tmp_path,
        **{"02-prd.md": PRD + "\n" + DEFERRED, "04-ux-spec.md": UX, "04-design-doc.md": "# Design\n\nNothing.\n"},
    )
    errors, _, _ = pt.check(root)
    assert any("does not close deferral D1" in f for f in errors)


def test_a_closed_deferral_is_silent(tmp_path):
    _, root = build(
        tmp_path,
        **{
            "02-prd.md": PRD + "\n" + DEFERRED,
            "04-ux-spec.md": UX,
            "04-design-doc.md": "# Design\n\nD1: the platform encoder, since it follows the OS locale.\n",
            "05-tasks.md": TASKS,
        },
    )
    errors, warnings, _ = pt.check(root)
    assert not any("D1" in f for f in errors + warnings)


def test_deferral_closure_needs_a_word_boundary(tmp_path):
    """`D1` inside `D10` is a different deferral, not a close."""
    _, root = build(
        tmp_path,
        **{
            "02-prd.md": PRD + "\n" + DEFERRED,
            "04-ux-spec.md": UX,
            "04-design-doc.md": "# Design\n\nD10: an unrelated decision.\n",
            "05-tasks.md": TASKS,
        },
    )
    errors, _, _ = pt.check(root)
    assert any("does not close deferral D1" in f for f in errors)

    write(root, "04-design-doc.md", "# Design\n\nD10: unrelated. (D1) the platform encoder.\n")
    errors, _, _ = pt.check(root)
    assert not any("deferral D1" in f for f in errors)


def test_a_deferral_waiting_on_an_unwritten_resolver_is_a_warning(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD + "\n" + DEFERRED, "04-ux-spec.md": UX})
    errors, warnings, _ = pt.check(root)
    assert not any("D1" in f for f in errors)
    assert any("waits on 04-design-doc.md" in f for f in warnings)


def test_a_deferral_pointing_upstream_is_an_error(tmp_path):
    upstream = DEFERRED.replace("04-design-doc.md", "02-prd.md")
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX + "\n" + upstream})
    errors, _, _ = pt.check(root)
    assert any("does not run after it" in f for f in errors)


def test_a_deferral_naming_something_that_is_not_an_artifact_is_an_error(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD + "\n" + DEFERRED.replace("04-design-doc.md", "a meeting")})
    errors, _, _ = pt.check(root)
    assert any("not a pipeline artifact" in f for f in errors)


# --- the spec merge ----------------------------------------------------------


def test_a_requirement_ships_only_when_every_claiming_task_is_checked(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "05-tasks.md": TASKS})
    assert sorted(pt.shipped(root)) == ["R1"]


def test_a_requirement_no_task_claims_never_ships(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "05-tasks.md": "## 1. Setup\n\n- [x] 1.1 Nothing traced\n"})
    assert pt.shipped(root) == {}


def test_merge_replaces_a_requirement_and_keeps_the_others(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD})
    spec = tmp_path / "docs/specs/data-export/spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "# data-export\n\n## Purpose\n\nHanded to accountants.\n\n## Requirements\n\n"
        "### Requirement: Export a report\nAn older wording.\n\n"
        "### Requirement: Something else entirely\nOwned by another initiative.\n",
        encoding="utf-8",
    )
    lines, problem = pt.merge(spec, pt.requirements(root)["R1"])
    assert problem is None
    merged = "\n".join(lines)
    assert "Something else entirely" in merged, "a merge must not delete another initiative's requirement"
    assert "An older wording" not in merged
    assert "#### Scenario: R1.S1" in merged
    assert "Handed to accountants." in merged


def test_merge_is_idempotent(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD})
    spec = tmp_path / "docs/specs/data-export/spec.md"
    spec.parent.mkdir(parents=True)
    requirement = pt.requirements(root)["R1"]
    once, problem = pt.merge(spec, requirement)
    assert problem is None
    spec.write_text("\n".join(once), encoding="utf-8")
    assert pt.merge(spec, requirement) == (once, None)


# --- the change vocabulary -----------------------------------------------------

SPEC = """# data-export

## Purpose

Handed to accountants.

## Requirements

### Requirement: Export a report
The system SHALL export any report the user can see as a CSV file.

#### Scenario: R1.S1
- **WHEN** a report with no rows is exported
- **THEN** the file contains the header row and nothing else

#### Scenario: R1.S2
- **WHEN** a cell begins with `=`
- **THEN** it is prefixed so no spreadsheet evaluates it

### Requirement: Something else entirely
Owned by another initiative.
"""

MODIFY_PRD = """## Requirements

### R4: Export a report as XLSX
The system SHALL export any report the user can see as an XLSX file.
Capability: data-export
Modifies: Export a report

#### R4.S1
- **WHEN** an export is requested
- **THEN** an XLSX file downloads
"""

REMOVE_PRD = """## Requirements

### R5: Retire CSV export
Removes: Export a report
Capability: data-export
Reason: XLSX replaced it and the CSV path has no remaining consumers.
Migration: saved CSV exports stay downloadable; new exports produce XLSX only.
"""


def spec_repo(tmp_path, prd):
    repo, root = build(tmp_path, **{"02-prd.md": prd})
    write(tmp_path / "docs/specs/data-export", "spec.md", SPEC)
    return repo, root, tmp_path / "docs/specs/data-export/spec.md"


def test_an_upsert_dropping_a_scenario_is_refused_by_name(tmp_path):
    """The scenario may be another initiative's, so losing it must be said, not done."""
    thin = PRD.replace(
        "#### R1.S2\n- **WHEN** a cell begins with `=`\n- **THEN** it is prefixed so no spreadsheet evaluates it\n",
        "",
    )
    _, root, spec = spec_repo(tmp_path, thin)
    lines, problem = pt.merge(spec, pt.requirements(root)["R1"])
    assert lines is None
    assert "R1.S2" in problem
    assert "Modifies:" in problem


def test_modifies_replaces_and_renames_the_spec_requirement(tmp_path):
    _, root, spec = spec_repo(tmp_path, MODIFY_PRD)
    requirement = pt.requirements(root)["R4"]
    assert requirement["modifies"] == "Export a report"
    once, problem = pt.merge(spec, requirement)
    assert problem is None
    merged = "\n".join(once)
    assert "### Requirement: Export a report as XLSX" in merged
    assert "### Requirement: Export a report\n" not in merged + "\n"
    assert "Something else entirely" in merged
    spec.write_text("\n".join(once), encoding="utf-8")
    assert pt.merge(spec, requirement) == (once, None), "an applied modify converges"


def test_removes_deletes_the_block_and_stays_idempotent(tmp_path):
    _, root, spec = spec_repo(tmp_path, REMOVE_PRD)
    requirement = pt.requirements(root)["R5"]
    once, problem = pt.merge(spec, requirement)
    assert problem is None
    merged = "\n".join(once)
    assert "Export a report" not in merged
    assert "Something else entirely" in merged
    spec.write_text("\n".join(once), encoding="utf-8")
    again, problem = pt.merge(spec, requirement)
    assert problem is None
    assert again == once, "an applied removal converges rather than failing"


def test_a_modify_naming_a_requirement_the_spec_never_held_is_a_problem(tmp_path):
    _, root, spec = spec_repo(tmp_path, MODIFY_PRD.replace("Export a report\n", "No such requirement\n", 1))
    requirement = pt.requirements(root)["R4"]
    lines, problem = pt.merge(spec, requirement)
    assert lines is None
    assert "does not hold" in problem


def test_a_removal_without_reason_or_migration_is_an_error(tmp_path):
    _, root, _ = spec_repo(tmp_path, REMOVE_PRD.replace("Migration: saved CSV exports stay downloadable; new exports produce XLSX only.\n", ""))
    errors, _, _ = pt.check(root)
    assert any("without both a Reason: and a Migration: line" in f for f in errors)


def test_a_removal_no_task_cites_is_an_error_and_never_ships(tmp_path):
    _, root, _ = spec_repo(tmp_path, REMOVE_PRD)
    write(root, "05-tasks.md", "## 1. Cleanup\n\n- [x] 1.1 Unrelated work\n")
    errors, _, _ = pt.check(root)
    assert any("no task cites R5" in f for f in errors)
    assert pt.shipped(root) == {}


def test_a_removal_ships_through_a_bare_requirement_citation(tmp_path):
    _, root, _ = spec_repo(tmp_path, REMOVE_PRD)
    write(root, "05-tasks.md", "## 1. Cleanup\n\n- [x] 1.1 Decommission the CSV export path (R5)\n")
    assert sorted(pt.shipped(root)) == ["R5"]
    errors, _, _ = pt.check(root)
    assert not any("R5" in f for f in errors)


def test_a_prd_restating_a_spec_requirement_that_drops_a_scenario_is_an_error(tmp_path):
    thin = PRD.replace(
        "#### R1.S2\n- **WHEN** a cell begins with `=`\n- **THEN** it is prefixed so no spreadsheet evaluates it\n",
        "",
    )
    _, root, _ = spec_repo(tmp_path, thin)
    errors, _, _ = pt.check(root)
    assert any("drops R1.S2" in f for f in errors)


def test_unmerged_sees_a_requirement_missing_from_an_existing_spec(tmp_path):
    """A spec file that exists no longer proves the requirement inside it was merged."""
    repo, root, spec = spec_repo(tmp_path, PRD)
    write(root, "05-tasks.md", TASKS.replace("- [ ] 2.2", "- [x] 2.2"))
    assert pt._unmerged(root) == ["R2"], "R2 shipped but Export history is not in the spec"
    lines, problem = pt.merge(spec, pt.requirements(root)["R2"])
    assert problem is None
    spec.write_text("\n".join(lines), encoding="utf-8")
    assert pt._unmerged(root) == []


def test_unmerged_sees_an_unapplied_removal(tmp_path):
    _, root, spec = spec_repo(tmp_path, REMOVE_PRD)
    write(root, "05-tasks.md", "## 1. Cleanup\n\n- [x] 1.1 Decommission the CSV export path (R5)\n")
    assert pt._unmerged(root) == ["R5"], "the target is still in the spec, so the removal has not merged"
    lines, _ = pt.merge(spec, pt.requirements(root)["R5"])
    spec.write_text("\n".join(lines), encoding="utf-8")
    assert pt._unmerged(root) == []


# --- the command line --------------------------------------------------------


def run(*args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "NO_COLOR": "1", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def test_status_names_the_next_command(tmp_path):
    build(tmp_path, **{"00-brief.md": "brief"})
    result = run("status", "demo", cwd=tmp_path)
    assert result.returncode == pt.OK
    assert "/product-team:2-write-prd" in result.stdout


def test_a_warning_passes_check_by_default_and_fails_it_under_strict(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX})
    write(root, "05-backlog/story-1.1.md", STORY)
    lenient = run("check", "demo", "--json", cwd=tmp_path)
    assert lenient.returncode == pt.OK
    report = json.loads(lenient.stdout)
    assert "R2.S1" in " ".join(report["warnings"])
    assert report["errors"] == []
    assert run("check", "demo", "--strict", cwd=tmp_path).returncode == pt.FINDINGS


def test_an_error_fails_check_without_strict(tmp_path):
    _, root = build(tmp_path, **{"02-prd.md": PRD, "04-ux-spec.md": UX, "05-tasks.md": TASKS})
    write(root, "05-backlog/story-1.1.md", STORY.replace("R1.S1, R1.S2", "R1.S1, R9.S4"))
    result = run("check", "demo", "--json", cwd=tmp_path)
    assert result.returncode == pt.FINDINGS
    assert "R9.S4" in " ".join(json.loads(result.stdout)["errors"])


STATUS = """# STATUS: Demo

| Gate | Status | Decided by | Date | Reason / concern accepted |
|---|---|---|---|---|
| Gate 0 | approved | @jose | 2026-08-16 | small blast radius, kill review at Gate 1 |
| Gate 1 | pending |  |  |  |
"""


def test_gate_rows_bind_decider_date_and_reason(tmp_path):
    """The columns are Status, Decided by, Date, Reason; binding one to the right put
    the date where the decider goes and dropped the reason, and this is the only reader."""
    _, root = build(tmp_path, **{"00-brief.md": "brief"})
    write(root, "STATUS.md", STATUS)
    result = run("status", "demo", "--json", cwd=tmp_path)
    gate = json.loads(result.stdout)["gates"][0]
    assert gate == {
        "gate": "Gate 0",
        "status": "approved",
        "decided_by": "@jose",
        "date": "2026-08-16",
        "reason": "small blast radius, kill review at Gate 1",
    }


LEGACY_STATUS = """# STATUS

| Stage | Status | Gate PR | Decided by | Date | Notes |
|---|---|---|---|---|---|
| 0-brief (Gate 0) | approved | https://example.test/pull/40 | @jose | 2026-08-09 | Gate 0 PR merged |
"""


def test_gate_rows_follow_the_header_in_a_legacy_status_table(tmp_path):
    """The pre-rework table had a Gate PR column before Decided by; positions come from
    the header row, so both shapes bind the decider to the decider."""
    _, root = build(tmp_path, **{"00-brief.md": "brief"})
    write(root, "STATUS.md", LEGACY_STATUS)
    result = run("status", "demo", "--json", cwd=tmp_path)
    gate = json.loads(result.stdout)["gates"][0]
    assert gate["decided_by"] == "@jose"
    assert gate["date"] == "2026-08-09"
    assert gate["reason"] == "Gate 0 PR merged"


def test_spec_merge_refuses_a_silent_scenario_drop_end_to_end(tmp_path):
    thin = PRD.replace(
        "#### R1.S2\n- **WHEN** a cell begins with `=`\n- **THEN** it is prefixed so no spreadsheet evaluates it\n",
        "",
    )
    repo, root, _ = spec_repo(tmp_path, thin)
    write(root, "05-tasks.md", "## 1. Export\n\n- [x] 1.1 Encoder covering R1.S1\n")
    result = run("spec-merge", "demo", cwd=tmp_path)
    assert result.returncode == pt.FINDINGS
    assert "R1.S2" in result.stdout


def test_an_unknown_initiative_is_a_usage_error(tmp_path):
    build(tmp_path, **{"00-brief.md": "brief"})
    result = run("status", "nope", cwd=tmp_path)
    assert result.returncode == pt.USAGE
    assert "nope" in result.stderr


def test_the_slug_is_inferred_when_there_is_only_one(tmp_path):
    build(tmp_path, **{"00-brief.md": "brief"})
    result = run("status", cwd=tmp_path)
    assert result.returncode == pt.OK
    assert "demo" in result.stdout


def test_spec_merge_dry_run_writes_nothing(tmp_path):
    build(tmp_path, **{"02-prd.md": PRD, "05-tasks.md": TASKS})
    result = run("spec-merge", "demo", "--dry-run", cwd=tmp_path)
    assert result.returncode == pt.OK
    assert not (tmp_path / "docs/specs").exists()


def test_spec_merge_writes_the_capability_spec(tmp_path):
    build(tmp_path, **{"02-prd.md": PRD, "05-tasks.md": TASKS})
    assert run("spec-merge", "demo", cwd=tmp_path).returncode == pt.OK
    spec = tmp_path / "docs/specs/data-export/spec.md"
    assert "### Requirement: Export a report" in spec.read_text()
    assert "Export history" not in spec.read_text(), "R2 has an unchecked task, so it has not shipped"


@pytest.mark.parametrize("subcommand", sorted(pt.COMMANDS))
def test_every_subcommand_runs_on_a_bare_initiative(subcommand, tmp_path):
    """No subcommand may traceback on an initiative holding only a brief."""
    build(tmp_path, **{"00-brief.md": "brief"})
    result = run(subcommand, "demo", cwd=tmp_path)
    assert result.returncode in (pt.OK, pt.FINDINGS), result.stderr
    assert "Traceback" not in result.stderr
