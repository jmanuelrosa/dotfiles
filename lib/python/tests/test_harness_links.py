"""The ai role's link table: what lands in each harness's home, and the four tasks that put it there.

HARNESS_LINKS in roles/ai/defaults/main.yml is the whole inventory. The tasks that install it
are generic, so the table is where a mistake lives, and every mistake here is silent: a link to
a path the repo no longer has is written happily with `force: true`, a directory missing from
`dirs` fails only on a fresh machine, and two entries writing one destination leave whichever
ran last.

The expansion is dotkit.testing.harness_links, which mirrors the tasks: `files` one link each,
`globs` one link per regular file the pattern matches.
"""

import re

import pytest
import yaml
from dotkit.testing import (
    AGENTS,
    AI_TASKS,
    CLAUDE,
    CODEX,
    HARNESS,
    INSTRUCTIONS,
    PI,
    RULES,
    ai_defaults,
    harness_dirs,
    harness_links,
)

LINK_FILES_TASK = "Link harness files"
LINK_GLOBS_TASK = "Link harness globs"
EXPAND_TASK = "Expand the harness link globs"
FIND_TASK = "Find the links in the harness glob directories"
INSPECT_TASK = "Inspect the links in the harness glob directories"
PRUNE_TASK = "Remove harness links the repo no longer ships"
DIRS_TASK = "Ensure AI config directories exist"
CODEX_APPLY_TASK = "Merge the harness policy into Codex's config"


def ai_task(name):
    matching = [t for t in yaml.safe_load(AI_TASKS.read_text()) if t.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the ai role"
    return matching[0]


@pytest.fixture(scope="module")
def links():
    return harness_links()


# --- the table --------------------------------------------------------------------


def test_harness_dir_is_the_tree_the_tests_read():
    """One path per language: the role's HARNESS_DIR and dotkit's HARNESS must be the same
    directory, or the suites pin a tree the play never links."""
    assert ai_defaults()["HARNESS_DIR"] == "{{ role_path }}/files/harness"
    assert HARNESS.name == "harness" and HARNESS.parent.name == "files"
    assert HARNESS.parent.parent.name == "ai"


def test_every_enabled_harness_has_a_link_set():
    defaults = ai_defaults()
    assert set(defaults["HARNESS_ENABLED"]) <= set(defaults["HARNESS_LINKS"])
    assert "shared" not in defaults["HARNESS_ENABLED"], "shared is always installed"


def test_every_source_exists(links):
    """`force: true` writes a link to a missing path and reports changed, so a source the
    repo stopped shipping is a dangling link on every machine, with nothing failing."""
    missing = sorted(dest for dest, src in links.items() if not src.exists())
    assert not missing, f"linked from paths that do not exist: {missing}"


def test_every_destination_directory_is_created_first(links):
    """`state: link` does not create parents, so a missing entry fails a fresh machine only."""
    dirs = harness_dirs()
    orphans = sorted(dest for dest in links if dest.rsplit("/", 1)[0] not in dirs)
    assert not orphans, f"no dirs entry creates the parent of {orphans}"


def test_each_harness_reads_the_one_neutral_instructions_file(links):
    assert links["~/.claude/CLAUDE.md"] == INSTRUCTIONS
    assert links["~/.pi/agent/AGENTS.md"] == INSTRUCTIONS
    assert links["~/.codex/AGENTS.md"] == INSTRUCTIONS


def test_claude_never_gets_a_user_level_agents_md(links):
    """Claude reads ~/.claude/AGENTS.md as an ancestor `.claude/AGENTS.md` of every project
    under $HOME, so a link there loads the instructions a second time beside CLAUDE.md."""
    assert "~/.claude/AGENTS.md" not in links


def test_neutral_and_claude_only_rules_land_side_by_side(links):
    assert links["~/.claude/rules/code-review.md"] == RULES / "code-review.md"
    assert links["~/.claude/rules/claude.md"] == CLAUDE / "rules" / "claude.md"


def test_the_claude_adapter_files_are_linked(links):
    assert links["~/.claude/settings.json"] == CLAUDE / "settings.json"
    assert links["~/.claude/statusline.sh"] == CLAUDE / "statusline.sh"


def test_every_hook_is_linked_and_its_tests_are_not(links):
    hooks = {dest for dest in links if dest.startswith("~/.claude/hooks/")}
    shipped = {f"~/.claude/hooks/{p.name}" for p in (HARNESS / "hooks").iterdir() if p.is_file()}
    assert hooks == shipped
    assert not any("tests" in dest for dest in hooks)


def test_every_global_agent_is_linked_for_claude_and_the_directory_for_pi(links):
    """pi-subagents reads global agents only from ~/.pi/agent/agents and has no neutral
    root, so pi gets the directory; Claude gets each file, which the prune can manage."""
    claude = {dest for dest in links if dest.startswith("~/.claude/agents/")}
    assert claude == {f"~/.claude/agents/{p.name}" for p in AGENTS.glob("*.md")}
    assert links["~/.pi/agent/agents"] == AGENTS


def test_the_pi_adapter_files_are_linked(links):
    for name in ("settings.json", "models.json", "model-routing.json", "subagents.json",
                 "sandbox.json", "APPEND_SYSTEM.md"):
        assert links[f"~/.pi/agent/{name}"] == PI / name
    config = "~/.pi/agent/extensions/pi-permission-system/config.json"
    assert links[config] == PI / "permission-system" / "config.json"


def test_pi_never_gets_a_replacement_system_prompt(links):
    """SYSTEM.md replaces pi's own prompt; APPEND_SYSTEM.md adds to it."""
    assert "~/.pi/agent/SYSTEM.md" not in links


def test_the_permission_system_directory_is_real_not_a_link(links):
    """pi-permission-system writes its review log beside its config, with bash command
    strings unredacted, so the directory must never resolve into the checkout."""
    directory = "~/.pi/agent/extensions/pi-permission-system"
    assert directory in harness_dirs()
    assert directory not in links


def test_codex_gets_its_rendered_hooks_and_the_scripts_they_name(links):
    assert links["~/.codex/hooks.json"] == CODEX / "generated" / "hooks.json"
    hooks = {dest for dest in links if dest.startswith("~/.codex/hooks/")}
    assert hooks == {f"~/.codex/hooks/{p.name}" for p in (HARNESS / "hooks").iterdir() if p.is_file()}


def test_codex_config_and_rules_are_never_links(links):
    """Codex writes both: its settings into config.toml and its own approvals into rules/.
    A link would land those writes in this checkout, and its rules loader skips a symlink."""
    assert "~/.codex/config.toml" not in links
    assert not any(dest.startswith("~/.codex/rules") for dest in links)


def test_codex_config_is_merged_by_the_generator_on_every_run():
    task = ai_task(CODEX_APPLY_TASK)
    argv = task["ansible.builtin.command"]["argv"]
    assert "'harness-build'" in argv or "/bin/harness-build" in argv
    assert "'apply', 'codex'" in argv and "ansible_check_mode" in argv
    assert task["check_mode"] is False, "the --check form is how a dry run sees pending changes"
    assert task["changed_when"] == "'up to date' not in codex_apply.stdout"
    assert task["when"] == "'codex' in HARNESS_ENABLED"


def test_rtk_reads_its_config_from_application_support(links):
    """rtk ignores XDG_CONFIG_HOME on macOS."""
    assert links["~/Library/Application Support/rtk/config.toml"] == HARNESS / "rtk/config.toml"


# --- the generic tasks ------------------------------------------------------------


def test_the_file_links_are_absolute_and_forced():
    """A relative src is read against the link's own directory and dangles; without force a
    pre-existing file fails the play."""
    spec = ai_task(LINK_FILES_TASK)["ansible.builtin.file"]
    assert spec["src"] == "{{ HARNESS_DIR }}/{{ item.src }}"
    assert spec["state"] == "link" and spec["force"] is True


def test_the_glob_links_come_from_the_expanded_list():
    task = ai_task(LINK_GLOBS_TASK)
    assert task["loop"] == "{{ harness_glob_links }}"
    assert task["ansible.builtin.file"]["force"] is True
    expand = ai_task(EXPAND_TASK)["ansible.builtin.set_fact"]["harness_glob_links"]
    assert "query('fileglob', HARNESS_DIR" in expand, "a glob must resolve against the harness tree"


def test_the_directories_task_creates_every_set_and_the_ai_dirs():
    loop = ai_task(DIRS_TASK)["loop"]
    assert "map(attribute='dirs')" in loop and "AI_DIRS" in loop


def test_the_prune_only_removes_symlinks_into_this_role():
    """Everything else in those directories belongs to someone: herdr's real hook file, a
    rule written by hand, a link into another checkout."""
    found = ai_task(FIND_TASK)["ansible.builtin.find"]
    assert found == {"paths": "{{ harness_glob_dirs }}", "file_type": "link"}

    inspect = ai_task(INSPECT_TASK)
    assert inspect["loop"] == "{{ harness_dir_links.files }}"
    assert inspect["ansible.builtin.stat"] == {"path": "{{ item.path }}", "follow": False}

    prune = ai_task(PRUNE_TASK)
    assert prune["loop"] == "{{ harness_dir_link_stats.results }}"
    conditions = " ".join(prune["when"])
    assert "item.stat.islnk" in conditions
    assert "item.stat.lnk_source is match('^' ~ role_path ~ '/files/')" in conditions


def test_the_prune_keeps_exactly_what_the_glob_task_links():
    """Two lists that drift would delete a link the task above it just made."""
    conditions = " ".join(ai_task(PRUNE_TASK)["when"])
    assert "not in (harness_glob_links | map(attribute='dest'))" in conditions


HARNESS_MECHANICS = {
    "a settings key": r"excludedCommands|plansDirectory|settings\.json",
    "a hook script": r"`[\w-]+\.sh`",
    "a slash command": r"`/[\w:-]+`",
    "a harness-named agent": r"\bExplore\b",
    "a harness-qualified aside": r"\b(?:[Ii]n|[Uu]nder) (?:Claude Code|[Pp]i|Codex|opencode)\b",
}


@pytest.mark.parametrize("kind", HARNESS_MECHANICS)
def test_the_neutral_instructions_name_no_harness_mechanics(kind):
    """Every harness loads this file, so a mechanic only one of them has reads as an
    instruction the others cannot follow; it belongs in adapters/<h>/ instead."""
    found = re.findall(HARNESS_MECHANICS[kind], INSTRUCTIONS.read_text())
    assert not found, f"{INSTRUCTIONS.name} names {kind}: {found}"
