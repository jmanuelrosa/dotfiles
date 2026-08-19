"""Group C: `claude-kit converge`, and the discovery that makes `--all` mean something.

Two altitudes, and the split matters. `projects.py` decides *which* directories a sweep
touches, which is where the damage would be: a filter that lets `$HOME` through writes
into `~/.claude`'s neighbour, and one that lets a vanished registry key through crashes
a hook. `commands/converge.py` decides what a run reports and exits, and it owns almost
no logic of its own, because the convergence itself is `pi.py`'s and is tested there.

What is deliberately NOT retested here: whether converge refuses a foreign `.agents`,
whether the skills target is relative, whether a seat plugin's agent is found inside it.
Those are `test_pi.py`'s, and asserting them again here would mean two places to update
when the rule changes.
"""

import json

import yaml

from claude_kit import checks, errors, pi, projects
from claude_kit.cli import build_parser
from claude_kit.commands import converge
from dotkit.testing import CLAUDE, REPO

SKILL = CLAUDE / "skills" / "coderabbit"


def args(*argv):
    """A parsed namespace, from the real parser rather than a stub.

    A hand-rolled namespace is how a flag gets renamed in cli.py and keeps passing here.
    """
    return build_parser().parse_args(["converge", *argv])


def make_project(path):
    """A directory in the state that wants both links: one claude skill, linked."""
    leaf = path / ".claude" / "skills"
    leaf.mkdir(parents=True)
    (leaf / "coderabbit").symlink_to(SKILL)
    return path


# --- C1: what counts as a project to sweep ----------------------------------


def test_either_mark_is_enough(tmp_path):
    """A manifest OR a skills directory. Requiring both would miss exactly the projects
    this command exists for: the ones provisioned before claude-kit wrote a manifest."""
    manifest_only = tmp_path / "a"
    (manifest_only / ".claude").mkdir(parents=True)
    (manifest_only / ".claude" / "claude-kit.json").write_text("{}")
    skills_only = tmp_path / "b"
    (skills_only / ".claude" / "skills").mkdir(parents=True)

    assert projects.marks_a_project(manifest_only)
    assert projects.marks_a_project(skills_only)
    assert not projects.marks_a_project(tmp_path / "c")


def test_a_project_with_nothing_pi_could_see_is_dropped(home, tmp_path):
    """The filter that keeps a commands-only project out of every future report.

    `.claude/commands/` is Claude-only by construction, so a sweep can never change
    anything there, and a note about it would be permanent.
    """
    commands = tmp_path / "commandsy"
    (commands / ".claude" / "commands").mkdir(parents=True)
    (commands / ".claude" / "claude-kit.json").write_text("{}")
    assert projects.keep(commands, home) is None


def test_an_emptied_skills_directory_is_dropped(home, tmp_path):
    """`remove` unlinks skills and leaves the leaf, so "has a leaf" and "has skills" are
    different questions and only the second is a reason to sweep."""
    emptied = tmp_path / "emptied"
    (emptied / ".claude" / "skills").mkdir(parents=True)
    assert projects.keep(emptied, home) is None


def test_home_is_never_swept(home):
    """$HOME's .claude *is* ~/.claude, so a project view there would be a global one."""
    (home / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
    (home / ".claude" / "skills" / "coderabbit").symlink_to(SKILL)
    assert projects.keep(home, home) is None
    assert home not in projects.discover(home)


def test_a_directory_that_is_gone_is_dropped(home, tmp_path):
    """~/.claude.json keeps entries for deleted checkouts; two on this machine today."""
    assert projects.keep(tmp_path / "never-existed", home) is None


# --- C2: the two discovery sources, and why it takes both -------------------


def write_registry(home, *paths):
    (home / ".claude.json").write_text(json.dumps({"projects": {str(p): {} for p in paths}}))


def test_the_registry_finds_a_project_outside_every_root(home, tmp_path):
    """Claude Code's own list is what reaches a checkout the walk would never see."""
    far = make_project(tmp_path / "somewhere" / "else")
    write_registry(home, far)
    assert projects.discover(home) == [far]


def test_a_missing_or_corrupt_registry_is_not_fatal(home, tmp_path):
    """Half the sources is still a sweep worth running, and this runs from a hook."""
    assert projects.registered(home) == []
    (home / ".claude.json").write_text("{ not json")
    assert projects.registered(home) == []


def test_the_walk_finds_a_project_the_registry_never_recorded(home, tmp_path):
    nested = make_project(tmp_path / "roots" / "org" / "repo")
    assert projects.discover(home, [tmp_path / "roots"]) == [nested]


def test_the_walk_prunes_vendor_trees_and_dot_directories(home, tmp_path):
    """Pruning rather than filtering is what keeps this cheap enough for a hook."""
    root = tmp_path / "roots"
    make_project(root / "node_modules" / "pkg")
    make_project(root / ".cache" / "thing")
    assert projects.scan(root) == []


def test_the_walk_stops_at_its_depth(home, tmp_path):
    root = tmp_path / "roots"
    shallow = make_project(root / "a" / "b")
    make_project(root / "a" / "b" / "c" / "d" / "deep")
    assert projects.scan(root, depth=2) == [str(shallow)]


def test_one_project_in_both_sources_is_reported_once(home, tmp_path):
    """The two spell a path differently: the registry stores what Claude Code was handed
    and the walk stores what it found, so de-duplication is on the resolved path."""
    root = tmp_path / "roots"
    both = make_project(root / "repo")
    write_registry(home, str(both) + "/")
    assert projects.discover(home, [root]) == [both]


# --- C3: the pure reporting helpers -----------------------------------------


def test_a_blocked_project_is_not_counted_as_a_change():
    """Counting it would make the summary claim work the run explicitly refused to do."""
    assert converge.changes("blocked", None) == 0
    assert converge.blocked("blocked", None)


def test_changes_counts_both_halves():
    agents = pi.AgentLinks(linked=["a.md", "b.md"], pruned=["c.md"])
    assert converge.changes("linked", agents) == 4


def test_a_name_collision_never_fails_a_sweep():
    """It is a fact about this repo's registries, not about the project being swept, so
    failing every sweep on it would make the exit code useless for what it is for."""
    collided = pi.AgentLinks(collided={"seat.md": ["one", "two"]})
    assert not converge.blocked(None, collided)


def test_the_summary_keeps_the_wording_the_ai_role_matches_on(capsys):
    """`changed_when` in roles/ai/tasks/main.yml greps for `, 0 changes`, exactly as it
    does for sync. Pinned here because a reworded summary makes the role report every
    run as changed, silently and forever."""
    converge.summary(3, 0, False)
    assert ", 0 changes" in capsys.readouterr().out
    converge.summary(1, 2, True)
    out = capsys.readouterr().out
    assert "1 project," in out and "2 changes" in out and "dry run" in out


# --- C4: the command end to end ---------------------------------------------


def test_a_run_converges_both_views(home, tmp_path, monkeypatch):
    project = make_project(tmp_path / "repo")
    monkeypatch.chdir(project)
    assert converge.run(args()) == errors.OK
    assert pi.is_ours(project)


def test_a_second_run_reports_no_changes(home, tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path / "repo")
    monkeypatch.chdir(project)
    converge.run(args())
    capsys.readouterr()
    assert converge.run(args()) == errors.OK
    assert ", 0 changes" in capsys.readouterr().out


def test_a_dry_run_reports_the_change_and_writes_nothing(home, tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path / "repo")
    monkeypatch.chdir(project)
    assert converge.run(args("--dry-run")) == errors.OK
    out = capsys.readouterr().out
    assert "Would link" in out
    assert not (project / pi.PARENT).exists()


def test_a_sweep_visits_every_discovered_project(home, tmp_path, capsys):
    root = tmp_path / "roots"
    one = make_project(root / "one")
    two = make_project(root / "two")
    assert converge.run(args("--all", "--root", str(root))) == errors.OK
    assert pi.is_ours(one) and pi.is_ours(two)
    assert "2 projects" in capsys.readouterr().out


def test_a_foreign_agents_directory_exits_drift(home, tmp_path, monkeypatch, capsys):
    """Reporting a conflict and exiting 0 is how it goes unnoticed. Same reading as
    sync's blocked paths."""
    project = make_project(tmp_path / "repo")
    pi.link_path(project).mkdir(parents=True)
    monkeypatch.chdir(project)
    assert converge.run(args()) == errors.DRIFT
    assert "not ours" in capsys.readouterr().out


def test_running_in_home_reports_and_exits_ok(home, monkeypatch, capsys):
    """A hook fires wherever a session starts. `add` refuses here; this follows doctor,
    because a refusal painted at every session start is noise about nothing."""
    monkeypatch.chdir(home)
    assert converge.run(args()) == errors.OK
    assert "$HOME" in capsys.readouterr().out


def test_quiet_puts_nothing_on_stdout(home, tmp_path, monkeypatch, capsys):
    """Claude Code feeds a SessionStart hook's stdout back into the session as context,
    so an ordinary report there would spend tokens on a line about a symlink."""
    project = make_project(tmp_path / "repo")
    monkeypatch.chdir(project)
    assert converge.run(args("--quiet")) == errors.OK
    assert capsys.readouterr().out == ""
    assert pi.is_ours(project)


def test_quiet_still_sends_a_warning_somewhere_a_human_sees_it(home, tmp_path, monkeypatch, capsys):
    project = make_project(tmp_path / "repo")
    pi.link_path(project).mkdir(parents=True)
    monkeypatch.chdir(project)
    assert converge.run(args("--quiet")) == errors.DRIFT
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "not ours" in captured.err


# --- C5: the ignore file ----------------------------------------------------


def test_the_leaf_ignores_itself_without_touching_the_repo_root(home, tmp_path, monkeypatch):
    """The agent links are absolute paths into this dotfiles checkout, so committing one
    hands a teammate a dangling link. The ignore sits inside the directory we own,
    because a shared repo's root is not ours to edit."""
    project = make_project(tmp_path / "repo")
    monkeypatch.chdir(project)
    converge.run(args())
    # It names itself, because a .gitignore is not covered by its own patterns and that
    # one file is enough for `git status` to report the whole directory as untracked.
    assert pi.ignore_path(project).read_text() == "skills\nagents\n.gitignore\n"
    assert not (project / ".gitignore").exists()


def test_an_existing_ignore_file_is_never_overwritten(home, tmp_path):
    project = make_project(tmp_path / "repo")
    pi.ignore_path(project).parent.mkdir(parents=True)
    pi.ignore_path(project).write_text("theirs\n")
    assert pi.write_ignore(project) is False
    assert pi.ignore_path(project).read_text() == "theirs\n"


def test_our_ignore_file_does_not_keep_an_emptied_directory_alive(home, tmp_path):
    project = make_project(tmp_path / "repo")
    pi.converge(project)
    assert pi.ignore_path(project).exists()
    (project / ".claude" / "skills" / "coderabbit").unlink()
    assert pi.converge(project) == "unlinked"
    assert not (project / pi.PARENT).exists()


def test_someone_elses_ignore_file_does_keep_it(home, tmp_path):
    project = make_project(tmp_path / "repo")
    pi.converge(project)
    pi.ignore_path(project).write_text("theirs\n")
    (project / ".claude" / "skills" / "coderabbit").unlink()
    assert pi.converge(project) == "unlinked"
    assert pi.ignore_path(project).read_text() == "theirs\n"


# --- C6: G21, the two context files -----------------------------------------
#
# Lives here rather than in test_doctor.py because it is the same subject as the rest of
# this file: what pi reads from a project that Claude Code reads differently.


def test_a_project_with_only_claude_md_is_fine(tmp_path):
    """Pi reads CLAUDE.md natively, so the common case needs no AGENTS.md at all. This is
    the assertion that keeps a well-meaning fixer from symlinking 28 repos for nothing."""
    (tmp_path / "CLAUDE.md").write_text("# project\n")
    assert checks.split_context(tmp_path) == []


def test_two_real_files_are_reported(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# the long one\n")
    (tmp_path / "AGENTS.md").write_text("# the short one\n")
    found = checks.split_context(tmp_path)
    assert len(found) == 1
    assert found[0].check == "split-context"
    assert not found[0].is_problem
    assert "AGENTS.md" in found[0].detail and "CLAUDE.md" in found[0].detail


def test_the_symlink_that_fixes_it_is_not_reported(tmp_path):
    """Otherwise doctor complains about its own remedy, every run, forever."""
    (tmp_path / "CLAUDE.md").write_text("# one file\n")
    (tmp_path / "AGENTS.md").symlink_to("CLAUDE.md")
    assert checks.split_context(tmp_path) == []


def test_an_override_outranks_agents_md(tmp_path):
    """AGENTS.override.md is first in pi's own precedence order, so it is the file that
    actually wins and therefore the one worth naming."""
    (tmp_path / "CLAUDE.md").write_text("# claude\n")
    (tmp_path / "AGENTS.md").symlink_to("CLAUDE.md")
    (tmp_path / "AGENTS.override.md").write_text("# pi only\n")
    assert "AGENTS.override.md" in checks.split_context(tmp_path)[0].detail


def test_no_claude_md_is_nothing_to_split(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# the only one\n")
    assert checks.split_context(tmp_path) == []
    assert checks.split_context(None) == []


# --- C7: the doctor notes point at this command ------------------------------


def test_the_pi_notes_name_the_command_that_only_converges(home, tmp_path):
    """They used to say `add` or `restore`, which fix it as a side effect of installing
    something. A note whose only advice is to install an artifact you did not ask for is
    one a reader has to work around."""
    project = make_project(tmp_path / "repo")
    detail = checks.pi_skills_unreachable(project)[0].detail
    assert "claude-kit converge" in detail
    assert "claude-kit add" not in detail


# --- C8: the two triggers ----------------------------------------------------
#
# The command is worth little if nothing calls it, and neither caller is exercised by
# running the tool: one is a line of YAML and the other a line of JSON. Both are pinned
# here, because a trigger that silently stops firing looks exactly like a machine where
# there was nothing to converge.

AI_TASKS = REPO / "roles/ai/tasks/main.yml"
SETTINGS = REPO / "roles/ai/files/claude/settings.json"
CONVERGE_TASK = "Converge pi's view of every project's skills and plugin agents"


def converge_task():
    tasks = yaml.safe_load(AI_TASKS.read_text())
    matching = [t for t in tasks if t.get("name") == CONVERGE_TASK]
    assert len(matching) == 1, f"expected exactly one '{CONVERGE_TASK}' task"
    return matching[0]


def session_start_commands():
    hooks = json.loads(SETTINGS.read_text())["hooks"]["SessionStart"]
    return [hook["command"] for entry in hooks for hook in entry["hooks"]]


def test_the_role_sweeps_every_project():
    """This is the task that clears a backlog nobody is standing in. Losing it would be
    silent: the play succeeds and pi keeps reading nothing."""
    task = converge_task()
    assert "claude-kit converge --all" in task["ansible.builtin.command"]["cmd"]


def test_the_role_reads_changed_off_the_summary_wording(capsys):
    """Same contract as sync's, asserted the same way: lose the marker from a quiet run
    and every play reports changed forever; let it into a busy run and the sweep goes
    unreported."""
    marker = ", 0 changes"
    assert marker in converge_task()["changed_when"]

    converge.summary(4, 0, False)
    assert marker in capsys.readouterr().out
    converge.summary(4, 1, False)
    assert marker not in capsys.readouterr().out


def test_the_role_dry_runs_under_check_mode():
    task = converge_task()
    assert "--dry-run" in task["ansible.builtin.command"]["cmd"]
    assert "ansible_check_mode" in task["ansible.builtin.command"]["cmd"]
    assert task["check_mode"] is False


def test_the_role_pins_both_environmental_inputs():
    """Discovery reads $HOME/.claude.json and walks $HOME/Developer, so an inherited HOME
    would sweep some other machine's projects."""
    environment = converge_task()["environment"]
    assert "HOME" in environment
    assert "DOTFILES_DIR" in environment


def test_a_session_start_hook_converges_the_project_being_opened():
    """The per-repo half: every repo self-heals the moment it is opened, which is also
    the moment it matters. --quiet is load-bearing rather than tidy, because Claude Code
    feeds a SessionStart hook's stdout into the session as context."""
    commands = session_start_commands()
    converging = [c for c in commands if "claude-kit converge" in c]
    assert len(converging) == 1, f"expected one converge hook, got {converging}"
    assert "--quiet" in converging[0]
    assert "--all" not in converging[0], "a sweep of 28 projects does not belong on a session start"


def test_no_session_start_hook_runs_twice():
    """Two entries registered the same herdr script, once through ~ and once through an
    absolute path baked in from this machine, so it ran twice on every session start."""
    commands = session_start_commands()
    scripts = [c.split("/")[-1] for c in commands]
    assert len(scripts) == len(set(scripts)), f"a hook is registered twice: {scripts}"
