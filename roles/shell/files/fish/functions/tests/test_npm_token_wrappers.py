"""The npm_token wrappers hand the keychain tokens to the wrapped call and nothing else."""

import shutil
import subprocess
from pathlib import Path

import pytest

FUNCTIONS = Path(__file__).resolve().parents[1]
WRAPPERS = FUNCTIONS / "npm_token"
UI = FUNCTIONS / "ui"


@pytest.fixture
def harness(tmp_path):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("Fish is required for wrapper tests")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    security = stubs / "security"
    security.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> "$SECURITY_ARGS"\n'
        'case "$3" in\n'
        '  personal-service) test -n "$PERSONAL" || exit 44; printf "%s\\n" "$PERSONAL" ;;\n'
        '  work-service) test -n "$WORK" || exit 44; printf "%s\\n" "$WORK" ;;\n'
        "  *) exit 44 ;;\n"
        "esac\n"
    )
    npm = stubs / "npm"
    npm.write_text(
        "#!/bin/sh\n"
        'printf "child NPM_TOKEN=%s\\n" "${NPM_TOKEN-unset}"\n'
        'printf "child DID_NPM_TOKEN=%s\\n" "${DID_NPM_TOKEN-unset}"\n'
        'printf "args=%s\\n" "$*"\n'
    )
    for stub in (security, npm):
        stub.chmod(0o755)
    args = tmp_path / "security-args"

    def run(items, **tokens):
        listed = " ".join(f"'{item}'" for item in items)
        script = (
            f'set -g fish_function_path "{WRAPPERS}" "{UI}" $fish_function_path; '
            f"set -g NPM_TOKEN_KEYCHAIN_ITEMS {listed}; "
            "npm install @scope/pkg; "
            "set -q NPM_TOKEN; or set -q DID_NPM_TOKEN; and echo parent=set; or echo parent=unset"
        )
        return subprocess.run(
            [fish, "--no-config", "--command", script],
            env={
                "HOME": str(tmp_path),
                "PATH": f"{stubs}:/usr/bin:/bin",
                "NO_COLOR": "1",
                "SECURITY_ARGS": str(args),
                **tokens,
            },
            capture_output=True,
            text=True,
            timeout=10,
        )

    run.security_args = args
    return run


PERSONAL_ITEM = "NPM_TOKEN:personal-service:me"
WORK_ITEM = "DID_NPM_TOKEN:work-service:me"


def test_the_personal_profile_injects_only_its_token(harness):
    result = harness([PERSONAL_ITEM], PERSONAL="personal-token")
    assert result.returncode == 0, result.stderr
    assert "child NPM_TOKEN=personal-token" in result.stdout
    assert "child DID_NPM_TOKEN=unset" in result.stdout
    assert "args=install @scope/pkg" in result.stdout
    assert "parent=unset" in result.stdout
    assert harness.security_args.read_text().split() == [
        "find-generic-password", "-s", "personal-service", "-a", "me", "-w",
    ]
    assert result.stderr == ""


def test_the_work_profile_injects_both_tokens(harness):
    result = harness([PERSONAL_ITEM, WORK_ITEM], PERSONAL="personal-token", WORK="work-token")
    assert result.returncode == 0, result.stderr
    assert "child NPM_TOKEN=personal-token" in result.stdout
    assert "child DID_NPM_TOKEN=work-token" in result.stdout
    assert "parent=unset" in result.stdout
    assert result.stderr == ""


def test_a_missing_item_warns_and_still_injects_the_others(harness):
    result = harness([PERSONAL_ITEM, WORK_ITEM], WORK="work-token")
    assert result.returncode == 0, result.stderr
    assert "child NPM_TOKEN=unset" in result.stdout
    assert "child DID_NPM_TOKEN=work-token" in result.stdout
    assert "args=install @scope/pkg" in result.stdout
    assert "personal-service" in result.stderr
    assert "work-service" not in result.stderr


def test_no_listed_items_passes_the_call_through_silently(harness):
    result = harness([])
    assert result.returncode == 0, result.stderr
    assert "child NPM_TOKEN=unset" in result.stdout
    assert "args=install @scope/pkg" in result.stdout
    assert not harness.security_args.exists()
    assert result.stderr == ""


@pytest.mark.parametrize("source", sorted(WRAPPERS.glob("*.fish")), ids=lambda path: path.name)
def test_wrapper_sources_parse(source):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("Fish is required for wrapper tests")
    result = subprocess.run([fish, "--no-execute", str(source)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
