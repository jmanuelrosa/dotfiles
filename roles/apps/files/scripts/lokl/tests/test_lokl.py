"""`lokl` keeps a dev domain's hosts entry and its Caddy site file in agreement.

Most of these load the tool as a module and call its functions directly, since the
parsing and the hosts-file surgery are where the subtlety is. An extensionless
executable cannot be imported by name, so it is loaded through a SourceFileLoader.

Nothing here needs root. `write_hosts` escalates only when the target is not writable by
this user, so a tmp_path hosts file exercises the whole add/remove/sync path for real.
Nothing here reaches the machine's own config either: both path overrides set
`overridden`, which is what stops a fixture run from reloading a live proxy or asking the
system resolver about a name only the fixture knows.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys

import pytest
from dotkit.testing import APPS_SCRIPTS_DIR, REPO

TOOL = APPS_SCRIPTS_DIR / "lokl" / "lokl"
CADDY_DIR = REPO / "roles/apps/files/caddy"
SITES = CADDY_DIR / "sites"

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NOT_FOUND = 2
EXIT_INVALID = 3
EXIT_PRIVILEGE = 4


def load():
    loader = importlib.machinery.SourceFileLoader("lokl_tool", str(TOOL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return load()


@pytest.fixture
def machine(tmp_path):
    """A fixture Caddyfile, an empty sites/ and a plausible hosts file."""
    etc = tmp_path / "etc"
    (etc / "sites").mkdir(parents=True)
    (etc / "Caddyfile").write_text("{\n\tauto_https off\n}\n\nimport sites/*.caddyfile\n")
    hosts = tmp_path / "hosts"
    hosts.write_text("##\n# Host Database\n##\n127.0.0.1\tlocalhost\n::1\tlocalhost\n")
    return {"caddyfile": etc / "Caddyfile", "sites": etc / "sites", "hosts": hosts}


def run(machine, *args, cwd=None):
    environment = dict(
        os.environ,
        LOKL_CADDYFILE=str(machine["caddyfile"]),
        LOKL_HOSTS=str(machine["hosts"]),
        NO_COLOR="1",
    )
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True,
        text=True,
        env=environment,
        cwd=cwd,
    )


# --- names -------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("my-custom-project", "my-custom-project.localhost"),
        ("my-custom-project.localhost", "my-custom-project.localhost"),
        ("Pickleball", "pickleball.localhost"),
        ("PICKLEBALL.LOCALHOST", "pickleball.localhost"),
        ("my-custom-project.localhost.", "my-custom-project.localhost"),
        ("  drivein  ", "drivein.localhost"),
        ("a", "a.localhost"),
        ("app2", "app2.localhost"),
    ],
)
def test_normalise_accepts_both_spellings(tool, raw, expected):
    label, domain = tool.normalise(raw)
    assert domain == expected
    assert label == expected.split(".")[0]


@pytest.mark.parametrize(
    "raw", ["", "  ", "-leading", "trailing-", "not a name", "under_score", "a.b", "üml"]
)
def test_normalise_refuses_anything_that_is_not_a_dns_label(tool, raw):
    label, complaint = tool.normalise(raw)
    assert label is None
    assert complaint


# --- derived ports -----------------------------------------------------------


def test_derive_port_is_stable_for_one_seed(tool):
    """The whole point. `hash()` would satisfy every other test here and fail this one,
    because str hashing is salted per process unless PYTHONHASHSEED is pinned."""
    assert tool.derive_port("/Users/me/projects/my-custom-project") == tool.derive_port(
        "/Users/me/projects/my-custom-project"
    )


@pytest.mark.parametrize(
    "seed,expected",
    [("/Users/me/projects/my-custom-project", 33350), ("/tmp/a", 30694), ("x", 39876)],
)
def test_derive_port_pins_the_algorithm(tool, seed, expected):
    """Golden values, so changing the digest or the window is a deliberate act. Every
    already-assigned port in every clone would move if this changed by accident."""
    assert tool.derive_port(seed) == expected


def test_derive_port_spreads_neighbouring_directories_across_the_window(tool):
    """Two worktrees of one repo sit side by side and differ by one character, so a digest
    that bucketed them would defeat the whole point.

    Not asserted as zero collisions: 200 seeds over 20000 slots collide about once by the
    birthday bound, and a bare derivation has no way to know what is taken. Freedom from
    collisions is the next test's contract, not this one's.
    """
    ports = {tool.derive_port(f"/Users/me/projects/front-{n}") for n in range(200)}
    assert len(ports) >= 190


def test_assignment_is_collision_free_once_the_taken_set_is_threaded(tool):
    """What `add` actually does, and the guarantee that matters: every project gets a port
    of its own however many hash into the same slot."""
    taken = set()
    for n in range(500):
        port = tool.derive_port(f"/Users/me/projects/front-{n}", taken=taken)
        assert port not in taken
        taken.add(port)
    assert len(taken) == 500


@pytest.mark.parametrize("seed", ["a", "/x/y", "/Users/me/dev/a-very-long-project-name-here", ""])
def test_derive_port_stays_inside_the_window(tool, seed):
    """Below 49152 so it is never in the ephemeral range macOS hands to outbound sockets,
    and above 19999 so it cannot collide with a dev server's default port."""
    port = tool.derive_port(seed)
    assert tool.PORT_FLOOR <= port <= tool.PORT_CEILING
    assert port < 49152


def test_derive_port_steps_over_what_is_taken(tool):
    first = tool.derive_port("/x")
    second = tool.derive_port("/x", taken={first})
    assert second != first
    assert tool.derive_port("/x", taken={first}) == second


def test_derive_port_probing_is_a_function_of_the_taken_set(tool):
    """Walking forward from the hashed slot, rather than rehashing, is what keeps a
    second caller with the same inputs getting the same answer."""
    first = tool.derive_port("/x")
    assert tool.derive_port("/x", taken={first, first + 1}) == first + 2


def test_derive_port_never_returns_a_port_caddy_holds(tool):
    for port in tool.RESERVED:
        assert tool.derive_port("/x", taken=set()) != port


def test_derive_port_gives_up_when_the_window_is_full(tool):
    full = set(range(tool.PORT_FLOOR, tool.PORT_CEILING + 1))
    assert tool.derive_port("/x", taken=full) is None


def test_assigned_ports_ignores_an_unparsed_site(tool):
    assert tool.assigned_ports({"a.localhost": (3000, None), "b.localhost": (None, None)}) == {3000}


# --- site files --------------------------------------------------------------


def test_render_site_round_trips_through_the_parser(tool):
    text = tool.render_site("my-custom-project.localhost", 4321)
    assert tool.parse_site(text) == ("my-custom-project.localhost", 4321)


def test_render_site_lists_both_loopback_families_behind_a_failover(tool):
    """An IPv4-only upstream answers 502 for a server that bound [::1], and the default
    selection policy is random, so the pair without `lb_policy first` fails half the time."""
    text = tool.render_site("x.localhost", 3000)
    assert "reverse_proxy 127.0.0.1:3000 [::1]:3000 {" in text
    assert "lb_policy first" in text
    assert "0.0.0.0" not in text


def test_render_site_is_caddy_fmt_clean(tool, tmp_path):
    """`caddy fmt` warns on every reload of a file it would reformat."""
    if shutil.which("caddy") is None:
        pytest.skip("caddy is not installed")
    target = tmp_path / "x.caddyfile"
    target.write_text(tool.render_site("x.localhost", 3000))
    formatted = subprocess.run(
        ["caddy", "fmt", str(target)], capture_output=True, text=True, check=True
    )
    assert formatted.stdout == target.read_text()


def test_parse_site_reports_a_hand_written_file_without_a_port(tool):
    domain, port = tool.parse_site("http://hand.localhost {\n\trespond \"hi\"\n}\n")
    assert (domain, port) == ("hand.localhost", None)


def test_parse_site_ignores_a_file_with_no_site_block(tool):
    assert tool.parse_site("# just a comment\n") == (None, None)


def test_sites_reads_a_directory_in_domain_order(tool, machine):
    for name, port in (("beta", 3000), ("alpha", 3001)):
        (machine["sites"] / f"{name}.caddyfile").write_text(
            tool.render_site(f"{name}.localhost", port)
        )
    found = tool.sites(machine["sites"])
    assert list(found) == ["alpha.localhost", "beta.localhost"]
    assert found["alpha.localhost"][0] == 3001


def test_sites_of_a_missing_directory_is_empty(tool, tmp_path):
    assert tool.sites(tmp_path / "nothing") == {}


# --- the hosts block ---------------------------------------------------------


def test_hosts_block_is_empty_when_nothing_is_configured(tool):
    assert tool.hosts_block([]) == ""


def test_replace_block_appends_when_no_block_exists(tool):
    result = tool.replace_block("127.0.0.1\tlocalhost\n", tool.hosts_block(["a.localhost"]))
    assert result.startswith("127.0.0.1\tlocalhost\n\n")
    assert "127.0.0.1\ta.localhost" in result
    assert result.endswith(tool.END + "\n")


def test_replace_block_swaps_in_place_and_keeps_the_tail(tool):
    first = tool.replace_block("127.0.0.1\tlocalhost\n", tool.hosts_block(["a.localhost"]))
    withtail = first + "\n255.255.255.255\tbroadcasthost\n"
    second = tool.replace_block(withtail, tool.hosts_block(["b.localhost"]))
    assert "a.localhost" not in second
    assert "127.0.0.1\tb.localhost" in second
    assert second.rstrip().endswith("255.255.255.255\tbroadcasthost")
    assert second.count(tool.BEGIN) == 1


def test_replace_block_drops_the_block_when_it_empties(tool):
    populated = tool.replace_block("127.0.0.1\tlocalhost\n", tool.hosts_block(["a.localhost"]))
    emptied = tool.replace_block(populated, "")
    assert emptied == "127.0.0.1\tlocalhost\n"


def test_replace_block_is_idempotent(tool):
    block = tool.hosts_block(["a.localhost"])
    once = tool.replace_block("127.0.0.1\tlocalhost\n", block)
    assert tool.replace_block(once, block) == once


@pytest.mark.parametrize(
    "content",
    [
        "127.0.0.1\tlocalhost\n{begin}\n127.0.0.1\ta.localhost\n",
        "127.0.0.1\tlocalhost\n{end}\n",
        "{end}\n{begin}\n",
        "{begin}\n{begin}\n{end}\n",
    ],
)
def test_replace_block_refuses_a_half_marked_file(tool, content):
    """Appending a second block past a broken marker leaves the first one live, resolving
    names nothing lists any more. Refusing is the only safe answer."""
    filled = content.format(begin=tool.BEGIN, end=tool.END)
    with pytest.raises(ValueError):
        tool.replace_block(filled, tool.hosts_block(["b.localhost"]))


def test_foreign_entries_finds_a_hand_written_duplicate(tool):
    content = tool.replace_block(
        "127.0.0.1\tlocalhost\n127.0.0.1 a.localhost\n", tool.hosts_block(["a.localhost"])
    )
    assert tool.foreign_entries(content, ["a.localhost"]) == ["127.0.0.1 a.localhost"]


def test_foreign_entries_ignores_the_managed_block_and_comments(tool):
    content = tool.replace_block(
        "127.0.0.1\tlocalhost\n# 127.0.0.1 a.localhost\n", tool.hosts_block(["a.localhost"])
    )
    assert tool.foreign_entries(content, ["a.localhost"]) == []


# --- end to end through the executable ---------------------------------------


def test_add_writes_the_site_file_and_the_hosts_entry(machine):
    assert run(machine, "add", "my-custom-project", "4321").returncode == EXIT_OK
    site = machine["sites"] / "my-custom-project.caddyfile"
    assert site.exists()
    assert "127.0.0.1:4321" in site.read_text()
    assert "127.0.0.1\tmy-custom-project.localhost" in machine["hosts"].read_text()


def test_add_without_a_port_derives_one_from_the_directory(tool, tmp_path, machine):
    project = tmp_path / "projA"
    project.mkdir()
    result = run(machine, "add", "my-custom-project", cwd=project)
    assert result.returncode == EXIT_OK
    expected = tool.derive_port(project)
    assert f":{expected}" in (machine["sites"] / "my-custom-project.caddyfile").read_text()
    assert "port derived from" in result.stdout


def test_add_without_a_port_gives_two_directories_two_ports(machine, tmp_path):
    """The collision this exists to avoid: two worktrees started without thinking."""
    for name in ("one", "two"):
        project = tmp_path / name
        project.mkdir()
        assert run(machine, "add", name, cwd=project).returncode == EXIT_OK
    ports = {
        int(text.split(":")[1].split()[0])
        for text in (path.read_text() for path in machine["sites"].glob("*.caddyfile"))
        for text in [text.split("reverse_proxy 127.0.0.1")[1]]
    }
    assert len(ports) == 2


def test_add_without_a_port_keeps_the_port_a_domain_already_has(machine, tmp_path):
    """Re-deriving here would let an unrelated project taking the hashed slot silently
    move a domain that was working."""
    project = tmp_path / "projA"
    project.mkdir()
    run(machine, "add", "my-custom-project", "3001", cwd=project)
    result = run(machine, "add", "my-custom-project", cwd=project)
    assert result.returncode == EXIT_OK
    assert "already proxying to :3001" in result.stdout
    assert "127.0.0.1:3001" in (machine["sites"] / "my-custom-project.caddyfile").read_text()


def test_add_without_a_port_avoids_a_port_another_domain_holds(tool, machine, tmp_path):
    project = tmp_path / "projA"
    project.mkdir()
    hashed = tool.derive_port(project)
    (machine["sites"] / "squatter.caddyfile").write_text(
        tool.render_site("squatter.localhost", hashed)
    )
    assert run(machine, "add", "my-custom-project", cwd=project).returncode == EXIT_OK
    assert f":{hashed + 1}" in (machine["sites"] / "my-custom-project.caddyfile").read_text()


# --- the port command --------------------------------------------------------


def test_port_prints_a_bare_number(machine, tmp_path):
    """It is read by a shell, so stdout carries a value and nothing else: no glyph, no
    colour, no trailing prose."""
    result = run(machine, "port", cwd=tmp_path)
    assert result.returncode == EXIT_OK
    assert result.stdout.strip().isdigit()
    assert result.stdout.count("\n") == 1


def test_port_is_stable_for_one_directory(machine, tmp_path):
    first = run(machine, "port", cwd=tmp_path).stdout
    assert run(machine, "port", cwd=tmp_path).stdout == first


def test_port_differs_between_directories(machine, tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    a = run(machine, "port", cwd=tmp_path / "a").stdout
    b = run(machine, "port", cwd=tmp_path / "b").stdout
    assert a != b


def test_port_by_name_reads_the_site_file_from_anywhere(machine, tmp_path):
    """The form a dev script uses: the recorded port, not the hash for wherever the
    script happened to be run from."""
    (tmp_path / "elsewhere").mkdir()
    run(machine, "add", "my-custom-project", "3001", cwd=tmp_path)
    result = run(machine, "port", "my-custom-project.localhost", cwd=tmp_path / "elsewhere")
    assert result.stdout.strip() == "3001"


def test_port_of_an_unconfigured_name_answers_for_the_directory(tool, machine, tmp_path):
    result = run(machine, "port", "not-added-yet", cwd=tmp_path)
    assert result.returncode == EXIT_OK
    assert int(result.stdout.strip()) == tool.derive_port(tmp_path)


def test_port_refuses_a_name_that_is_not_a_label(machine, tmp_path):
    assert run(machine, "port", "Not A Name", cwd=tmp_path).returncode == EXIT_USAGE


def test_add_is_idempotent(machine):
    run(machine, "add", "my-custom-project", "4321")
    before = machine["hosts"].read_text()
    result = run(machine, "add", "my-custom-project", "4321")
    assert result.returncode == EXIT_OK
    assert machine["hosts"].read_text() == before
    assert "already proxying" in result.stdout


def test_add_repoints_an_existing_domain(machine):
    run(machine, "add", "my-custom-project", "4321")
    result = run(machine, "add", "my-custom-project", "4322")
    assert result.returncode == EXIT_OK
    assert "repointed from :4321" in result.stdout
    assert "127.0.0.1:4322" in (machine["sites"] / "my-custom-project.caddyfile").read_text()
    assert machine["hosts"].read_text().count("my-custom-project.localhost") == 1


def test_add_warns_when_two_domains_share_a_port(machine):
    run(machine, "add", "one", "3000")
    result = run(machine, "add", "two", "3000")
    assert result.returncode == EXIT_OK
    assert "one.localhost also points at :3000" in result.stdout


@pytest.mark.parametrize("port", ["80", "2019"])
def test_add_refuses_the_ports_caddy_holds(machine, port):
    """A site pointing at either is a proxy loop rather than a project."""
    result = run(machine, "add", "loop", port)
    assert result.returncode == EXIT_USAGE
    assert not list(machine["sites"].glob("*.caddyfile"))


@pytest.mark.parametrize("port", ["0", "70000"])
def test_add_refuses_a_port_outside_the_range(machine, port):
    assert run(machine, "add", "x", port).returncode == EXIT_USAGE


def test_add_refuses_a_name_that_is_not_a_label(machine):
    result = run(machine, "add", "Not A Name", "3000")
    assert result.returncode == EXIT_USAGE
    assert not list(machine["sites"].glob("*.caddyfile"))


def test_add_will_not_create_the_site_directory_on_the_real_prefix(tmp_path):
    """That path is a symlink the playbook owns, and `state: link` cannot replace a real
    directory, so conjuring one here would break the task that repairs it."""
    environment = dict(os.environ, NO_COLOR="1")
    environment.pop("LOKL_CADDYFILE", None)
    environment.pop("LOKL_HOSTS", None)
    environment["HOMEBREW_PREFIX"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(TOOL), "add", "x", "3000"],
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == EXIT_NOT_FOUND
    assert "make run-role ROLE=apps" in result.stderr
    assert not (tmp_path / "etc" / "sites").exists()


def test_remove_drops_both_halves(machine):
    run(machine, "add", "my-custom-project", "4321")
    assert run(machine, "remove", "my-custom-project.localhost").returncode == EXIT_OK
    assert not (machine["sites"] / "my-custom-project.caddyfile").exists()
    assert "my-custom-project" not in machine["hosts"].read_text()
    assert machine["hosts"].read_text().endswith("::1\tlocalhost\n")


def test_remove_of_an_unknown_domain_is_not_found(machine):
    assert run(machine, "remove", "nope").returncode == EXIT_NOT_FOUND


def test_sync_rebuilds_the_block_from_the_site_files(tool, machine):
    """The case a clone lands in: the site files are committed, the hosts entries are not."""
    (machine["sites"] / "cloned.caddyfile").write_text(tool.render_site("cloned.localhost", 5173))
    assert run(machine, "sync").returncode == EXIT_OK
    assert "127.0.0.1\tcloned.localhost" in machine["hosts"].read_text()
    again = run(machine, "sync")
    assert again.returncode == EXIT_OK
    assert "already in sync" in again.stdout


def test_sync_refuses_a_hosts_file_with_broken_markers(tool, machine):
    """A file to repair by hand, not a write that was refused, so not EXIT_PRIVILEGE."""
    machine["hosts"].write_text(f"127.0.0.1\tlocalhost\n{tool.BEGIN}\n127.0.0.1\tstray\n")
    assert run(machine, "sync").returncode == EXIT_INVALID


def test_list_sees_a_domain_aliased_onto_a_shared_hosts_line(tool, machine):
    """A hosts line may carry several names against one address."""
    (machine["sites"] / "aliased.caddyfile").write_text(tool.render_site("aliased.localhost", 3000))
    machine["hosts"].write_text("127.0.0.1\tlocalhost aliased.localhost\n")
    assert "no hosts entry" not in run(machine, "list").stdout


def test_list_says_so_when_nothing_is_configured(machine):
    result = run(machine, "list")
    assert result.returncode == EXIT_OK
    assert "none configured yet" in result.stdout


def test_list_flags_a_domain_with_no_hosts_entry(tool, machine):
    (machine["sites"] / "orphan.caddyfile").write_text(tool.render_site("orphan.localhost", 3000))
    result = run(machine, "list")
    assert "no hosts entry" in result.stdout
    assert "lokl sync" in result.stdout


def test_bare_invocation_prints_help(machine):
    result = run(machine)
    assert result.returncode == EXIT_USAGE
    assert "add" in result.stdout and "sync" in result.stdout


# --- what ships in this repo -------------------------------------------------


def test_the_caddyfile_imports_the_site_directory():
    """Without the import the proxy starts, validates and serves nothing, because a glob
    matching no files is only a warning."""
    assert "import sites/*.caddyfile" in (CADDY_DIR / "Caddyfile").read_text()


def test_the_playbook_links_the_site_directory_beside_the_caddyfile():
    """Caddy resolves the import against the directory of the file it was handed and does
    not follow the Caddyfile symlink back here, so the second link is what serves the
    domains at all. Losing it is silent: the config still validates."""
    tasks = (REPO / "roles/apps/tasks/development.yml").read_text()
    assert "CADDY_SITES_PATH" in tasks
    defaults = (REPO / "roles/apps/defaults/main.yml").read_text()
    assert "CADDY_SITES_PATH:" in defaults
    assert "lokl" in defaults


def test_every_committed_site_file_is_what_the_tool_would_write(tool):
    """A hand-edited site file is how the fmt warning and the 502 pair come back."""
    for path in sorted(SITES.glob("*.caddyfile")):
        domain, port = tool.parse_site(path.read_text())
        assert domain, f"{path.name} holds no site block"
        assert port, f"{path.name} holds no reverse_proxy port"
        assert path.stem == domain.split(".")[0], f"{path.name} does not match {domain}"
        assert path.read_text() == tool.render_site(domain, port)


def test_the_lokl_aliases_are_gone():
    """`lokl` owns the proxy verbs now. An alias of the same name is a second
    implementation that drifts, which is why the claude-skill functions went too."""
    aliases = (REPO / "roles/shell/files/fish/conf.d/aliases.fish").read_text()
    assert "alias lokl:" not in aliases
