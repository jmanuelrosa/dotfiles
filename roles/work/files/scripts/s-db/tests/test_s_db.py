import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotkit.testing import FISH_FUNCTIONS

SCRIPT = Path(__file__).resolve().parents[1] / "s-db"
STAGING_INSTANCES = {
    "didomi": "addingwell-dev-326312:europe-west1:addingwell-dev-postgres",
    "pentla": "pentla-staging:europe-west1:pentla-api-staging-db",
}


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
    (functions / "gcp_adc.fish").symlink_to(FISH_FUNCTIONS / "gcp_adc/gcp_adc.fish")
    for account in STAGING_INSTANCES:
        adc = home / f".config/gcloud-profiles/adc/{account}/application_default_credentials.json"
        adc.parent.mkdir(parents=True)
        adc.write_text("{}")
    bin_dir = home / "bin"
    bin_dir.mkdir()
    proxy_call = tmp_path / "proxy-call"
    pg_call = tmp_path / "pg-call"
    cloud_call = tmp_path / "cloud-call"

    stubs = {
        local / "bin/cloud-sql-proxy": f"""#!{fish}
printf '%s\\n' "$CLOUDSDK_ACTIVE_CONFIG_NAME" $argv > "$PROXY_CALL"
printf '%s\\n' "$GOOGLE_APPLICATION_CREDENTIALS" > "$ADC_CALL"
if test "$PROXY_FAILURE" = 1
    printf '%s\\n' 'ADC login required' >&2
    exit 1
end
if test "$PROXY_BACKGROUND" = 1
    exec sleep 2
end
""",
        bin_dir / "lsof": """#!/bin/sh
if [ "$PROXY_REUSED" = 1 ]; then
    printf '4242\\n'
fi
""",
        bin_dir / "ps": "#!/bin/sh\nprintf 'cloud-sql-proxy\\n'\n",
        bin_dir / "gcloud": f"""#!{fish}
switch (string join ' ' -- $argv)
    case 'config get-value account'
        if test "$GCLOUD_SIGNED_OUT" != 1
            printf '%s@didomi.test\\n' "$CLOUDSDK_ACTIVE_CONFIG_NAME"
        end
    case 'config get-value project'
        echo "$CLOUDSDK_ACTIVE_CONFIG_NAME-project"
    case 'auth application-default login *'
        test "$CLOUDSDK_CONFIG" = "$HOME/.config/gcloud-profiles/adc/$LOGIN_PROFILE"; or exit 1
        test "$CLOUDSDK_ACTIVE_CONFIG_NAME" = default; or exit 1
        test -z "$GOOGLE_APPLICATION_CREDENTIALS"; or exit 1
        printf '%s\\n' $argv > "$CLOUD_CALL"
        test "$LOGIN_FAILURE" != 1; or exit 1
        printf '{{}}\\n' > "$CLOUDSDK_CONFIG/application_default_credentials.json"
    case '*'
        printf '%s\\n' 'Unexpected cloud command' >&2
        exit 1
end
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
        CLOUDSDK_ACTIVE_CONFIG_NAME="didomi",
        GOOGLE_APPLICATION_CREDENTIALS=str(home / "unused-adc.json"),
        PROXY_CALL=str(proxy_call),
        PG_CALL=str(pg_call),
        CLOUD_CALL=str(cloud_call),
        ADC_CALL=str(tmp_path / "adc-call"),
    )

    def run(
        *args, background=False, reused=False, signed_out=False, proxy_failure=False,
        configuration="didomi", missing_adc=False, answer=None, login_failure=False,
    ):
        if missing_adc:
            for adc in (home / ".config/gcloud-profiles/adc").glob("*/*.json"):
                adc.unlink()
        terminal = "function isatty; return 0; end; " if answer is not None else ""
        result = subprocess.run(
            [
                fish,
                "--no-config",
                "--command",
                (
                    terminal
                    + 'set -p fish_function_path "$HOME/.config/fish/functions"; '
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
                "PROXY_FAILURE": str(int(proxy_failure)),
                "CLOUDSDK_ACTIVE_CONFIG_NAME": configuration,
                "LOGIN_PROFILE": "pentla" if "pentla" in args else configuration,
                "LOGIN_FAILURE": str(int(login_failure)),
            },
            input=f"{answer}\n" if answer is not None else None,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            assert result.stderr == "", result.stderr
        if answer != "y":
            assert not cloud_call.exists(), "s-db must not authenticate without confirmation"
        calls = {
            name: path.read_text().splitlines() if path.exists() else []
            for name, path in (("proxy", proxy_call), ("pg", pg_call))
        }
        if "--auto-iam-authn" in calls["proxy"]:
            account = calls["proxy"][0]
            assert (tmp_path / "adc-call").read_text().strip() == str(
                home / f".config/gcloud-profiles/adc/{account}/application_default_credentials.json"
            )
        return result, calls

    return run


@pytest.mark.parametrize("command", [[], ["connect"]])
@pytest.mark.parametrize(
    "selection", [[], ["--account", "didomi"], ["--account", "pentla"], ["-a", "pentla"]]
)
def test_foreground_proxy_selects_named_configuration_and_target(run_db, command, selection):
    result, calls = run_db(*command, "staging", *selection)
    assert result.returncode == 0, result.stderr
    account = selection[-1] if selection else "didomi"
    assert calls["proxy"] == [
        account,
        "--auto-iam-authn",
        f"--quota-project={STAGING_INSTANCES[account].split(':')[0]}",
        "--run-connection-test",
        "--port",
        "5433",
        STAGING_INSTANCES[account],
    ]
    assert calls["pg"] == []
    assert f"Project: {STAGING_INSTANCES[account].split(':')[0]}" in result.stdout
    assert f"Instance: {STAGING_INSTANCES[account]}" in result.stdout
    assert f"User: {account}@didomi.test" in result.stdout
    assert "Password: none, the proxy signs in with IAM" in result.stdout


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
        assert calls["pg"][0] == "didomi"
        assert "--port=5434" in calls["pg"]


@pytest.mark.parametrize("selection", [[], ["--account", "pentla"]])
def test_staging_dump_signs_in_as_the_configuration_account(run_db, selection):
    result, calls = run_db("dump", "staging", *selection, background=True)
    assert result.returncode == 0, result.stderr
    account = "pentla" if selection else "didomi"
    assert calls["proxy"] == [
        account,
        "--auto-iam-authn",
        f"--quota-project={STAGING_INSTANCES[account].split(':')[0]}",
        "--run-connection-test",
        "--port",
        "5433",
        STAGING_INSTANCES[account],
    ]
    assert "--gcloud-auth" not in calls["proxy"]
    database = "pentla" if selection else "addingwell"
    assert f"--dbname={database}" in calls["pg"]
    assert f"--username={account}@didomi.test" in calls["pg"]
    assert not any(arg.startswith("--password") for arg in calls["pg"])


@pytest.mark.parametrize("selection", [[], ["--account", "pentla"]])
def test_staging_detached_proxy_uses_adc(run_db, selection):
    result, calls = run_db("staging", "--detach", *selection, background=True)
    assert result.returncode == 0, result.stderr
    assert "--auto-iam-authn" in calls["proxy"]
    assert "--gcloud-auth" not in calls["proxy"]
    assert "Application Default Credentials" in result.stdout
    account = "pentla" if selection else "didomi"
    assert calls["proxy"][-1] == STAGING_INSTANCES[account]
    assert f"Project: {STAGING_INSTANCES[account].split(':')[0]}" in result.stdout
    assert f"Instance: {STAGING_INSTANCES[account]}" in result.stdout
    assert f"gcp_adc login {account}" in result.stdout


@pytest.mark.parametrize(
    ("command", "error"),
    [
        (["staging"], "ADC login required"),
        (["staging", "--detach"], "Failed to start cloud-sql-proxy"),
        (["dump", "staging"], "Failed to start cloud-sql-proxy"),
    ],
)
def test_proxy_failure_does_not_report_a_connection_or_dump(run_db, command, error):
    result, calls = run_db(*command, proxy_failure=True)
    assert result.returncode != 0
    assert "Connected" not in result.stdout
    assert "Dumped" not in result.stdout
    assert calls["pg"] == []
    assert error in result.stderr
    assert "roles/serviceusage.serviceUsageConsumer" in result.stderr
    assert "roles/cloudsql.client" in result.stderr
    assert "roles/cloudsql.instanceUser" in result.stderr


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
    result, calls = run_db(*command, missing_adc=True, signed_out=True)
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
    assert "--dbname=pentla" in result.stdout
    assert calls == {"proxy": [], "pg": []}


@pytest.mark.parametrize("command", [["staging"], ["dump", "staging"]])
@pytest.mark.parametrize("missing_adc", [False, True])
def test_running_proxy_is_reused_without_changing_its_account(run_db, command, missing_adc):
    result, calls = run_db(
        *command, "--account", "pentla", reused=True, missing_adc=missing_adc
    )
    assert result.returncode == 0, result.stderr
    assert calls["proxy"] == []
    assert "Stop this one to change accounts" in result.stdout


@pytest.mark.parametrize("command", [["staging"], ["dump", "staging"]])
def test_directory_configuration_is_the_default(run_db, command):
    result, calls = run_db(*command, configuration="pentla", background=True)
    assert result.returncode == 0, result.stderr
    assert calls["proxy"][0] == "pentla"
    assert calls["proxy"][-1] == STAGING_INSTANCES["pentla"]


def test_explicit_account_overrides_the_directory_configuration(run_db):
    result, calls = run_db("staging", "--account", "didomi", configuration="pentla")
    assert result.returncode == 0, result.stderr
    assert calls["proxy"][0] == "didomi"


def test_unset_directory_configuration_uses_didomi(run_db):
    result, calls = run_db("staging", configuration="")
    assert result.returncode == 0, result.stderr
    assert calls["proxy"][0] == "didomi"


@pytest.mark.parametrize("command", [["staging"], ["staging", "--detach"], ["dump", "staging"]])
def test_missing_adc_in_automation_stops_with_setup_instructions(run_db, command):
    result, calls = run_db(*command, missing_adc=True)
    assert result.returncode != 0
    assert "gcp_adc login didomi" in result.stderr
    assert calls == {"proxy": [], "pg": []}


@pytest.mark.parametrize("answer", ["n", ""])
def test_missing_adc_declined_login_stops_before_connecting(run_db, answer):
    result, calls = run_db("staging", missing_adc=True, answer=answer)
    assert result.returncode != 0
    assert "No ADC credentials saved" in result.stdout
    assert calls == {"proxy": [], "pg": []}


def test_missing_adc_confirmed_login_saves_the_selected_profile(run_db):
    result, calls = run_db("staging", "--account", "pentla", missing_adc=True, answer="y")
    assert result.returncode == 0, result.stderr
    assert calls["proxy"][0] == "pentla"


def test_failed_adc_login_stops_before_connecting(run_db):
    result, calls = run_db("staging", missing_adc=True, answer="y", login_failure=True)
    assert result.returncode != 0
    assert calls == {"proxy": [], "pg": []}


def test_dry_run_does_not_require_or_create_adc(run_db):
    result, calls = run_db("dump", "staging", "--dry", missing_adc=True)
    assert result.returncode == 0, result.stderr
    assert calls == {"proxy": [], "pg": []}


def test_account_requires_a_value(run_db):
    result, calls = run_db("staging", "--account")
    assert result.returncode != 0
    assert calls == {"proxy": [], "pg": []}


def test_help_describes_named_configuration_default(run_db):
    result, calls = run_db("--help")
    assert result.returncode == 0, result.stderr
    assert "--account NAME Named gcloud configuration (default: didomi)" in result.stdout
    assert "Application Default Credentials" in result.stdout
    assert calls == {"proxy": [], "pg": []}
