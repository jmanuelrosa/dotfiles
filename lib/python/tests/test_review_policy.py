"""The review policy reaches every session, and no REVIEW.md reaches anything.

One artifact states the design, and it has three ways of silently ceasing to work.

`files/claude/rules/code-review.md` is a user-scope rule: linked into ~/.claude/rules/ it
loads at launch in every project, which is the whole reason it was written there instead
of as a repository REVIEW.md. Claude Code reads no REVIEW.md locally at all (the 2.1.220
binary contains the string nowhere), so the rules directory is the only route a machine-
wide review policy has. Miss the link task or the parent directory and the policy is a
file in a git repo that nothing ever reads, which looks exactly like a policy that is
working.

Nothing here ships a REVIEW.md, and the one guard left of that is that none appears in
~/.claude. Linked into rules/ one would become an always-on instruction about a file the
local review cannot read, and linked at the top level it would sit beside CLAUDE.md as a
rule nothing scoped. A repository REVIEW.md is written at the root that reads it, on the
day hosted Code Review is enabled, and never staged here in the meantime.

The second failure is drift. The policy routes each axis to a seat plugin's failure-modes
skill rather than to reference filenames, so retitling a reference upstream cannot strand
it; renaming or dropping a *seat* still can, and a route to a plugin that does not exist
is a checklist silently never opened.

The policy is split across two files by audience, and the split is what these tests pin.
`rules/code-review.md` stays resident in every session and holds only what has to hold
whether or not a skill was loaded: the severity vocabulary, the axes, and the boundaries.
The machinery for turning a read diff into a report (verification bar, effort table, seat
routing, skip rules, the banned mutators, the report format) lives in the
`review-mechanics` skill and loads on demand. Each assertion below points at whichever
file owns its claim, so a claim cannot quietly move between them and still pass.

The third is a bare `/code-review`. Effort is the command's first argument and it decides
the whole shape of the run: one diff pass and no verify step at `low`, eight finder angles
at `medium`, a recall-oriented net from `high` up. `disableModelInvocation: true` means no
agent can pass it, so every call site here is prose telling a human what to type, and one
that names no level silently asks for the default however large the diff is. The policy's
table is the authority; these tests are what keep the twenty call sites agreeing with it.
"""

import json
import re

import pytest
import yaml
from dotkit.testing import CLAUDE, PLUGINS, REPO, SKILLS

AI_TASKS = REPO / "roles/ai/tasks/main.yml"

RULES = CLAUDE / "rules"
POLICY = RULES / "code-review.md"
MECHANICS = SKILLS / "review-mechanics" / "SKILL.md"
SKILL_REGISTRY = CLAUDE / "skill-registry.json"

DIRS_TASK = "Ensure AI config directories exist"
RULES_TASK = "Symlink claude rules"
CONFIG_TASK = "Symlink claude config files"

# The policy exists partly to collapse the four vocabularies our own artifacts used
# (Critical/Nit, P0-P2, nitpick/warning, Important/Nit), so a word dropped from it
# reopens the translation problem it closed.
SEVERITIES = ("blocker", "important", "nit", "pre-existing")

# Named as out of scope during a review because each one writes. A rename here leaves the
# policy banning something that no longer exists while the renamed skill goes unbanned.
MUTATORS = (
    "code-simplification",
    "knip",
    "coderabbit",
    "pr",
    "performance-optimization",
)

SEAT_ROUTE = re.compile(r"\b([a-z]+):\1-failure-modes\b")

# The harness accepts these six as `/code-review`'s first argument. `ultra` is in the list
# because it is spellable, not because it is a rung above `max`: it runs in the cloud and
# is billed separately.
EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")

# Every occurrence, level or not, so a bare one is a failure rather than a miss.
CALL_SITE = re.compile(r"/code-review(?:\s+(\w+))?")

# A reviewer whose axes are a subset of the policy's and whose severity scale is one of the
# four this policy collapsed. It is upstream, so its body cannot be fixed; dropping `review`
# from its groups is what stops `scout` and `--group review` offering it as a reviewer, and
# that only works while claude-kit leaves hand-maintained groups alone.
SUPERSEDED = "code-review-and-quality"


def call_sites():
    """Our own artifacts that tell a caller to run a review, and nothing upstream.

    The upstream skill trees are excluded for the reason the policy's own skip rules give:
    `claude-kit update` replaces them wholesale, so an edit there is discarded on the next
    sync.
    """
    yield from sorted(PLUGINS.glob("*/agents/*.md"))
    yield from sorted((SKILLS / "feature-team").glob("*.md"))
    yield CLAUDE / "GETTING-STARTED.md"
    yield CLAUDE / "README.md"


def ai_task(name):
    tasks = yaml.safe_load(AI_TASKS.read_text())
    matching = [t for t in tasks if t.get("name") == name]
    assert len(matching) == 1, f"expected exactly one '{name}' task in the ai role"
    return matching[0]


def test_the_policy_is_linked_into_the_user_rules_directory():
    """The only route a machine-wide review policy has."""
    task = ai_task(RULES_TASK)
    spec = task["ansible.builtin.file"]
    assert spec["state"] == "link"
    assert "{{ role_path }}" in spec["src"], "src must be absolute or the link dangles"
    assert spec["dest"] == "{{ HOME }}/.claude/rules/{{ item | basename }}"
    assert task["with_fileglob"] == ["{{ role_path }}/files/claude/rules/*.md"], (
        "the glob must be *.md so a future tests/ or README beside a rule stays unlinked"
    )


def test_the_rules_directory_is_created_before_anything_links_into_it():
    """`state: link` does not create parents, so a missing entry here fails the play."""
    task = ai_task(DIRS_TASK)
    assert "{{ HOME }}/.claude/rules" in task["loop"]


def test_the_policy_exists_and_is_the_only_kind_of_file_in_the_rules_tree():
    """Every .md here is linked, so anything that is not a rule becomes one."""
    assert POLICY.is_file()
    stray = [p.name for p in RULES.iterdir() if p.suffix != ".md"]
    assert stray == [], f"non-rule files in rules/ would confuse the tree: {stray}"


def test_no_review_md_reaches_the_home_directory():
    """The local review reads no REVIEW.md, so one in ~/.claude is a file nothing opens.

    In rules/ it would be an always-on instruction about an unreadable file. In the
    top-level loop it would sit beside CLAUDE.md as an unscoped rule. A repository
    REVIEW.md belongs at the root that reads it, written the day hosted Code Review is
    enabled, not staged here against a day that may not come.
    """
    assert not (RULES / "REVIEW.md").exists()
    assert "REVIEW.md" not in ai_task(CONFIG_TASK)["loop"]


@pytest.mark.parametrize("severity", SEVERITIES)
def test_the_policy_holds_the_whole_severity_vocabulary(severity):
    assert severity in POLICY.read_text(), f"the policy dropped `{severity}`"


def test_the_resident_policy_routes_to_the_mechanics_skill():
    """The split only works while the always-on half names the half that is not.

    Nothing in the harness wires the policy to `/code-review`: it applies because it is
    resident. So the deferred half has no route at all except this sentence, and losing it
    leaves a reviewer with the severities and no verification bar.
    """
    assert MECHANICS.is_file(), "the deferred half of the policy is missing"
    assert "review-mechanics" in POLICY.read_text(), (
        "the policy stopped naming `review-mechanics`, so nothing loads the report machinery"
    )


def test_the_mechanics_skill_is_tagged_global():
    """Untagged it never links into ~/.claude/skills, so the stub points at nothing.

    `claude-kit sync` derives the user-scope set from the `global` tag, and prunes anything
    in that tree it cannot derive.
    """
    entries = [
        skill
        for skill in json.loads(SKILL_REGISTRY.read_text())["local_skills"]
        if skill["name"] == "review-mechanics"
    ]
    assert len(entries) == 1, f"expected one local entry, found {len(entries)}"
    assert "global" in entries[0]["groups"], (
        "`review-mechanics` is not tagged `global`, so it never reaches ~/.claude/skills"
    )


def test_every_seat_the_policy_routes_to_exists():
    """A route to a renamed or dropped seat is a checklist silently never opened."""
    routed = {m.group(1) for m in SEAT_ROUTE.finditer(MECHANICS.read_text())}
    assert routed, "the mechanics skill should route at least one axis to a seat"
    missing = [
        seat
        for seat in sorted(routed)
        if not (PLUGINS / seat / "skills" / f"{seat}-failure-modes" / "SKILL.md").is_file()
    ]
    assert missing == [], f"policy routes to seats that do not ship: {missing}"


@pytest.mark.parametrize("skill", MUTATORS)
def test_every_banned_mutator_still_exists_under_that_name(skill):
    """The ban is by name, so a rename would quietly unban the thing that writes."""
    assert skill in MECHANICS.read_text(), f"the mechanics skill stopped naming `{skill}`"
    assert (SKILLS / skill / "SKILL.md").is_file(), f"`{skill}` is not a skill any more"


def test_the_policy_bans_the_flag_the_harness_itself_ships():
    """`--fix` mutates exactly as the other named tools do.

    A list of other people's writers reads as a complete ban while leaving the one flag a
    reviewer is most likely to reach for unmentioned.
    """
    assert "/code-review --fix" in MECHANICS.read_text()


@pytest.mark.parametrize("path", list(call_sites()), ids=lambda p: p.name)
def test_every_call_site_names_an_effort(path):
    """A bare `/code-review` asks for the default whatever the diff is.

    Nothing can pass effort on the caller's behalf, so the level has to be in the text.
    """
    bare = [
        line.strip()
        for line in path.read_text().split("\n")
        if any(m.group(1) not in EFFORTS for m in CALL_SITE.finditer(line))
    ]
    assert bare == [], f"{path.name} tells a caller to run a review with no effort: {bare}"


def test_at_least_one_call_site_exists_to_check():
    """The parametrize above passes vacuously if the glob ever stops matching."""
    found = [p for p in call_sites() if CALL_SITE.search(p.read_text())]
    assert len(found) >= 15, f"expected the seat bench plus the docs, found {len(found)}"


@pytest.mark.parametrize("effort", EFFORTS)
def test_the_policy_documents_every_effort_a_call_site_could_name(effort):
    """The table is the authority, so a level pinned anywhere must be described here."""
    assert f"`{effort}`" in MECHANICS.read_text(), f"the effort table omits `{effort}`"


def test_the_superseded_reviewer_is_named_and_untagged():
    """Three halves of one claim, and the third is the one that can rot silently.

    Its body is upstream and unfixable, so the policy states precedence and the registry
    stops advertising it as a reviewer. `registry.stamp_entry` writes only `updated_at`,
    which is what makes a hand-maintained `groups` survive `claude-kit update`; if that ever
    changes, `review` comes back and this fails.
    """
    assert SUPERSEDED in MECHANICS.read_text(), (
        "the mechanics skill stopped naming the rival reviewer"
    )
    assert (SKILLS / SUPERSEDED / "SKILL.md").is_file()

    entries = [
        skill
        for repo in json.loads(SKILL_REGISTRY.read_text())["repos"].values()
        for skill in repo["skills"]
        if skill["upstream_path"].rsplit("/", 1)[-1] == SUPERSEDED
    ]
    assert len(entries) == 1, f"expected one tracked entry, found {len(entries)}"
    assert "review" not in entries[0]["groups"], (
        f"`{SUPERSEDED}` is tagged `review` again, so scout offers it as a reviewer"
    )
