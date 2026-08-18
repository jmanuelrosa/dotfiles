"""The pi guardrails extension drives the claude hooks, and reimplements none of them.

There is no TypeScript suite here, and the extension is the kind of file that fails quietly:
every one of its couplings is a string agreed with a python script it spawns. A renamed hook,
a renamed payload key, a third gated skill, or a reworded refusal all leave an extension that
loads, runs on every tool call, and simply never blocks anything. Pi reports nothing, because
from Pi's side a guardrail that allows everything looks exactly like one that found nothing
wrong.

So the assertions here are the agreement itself, read off both sides: whatever the extension
writes into a hook's stdin, that hook must read; whatever it looks for in a hook's output, that
hook must print. Plus the rule that keeps the agreement small, which is that the logic stays in
python. The moment this file has to know how a dash is counted, the extension has stopped being
an adapter.
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from dotkit.testing import HOOKS, PI_EXTENSIONS, REPO

EXTENSION = PI_EXTENSIONS / "guardrails.ts"
TASKS = REPO / "roles/ai/tasks/main.yml"

# Every hook the extension drives, and what each one reads out of the event it is handed. The
# direction is what matters: a key a hook reads and the extension never sends is a field the
# hook finds empty, which reads to it as a call with nothing to object to.
#
# Two of the four read `tool_name`: the em dash gate, which routes Write from Edit, and the
# cloud gate, which checks it rather than trusting a matcher. git-skill-gate and
# pre-commit-verify are routed by a `matcher` in settings.json and never see a tool they were
# not meant for. The extension sends every field to all four anyway, since the payload is a
# claude PreToolUse event and a faithful one costs nothing, but a field nobody reads is not a
# contract and is not listed here.
CONTRACTS = {
    "em-dash-gate.sh": ("tool_name", "tool_input", "cwd", "Write", "Edit", "file_path", "content",
                        "old_string", "new_string"),
    "git-skill-gate.sh": ("tool_input", "cwd", "command", "transcript_path", "attributionSkill"),
    "pre-commit-verify.sh": ("tool_input", "cwd", "command"),
    # Reads `tool_name` like the em dash gate, because in claude it is matched on Bash but
    # routed unconditionally, so it checks the tool itself. It never reads `cwd`.
    "cloud-readonly-gate.sh": ("tool_name", "tool_input", "command"),
}

# The fingerprints of each hook's own logic. Written as escapes for the two dash characters so
# this file, like the gate it guards, can be edited without tripping the gate.
DUPLICATION = (
    "\u2014",
    "\u2013",
    "u2014",
    "u2013",
    "no-verify",
    "Co-Authored-By",
    "rev-parse",
    "package.json",
)


@pytest.fixture(scope="module")
def source():
    return EXTENSION.read_text()


def hook_source(name):
    return (HOOKS / name).read_text()


def test_the_extension_ships():
    assert EXTENSION.is_file(), f"{EXTENSION.relative_to(REPO)} is missing"


def test_the_hop_to_the_hooks_resolves(source):
    """The extension walks out of files/pi/ to reach files/claude/hooks/, and it is reached
    through a symlink, so the walk starts at the resolved file. A wrong hop is not an error at
    load time: `existsSync` is false, every hook is skipped, and every call is allowed."""
    line = next(line for line in source.splitlines() if line.startswith("const HOOKS_DIR"))
    hop = re.findall(r'"([^"]+)"', line)
    assert hop, "HOOKS_DIR no longer joins literal path segments; this test cannot follow it"
    assert EXTENSION.parent.joinpath(*hop).resolve() == HOOKS.resolve()


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_each_driven_hook_exists(name, source):
    assert name in source, f"{name} is no longer driven from the extension"
    assert (HOOKS / name).is_file(), f"the extension spawns {name}, which is not in {HOOKS.name}/"


@pytest.mark.parametrize(
    ("name", "key"),
    [(name, key) for name, keys in sorted(CONTRACTS.items()) for key in keys],
)
def test_a_key_the_hook_reads_is_a_key_the_extension_sends(name, key, source):
    assert key in hook_source(name), f"{name} no longer reads {key!r}; this contract is stale"
    assert key in source, (
        f"{name} reads {key!r}, which the extension does not send. A hook sees a missing field as "
        f"an absent one, so this is a gate that runs and finds nothing to block."
    )


def test_the_gated_skills_match_the_hook(source):
    """git-skill-gate decides which command needs which skill; the extension only reports which
    skills the session is in. A skill the hook gates and the extension never looks for is one
    whose commands can never be run in pi at all, since the gate would see an empty window."""
    block = re.search(r"SKILLS_FOR_SUBCOMMAND = \{(.*?)\n\}", hook_source("git-skill-gate.sh"), re.S)
    gated = set(re.findall(r'\{"([^"]+)"\}', block.group(1)))
    listed = set(re.findall(r'"([^"]+)"', re.search(r"GATED_SKILLS = \[(.*?)\]", source).group(1)))
    assert listed == gated


def test_the_translated_refusal_is_one_the_hook_prints(source):
    """The hook names /commit and ~/.claude/settings.json, so the extension appends pi's spelling
    of the same instruction. It finds that message by a phrase, and a reworded hook would leave
    the caller told to run a command that does not exist here."""
    phrase = re.search(r'message\.includes\("([^"]+)"\)', source).group(1)
    assert phrase in hook_source("git-skill-gate.sh")


@pytest.mark.parametrize("fingerprint", DUPLICATION)
def test_no_hook_logic_is_reimplemented(fingerprint, source):
    """The one rule that keeps the couplings above countable.

    Each of these is a piece of a hook's decision: the dash characters em-dash-gate counts, the
    flag and the attribution line git-skill-gate refuses, the probes pre-commit-verify uses to
    find a project's lint. In TypeScript any of them is a second implementation, untested, that
    disagrees with the python one the first time either changes.
    """
    assert fingerprint not in source, (
        f"guardrails.ts contains {fingerprint!r}, which belongs to a hook's own logic. The "
        f"extension maps events onto hook payloads and nothing else."
    )


def test_the_ask_tier_is_read_from_the_hook_and_refused(source):
    """Claude has three answers to a PreToolUse hook and pi has two.

    cloud-readonly-gate's middle tier is the broad one, every non-read-only cloud
    command, and it arrives as JSON on stdout with exit 0. Exit status alone therefore
    reports the same thing for `ask` and for `allow`, so an extension that only checked
    the code would let the whole tier through while looking like it had bridged the gate.
    """
    assert "permissionDecision" in source, "the ask tier is not read at all"
    assert '"ask"' in source, "nothing distinguishes ask from allow"
    # The hook is the one that decides; the extension only maps the decision.
    hook = hook_source("cloud-readonly-gate.sh")
    assert '"permissionDecision": "ask"' in hook
    assert "permissionDecisionReason" in hook and "permissionDecisionReason" in source


def test_stdout_is_captured_or_the_ask_tier_cannot_be_seen(source):
    """The gate reports `ask` on stdout, so ignoring stdout silently drops the tier."""
    assert 'stdio: ["pipe", "pipe", "pipe"]' in source, "stdout is not captured"


def test_the_refusal_says_why_pi_cannot_ask(source):
    """A caller told only "blocked" for a command Claude would have asked about has no
    way to know the difference is the harness rather than the command."""
    assert "no confirmation prompt" in source


def test_the_role_installs_the_extension():
    """Pi discovers extensions by directory, so both halves are needed and neither is loud when
    missing: no directory means the link task writes into a path that does not exist, and no link
    task means a directory pi finds empty."""
    tasks = TASKS.read_text()
    assert ".pi/agent/extensions" in tasks
    assert "files/pi/extensions/*.ts" in tasks


# --- the extension, executed ---------------------------------------------------

# Everything above reads the source as a string, which is the right shape for a contract with
# another file and the wrong shape for logic. Two functions here decide whether a gate opens,
# and a grep cannot tell a working one from a broken one: the skill window silently expiring is
# exactly the kind of bug that leaves every assertion above green. So these run the real thing,
# by the same technique test_pi_discovery.py uses on pi's own loader.

PI_PACKAGE = "@earendil-works/pi-coding-agent"

# The private functions the executed half drives, re-exported into a copy of the extension.
DRIVEN = ("activeSkills", "writeTranscript")


def pi_package():
    """The installed pi package, found through the `pi` on PATH rather than a pinned cellar path."""
    binary = shutil.which("pi")
    if binary is None:
        return None
    root = Path(binary).resolve().parent.parent
    for candidate in (
        root / "lib/node_modules" / PI_PACKAGE,
        root / "libexec/lib/node_modules" / PI_PACKAGE,
    ):
        if candidate.is_dir():
            return candidate
    return None


@pytest.fixture(scope="module")
def runner(tmp_path_factory):
    """A directory the extension can be imported from, with pi resolvable.

    The file is written rather than linked because node resolves a bare import from the realpath
    of the importing module, so a link would send it looking for node_modules in this checkout.
    """
    package = pi_package()
    if package is None or shutil.which("node") is None:
        pytest.skip("pi and node are needed to execute the extension")
    root = tmp_path_factory.mktemp("guardrails")
    scope = root / "node_modules" / "@earendil-works"
    scope.mkdir(parents=True)
    (scope / "pi-coding-agent").symlink_to(package)
    # Re-exported into the copy rather than exported from the extension, so pi's own surface
    # stays the single default export it loads.
    (root / "guardrails.ts").write_text(f"{EXTENSION.read_text()}\nexport {{ {', '.join(DRIVEN)} }};\n")
    return root


def run_in_node(runner, body):
    """`body` as an ES module beside the extension, with its stdout parsed as JSON."""
    script = f'import {{ {", ".join(DRIVEN)} }} from "./guardrails.ts";\n{body}'
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=runner,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def branch(user_texts, assistant_after=0):
    """A session branch: the user messages in order, then `assistant_after` entries of work."""
    entries = [{"message": {"role": "user", "content": text}} for text in user_texts]
    entries += [{"message": {"role": "assistant", "content": "work"}}] * assistant_after
    return entries


def skills_for(runner, entries):
    body = f"""
    const found = activeSkills({{ sessionManager: {{ getBranch: () => ({json.dumps(entries)}) }} }});
    process.stdout.write(JSON.stringify([...found].sort()));
    """
    return run_in_node(runner, body)


def test_a_loaded_skill_survives_the_work_it_asks_for(runner):
    """The bug this guards: pi tags the invocation once, so counting every entry expired it
    partway through the flow and git-skill-gate then refused the commit the skill exists to make.
    Real sessions on this machine run 278 and 38 entries past their tag."""
    entries = branch(['<skill name="commit" location="x">go</skill>'], assistant_after=300)
    assert skills_for(runner, entries) == ["commit"]


def test_the_window_still_expires_a_stale_invocation(runner):
    """Bounded, or one /skill:commit would hold the gate open for the rest of the session."""
    entries = branch(['<skill name="commit">go</skill>'] + ["unrelated"] * 40)
    assert skills_for(runner, entries) == []


def test_a_skill_the_session_never_loaded_is_not_found(runner):
    assert skills_for(runner, branch(["please commit this for me"])) == []


def test_the_model_reading_a_skill_file_does_not_open_the_gate(runner):
    """Only the invocation tag on a user message counts, never an assistant message quoting it."""
    entries = [{"message": {"role": "assistant", "content": '<skill name="commit">'}}]
    assert skills_for(runner, entries) == []


def test_both_gated_skills_are_found_together(runner):
    entries = branch(['<skill name="commit">a</skill>', '<skill name="pr">b</skill>'])
    assert skills_for(runner, entries) == ["commit", "pr"]


def test_the_transcript_name_does_not_come_from_the_tool_call(runner):
    """`toolCallId` is provider-supplied, so it is a trust boundary in front of a path: real ids
    already carry a `|`, one with a `/` would fail the write and leave the window unchecked, and
    one starting with `../` would write then unlink outside tmpdir."""
    body = """
    const paths = [await writeTranscript(new Set(["commit"])), await writeTranscript(new Set())];
    process.stdout.write(JSON.stringify(paths));
    """
    first, second = run_in_node(runner, body)
    for path in (first, second):
        assert Path(path).resolve().parent == Path(tempfile.gettempdir()).resolve()
    assert first != second, "a fixed name would collide between concurrent calls"


def test_the_transcript_is_written_even_when_no_skill_is_active(runner):
    """Load-bearing: the hook reads a file it cannot open as a parse failure and allows the
    command, so a missing file would turn the gate off rather than closing it."""
    body = """
    const path = await writeTranscript(new Set());
    const { readFileSync } = await import("node:fs");
    process.stdout.write(JSON.stringify({ exists: true, body: readFileSync(path, "utf8") }));
    """
    assert run_in_node(runner, body) == {"exists": True, "body": ""}


def test_the_transcript_is_the_jsonl_the_hook_parses(runner):
    """One `attributionSkill` per line, which is the only shape skills_in_window reads."""
    body = """
    const path = await writeTranscript(new Set(["commit", "pr"]));
    const { readFileSync } = await import("node:fs");
    process.stdout.write(JSON.stringify(readFileSync(path, "utf8").trim().split("\\n")));
    """
    lines = [json.loads(line) for line in run_in_node(runner, body)]
    assert sorted(entry["attributionSkill"] for entry in lines) == ["commit", "pr"]
