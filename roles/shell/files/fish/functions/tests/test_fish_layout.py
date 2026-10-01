import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROLE = Path(__file__).resolve().parents[4]
FISH = ROLE / "files/fish"
TASKS = yaml.safe_load((ROLE / "tasks/main.yml").read_text())


@pytest.mark.parametrize("category", ["conf.d", "functions"])
def test_each_source_belongs_to_a_documented_feature(category):
    root = FISH / category
    sources = list(root.rglob("*.fish"))
    assert sources
    for source in sources:
        assert source.parent.parent == root, source
        assert (source.parent / "README.md").is_file(), source
    assert len({source.name for source in sources}) == len(sources)


@pytest.mark.parametrize(
    "category,discovery,installation",
    [
        ("conf.d", "Discover fish conf.d snippets", "Symlink fish conf.d"),
        ("functions", "Discover fish function sources", "Symlink fish functions"),
    ],
)
def test_recursive_discovery_preserves_flat_installation(category, discovery, installation):
    discover = next(task for task in TASKS if task["name"] == discovery)
    install = next(task for task in TASKS if task["name"] == installation)
    assert discover["ansible.builtin.find"] == {
        "paths": "{{ role_path }}/files/fish/" + category,
        "patterns": "*.fish",
        "file_type": "file",
        "recurse": True,
    }
    assert install["ansible.builtin.file"] == {
        "src": "{{ item.path }}",
        "dest": "{{ HOME }}/.config/fish/" + category + "/{{ item.path | basename }}",
        "state": "link",
        "force": True,
    }
    assert discover["register"] + ".files" in install["loop"]


@pytest.mark.parametrize(
    "guard,variable,register,installation",
    [
        ("Require unique fish conf.d filenames", "fish_confd_names", "fish_confd_sources", "Symlink fish conf.d"),
        ("Require unique fish function filenames", "fish_function_names", "fish_function_sources", "Symlink fish functions"),
    ],
)
def test_duplicate_filename_guards_run_before_linking(guard, variable, register, installation):
    check = next(task for task in TASKS if task["name"] == guard)
    install = next(task for task in TASKS if task["name"] == installation)
    assert TASKS.index(check) < TASKS.index(install)
    assert check["vars"][variable] == (
        "{{ " + register + ".files | map(attribute='path') | map('basename') | list }}"
    )
    assert check["ansible.builtin.assert"]["that"] == [
        variable + " | unique | length == " + variable + " | length"
    ]


def test_pruning_preserves_grouped_sources_and_foreign_links():
    install = next(task for task in TASKS if task["name"] == "Symlink fish functions")
    prune = next(task for task in TASKS if task["name"] == "Prune fish function symlinks whose source is gone")
    inspect = next(task for task in TASKS if task["name"] == "Inspect linked fish function targets")
    assert TASKS.index(install) < TASKS.index(inspect) < TASKS.index(prune)
    assert inspect["ansible.builtin.stat"] == {"path": "{{ item.path }}", "follow": False}
    assert inspect["loop"] == "{{ fish_function_links.files }}"
    assert inspect["register"] == "fish_function_link_stats"
    assert prune["loop"] == "{{ fish_function_link_stats.results }}"
    assert prune["ansible.builtin.file"]["path"] == "{{ item.item.path }}"
    assert prune["vars"]["functions_dir"] == "{{ role_path }}/files/fish/functions"
    assert prune["when"] == [
        "item.stat.lnk_source.startswith(functions_dir ~ '/')",
        "(item.item.path | basename) not in (fish_function_sources.files | map(attribute='path') | map('basename') | list)",
    ]


def test_readme_local_links_resolve():
    readmes = [ROLE / "README.md", ROLE / "docs/lns.md", *FISH.rglob("README.md")]
    for readme in readmes:
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", readme.read_text()):
            if "://" not in target:
                assert (readme.parent / target).exists(), (readme, target)


def test_flat_links_autoload_functions_from_grouped_sources(tmp_path):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("Fish is required for autoload tests")
    home = tmp_path / "home"
    functions = home / ".config/fish/functions"
    functions.mkdir(parents=True)
    sources = sorted((FISH / "functions").rglob("*.fish"))
    for source in sources:
        (functions / source.name).symlink_to(source)
    names = " ".join(source.stem for source in sources)
    result = subprocess.run(
        [fish, "--no-config", "--command",
         f'set -g fish_function_path "{functions}" $fish_function_path; '
         f'functions -q {names}; or exit 1; _ui note "autoloaded"'],
        env={**os.environ, "HOME": str(home), "NO_COLOR": "1"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "autoloaded" in result.stdout
