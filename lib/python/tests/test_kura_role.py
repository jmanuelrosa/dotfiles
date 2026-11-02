"""How kura reaches this machine, and what this repository's catalog owes it.

kura used to live in `roles/ai/files/scripts/claude-kit/` and its suite ran here. It is
released separately now, so what remains is the half this repository can break:

  the installer   a pinned release and checksum, machine config and catalog links, the
                  catalog commit CI tests against, and the `kura sync` the role runs on
                  every play
  the harness     that every artifact this repository ships is loadable

Kura manages skills, standalone agents and bundles, and owns the native roots they are
linked into; the seats and the product pipeline are bundles inside the catalog. The tool's own behaviour is
asserted in its own repository against a fixture catalog, and the catalog's content in the catalog's own tests.
Nothing here imports kura: the derivations that need its answers ask the
installed command and skip when it is absent or predates the multi-harness interface.
"""

import json
import re
import tomllib

import pytest
import yaml
from dotkit.testing import (
    CLAUDE_SETTINGS,
    HARNESS,
    REPO,
    ai_defaults,
    harness_links,
)

AI_TASKS = REPO / "roles/ai/tasks/main.yml"
AI_DEFAULTS = REPO / "roles/ai/defaults/main.yml"
COREUTILS_DEFAULTS = REPO / "roles/coreutils/defaults/main.yml"
CI_WORKFLOW = REPO / ".github/workflows/pull_request.yml"
SETTINGS = CLAUDE_SETTINGS

SYNC_TASK = "Sync global skills and agents with kura"
INSTALL_TASK = "Install the pinned kura release"
CONFIG_TASK = "Link kura's catalog and machine config"
CLONE_TASK = "Clone the agent catalog"
LINK_TASK = "Link AI scripts into the user bin directory"
HOSTOF_TASK = "Install the pinned hostof release"

# The two roles that still install checkout-owned scripts with a manifest and a link
# loop. An externally released command has its own installation contract, asserted
# separately below.
INSTALLERS = [
    ("ai", "AI_SCRIPTS", LINK_TASK),
    ("work", "WORK_SCRIPTS", "Link work scripts into the user bin directory"),
]

def role_task(role, name):
    tasks = yaml.safe_load((REPO / f"roles/{role}/tasks/main.yml").read_text())
    matching = [t for t in tasks if t.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the {role} role"
    return matching[0]


def role_manifest(role, var):
    return yaml.safe_load((REPO / f"roles/{role}/defaults/main.yml").read_text())[var]


# --- the installer ------------------------------------------------------------


def test_the_kura_release_is_pinned_to_a_checksum():
    kura = yaml.safe_load(AI_DEFAULTS.read_text())["KURA"]
    assert kura["repository"] == "https://github.com/jmanuelrosa/kura"
    assert re.fullmatch(r"v\d+\.\d+\.\d+", kura["release"])
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", kura["checksum"])


def test_the_role_downloads_kura_as_the_command_file():
    task = role_task("ai", INSTALL_TASK)["ansible.builtin.get_url"]
    assert task == {
        "url": "{{ KURA.repository }}/releases/download/{{ KURA.release }}/kura",
        "dest": "{{ HOME }}/.local/bin/kura",
        "checksum": "{{ KURA.checksum }}",
        "mode": "0755",
    }


def test_kura_is_not_in_the_script_link_manifest():
    """It is downloaded, not linked. An entry here would make the link loop replace the
    released asset with a symlink into a directory this repository no longer holds, and
    the play would report changed while doing it."""
    assert "kura" not in role_manifest("ai", "AI_SCRIPTS")
    assert "claude-kit" not in role_manifest("ai", "AI_SCRIPTS")


def test_the_role_links_kuras_catalog_and_machine_configuration():
    task = role_task("ai", CONFIG_TASK)
    assert task["ansible.builtin.file"] == {
        "src": "{{ item.src }}",
        "dest": "{{ HOME }}/.config/kura/{{ item.name }}",
        "state": "link",
        "force": True,
    }, "force repoints a link naming an older checkout"
    assert task["loop"] == [
        {"name": "catalog", "src": "{{ AGENT_CATALOG.path }}"},
        {"name": "config.json", "src": "{{ HARNESS_DIR }}/kura/config.json"},
    ]
    assert json.loads((HARNESS / "kura/config.json").read_text()) == {
        "schemaVersion": 1,
        "globalHarnesses": ["claude", "pi"],
        "pi": {"agents": {"global": "~/.pi/agent/agents", "project": ".pi/agents"}},
    }


def test_the_role_clones_the_catalog_without_ever_updating_it():
    """`kura update` edits the clone in place, so a pull or reset on a later play would
    clobber registry and skill changes that have not been committed yet."""
    catalog = ai_defaults()["AGENT_CATALOG"]
    assert catalog.keys() == {"repository", "path", "commit"}
    assert catalog["repository"] == "https://github.com/jmanuelrosa/agent-catalog.git"
    assert catalog["path"] == "{{ HOME }}/Developer/agent-catalog"
    task = role_task("ai", CLONE_TASK)
    assert task["ansible.builtin.git"] == {
        "repo": "{{ AGENT_CATALOG.repository }}",
        "dest": "{{ AGENT_CATALOG.path }}",
        "version": "main",
        "update": False,
    }
    assert task["register"] == "agent_catalog"


def test_ci_tests_against_the_pinned_catalog_commit():
    """CI cloning catalog main let a catalog-only change turn this repository red. The pin
    is a full SHA in the defaults, and CI reads it from there so it is written only once."""
    commit = ai_defaults()["AGENT_CATALOG"]["commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", commit)

    steps = yaml.safe_load(CI_WORKFLOW.read_text())["jobs"]["test"]["steps"]
    script = next(step["run"] for step in steps if step.get("name") == CLONE_TASK)
    assert "roles/ai/defaults/main.yml" in script
    assert '["AGENT_CATALOG"]' in script and '["commit"]' in script
    assert "checkout --quiet --detach FETCH_HEAD" in script
    assert "git clone" not in script
    assert commit not in CI_WORKFLOW.read_text(), "the pin lives only in the ai role's defaults"


def test_the_sandbox_reads_the_catalog_where_the_role_clones_it():
    """The sandbox checks the resolved path, so a skill script reached through
    ~/.claude/skills is read from the clone, and a stale rule here denies every one."""
    clone = ai_defaults()["AGENT_CATALOG"]["path"].replace("{{ HOME }}", "~")
    with (HARNESS / "policy/sandbox.toml").open("rb") as handle:
        reads = tomllib.load(handle)["filesystem"]["allow_read"]
    assert f"{clone}/skills" in reads
    assert f"{clone}/bundles" in reads


def test_the_role_syncs_global_artifacts_after_kura_can_read_the_catalog():
    """Bare `kura sync` links both skills and agents; `--type skill` would leave agents out.
    Project convergence stays with the SessionStart hook below, never the play."""
    task = role_task("ai", SYNC_TASK)
    argv = task["ansible.builtin.command"]["argv"]
    assert "[HOME ~ '/.local/bin/kura', 'sync']" in argv
    assert "['--dry-run'] if ansible_check_mode" in argv
    assert "--type" not in argv
    assert task["ansible.builtin.command"]["removes"] == "{{ HOME }}/.local/bin/kura"
    assert task["check_mode"] is False
    assert task["changed_when"] == "', 0 changes' not in kura_sync.stdout"
    assert task["when"] == "not (ansible_check_mode and agent_catalog is changed)", (
        "a check run on a fresh machine has no clone for the dry run to read"
    )

    tasks = yaml.safe_load(AI_TASKS.read_text())
    names = [t["name"] for t in tasks]
    assert names.index(INSTALL_TASK) < names.index(CLONE_TASK) < names.index(CONFIG_TASK) < names.index(SYNC_TASK)
    assert not any("converge" in str(t.get("ansible.builtin.command", "")) for t in tasks)


def test_a_session_start_hook_converges_only_an_initialized_exact_cwd():
    """Kura treats cwd as the exact project and refuses when root kura.json is
    absent. The hook stays silent in an uninitialized directory without hiding a real
    convergence failure in an initialized one."""
    hooks = json.loads(SETTINGS.read_text())["hooks"]["SessionStart"]
    commands = [hook["command"] for entry in hooks for hook in entry["hooks"]]
    converging = [c for c in commands if "kura converge" in c]
    assert converging == [
        "if [ -f ./kura.json ]; then ~/.local/bin/kura converge --quiet; fi"
    ]


def test_standalone_agents_are_catalog_owned_and_global():
    links = harness_links()
    assert not any(dest.startswith("~/.claude/agents/") for dest in links)
    assert "~/.pi/agent/agents" not in links
    assert "{{ HOME }}/.pi/agent/agents" not in ai_defaults()["HARNESS_LINKS"]["pi"]["dirs"]
    assert "{{ HOME }}/.claude/agents" not in ai_defaults()["HARNESS_LINKS"]["claude"]["dirs"]


# --- the installers that still link from this checkout ------------------------


def test_hostof_release_is_pinned_to_a_checksum():
    import re

    hostof = yaml.safe_load(COREUTILS_DEFAULTS.read_text())["HOSTOF"]
    assert hostof["repository"] == "https://github.com/jmanuelrosa/hostof"
    assert re.fullmatch(r"v\d+\.\d+\.\d+", hostof["release"])
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", hostof["checksum"])


def test_coreutils_downloads_hostof_as_the_command_file():
    task = role_task("coreutils", HOSTOF_TASK)["ansible.builtin.get_url"]
    assert task == {
        "url": "{{ HOSTOF.repository }}/releases/download/{{ HOSTOF.release }}/hostof",
        "dest": "{{ HOME }}/.local/bin/hostof",
        "checksum": "{{ HOSTOF.checksum }}",
        "mode": "0755",
    }


@pytest.mark.parametrize(("role", "var", "task_name"), INSTALLERS)
def test_the_link_task_loops_the_manifest_with_an_absolute_source(role, var, task_name):
    """A relative src here is the silent failure worth pinning.

    ansible.builtin.file does not resolve src through the role search path the way copy
    and template do, and with force: true it skips the existence guard too. Drop
    role_path and the play still reports changed while the link dangles.
    """
    task = role_task(role, task_name)
    assert task.get("loop") == "{{ %s }}" % var, "the task should loop the manifest"
    src = task["ansible.builtin.file"]["src"]
    assert "{{ role_path }}" in src, f"src must be absolute, got: {src}"
    assert "{{ item }}/{{ item }}" in src, f"src should be <name>/<name>, got: {src}"
    assert "when" not in task, "the manifest replaces the .md guard; nothing left to skip"
    assert "with_fileglob" not in task, "a glob would match only directories, which fileglob drops"


@pytest.mark.parametrize(("role", "var", "task_name"), INSTALLERS)
def test_every_tool_directory_is_in_the_manifest(role, var, task_name):
    """A tool absent from the manifest is simply never installed, and nothing says so.

    The glob this replaced had the opposite failure, installing whatever was dropped in
    the directory. Both are silent, so the manifest and the directory are pinned to
    each other.
    """
    scripts = REPO / f"roles/{role}/files/scripts"
    on_disk = {
        entry.name
        for entry in scripts.iterdir()
        if entry.is_dir() and not entry.is_symlink() and not entry.name.startswith(".")
    }
    assert on_disk == set(role_manifest(role, var)), (
        f"{role} tool directories do not match {var}"
    )


@pytest.mark.parametrize(("role", "var", "task_name"), INSTALLERS)
def test_every_tool_ships_an_executable_named_after_its_directory(role, var, task_name):
    """The convention the one-line loop depends on: files/scripts/<name>/<name>."""
    import stat

    for name in role_manifest(role, var):
        executable = REPO / f"roles/{role}/files/scripts" / name / name
        assert executable.is_file(), f"{name}/ has no executable named {name}"
        assert executable.stat().st_mode & stat.S_IXUSR, f"{name}/{name} is on PATH but not +x"


# --- the artifacts this repository ships --------------------------------------


def artifact_files():
    """The catalog's own suite covers its artifacts; these are the ones the harness ships."""
    agents = [p for p in HARNESS.rglob("*.md") if p.parent.name == "agents"]
    return sorted({*HARNESS.rglob("SKILL.md"), *agents})


def frontmatter(path):
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    return text.split("---\n", 2)[1]


def test_every_artifact_ships_frontmatter_a_yaml_parser_accepts():
    """The failure this exists for is lexical and silent: an unquoted ": " in a plain
    value reads as a mapping where none is allowed, so the block fails whole and the
    artifact does not load, with no error anywhere.

    PyYAML is the oracle. kura's scanner is the thing that has to agree with it, and
    that contract is asserted in kura's own suite; this asserts the corpus.
    """
    offenders = []
    for path in artifact_files():
        block = frontmatter(path)
        if block is None:
            offenders.append(f"{path.relative_to(REPO)}: no frontmatter block")
            continue
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError as error:
            offenders.append(f"{path.relative_to(REPO)}: {error.__class__.__name__}")
            continue
        if not isinstance(parsed, dict) or "name" not in parsed:
            offenders.append(f"{path.relative_to(REPO)}: declares no name")
    assert offenders == [], "\n".join(offenders)
