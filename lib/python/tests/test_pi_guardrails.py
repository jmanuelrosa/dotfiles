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

import re

import pytest
from dotkit.testing import HOOKS, PI_EXTENSIONS, REPO

EXTENSION = PI_EXTENSIONS / "guardrails.ts"
TASKS = REPO / "roles/ai/tasks/main.yml"

# Every hook the extension drives, and what each one reads out of the event it is handed. The
# direction is what matters: a key a hook reads and the extension never sends is a field the
# hook finds empty, which reads to it as a call with nothing to object to.
#
# Only the em dash gate reads `tool_name`, because in claude the other two are routed by a
# `matcher` in settings.json and never see a tool they were not meant for. The extension sends
# it to all three anyway, since the payload is a claude PreToolUse event and a faithful one
# costs nothing, but a field nobody reads is not a contract and is not listed here.
CONTRACTS = {
    "em-dash-gate.sh": ("tool_name", "tool_input", "cwd", "Write", "Edit", "file_path", "content",
                        "old_string", "new_string"),
    "git-skill-gate.sh": ("tool_input", "cwd", "command", "transcript_path", "attributionSkill"),
    "pre-commit-verify.sh": ("tool_input", "cwd", "command"),
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


def test_the_role_installs_the_extension():
    """Pi discovers extensions by directory, so both halves are needed and neither is loud when
    missing: no directory means the link task writes into a path that does not exist, and no link
    task means a directory pi finds empty."""
    tasks = TASKS.read_text()
    assert ".pi/agent/extensions" in tasks
    assert "files/pi/extensions/*.ts" in tasks
