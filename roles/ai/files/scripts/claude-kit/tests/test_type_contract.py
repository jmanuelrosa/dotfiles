"""Group A: the --type contract.

`--type` is required on every command except `doctor` and `adopt`, where a result
spanning all three types is the whole point. Nothing is inferred from a name,
which is what lets the skill, agent and plugin namespaces overlap.

A3 and A5 need a catalog to resolve names against, and A6 needs `doctor`; they
live with those steps rather than here.
"""

import pytest

from claude_kit import errors
from claude_kit.cli import TYPES, build_parser

TYPED = ["list", "add", "remove", "update", "outdated"]
UNTYPED = ["doctor", "adopt"]


def parse(argv):
    """Run argv through the parser, returning (exit_code, stderr-ish message).

    argparse raises SystemExit on a usage error, which is the behaviour under
    test: the Parser subclass maps it to USAGE rather than argparse's default 2.
    """
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(argv)
    return excinfo.value.code


# --- A1: --type is required -------------------------------------------------


@pytest.mark.parametrize("command", TYPED)
def test_a1_omitting_type_is_a_usage_error(command, capsys):
    """Given any command except doctor, When --type is omitted, Then exit USAGE."""
    argv = [command] if command in ("list", "update", "outdated") else [command, "x"]
    assert parse(argv) == errors.USAGE
    assert "--type" in capsys.readouterr().err


@pytest.mark.parametrize("command", TYPED)
def test_a1_names_the_valid_values(command, capsys):
    """The refusal has to say what to pass, not merely that something is missing."""
    argv = [command] if command in ("list", "update", "outdated") else [command, "x"]
    parse(argv)
    err = capsys.readouterr().err
    for kind in TYPES:
        assert kind in err, f"{command} refusal should name '{kind}'"


def test_a1_touches_nothing(kit, tmp_path):
    """Given --type is missing, Then nothing is read, written or fetched.

    End to end, because the claim is about side effects: a usage error must not
    create ~/.claude entries or a project state file.
    """
    result = kit("add", "commit", cwd=tmp_path)
    assert result.returncode == errors.USAGE
    assert list((kit.home / ".claude").iterdir()) == []
    assert not (tmp_path / ".claude").exists()


# --- A2: --type must be one of the three ------------------------------------


@pytest.mark.parametrize("command", TYPED)
def test_a2_invalid_type_is_a_usage_error(command):
    """Given --type widget, Then exit USAGE."""
    argv = ["--type", "widget"]
    full = [command, *argv] if command in ("list", "update", "outdated") else [command, "x", *argv]
    assert parse(full) == errors.USAGE


def test_a2_invalid_type_lists_the_valid_values(capsys):
    parse(["add", "x", "--type", "widget"])
    err = capsys.readouterr().err
    for kind in TYPES:
        assert kind in err


@pytest.mark.parametrize("kind", TYPES)
def test_a2_each_valid_type_is_accepted(kind):
    args = build_parser().parse_args(["add", "commit", "--type", kind])
    assert args.type == kind


# --- doctor and adopt are the documented exceptions -------------------------


def test_doctor_accepts_no_type():
    """Given doctor with no --type, Then parsing succeeds and type is None.

    The cross-type checks cannot run inside a single type, so requiring --type
    here would stop doctor doing half its job.
    """
    args = build_parser().parse_args(["doctor"])
    assert args.command == "doctor"
    assert args.type is None


def test_adopt_accepts_no_type():
    """One claude-kit.json holds all three types, so requiring --type could only
    ever write a partial file."""
    args = build_parser().parse_args(["adopt"])
    assert args.command == "adopt"
    assert args.type is None
    assert args.dry_run is False


@pytest.mark.parametrize("command", UNTYPED)
@pytest.mark.parametrize("kind", TYPES)
def test_the_untyped_commands_still_accept_a_type_as_a_filter(command, kind):
    args = build_parser().parse_args([command, "--type", kind])
    assert args.type == kind


@pytest.mark.parametrize("command", UNTYPED)
def test_the_untyped_commands_reject_an_invalid_type(command):
    """Optional does not mean unvalidated."""
    assert parse([command, "--type", "widget"]) == errors.USAGE


def test_adopt_carries_dry_run():
    args = build_parser().parse_args(["adopt", "--dry-run"])
    assert args.dry_run is True


# --- A4: one --type per call ------------------------------------------------


def test_a4_one_type_applies_to_every_name():
    """Given several names, Then the single --type covers all of them."""
    args = build_parser().parse_args(["add", "a", "b", "c", "--type", "skill"])
    assert args.names == ["a", "b", "c"]
    assert args.type == "skill"


# --- flag wiring ------------------------------------------------------------


def test_global_defaults_off_and_sets_want_global():
    """`global` is a Python keyword, so the flag has to land on another dest."""
    assert build_parser().parse_args(["add", "x", "--type", "skill"]).want_global is False
    assert build_parser().parse_args(["add", "x", "--type", "skill", "--global"]).want_global is True


def test_remove_carries_no_cascade():
    args = build_parser().parse_args(["remove", "x", "--type", "skill", "--no-cascade"])
    assert args.no_cascade is True


def test_update_and_outdated_take_no_names_meaning_all():
    """Bare `update --type skill` targets every tracked skill."""
    for command in ("update", "outdated"):
        args = build_parser().parse_args([command, "--type", "skill"])
        assert args.names == []


def test_a_subcommand_is_required():
    assert parse([]) == errors.USAGE


def test_unknown_subcommand_is_a_usage_error():
    assert parse(["frobnicate", "--type", "skill"]) == errors.USAGE


# --- the shim ---------------------------------------------------------------


def test_shim_runs_and_reports_the_table(kit):
    """The shim must resolve the package through its own path, not the cwd."""
    result = kit("--help")
    assert result.returncode == errors.OK
    for command in [*TYPED, *UNTYPED]:
        assert command in result.stdout


def test_shim_works_from_an_unrelated_cwd(kit, tmp_path):
    """Given cwd is nowhere near the checkout, Then the package still imports."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert kit("--help", cwd=elsewhere).returncode == errors.OK
