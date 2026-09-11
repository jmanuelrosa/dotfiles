"""How kura reaches this machine, and what this repository's catalog owes it.

kura used to live in `roles/ai/files/scripts/claude-kit/` and its suite ran here. It is
released separately now, so what remains is the half this repository can break:

  the installer   a pinned release and checksum, the legacy link's removal, the catalog
                  symlink, and the two commands the role runs
  the catalog     that every artifact under files/claude/ is loadable, that seat routing
                  names every implementer seat, and that the `global` tag says what the
                  registries mean it to say

The tool's own behaviour is asserted in its own repository against a fixture catalog.
Nothing here imports it: the derivations that need its answers ask the installed command
and skip when it is not installed yet. `list --json` is the interface the Television
cables read; `sync --dry-run` is the one that reveals the effective global set, because
`list` hides dependency-only rows and two of the global skills are reached only as
dependencies.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest
import yaml
from dotkit.testing import AGENTS, CLAUDE, PLUGINS, REPO, SKILLS

AI_TASKS = REPO / "roles/ai/tasks/main.yml"
AI_DEFAULTS = REPO / "roles/ai/defaults/main.yml"
COREUTILS_DEFAULTS = REPO / "roles/coreutils/defaults/main.yml"
SETTINGS = CLAUDE / "settings.json"

SYNC_TASK = "Converge global claude skills, agents and plugins"
CONVERGE_TASK = "Converge pi's view of every project's skills and plugin agents"
INSTALL_TASK = "Install the pinned kura release"
CATALOG_TASK = "Point kura at the artifact catalog"
LEGACY_REMOVE_TASK = "Remove the legacy claude-kit symlink"
LINK_TASK = "Link AI scripts into the user bin directory"
HOSTOF_TASK = "Install the pinned hostof release"

# The two roles that still install checkout-owned scripts with a manifest and a link
# loop. An externally released command has its own installation contract, asserted
# separately below.
INSTALLERS = [
    ("ai", "AI_SCRIPTS", LINK_TASK),
    ("work", "WORK_SCRIPTS", "Link work scripts into the user bin directory"),
]

# Every marker the role matches on, and the only reason a reworded summary in another
# repository is this repository's problem.
CHANGED_MARKER = ", 0 changes"


def role_task(role, name):
    tasks = yaml.safe_load((REPO / f"roles/{role}/tasks/main.yml").read_text())
    matching = [t for t in tasks if t.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the {role} role"
    return matching[0]


def role_manifest(role, var):
    return yaml.safe_load((REPO / f"roles/{role}/defaults/main.yml").read_text())[var]


def kura_or_skip():
    """The installed command, or a skip.

    Asking it is how this suite avoids a second implementation of the `global`
    derivation. There was one once, 130 lines of Jinja in this role, and it drifted
    from the tool's copy the moment either changed.
    """
    found = shutil.which("kura")
    if found is None:
        pytest.skip("kura is not installed; run the ai role first")
    return found


def listing(kind):
    rows = subprocess.run(
        [kura_or_skip(), "list", "--type", kind, "--json"],
        env={**os.environ, "KURA_CATALOG": str(CLAUDE), "NO_COLOR": "1"},
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(rows.stdout)


def effective_global(kind):
    """The set `sync` would link into a clean `~/.claude`, which is the effective set.

    A dependency-only artifact is global when a global skill pulls it in, and `list`
    hides those rows by design, so the listing cannot see the whole set. An empty HOME
    makes every member a link rather than a no-op, so one parse covers all of them.
    """
    with tempfile.TemporaryDirectory() as home:
        run = subprocess.run(
            [kura_or_skip(), "sync", "--type", kind, "--dry-run"],
            env={
                **os.environ,
                "HOME": home,
                "KURA_CATALOG": str(CLAUDE),
                "NO_COLOR": "1",
            },
            capture_output=True,
            text=True,
            check=True,
        )
    return set(re.findall(r"Would link '([^']+)'", run.stdout))


# --- the installer ------------------------------------------------------------


def test_the_release_is_pinned_to_a_tag_and_a_checksum():
    """The tag is for reading and the checksum is the identity. There is no --version
    flag to ask the installed file what it is, which is what makes the pin the only
    record of which build a machine runs."""
    import re

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


def test_the_legacy_symlink_is_removed_rather_than_replaced():
    """The command was renamed, so the download writes a different path and nothing
    overwrites the old link. Left in place it would keep a claude-kit on PATH pointing
    into a deleted directory, which fails as a dangling link rather than as a missing
    command."""
    task = role_task("ai", LEGACY_REMOVE_TASK)
    assert task["ansible.builtin.file"] == {
        "path": "{{ HOME }}/.local/bin/claude-kit",
        "state": "absent",
    }
    assert "islnk" in task["when"], "only a symlink this role wrote is ours to remove"


def test_the_role_points_kura_at_this_checkouts_catalog():
    """kura reads a catalog, not a checkout: this link is what makes an interactive
    run, the SessionStart hook and `wt add` work with no environment at all."""
    spec = role_task("ai", CATALOG_TASK)["ansible.builtin.file"]
    assert spec["state"] == "link"
    assert spec["src"] == "{{ role_path }}/files/claude"
    assert spec["dest"] == "{{ HOME }}/.local/share/kura/catalog"
    assert spec["force"] is True, "a link naming an older checkout must be repointed"


@pytest.mark.parametrize("name", [SYNC_TASK, CONVERGE_TASK])
def test_the_role_runs_the_installed_command(name):
    """Not the checkout's copy, which no longer exists, and not a bare `kura` resolved
    off the play's PATH."""
    assert "{{ HOME }}/.local/bin/kura" in role_task("ai", name)["ansible.builtin.command"]["cmd"]


@pytest.mark.parametrize("name", [SYNC_TASK, CONVERGE_TASK])
def test_the_role_pins_both_environmental_inputs(name):
    """HOME and KURA_CATALOG are the tool's only environmental inputs. An inherited
    HOME would sweep another machine's projects, and naming the catalog is what says
    this apply provisions from this checkout rather than from whatever the managed
    symlink currently points at."""
    environment = role_task("ai", name)["environment"]
    assert environment["HOME"] == "{{ HOME }}"
    assert environment["KURA_CATALOG"] == "{{ role_path }}/files/claude"


@pytest.mark.parametrize("name", [SYNC_TASK, CONVERGE_TASK])
def test_the_role_reads_changed_off_the_summary_wording(name):
    """The marker is a cross-repository contract: kura's suite asserts its summary
    emits it, and this asserts the role matches on it. Lose either half and every
    apply reports changed forever."""
    task = role_task("ai", name)
    assert CHANGED_MARKER in task["changed_when"]


@pytest.mark.parametrize("name", [SYNC_TASK, CONVERGE_TASK])
def test_the_role_dry_runs_under_check_mode(name):
    """A bare `command` task would sync for real during `make check`, and skipping it
    would make `make check` silent about the one task that deletes things."""
    task = role_task("ai", name)
    assert "--dry-run" in task["ansible.builtin.command"]["cmd"]
    assert "ansible_check_mode" in task["ansible.builtin.command"]["cmd"]
    assert task["check_mode"] is False


def test_a_session_start_hook_converges_the_project_being_opened():
    """The per-repo half: every repo self-heals the moment it is opened, which is also
    the moment it matters. --quiet is load-bearing rather than tidy, because Claude Code
    feeds a SessionStart hook's stdout into the session as context."""
    hooks = json.loads(SETTINGS.read_text())["hooks"]["SessionStart"]
    commands = [hook["command"] for entry in hooks for hook in entry["hooks"]]
    converging = [c for c in commands if "kura converge" in c]
    assert len(converging) == 1, f"expected one converge hook, got {converging}"
    assert "--quiet" in converging[0]
    assert "--all" not in converging[0], "a sweep of every project does not belong on a session start"


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


# --- the catalog this repository owns -----------------------------------------


def artifact_files():
    """Every artifact document under files/claude/, plugin-bundled ones included.

    The bundled ones are in no registry, so nothing else would ever read them.
    """
    agents = [p for p in CLAUDE.rglob("*.md") if p.parent.name == "agents"]
    return sorted({*CLAUDE.rglob("SKILL.md"), *agents})


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
            offenders.append(f"{path.relative_to(CLAUDE)}: no frontmatter block")
            continue
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError as error:
            offenders.append(f"{path.relative_to(CLAUDE)}: {error.__class__.__name__}")
            continue
        if not isinstance(parsed, dict) or "name" not in parsed:
            offenders.append(f"{path.relative_to(CLAUDE)}: declares no name")
    assert offenders == [], "\n".join(offenders)


def seat_agents():
    """Every staff-engineer agent shipped by a seat plugin, with its frontmatter."""
    for plugin in sorted(PLUGINS.iterdir()):
        for path in sorted((plugin / "agents").glob("*-staff-engineer.md")):
            block = frontmatter(path)
            yield path, (yaml.safe_load(block) if block else {})


def test_implementer_seats_are_the_ones_without_a_tools_allowlist():
    """The advisor/implementer split is readable from frontmatter alone.

    `tools:` is what makes a seat read-only, and a read-only seat owns no slice. Pinned
    so the next advisor seat is a deliberate addition here rather than a silent
    disappearance from architect's routing.
    """
    advisors = {p.stem for p, fm in seat_agents() if "tools" in fm}
    assert advisors == {"security-staff-engineer"}


def test_architect_routes_to_every_implementer_seat():
    """A seat architect never names is a seat it never assigns work to.

    This list rotted from twelve seats to seven without anyone noticing: design,
    mobile, desktop, dx and gtm each shipped without reaching architect.md, so
    architect silently defaulted their work to the frontend and backend seats. The
    symptom was invisible, because defaulting is indistinguishable from routing.
    """
    routing = (AGENTS / "architect.md").read_text()
    missing = sorted(
        path.stem
        for path, fm in seat_agents()
        if "tools" not in fm and path.stem.removesuffix("-staff-engineer") not in routing
    )
    assert missing == [], (
        f"seats absent from architect.md's enumeration: {', '.join(missing)}. "
        f"Architect cannot assign a slice to a seat it does not name."
    )


def test_every_registered_skill_has_a_source_on_disk():
    """A registry row naming nothing is a skill `sync` reports missing and refuses to
    exit 0 over, and a row nobody notices is how that happens."""
    registry = json.loads((CLAUDE / "skill-registry.json").read_text())
    local = [entry["name"] for entry in registry.get("local_skills") or []]
    missing = [name for name in local if not (SKILLS / name).is_dir()]
    assert missing == [], f"registered skills with no directory: {missing}"


def test_the_global_set_holds_exactly_the_documented_membership():
    """Pinned so a registry retag shows up as a failing test rather than as a silent
    change to what lands in ~/.claude.

    Read from `sync --dry-run` rather than derived here. The derivation is kura's, it
    expands dependencies one level for a global skill and two for a global agent, and a
    second copy of it in this repository is exactly the drift the Jinja version caused.
    """
    assert effective_global("skill") == {
        "ac",
        "agent-audit",
        "agent-writer",
        "setup-review",
        "setup-review-mechanics",
        "cloudflare",
        "commit",
        "documentation-and-adrs",
        "domain-modeling",
        "feature-team",
        "grill-me",
        "grill-with-docs",
        "grilling",
        "handoff",
        "humanizer",
        "jira",
        "planning-and-task-breakdown",
        "pr",
        "product-lead",
        "research",
        "review-mechanics",
        "skill-writer",
        "to-plan",
    }


def test_every_manifested_plugin_is_listed():
    """The plugin namespace comes from manifests on disk rather than from a registry,
    so a plugin with a malformed manifest disappears from the listing silently."""
    on_disk = {
        d.name for d in PLUGINS.iterdir() if (d / ".claude-plugin" / "plugin.json").is_file()
    }
    assert {row["name"] for row in listing("plugin")} == on_disk
