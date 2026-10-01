import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

SNIPPET = Path(__file__).resolve().parents[2] / "conf.d/gcloud-profiles/gcloud-profiles.fish"


@pytest.fixture
def home(tmp_path):
    home = (tmp_path / "home").resolve()
    for directory in (
        "Developer/work/addingwell/backend/tests",
        "Developer/work/addingwell-other",
        "other-project",
        "bin",
    ):
        (home / directory).mkdir(parents=True)
    cloud_stub = home / "bin" / "gcloud"
    cloud_stub.write_text(
        "#!/bin/sh\nprintf 'unexpected cloud command\\n' >&2\nexit 1\n"
    )
    cloud_stub.chmod(0o755)
    return home


@pytest.fixture
def run_fish(home):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("Fish is required for shell behavior tests")

    def run(script, *, configuration=None, cwd=None, interactive=True):
        env = os.environ.copy()
        env.update(
            HOME=str(home),
            XDG_CONFIG_HOME=str(home / ".config"),
            XDG_DATA_HOME=str(home / ".local" / "share"),
            XDG_CACHE_HOME=str(home / ".cache"),
            TERM="dumb",
            TEST_GCLOUD_SNIPPET=str(SNIPPET),
            TEST_FISH_BINARY=fish,
            PATH=os.pathsep.join((str(home / "bin"), env["PATH"])),
        )
        env.pop("CLOUDSDK_ACTIVE_CONFIG_NAME", None)
        if configuration is not None:
            env["CLOUDSDK_ACTIVE_CONFIG_NAME"] = configuration
        commands = r"""
function show_profile
    if set -q CLOUDSDK_ACTIVE_CONFIG_NAME
        printf 'set:%s\n' "$CLOUDSDK_ACTIVE_CONFIG_NAME"
    else
        printf 'unset\n'
    end
end
source "$TEST_GCLOUD_SNIPPET"
""" + script
        args = [fish, "--no-config"]
        if interactive:
            args.append("--interactive")
        result = subprocess.run(
            [*args, "--command", commands],
            cwd=cwd or home,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert (result.returncode, result.stderr) == (0, ""), result.stdout
        return result.stdout.splitlines()

    return run


def profile(value):
    return "unset" if value is None else f"set:{value}"


@pytest.mark.parametrize("configuration", [None, "", "personal"])
def test_unmapped_startup_preserves_environment(run_fish, configuration):
    assert run_fish("show_profile", configuration=configuration) == [
        profile(configuration)
    ]


@pytest.mark.parametrize("child", ["", "backend/tests"])
def test_mapped_startup_and_restore(run_fish, home, child):
    root = home / "Developer" / "work" / "addingwell"
    assert run_fish(
        'show_profile; cd "$HOME"; show_profile',
        cwd=root / child,
        configuration="pentla",
    ) == ["set:didomi", "set:pentla"]


@pytest.mark.parametrize("configuration", [None, "", "pentla"])
def test_directory_events_and_sibling_boundary(run_fish, configuration):
    assert run_fish(
        r"""
show_profile
cd "$HOME/Developer/work/addingwell"
show_profile
cd backend/tests
show_profile
cd "$HOME/Developer/work/addingwell-other"
show_profile
""",
        configuration=configuration,
    ) == [profile(configuration), "set:didomi", "set:didomi", profile(configuration)]


@pytest.mark.parametrize("child_first", [False, True])
def test_most_specific_mapping_wins_in_either_order(run_fish, child_first):
    pairs = [
        '"$HOME/Developer/work/addingwell" didomi',
        '"$HOME/Developer/work/addingwell/backend" pentla',
    ]
    if child_first:
        pairs.reverse()
    assert run_fish(
        "set -g GCLOUD_DIRECTORY_PROFILES " + " ".join(pairs) + r"""
cd "$HOME/Developer/work/addingwell/backend/tests"
show_profile
cd ../..
show_profile
cd "$HOME"
show_profile
""",
        configuration="personal",
    ) == ["set:pentla", "set:didomi", "set:personal"]


def test_transitions_between_roots_preserve_original_snapshot(run_fish):
    assert run_fish(
        r"""
set -g GCLOUD_DIRECTORY_PROFILES \
    "$HOME/Developer/work/addingwell" didomi \
    "$HOME/other-project" pentla
cd "$HOME/Developer/work/addingwell"
show_profile
cd "$HOME/other-project"
show_profile
cd "$HOME"
show_profile
""",
        configuration="personal",
    ) == ["set:didomi", "set:pentla", "set:personal"]


@pytest.mark.parametrize("configuration", [None, "", "personal"])
def test_resourcing_preserves_snapshot(run_fish, configuration):
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell"
source "$TEST_GCLOUD_SNIPPET"
source "$TEST_GCLOUD_SNIPPET"
show_profile
cd "$HOME"
show_profile
""",
        configuration=configuration,
    ) == ["set:didomi", profile(configuration)]


def test_new_entry_captures_updated_unmapped_baseline(run_fish):
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell"
cd "$HOME"
show_profile
set -gx CLOUDSDK_ACTIVE_CONFIG_NAME pentla
cd "$HOME/Developer/work/addingwell"
show_profile
cd "$HOME"
show_profile
"""
    ) == ["unset", "set:didomi", "set:pentla"]


def test_logical_symlink_path_does_not_match_target(run_fish, home):
    (home / "linked-project").symlink_to(home / "Developer/work/addingwell")
    assert run_fish(
        'cd "$HOME/linked-project/backend"; show_profile',
        configuration="personal",
    ) == ["set:personal"]


def test_roots_with_spaces_and_glob_characters_are_literal(run_fish, home):
    (home / "project [work]*").mkdir()
    (home / "project w-other").mkdir()
    assert run_fish(
        r"""
set -g GCLOUD_DIRECTORY_PROFILES "$HOME/project [work]*" pentla
cd "$HOME/project [work]*"
show_profile
cd "$HOME/project w-other"
show_profile
"""
    ) == ["set:pentla", "unset"]


@pytest.mark.parametrize("root", ['"$HOME/"', "/"])
def test_normalized_and_filesystem_roots(run_fish, root):
    assert run_fish(
        "set -g GCLOUD_DIRECTORY_PROFILES " + root + r""" personal \
    "$HOME/Developer/work/addingwell/" didomi
cd "$HOME/other-project"
show_profile
cd "$HOME/Developer/work/addingwell/backend"
show_profile
"""
    ) == ["set:personal", "set:didomi"]


@pytest.mark.parametrize("configuration", [None, "pentla"])
def test_noninteractive_shell_does_not_register_or_switch(run_fish, home, configuration):
    assert run_fish(
        r"""
if functions -q __gcloud_directory_profile; or set -q GCLOUD_DIRECTORY_PROFILES
    printf 'unexpected switcher registration\n'
end
show_profile
cd "$HOME"
show_profile
""",
        cwd=home / "Developer/work/addingwell",
        configuration=configuration,
        interactive=False,
    ) == [profile(configuration), profile(configuration)]


def test_independent_shells_have_independent_baselines(run_fish, home):
    assert run_fish(
        'show_profile; cd "$HOME"; show_profile',
        cwd=home / "Developer/work/addingwell",
        configuration="personal",
    ) == ["set:didomi", "set:personal"]
    assert run_fish("show_profile", configuration="pentla") == ["set:pentla"]


def test_nested_shell_restores_inherited_configuration(run_fish):
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell"
show_profile
"$TEST_FISH_BINARY" --no-config --interactive --command \
    'source "$TEST_GCLOUD_SNIPPET"; cd "$HOME"; printf "set:%s\n" "$CLOUDSDK_ACTIVE_CONFIG_NAME"'
cd "$HOME"
show_profile
""",
        configuration="personal",
    ) == ["set:didomi", "set:didomi", "set:personal"]


def test_project_envrc_is_not_executed(run_fish, home):
    root = home / "Developer/work/addingwell"
    (root / ".envrc").write_text('touch "$HOME/project-env-loaded"\n')
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell/backend"
if set -q PROJECT_ENV_WAS_LOADED
    printf 'unexpected project environment\n'
end
show_profile
cd "$HOME"
show_profile
"""
    ) == ["set:didomi", "unset"]
    assert not (home / "project-env-loaded").exists()


def test_hook_has_no_project_file_loader():
    source = SNIPPET.read_text()
    assert not any(loader in source for loader in ("source ", ".env", "dotenv", "direnv"))


def test_provisioning_creates_directory_and_backs_up_snippet():
    tasks = yaml.safe_load((SNIPPET.parents[4] / "tasks/main.yml").read_text())
    directories = next(
        task for task in tasks if task["name"] == "Ensure shell config directories exist"
    )
    backups = next(
        task for task in tasks if task["name"] == "Check if files to backup exists"
    )
    assert ".config/fish/conf.d" in directories["with_items"]
    assert ".config/fish/conf.d/gcloud-profiles.fish" in backups["with_items"]
