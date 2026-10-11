"""The sentry wrapper picks one account's config dir from the working directory, or refuses."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

WRAPPER = Path(__file__).resolve().parents[1] / "sentry"
UI = Path(__file__).resolve().parents[5] / "shell/files/fish/functions/ui/_ui.fish"


@pytest.fixture
def harness(tmp_path):
    if shutil.which("fish") is None:
        pytest.skip("Fish is required for wrapper tests")
    home = tmp_path / "home"
    functions = home / ".config/fish/functions"
    functions.mkdir(parents=True)
    (functions / "_ui.fish").symlink_to(UI)

    wrapper_bin = tmp_path / "wrapper-bin"
    wrapper_bin.mkdir()
    (wrapper_bin / "sentry").symlink_to(WRAPPER)
    real_bin = tmp_path / "real-bin"
    real_bin.mkdir()
    real = real_bin / "sentry"
    real.write_text(
        "#!/bin/sh\n"
        'printf "config=%s\\n" "${SENTRY_CONFIG_DIR-unset}"\n'
        'printf "args=%s\\n" "$*"\n'
    )
    real.chmod(0o755)

    developer = home / "Developer"
    for project in ("personal/app", "personal/pentla/api", "work/console", "elsewhere"):
        (developer / project).mkdir(parents=True)
    accounts = home / ".config/sentry"
    accounts.mkdir(parents=True)
    (accounts / "accounts").write_text(
        f"personal {developer}/personal\n"
        f"pentla {developer}/personal/pentla\n"
        f"didomi {developer}/work\n"
    )

    def run(cwd, *args, **env):
        return subprocess.run(
            [str(wrapper_bin / "sentry"), *args],
            cwd=developer / cwd,
            env={
                "HOME": str(home),
                "PATH": os.pathsep.join((str(wrapper_bin), str(real_bin), "/usr/bin", "/bin", str(Path(shutil.which("fish")).parent))),
                "PWD": str(developer / cwd),
                "NO_COLOR": "1",
                **env,
            },
            capture_output=True,
            text=True,
            timeout=10,
        )

    run.accounts = accounts
    return run


def test_a_mapped_directory_gets_its_account(harness):
    result = harness("work/console", "issue", "list")
    assert result.returncode == 0, result.stderr
    assert f"config={harness.accounts}/didomi" in result.stdout
    assert "args=issue list" in result.stdout


def test_the_most_specific_root_wins(harness):
    result = harness("personal/pentla/api", "issue", "list")
    assert result.returncode == 0, result.stderr
    assert f"config={harness.accounts}/pentla" in result.stdout


def test_a_sibling_root_does_not_claim_by_prefix(harness):
    result = harness("personal/app", "issue", "list")
    assert f"config={harness.accounts}/personal" in result.stdout


def test_a_root_written_through_a_symlink_still_claims_its_directory(harness, tmp_path):
    linked = tmp_path / "linked-developer"
    linked.symlink_to(harness.accounts.parent.parent / "Developer")
    (harness.accounts / "accounts").write_text(f"didomi {linked}/work\n")
    result = harness("work/console", "issue", "list")
    assert result.returncode == 0, result.stderr
    assert f"config={harness.accounts}/didomi" in result.stdout


def test_an_unmapped_directory_is_refused_before_the_binary_runs(harness):
    result = harness("elsewhere", "auth", "login")
    assert result.returncode == 1
    assert "config=" not in result.stdout
    assert result.stderr.startswith("✗ No Sentry account claims")
    assert "personal, pentla, didomi" in result.stderr


def test_an_explicit_account_overrides_the_directory(harness):
    result = harness("work/console", "issue", "list", SENTRY_ACCOUNT="personal")
    assert f"config={harness.accounts}/personal" in result.stdout


def test_an_unknown_account_is_refused(harness):
    result = harness("work/console", "issue", "list", SENTRY_ACCOUNT="../../.ssh")
    assert result.returncode == 1
    assert "config=" not in result.stdout
    assert result.stderr.startswith("✗ Unknown Sentry account '../../.ssh'")


def test_an_explicit_config_dir_passes_through(harness, tmp_path):
    result = harness("elsewhere", "auth", "login", SENTRY_CONFIG_DIR=str(tmp_path / "throwaway"))
    assert result.returncode == 0, result.stderr
    assert f"config={tmp_path / 'throwaway'}" in result.stdout
