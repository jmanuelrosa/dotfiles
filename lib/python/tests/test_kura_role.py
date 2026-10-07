"""How kura reaches this machine, and what this repository's catalog owes it.

kura used to live in `roles/ai/files/scripts/claude-kit/` and its suite ran here. It is
released separately now, so what remains is the half this repository can break:

  the installer   a pinned release and checksum, machine config, the legacy command and
                  cross-harness link removals, and the commands the role runs
  the catalog     that the dedicated Kura view exposes skills, agents, bundles and their
                  registries, that every shipped artifact is loadable, that seat routing
                  names every implementer seat, and that `global` means what it should

Kura v0.7 manages skills, standalone agents and bundles. The role hands its old agent
links off to Kura; the seats and the product pipeline, which used to ship as Claude
plugins beside the catalog, are bundles inside it. The tool's own behaviour is
asserted in its own repository against a fixture catalog. Nothing here imports it: the derivations that need its answers ask the
installed command and skip when it is absent or predates the multi-harness interface.
"""

import json
import re

import pytest
import yaml
from dotkit.testing import (
    AGENT_REGISTRY,
    AGENTS,
    BUNDLES,
    CATALOG,
    CLAUDE_SETTINGS,
    HARNESS,
    REPO,
    SKILLS,
    ai_defaults,
    harness_links,
)

AI_TASKS = REPO / "roles/ai/tasks/main.yml"
AI_DEFAULTS = REPO / "roles/ai/defaults/main.yml"
COREUTILS_DEFAULTS = REPO / "roles/coreutils/defaults/main.yml"
SETTINGS = CLAUDE_SETTINGS
KURA_CATALOG = CATALOG

SYNC_TASK = "Converge global skills for Claude Code and Pi"
CONVERGE_TASK = "Converge initialized project skill views"
INSTALL_TASK = "Install the pinned kura release"
MACHINE_CONFIG_TASK = "Link kura machine config"
CATALOG_TASK = "Link the artifact catalog at the fixed path"
LEGACY_REMOVE_TASK = "Remove the legacy claude-kit symlink"
LEGACY_PI_SKILLS_CHECK_TASK = "Check for the superseded pi skills link"
LEGACY_PI_SKILLS_REMOVE_TASK = "Remove the superseded pi skills link"
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


def test_the_role_links_kuras_machine_configuration():
    spec = role_task("ai", MACHINE_CONFIG_TASK)["ansible.builtin.file"]
    assert spec == {
        "src": "{{ HARNESS_DIR }}/kura/config.json",
        "dest": "{{ HOME }}/.config/kura/config.json",
        "state": "link",
        "force": True,
    }
    assert json.loads((HARNESS / "kura/config.json").read_text()) == {
        "schemaVersion": 1,
        "globalHarnesses": ["claude", "pi"],
        "pi": {"agents": {"global": "~/.pi/agent/agents", "project": ".pi/agents"}},
    }


def test_the_role_links_the_catalog_at_the_fixed_path():
    spec = role_task("ai", CATALOG_TASK)["ansible.builtin.file"]
    assert spec["state"] == "link"
    assert spec["src"] == "{{ HARNESS_DIR }}/kura/catalog"
    assert spec["dest"] == "{{ HOME }}/.config/kura/catalog"
    assert spec["force"] is True, "a link naming an older checkout must be repointed"


def test_the_catalog_view_exposes_kuras_supported_inputs():
    assert {entry.name for entry in KURA_CATALOG.iterdir()} == {
        "skills",
        "skill-registry.json",
        "agents",
        "agent-registry.json",
        "bundles",
        "bundle-registry.json",
    }
    assert (KURA_CATALOG / "skills").is_dir()
    assert (KURA_CATALOG / "skill-registry.json").is_file()
    assert (KURA_CATALOG / "agents").is_dir()
    assert (KURA_CATALOG / "bundles").is_dir()
    assert (KURA_CATALOG / "agent-registry.json").is_file()
    assert (KURA_CATALOG / "bundle-registry.json").is_file()
    assert SKILLS == KURA_CATALOG / "skills"
    assert AGENTS == KURA_CATALOG / "agents"


def test_every_bundle_carries_what_kura_refuses_to_install_without():
    """A bundle with no manifest, no agent or no skill is a catalog error kura names.

    These arrived from `plugins/`, where the manifest was `.claude-plugin/plugin.json` and
    nothing read it: Claude Code ignored the keys this repository cared about, and kura
    never looked. `bundle.json` is read, so a missing one is now a bundle that does not
    exist rather than one that merely looks untagged.
    """
    for bundle in sorted(entry for entry in BUNDLES.iterdir() if entry.is_dir()):
        assert (bundle / "bundle.json").is_file(), bundle.name
        assert list((bundle / "agents").glob("*.md")), bundle.name
        assert list((bundle / "skills").glob("*/SKILL.md")), bundle.name


def test_every_shipped_bundle_has_one_registry_entry():
    registry = json.loads((KURA_CATALOG / "bundle-registry.json").read_text())
    assert registry["version"] == 3
    entries = registry["local"]
    names = [entry["name"] for entry in entries]
    assert len(names) == len(set(names))
    assert set(names) == {path.name for path in BUNDLES.iterdir() if path.is_dir()}
    for name in names:
        manifest = json.loads((BUNDLES / name / "bundle.json").read_text())
        assert manifest["name"] == name


def test_bundles_have_no_unsupported_registry_policy():
    registry = json.loads((KURA_CATALOG / "bundle-registry.json").read_text())
    unsupported = {"groups", "global", "dependencies", "dependency_only"}
    for entry in registry["local"]:
        assert not unsupported.intersection(entry), entry["name"]
        manifest = json.loads((BUNDLES / entry["name"] / "bundle.json").read_text())
        assert "groups" not in manifest, entry["name"]
        assert "global" not in manifest, entry["name"]


@pytest.mark.parametrize(("kind", "collection"), [("skill", "skills"), ("agent", "agents")])
def test_global_root_policy_is_boolean_and_separate_from_groups(kind, collection):
    registry = json.loads((KURA_CATALOG / f"{kind}-registry.json").read_text())
    entries = registry["local"] + [
        entry for repo in registry["upstream"].values() for entry in repo[collection]
    ]
    for entry in entries:
        assert type(entry.get("global", False)) is bool, entry
        assert "global" not in entry.get("groups", []), entry


def test_kura_convergence_tasks_remain_disabled():
    names = {task["name"] for task in yaml.safe_load(AI_TASKS.read_text())}
    assert SYNC_TASK not in names
    assert CONVERGE_TASK not in names


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


def test_the_old_cross_harness_skill_link_is_removed_only_when_it_is_ours():
    check = role_task("ai", LEGACY_PI_SKILLS_CHECK_TASK)["ansible.builtin.stat"]
    assert check == {"path": "{{ HOME }}/.pi/agent/skills", "follow": False}

    remove = role_task("ai", LEGACY_PI_SKILLS_REMOVE_TASK)
    assert remove["ansible.builtin.file"] == {
        "path": "{{ HOME }}/.pi/agent/skills",
        "state": "absent",
    }
    assert "islnk" in remove["when"]

    assertion = next(
        task for task in yaml.safe_load(AI_TASKS.read_text())
        if task.get("ansible.builtin.assert")
        and "pi skills" in task.get("name", "").lower()
    )["ansible.builtin.assert"]
    conditions = " ".join(assertion["that"])
    assert "lnk_source" in conditions
    assert '.claude/skills' in conditions


def test_standalone_agents_are_catalog_owned_and_global():
    links = harness_links()
    assert not any(dest.startswith("~/.claude/agents/") for dest in links)
    assert "~/.pi/agent/agents" not in links
    assert "{{ HOME }}/.pi/agent/agents" in ai_defaults()["HARNESS_LINKS"]["pi"]["dirs"]

    registry = json.loads(AGENT_REGISTRY.read_text())
    assert set(registry) == {"$schema", "version", "upstream", "local"}
    assert registry["version"] == 3
    registered = {entry["name"] for entry in registry["local"]}
    shipped = {path.stem for path in AGENTS.glob("*.md")}
    assert registered == shipped
    assert all(entry["global"] is True for entry in registry["local"])


@pytest.mark.parametrize("artifact_type", ["agent", "bundle"])
def test_agent_and_bundle_schemas_match_the_skill_registry(artifact_type):
    skill_registry = json.loads((CATALOG / "skill-registry.json").read_text())
    registry = json.loads((CATALOG / f"{artifact_type}-registry.json").read_text())
    assert registry["$schema"] == skill_registry["$schema"].replace(
        "skill-registry.schema.json", f"{artifact_type}-registry.schema.json"
    )


def test_legacy_agent_links_are_removed_only_when_the_role_owns_them():
    """lnk_source follows the catalog alias; lnk_target preserves the old source."""
    tasks = yaml.safe_load(AI_TASKS.read_text())
    names = [task["name"] for task in tasks]
    assert names.index(INSTALL_TASK) < names.index("Remove the legacy Pi agent bridge")
    assert names.index(INSTALL_TASK) < names.index("Remove only role-owned Claude agent links")
    pi_assert = role_task("ai", "Refuse an unexpected Pi agent root")
    assert "lnk_target" in " ".join(pi_assert["ansible.builtin.assert"]["that"])
    pi_remove = role_task("ai", "Remove the legacy Pi agent bridge")
    assert "islnk" in " ".join(pi_remove["when"])
    claude_remove = role_task("ai", "Remove only role-owned Claude agent links")
    assert "lnk_target" in " ".join(claude_remove["when"])
    assert "HARNESS_DIR ~ '/agents/'" in " ".join(claude_remove["when"])
    assert "{{ HOME }}/.claude/agents" not in {
        glob["dest"] for glob in ai_defaults()["HARNESS_LINKS"]["claude"]["globs"]
    }


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
    """Catalog skills and bundle-owned artifacts both need valid frontmatter."""
    agents = [p for p in HARNESS.rglob("*.md") if p.parent.name == "agents"]
    return sorted({*SKILLS.rglob("SKILL.md"), *HARNESS.rglob("SKILL.md"), *agents})


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


def seat_agents():
    """Every staff-engineer agent shipped by a catalog bundle, with its frontmatter."""
    for bundle in sorted(BUNDLES.iterdir()):
        agents_dir = bundle / "agents"
        if not agents_dir.is_dir():
            continue
        for path in sorted(agents_dir.glob("*-staff-engineer.md")):
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
    registry = json.loads((KURA_CATALOG / "skill-registry.json").read_text())
    local = [entry["name"] for entry in registry["local"]]
    missing = [name for name in local if not (SKILLS / name).is_dir()]
    assert missing == [], f"registered skills with no directory: {missing}"


def test_to_plan_dependencies_have_registered_sources():
    registry = json.loads((KURA_CATALOG / "skill-registry.json").read_text())
    entries = {entry["name"]: entry for entry in registry["local"]}
    entries.update(
        (entry["upstream_path"].rstrip("/").rsplit("/", 1)[-1], entry)
        for repo in registry["upstream"].values()
        for entry in repo["skills"]
    )
    assert entries["to-plan"]["dependencies"] == ["research", "grilling"]

    pending = list(entries["to-plan"]["dependencies"])
    visited = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        assert name in entries, f"unregistered dependency: {name}"
        assert (SKILLS / name / "SKILL.md").is_file(), f"missing dependency: {name}"
        pending.extend(entries[name].get("dependencies", []))


def test_the_global_set_holds_exactly_the_documented_membership():
    """Registry root policy changes the global set even while sync is disabled."""
    registry = json.loads((KURA_CATALOG / "skill-registry.json").read_text())
    global_roots = {entry["name"] for entry in registry["local"] if entry.get("global", False)}
    global_roots.update(
        entry["upstream_path"].rstrip("/").rsplit("/", 1)[-1]
        for repo in registry["upstream"].values()
        for entry in repo["skills"]
        if entry.get("global", False)
    )
    assert global_roots == {
        "ac",
        "agent-audit",
        "agent-writer",
        "setup-review",
        "setup-review-mechanics",
        "cloudflare",
        "commit",
        "documentation-and-adrs",
        "feature-team",
        "grill-me",
        "grill-with-docs",
        "handoff",
        "humanizer",
        "planning-and-task-breakdown",
        "pr",
        "product-lead",
        "research",
        "review-mechanics",
        "skill-writer",
        "to-plan",
    }
