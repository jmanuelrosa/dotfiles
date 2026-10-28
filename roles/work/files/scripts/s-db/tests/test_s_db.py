import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import FISH_FUNCTIONS

SCRIPT = Path(__file__).resolve().parents[1] / "s-db"


@pytest.fixture
def run_db(tmp_path):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("Fish is required for shell behavior tests")

    home = tmp_path / "home"
    work = home / "Developer/work/addingwell"
    work.mkdir(parents=True)
    local = work / ".local"
    (local / "bin").mkdir(parents=True)
    (local / "logs").mkdir()
    functions = home / ".config/fish/functions"
    functions.mkdir(parents=True)
    (functions / "_ui.fish").symlink_to(FISH_FUNCTIONS / "ui/_ui.fish")
    bin_dir = home / "bin"
    bin_dir.mkdir()
    proxy_call = tmp_path / "proxy-call"
    pg_call = tmp_path / "pg-call"
    cloud_call = tmp_path / "cloud-call"

    stubs = {
        local / "bin/cloud-sql-proxy": """#!/bin/sh
printf '%s\\n' "$CLOUDSDK_ACTIVE_CONFIG_NAME" "$@" > "$PROXY_CALL"
if [ "$PROXY_BACKGROUND" = 1 ]; then
    exec sleep 2
fi
""",
        bin_dir / "lsof": """#!/bin/sh
if [ "$PROXY_REUSED" = 1 ]; then
    printf '4242\\n'
fi
""",
        bin_dir / "ps": "#!/bin/sh\nprintf 'cloud-sql-proxy\\n'\n",
        bin_dir / "gcloud": """#!/bin/sh
if [ "$*" = "config get-value account" ]; then
    if [ "$GCLOUD_SIGNED_OUT" != 1 ]; then
        printf '%s@didomi.test\\n' "$CLOUDSDK_ACTIVE_CONFIG_NAME"
    fi
    exit 0
fi
printf '%s\\n' "$@" > "$CLOUD_CALL"
exit 1
""",
        bin_dir / "pg_dump": """#!/bin/sh
printf '%s\\n' "$CLOUDSDK_ACTIVE_CONFIG_NAME" "$@" > "$PG_CALL"
for arg in "$@"; do
    case "$arg" in
        --file=*) : > "${arg#--file=}" ;;
    esac
done
""",
        bin_dir / "pg_restore": """#!/bin/sh
printf '%s\\n' "$CLOUDSDK_ACTIVE_CONFIG_NAME" "$@" > "$PG_CALL"
""",
    }
    for path, source in stubs.items():
        path.write_text(source)
        path.chmod(0o755)

    (home / "sample.dump").touch()
    env = os.environ.copy()
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        XDG_DATA_HOME=str(home / ".local/share"),
        XDG_CACHE_HOME=str(home / ".cache"),
        PATH=os.pathsep.join((str(bin_dir), env["PATH"])),
        NO_COLOR="1",
        CLOUDSDK_ACTIVE_CONFIG_NAME="personal",
        GOOGLE_APPLICATION_CREDENTIALS=str(home / "unused-adc.json"),
        PROXY_CALL=str(proxy_call),
        PG_CALL=str(pg_call),
        CLOUD_CALL=str(cloud_call),
    )

    def run(*args, background=False, reused=False, signed_out=False):
        result = subprocess.run(
            [
                fish,
                "--no-config",
                "--command",
                (
                    'set -p fish_function_path "$HOME/.config/fish/functions"; '
                    'source "$argv[1]" $argv[2..-1]'
                ),
                str(SCRIPT),
                *args,
            ],
            cwd=home,
            env={
                **env,
                "PROXY_BACKGROUND": str(int(background)),
                "PROXY_REUSED": str(int(reused)),
                "GCLOUD_SIGNED_OUT": str(int(signed_out)),
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            assert result.stderr == "", result.stderr
        assert not cloud_call.exists(), "s-db must not change global cloud configuration"
        calls = {
            name: path.read_text().splitlines() if path.exists() else []
            for name, path in (("proxy", proxy_call), ("pg", pg_call))
        }
        return result, calls

    return run


@pytest.mark.parametrize("command", [[], ["connect"]])
@pytest.mark.parametrize("selection", [[], ["--account", "pentla"], ["-a", "pentla"]])
def test_foreground_proxy_selects_named_configuration(run_db, command, selection):
    result, calls = run_db(*command, "staging", *selection)
    assert result.returncode == 0, result.stderr
    account = "pentla" if selection else "didomi"
    assert calls["proxy"] == [
        account,
        "--gcloud-auth",
        "--auto-iam-authn",
        "--port",
        "5433",
        "addingwell-dev-326312:europe-west1:addingwell-dev-postgres",
    ]
    assert calls["pg"] == []
    assert f"User: {account}@didomi.test" in result.stdout


@pytest.mark.parametrize("selection", [[], ["--account", "pentla"]])
@pytest.mark.parametrize("command", [["production", "--detach"], ["dump", "production"]])
def test_background_proxy_selects_named_configuration(run_db, tmp_path, selection, command):
    result, calls = run_db(*command, *selection, background=True)
    assert result.returncode == 0, result.stderr
    log = tmp_path / "home/Developer/work/addingwell/.local/logs/cloud-sql-proxy-production.log"
    assert log.is_file()
    assert calls["proxy"] == [
        "pentla" if selection else "didomi",
        "--gcloud-auth",
        "--port",
        "5434",
        "addingwell-prod:europe-west1:addingwell-prod-postgres-13",
    ]
    if command[0] == "dump":
        assert calls["pg"][0] == "personal"
        assert "--port=5434" in calls["pg"]


@pytest.mark.parametrize("selection", [[], ["--account", "pentla"]])
def test_staging_dump_signs_in_as_the_configuration_account(run_db, selection):
    result, calls = run_db("dump", "staging", *selection, background=True)
    assert result.returncode == 0, result.stderr
    account = "pentla" if selection else "didomi"
    assert calls["proxy"][:3] == [account, "--gcloud-auth", "--auto-iam-authn"]
    assert f"--username={account}@didomi.test" in calls["pg"]
    assert not any(arg.startswith("--password") for arg in calls["pg"])


def test_production_keeps_the_postgres_user(run_db):
    result, calls = run_db("dump", "production", background=True)
    assert result.returncode == 0, result.stderr
    assert "--auto-iam-authn" not in calls["proxy"]
    assert "--username=postgres" in calls["pg"]


@pytest.mark.parametrize("command", [["staging"], ["dump", "staging"]])
def test_staging_without_a_signed_in_account_stops_before_the_proxy(run_db, command):
    result, calls = run_db(*command, signed_out=True)
    assert result.returncode != 0
    assert "No account is signed in to the 'didomi' gcloud configuration" in result.stderr
    assert calls == {"proxy": [], "pg": []}


@pytest.mark.parametrize("command", [["local"], ["dump", "local"], ["restore", "sample.dump"]])
def test_local_operations_need_no_cloud_credentials(run_db, command):
    result, calls = run_db(*command)
    assert result.returncode == 0, result.stderr
    assert calls["proxy"] == []
    assert "Account:" not in result.stdout


def test_dump_writes_to_local_backups(run_db, tmp_path):
    result, calls = run_db("dump", "local")
    assert result.returncode == 0, result.stderr
    file_argument = next(arg for arg in calls["pg"] if arg.startswith("--file="))
    dump = Path(file_argument.removeprefix("--file="))
    assert dump.parent == tmp_path / "home/Developer/work/addingwell/.local/backups"
    assert dump.is_file()


def test_dump_dry_run_shows_selection_without_starting_proxy(run_db):
    result, calls = run_db("dump", "staging", "--account", "pentla", "--dry")
    assert result.returncode == 0, result.stderr
    assert "Account: pentla (gcloud configuration)" in result.stdout
    assert "as pentla@didomi.test" in result.stdout
    assert calls == {"proxy": [], "pg": []}


@pytest.mark.parametrize("command", [["staging"], ["dump", "staging"]])
def test_running_proxy_is_reused_without_changing_its_account(run_db, command):
    result, calls = run_db(*command, "--account", "pentla", reused=True)
    assert result.returncode == 0, result.stderr
    assert calls["proxy"] == []
    assert "Stop this one to change accounts" in result.stdout


def test_account_requires_a_value(run_db):
    result, calls = run_db("staging", "--account")
    assert result.returncode != 0
    assert calls == {"proxy": [], "pg": []}


def test_help_describes_named_configuration_default(run_db):
    result, calls = run_db("--help")
    assert result.returncode == 0, result.stderr
    assert "--account NAME Named gcloud configuration (default: didomi)" in result.stdout
    assert calls == {"proxy": [], "pg": []}
