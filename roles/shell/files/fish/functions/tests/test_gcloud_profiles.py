import json
import os
import shlex
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
def profiles_config(home):
    config = home / ".config/gcloud-profiles/config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"~/Developer/work/addingwell": "didomi"}))
    return config


@pytest.fixture
def run_fish(home, profiles_config):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("Fish is required for shell behavior tests")

    def run(
        script, *, configuration=None, cwd=None, interactive=True, expected_error=None
    ):
        env = os.environ.copy()
        env.update(
            HOME=str(home),
            XDG_CONFIG_HOME=str(home / ".config"),
            XDG_DATA_HOME=str(home / ".local" / "share"),
            XDG_CACHE_HOME=str(home / ".cache"),
            TERM="dumb",
            TEST_GCLOUD_SNIPPET=str(SNIPPET),
            TEST_GCLOUD_CONFIG=str(profiles_config),
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
        assert result.returncode == 0, (result.stdout, result.stderr)
        if expected_error is None:
            assert result.stderr == "", result.stdout
        else:
            assert expected_error in result.stderr
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
def test_most_specific_mapping_wins_in_either_order(
    run_fish, profiles_config, child_first
):
    pairs = [
        ("~/Developer/work/addingwell", "didomi"),
        ("~/Developer/work/addingwell/backend", "pentla"),
    ]
    if child_first:
        pairs.reverse()
    profiles_config.write_text(json.dumps(dict(pairs)))
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell/backend/tests"
show_profile
cd ../..
show_profile
cd "$HOME"
show_profile
""",
        configuration="personal",
    ) == ["set:pentla", "set:didomi", "set:personal"]


def test_transitions_between_roots_preserve_original_snapshot(run_fish, profiles_config):
    profiles_config.write_text(
        json.dumps({"~/Developer/work/addingwell": "didomi", "~/other-project": "pentla"})
    )
    assert run_fish(
        r"""
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


def test_roots_with_spaces_and_glob_characters_are_literal(run_fish, home, profiles_config):
    (home / "project [work]*").mkdir()
    (home / "project w-other").mkdir()
    profiles_config.write_text(json.dumps({"~/project [work]*": "pentla"}))
    assert run_fish(
        r"""
cd "$HOME/project [work]*"
show_profile
cd "$HOME/project w-other"
show_profile
"""
    ) == ["set:pentla", "unset"]


@pytest.mark.parametrize("root", ["~/", "/"])
def test_normalized_and_filesystem_roots(run_fish, profiles_config, root):
    profiles_config.write_text(
        json.dumps({root: "personal", "~/Developer/work/addingwell/": "didomi"})
    )
    assert run_fish(
        r"""
cd "$HOME/other-project"
show_profile
cd "$HOME/Developer/work/addingwell/backend"
show_profile
"""
    ) == ["set:personal", "set:didomi"]


def test_absolute_root_loads_from_json(run_fish, home, profiles_config):
    root = home / "Developer/work/addingwell"
    profiles_config.write_text(json.dumps({str(root): "pentla"}))
    assert run_fish(
        'show_profile; cd "$HOME"; show_profile', cwd=root, configuration="personal"
    ) == ["set:pentla", "set:personal"]


@pytest.mark.parametrize("configuration", [None, "", "personal"])
def test_empty_config_preserves_environment(run_fish, profiles_config, configuration):
    profiles_config.write_text("{}")
    assert run_fish(
        'show_profile; cd "$HOME/Developer/work/addingwell"; show_profile',
        configuration=configuration,
    ) == [profile(configuration), profile(configuration)]


@pytest.mark.parametrize("configuration", [None, "", "personal"])
def test_config_edits_require_source_and_preserve_snapshot(run_fish, configuration):
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell"
show_profile
printf '%s\n' '{"~/Developer/work/addingwell": "pentla"}' > "$TEST_GCLOUD_CONFIG"
cd backend/tests
show_profile
source "$TEST_GCLOUD_SNIPPET"
show_profile
cd "$HOME"
show_profile
""",
        configuration=configuration,
    ) == ["set:didomi", "set:didomi", "set:pentla", profile(configuration)]


@pytest.mark.parametrize("configuration", [None, "", "personal"])
def test_empty_config_reload_restores_snapshot(run_fish, configuration):
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell"
show_profile
printf '{}\n' > "$TEST_GCLOUD_CONFIG"
source "$TEST_GCLOUD_SNIPPET"
show_profile
cd backend/tests
show_profile
""",
        configuration=configuration,
    ) == ["set:didomi", profile(configuration), profile(configuration)]


@pytest.mark.parametrize("configuration", [None, "", "personal"])
def test_invalid_startup_config_preserves_environment(
    run_fish, home, profiles_config, configuration
):
    profiles_config.write_text("{")
    assert run_fish(
        'show_profile; cd "$HOME"; show_profile',
        cwd=home / "Developer/work/addingwell",
        configuration=configuration,
        expected_error="parse error",
    ) == [profile(configuration), profile(configuration)]


@pytest.mark.parametrize("configuration", [None, "", "personal"])
def test_failed_reload_discards_partial_output_and_preserves_snapshot(
    run_fish, configuration
):
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell"
show_profile
printf '%s\n' '{"~/Developer/work/addingwell": "pentla"}' '{' > "$TEST_GCLOUD_CONFIG"
source "$TEST_GCLOUD_SNIPPET"
show_profile
cd "$HOME"
show_profile
cd "$HOME/Developer/work/addingwell/backend"
show_profile
cd "$HOME"
show_profile
""",
        configuration=configuration,
        expected_error="parse error",
    ) == [
        "set:didomi",
        "set:didomi",
        profile(configuration),
        "set:didomi",
        profile(configuration),
    ]


@pytest.mark.parametrize("interactive", [False, True])
def test_jq_runs_only_when_sourced(run_fish, home, interactive):
    jq = shutil.which("jq")
    assert jq is not None
    wrapper = home / "bin/jq"
    wrapper.write_text(
        '#!/bin/sh\nprintf "parse\\n" >> "$HOME/jq-calls"\n'
        f'exec {shlex.quote(jq)} "$@"\n'
    )
    wrapper.chmod(0o755)
    assert run_fish(
        r"""
cd "$HOME/Developer/work/addingwell"
show_profile
cd backend/tests
show_profile
cd "$HOME"
show_profile
source "$TEST_GCLOUD_SNIPPET"
show_profile
""",
        interactive=interactive,
    ) == (
        ["set:didomi", "set:didomi", "unset", "unset"] if interactive else ["unset"] * 4
    )
    calls = home / "jq-calls"
    if interactive:
        assert calls.read_text().splitlines() == ["parse", "parse"]
    else:
        assert not calls.exists()


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


def test_provisioning_creates_directory_and_links_mappings():
    tasks = yaml.safe_load((SNIPPET.parents[4] / "tasks/main.yml").read_text())
    directories = next(
        task for task in tasks if task["name"] == "Ensure shell config directories exist"
    )
    assert ".config/fish/conf.d" in directories["loop"]
    assert ".config/gcloud-profiles" in directories["loop"]
    configs = next(task for task in tasks if task["name"] == "Symlink shell configs")
    assert configs["ansible.builtin.file"]["dest"] == "{{ HOME }}/.config/{{ item.dest }}"
    assert {
        "src": "fish/conf.d/gcloud-profiles/config.json",
        "dest": "gcloud-profiles/config.json",
    } in configs["loop"]
    defaults = yaml.safe_load((SNIPPET.parents[4] / "defaults/main.yml").read_text())
    assert "jq" in defaults["BREW_PACKAGES"]["formulas"]


def test_shipped_config_contains_the_initial_mappings():
    assert json.loads(SNIPPET.with_name("config.json").read_text()) == {
        "~/Developer/work/addingwell": "didomi",
        "~/Developer/work/pentla": "pentla",
    }
