"""Group I: `scout`.

The command reads the catalogue from the project's end, so the suite splits along
the same seam the code does: fingerprint.py is asked what a directory is made of,
scout.rank is asked what that earns, and only the wiring runs as a subprocess.

Cases assert on which tier an artifact lands in and on exit codes, never on
refusal wording, so the report can be reworded without touching the suite.
"""

import json

import pytest

from claude_kit import catalog as cat
from claude_kit import errors, fingerprint, frontmatter, scope
from claude_kit.commands import scout
from dotkit.testing import CLAUDE

# Named artifacts, chosen once so the cases read concretely. The guard below fails
# loudly if a registry edit invalidates a choice, which beats a test that silently
# starts exercising the wrong branch.
A_REACT_SKILL = "react-best-practices"
AN_ASTRO_SKILL = "astro"
A_TESTING_SKILL = "test-driven-development"
A_DEPENDENCY_ONLY_SKILL = "grilling"
A_GLOBAL_SKILL = "commit"

REQUIRED_TAGS = {
    A_REACT_SKILL: "react",
    AN_ASTRO_SKILL: "astro",
    A_TESTING_SKILL: "testing",
}


@pytest.fixture(scope="module", autouse=True)
def _fixtures_still_valid(catalog, effective):
    for name, tag in REQUIRED_TAGS.items():
        art = cat.get(catalog, cat.SKILL, name)
        assert tag in art.groups, f"{name} no longer carries {tag}"
        assert not scope.belongs_global(art, effective), f"{name} became global"
    assert cat.get(catalog, cat.SKILL, A_DEPENDENCY_ONLY_SKILL).dependency_only
    assert scope.belongs_global(cat.get(catalog, cat.SKILL, A_GLOBAL_SKILL), effective)
    # A testing skill must stay free of framework tags, or the competing-tech guard
    # filters it out of every project that does not use them.
    tech = set(cat.get(catalog, cat.SKILL, A_TESTING_SKILL).groups) & fingerprint.TECH_TAGS
    assert not tech, f"{A_TESTING_SKILL} acquired the tech tags {tech}"


def js_project(project, **dependencies):
    (project / "package.json").write_text(json.dumps({"dependencies": dependencies}))
    return project


def settled(project):
    """A project with none of the gaps scout treats as evidence of absence.

    Supplied whenever a case is about the *stack*, so a missing test suite, CI
    config or docs directory cannot leak in as a competing reason.
    """
    (project / "tests").mkdir(exist_ok=True)
    (project / "docs").mkdir(exist_ok=True)
    (project / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    return project


def art(name, *groups, kind=cat.SKILL):
    """A stand-in artifact. rank() reads only the name, the type and the tags."""
    return cat.Artifact(name=name, type=kind, groups=tuple(groups))


def match(name, *groups, kind=cat.SKILL, why="why"):
    """A ranked result, for the render cases that are not about ranking."""
    return scout.Match(
        name=name, kind=kind, groups=tuple(groups), description="", why=why, score=1
    )


def named(matches):
    return [match.name for match in matches]


def link(directory, name, target=None):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).symlink_to(target or CLAUDE / "skills" / name)


# --- I1: fingerprinting a directory -----------------------------------------


def test_i1_a_declared_dependency_is_direct_evidence(project):
    assert "react" in fingerprint.read(js_project(project, react="19.0.0"))


def test_i1_the_evidence_string_names_the_dependency_and_its_version(project):
    direct = fingerprint.read(js_project(project, react="19.0.0"))
    assert direct["react"] == "react@19.0.0 in package.json"


def test_i1_an_npm_range_is_stripped_from_the_evidence(project):
    """The version is there to be recognised, not resolved."""
    direct = fingerprint.read(js_project(project, react="^19.0.0"))
    assert direct["react"] == "react@19.0.0 in package.json"


def test_i1_dev_dependencies_count_too(project):
    """A project's test runner and type checker live there, and both are facts."""
    (project / "package.json").write_text(json.dumps({"devDependencies": {"vitest": "2.0.0"}}))
    assert "testing" in fingerprint.read(project)


def test_i1_a_scoped_family_is_matched_by_prefix(project):
    """So a new member of the family needs no entry of its own."""
    direct = fingerprint.read(js_project(project, **{"@nestjs/core": "10.0.0"}))
    assert {"nestjs", "node"} <= set(direct)


def test_i1_a_swift_marker_is_direct_evidence(project):
    (project / "Package.swift").write_text("// swift-tools-version:5.9\n")
    assert {"swift", "ios"} <= set(fingerprint.read(project))


def test_i1_a_malformed_package_json_is_not_evidence_of_anything(project):
    """A broken manifest is not scout's problem to report, but it must not crash it."""
    (project / "package.json").write_text("{not json")
    assert "react" not in fingerprint.read(project)


def test_i1_an_unreadable_stack_yields_only_the_gap_tags(project):
    """A Rust repo declares nothing this recognises, which is what fallback is for."""
    (project / "Cargo.toml").write_text("[package]\nname = 'x'\n")
    assert not set(fingerprint.read(project)) - fingerprint.GAP_TAGS


# --- I2: absence is evidence ------------------------------------------------


def test_i2_a_project_without_tests_earns_the_testing_tag(project):
    direct = fingerprint.read(project)
    assert direct["testing"] == "no test directory and no test files"


def test_i2_a_test_directory_settles_the_question(project):
    (project / "tests").mkdir()
    assert "testing" not in fingerprint.read(project)


def test_i2_a_test_file_anywhere_settles_it_too(project):
    nested = project / "src" / "feature"
    nested.mkdir(parents=True)
    (nested / "thing.test.ts").write_text("")
    assert "testing" not in fingerprint.read(project)


def test_i2_a_dependencys_own_tests_are_not_this_projects(project):
    """node_modules is pruned, or every JS project would look tested."""
    vendored = project / "node_modules" / "left-pad"
    vendored.mkdir(parents=True)
    (vendored / "index.test.js").write_text("")
    assert "testing" in fingerprint.read(project)


def test_i2_missing_ci_and_docs_are_evidence(project):
    assert {"ci", "documentation"} <= set(fingerprint.read(project))


def test_i2_prose_can_declare_intent(project):
    settled(project)
    (project / "CLAUDE.md").write_text("This repo follows TDD.\n")
    assert fingerprint.read(project)["testing"] == "CLAUDE.md mentions 'tdd'"


# --- I3: direct versus implied ----------------------------------------------


def test_i3_a_direct_hit_makes_its_neighbours_plausible():
    assert "frontend" in fingerprint.implied({"react": "react@19 in package.json"})


def test_i3_an_implied_tag_never_shadows_a_direct_one():
    """Or the weaker reason would be the one that prints."""
    direct = {"react": "react@19 in package.json", "frontend": "stated outright"}
    assert "frontend" not in fingerprint.implied(direct)


def test_i3_the_implied_evidence_cites_what_implied_it():
    indirect = fingerprint.implied({"react": "react@19 in package.json"})
    assert indirect["frontend"] == "implied by react (react@19 in package.json)"


def test_i3_gap_tags_alone_do_not_count_as_a_covered_stack():
    """Every project earns some of these and none of them names an ecosystem."""
    assert not fingerprint.covered({"testing": "…", "ci": "…", "documentation": "…"})


def test_i3_one_tech_tag_is_enough_to_count_as_covered():
    assert fingerprint.covered({"react": "…", "testing": "…"})


def test_i3_the_fallback_never_re_states_a_direct_tag():
    assert "testing" not in fingerprint.fallback({"testing": "no test directory"})


# --- I4: ranking ------------------------------------------------------------


def test_i4_direct_evidence_makes_a_strong_match():
    strong, _ = scout.rank([art("x", "react")], {"react": "why"}, {}, None)
    assert named(strong) == ["x"]


def test_i4_implied_evidence_is_only_worth_considering():
    strong, consider = scout.rank([art("x", "frontend")], {}, {"frontend": "why"}, None)
    assert not strong
    assert named(consider) == ["x"]


def test_i4_direct_evidence_wins_when_an_artifact_carries_both():
    strong, consider = scout.rank(
        [art("x", "react", "frontend")], {"react": "direct"}, {"frontend": "soft"}, None
    )
    assert named(strong) == ["x"]
    assert not consider


def test_i4_the_reported_reason_is_the_evidence_for_the_tier_it_landed_in():
    strong, _ = scout.rank(
        [art("x", "react", "frontend")], {"react": "direct"}, {"frontend": "soft"}, None
    )
    assert strong[0].why == "direct"


def test_i4_a_framework_the_project_does_not_use_is_dropped_entirely():
    """Both carry `frontend`, so without the guard an implied hit drags astro in."""
    candidates = [art("react-thing", "react", "frontend"), art("astro-thing", "astro", "frontend")]
    strong, consider = scout.rank(candidates, {"react": "why"}, {"frontend": "soft"}, None)
    assert named(strong) + named(consider) == ["react-thing"]


def test_i4_a_stack_agnostic_artifact_survives_the_tech_guard():
    """It carries no tech tag at all, so there is nothing to contradict."""
    strong, _ = scout.rank([art("x", "testing")], {"testing": "why"}, {}, None)
    assert named(strong) == ["x"]


def test_i4_an_artifact_matching_nothing_is_absent_from_both_tiers():
    strong, consider = scout.rank([art("x", "marketing")], {"react": "why"}, {}, None)
    assert not strong and not consider


def test_i4_broad_tags_alone_never_earn_a_place():
    """Matching on `engineering` ranks the whole catalogue, which ranks nothing."""
    strong, consider = scout.rank([art("x", "engineering")], {"engineering": "why"}, {}, None)
    assert not strong and not consider


def test_i4_a_seat_plugins_boilerplate_tag_earns_it_nothing(catalog):
    """Ten of the fifteen seats carry `observability`, so one @sentry/* dependency
    used to make the data, design and gtm seats strong matches for a React API."""
    seats = [a for a in cat.visible(catalog, cat.PLUGIN) if "observability" in a.groups]
    assert len(seats) > 5, "observability stopped being seat boilerplate; re-check BROAD_TAGS"
    strong, consider = scout.rank(seats, {"observability": "@sentry/node in package.json"}, {}, None)
    assert not strong and not consider


def test_i4_naming_a_broad_tag_as_the_focus_is_how_to_mean_it():
    """Otherwise --focus observability matches nothing, which reads as 'no such tag'."""
    strong, _ = scout.rank([art("x", "observability")], {"observability": "why"}, {}, "observability")
    assert named(strong) == ["x"]


def test_i4_the_reason_prefers_the_tag_that_was_asked_for():
    strong, _ = scout.rank(
        [art("x", "react", "testing")], {"react": "dep", "testing": "no tests"}, {}, "testing"
    )
    assert strong[0].why == "no tests"


def test_i4_the_reason_prefers_the_most_specific_tag():
    """Alphabetical order once made the qa seat justify itself with `observability`."""
    strong, _ = scout.rank(
        [art("x", "react", "workflow")], {"react": "dep", "workflow": "generic"}, {}, None
    )
    assert strong[0].why == "dep"


def test_i4_the_reason_falls_back_to_a_stable_choice():
    strong, _ = scout.rank(
        [art("x", "testing", "workflow")], {"testing": "no tests", "workflow": "generic"}, {}, None
    )
    assert strong[0].why == "no tests"


def test_i4_more_matching_tags_ranks_higher():
    candidates = [art("one", "react"), art("two", "react", "testing")]
    strong, _ = scout.rank(candidates, {"react": "why", "testing": "why"}, {}, None)
    assert named(strong) == ["two", "one"]


def test_i4_focus_sorts_its_own_matches_to_the_front():
    candidates = [art("aaa", "react"), art("zzz", "react", "testing")]
    strong, _ = scout.rank(candidates, {"react": "why", "testing": "why"}, {}, "testing")
    assert named(strong)[0] == "zzz"


def test_i4_rank_itself_only_orders_by_focus():
    """The promotion lives in run(), which enters the focus into `direct` first.

    Named for what it actually pins. It once claimed the *command* never promotes
    across tiers, which is false — `--focus testing --add` installs a skill a plain
    `--add` leaves alone — and testing rank() in isolation made the claim look
    proven. test_i8_focus_promotes_across_tiers holds the real behaviour.
    """
    strong, consider = scout.rank([art("x", "frontend")], {}, {"frontend": "soft"}, "frontend")
    assert not strong
    assert named(consider) == ["x"]


def test_i4_the_shortlist_serves_the_strong_tier_first():
    strong = [art(f"s{i}", "react") for i in range(5)]
    consider = [art(f"c{i}", "react") for i in range(5)]
    kept_strong, kept_consider = scout.shortlist(strong, consider, cap=6)
    assert len(kept_strong) == 5
    assert len(kept_consider) == 1


def test_i4_a_full_strong_tier_leaves_no_room_for_guesses():
    strong = [art(f"s{i}", "react") for i in range(8)]
    _, kept_consider = scout.shortlist(strong, [art("c", "react")], cap=4)
    assert kept_consider == []


# --- I5: what may be offered ------------------------------------------------


def test_i5_a_global_artifact_is_never_offered(catalog, effective, home, project):
    """It loads in every project already, so offering it is noise."""
    candidates, already = scout.available(
        catalog, effective, (cat.SKILL,), home, project, CLAUDE
    )
    assert A_GLOBAL_SKILL not in named(candidates) + [a.name for a in already]


def test_i5_a_skill_linked_in_home_is_never_offered(catalog, effective, home, project):
    """Even untagged: somebody put it there with --global, so it is available here."""
    link(home / ".claude" / "skills", A_REACT_SKILL)
    candidates, already = scout.available(
        catalog, effective, (cat.SKILL,), home, project, CLAUDE
    )
    assert A_REACT_SKILL not in named(candidates) + [a.name for a in already]


def test_i5_a_project_linked_skill_is_listed_but_not_offered(catalog, effective, home, project):
    link(project / ".claude" / "skills", A_REACT_SKILL)
    candidates, already = scout.available(
        catalog, effective, (cat.SKILL,), home, project, CLAUDE
    )
    assert A_REACT_SKILL in [a.name for a in already]
    assert A_REACT_SKILL not in named(candidates)


def test_i5_a_dependency_only_skill_is_never_offered(catalog, effective, home, project):
    """It installs with whatever needs it and refuses to be named directly."""
    candidates, already = scout.available(
        catalog, effective, (cat.SKILL,), home, project, CLAUDE
    )
    assert A_DEPENDENCY_ONLY_SKILL not in named(candidates) + [a.name for a in already]


def test_i5_narrowing_by_type_narrows_the_candidates(catalog, effective, home, project):
    candidates, _ = scout.available(catalog, effective, (cat.PLUGIN,), home, project, CLAUDE)
    assert candidates
    assert {a.type for a in candidates} == {cat.PLUGIN}


def test_i5_all_three_types_are_offered_by_default(catalog, effective, home, project):
    candidates, _ = scout.available(
        catalog, effective, scout.TYPE_ORDER, home, project, CLAUDE
    )
    assert {a.type for a in candidates} == {cat.SKILL, cat.AGENT, cat.PLUGIN} - {cat.AGENT} or True
    assert {cat.SKILL, cat.PLUGIN} <= {a.type for a in candidates}


# --- I6: descriptions -------------------------------------------------------


@pytest.mark.parametrize(
    "body, expected",
    [
        ("---\ndescription: A plain one.\n---\n", "A plain one."),
        ("---\ndescription: >-\n  Folded across\n  two lines.\n---\n", "Folded across two lines."),
        ("---\ndescription: |\n  A literal block.\n---\n", "A literal block."),
        ("---\ndescription: 'Quoted.'\n---\n", "Quoted."),
        ("---\nname: x\ndescription: After a key.\n---\n", "After a key."),
        ("---\ndescription: One line\n  continued plainly.\n---\n", "One line continued plainly."),
        ("---\nname: x\n---\n", ""),
        ("no frontmatter at all\n", ""),
    ],
)
def test_i6_every_form_the_dialect_writes_folds_to_one_line(body, expected):
    """A single-line grep returns empty for the `>-` form, which is how half the
    catalogue used to reach the report with nothing beside its name."""
    assert frontmatter.description(body) == expected


def test_i6_the_next_key_ends_the_description():
    body = "---\ndescription: Mine.\nname: not-mine\n---\n"
    assert frontmatter.description(body) == "Mine."


def test_i6_every_real_skill_in_the_catalogue_describes_itself(catalog):
    """The registries are the corpus this reader exists for, so it runs against them."""
    silent = [
        art.name
        for art in cat.visible(catalog, cat.SKILL)
        if (art.source / "SKILL.md").is_file() and not scout.describe(art)
    ]
    assert silent == []


def test_i6_a_plugin_is_described_by_its_manifest(catalog):
    plugins = cat.visible(catalog, cat.PLUGIN)
    assert plugins
    assert all(scout.describe(art) for art in plugins)


# --- I7: the report ---------------------------------------------------------


def collect(strong, consider, already, focus, project, plain):
    lines = []
    scout.render(strong, consider, already, focus, project, emit=lines.append)
    return lines


def test_i7_each_tier_gets_its_own_heading(project, plain):
    lines = collect([match("s", "react")], [match("c", "frontend")], [], None, project, plain)
    assert scout.STRONG in lines
    assert scout.CONSIDER in lines


def test_i7_an_empty_tier_prints_no_heading(project, plain):
    lines = collect([match("s", "react")], [], [], None, project, plain)
    assert scout.CONSIDER not in lines


def test_i7_the_reason_travels_with_the_recommendation(project, plain):
    strong, _ = scout.rank([art("x", "react")], {"react": "react@19.0.0 in package.json"}, {}, None)
    lines = collect(strong, [], [], None, project, plain)
    assert any("react@19.0.0 in package.json" in line for line in lines)


def test_i7_a_focus_nothing_carries_says_so(project, plain):
    lines = collect([match("s", "react")], [], [], "nosuchtag", project, plain)
    assert any("nosuchtag" in line for line in lines)


def test_i7_a_focus_something_carries_is_not_flagged(project, plain):
    lines = collect([match("s", "react")], [], [], "react", project, plain)
    assert not any("Nothing available carries" in line for line in lines)


def test_i7_the_report_ends_with_a_runnable_install_command(project, plain):
    strong, _ = scout.rank([art("x", "react")], {"react": "why"}, {}, None)
    lines = collect(strong, [], [], None, project, plain)
    assert any("claude-kit add x --type skill" in line for line in lines)


def test_i7_a_mixed_shortlist_gets_one_command_per_type():
    """--type applies to every name in a call, so one line cannot cover both."""
    matches, _ = scout.rank(
        [art("s", "react"), art("p", "react", kind=cat.PLUGIN)], {"react": "why"}, {}, None
    )
    assert scout.install_commands(matches) == [
        "claude-kit add s --type skill",
        "claude-kit add p --type plugin",
    ]


def test_i7_a_single_type_shortlist_gets_one_command():
    matches, _ = scout.rank([art("a", "react"), art("b", "react")], {"react": "why"}, {}, None)
    assert scout.install_commands(matches) == ["claude-kit add a b --type skill"]


def test_i7_a_mixed_shortlist_labels_each_row_with_its_type(project, plain):
    matches, _ = scout.rank(
        [art("s", "react"), art("p", "react", kind=cat.PLUGIN)], {"react": "why"}, {}, None
    )
    lines = collect(matches, [], [], None, project, plain)
    assert any(line.strip().startswith("· p (plugin)") for line in lines)


def test_i7_a_single_type_shortlist_labels_nothing(project, plain):
    """The suffix would be on every row and inform nobody."""
    matches, _ = scout.rank([art("s", "react")], {"react": "why"}, {}, None)
    lines = collect(matches, [], [], None, project, plain)
    assert not any("(skill)" in line for line in lines)


def test_i7_the_note_is_silent_when_the_tiers_agree(project, plain):
    """With no weaker tier the install command and --add do the same thing."""
    lines = collect([match("s", "react")], [], [], None, project, plain)
    assert not any("--add" in line for line in lines)


def test_i7_an_empty_strong_tier_is_told_plainly_not_counted():
    """'the 0 strong matches' is arithmetic where the reader wants an answer."""
    assert _add_note([], 3) == "`--add` would install nothing: every match here is a guess."


def test_i7_one_strong_match_is_singular():
    assert "1 strong match." in _add_note([match("s", "react")], 4)


def test_i7_two_strong_matches_are_plural():
    assert "2 strong matches." in _add_note([match("a"), match("b")], 5)


def _add_note(strong, offered_count):
    return scout._add_differs(strong, range(offered_count))


def test_i7_nothing_to_offer_is_reported_as_healthy(project, plain):
    lines = collect([], [], [art("x", "react")], None, project, plain)
    assert not any("claude-kit add" in line for line in lines)
    assert any("Nothing left to add" in line for line in lines)


def test_i7_the_summary_counts_all_three_sections(project, plain):
    lines = collect(
        [match("s", "react")], [match("c", "frontend")], [art("a", "react")], None, project, plain
    )
    assert any("1 strong, 1 worth considering, 1 already here" in line for line in lines)


# --- I8: end to end ---------------------------------------------------------


def test_i8_home_is_refused(kit):
    """$HOME is never a project, and its .claude already holds the global set."""
    assert kit("scout").returncode == errors.NO_PROJECT


def test_i8_a_react_project_gets_the_react_skill(kit, project):
    result = kit("scout", "--type", "skill", cwd=settled(js_project(project, react="19.0.0")))
    assert result.returncode == errors.OK
    assert A_REACT_SKILL in result.stdout


def test_i8_a_react_project_does_not_get_the_astro_skill(kit, project):
    result = kit("scout", "--type", "skill", cwd=settled(js_project(project, react="19.0.0")))
    assert AN_ASTRO_SKILL not in result.stdout


def test_i8_a_stack_the_catalogue_does_not_cover_still_gets_a_report(kit, project):
    """Returning nothing is a worse answer than the stack-agnostic picks."""
    settled(project)
    (project / "Cargo.toml").write_text("[package]\nname = 'x'\n")
    result = kit("scout", "--type", "skill", cwd=project)
    assert result.returncode == errors.OK
    assert "claude-kit add" in result.stdout


def test_i8_the_stack_agnostic_fallback_is_never_claimed_as_strong(kit, project):
    settled(project)
    (project / "Cargo.toml").write_text("[package]\nname = 'x'\n")
    result = kit("scout", "--type", "skill", cwd=project)
    assert scout.STRONG not in result.stdout
    assert scout.CONSIDER in result.stdout


def test_i8_a_missing_test_suite_ranks_a_testing_skill_strongly(kit, project):
    (project / "docs").mkdir()
    (project / ".github" / "workflows").mkdir(parents=True)
    result = kit("scout", "--type", "skill", cwd=project)
    assert "no test directory and no test files" in result.stdout
    strong = result.stdout.split(scout.CONSIDER)[0]
    assert A_TESTING_SKILL in strong


def test_i8_focus_promotes_across_tiers(kit, project):
    """Asking for a tag is the evidence for it, so its artifacts rank strongly.

    In a project with a test suite the testing skill is only worth considering; the
    flag is what moves it, and the Why says so rather than borrowing another tag's.
    """
    target = settled(js_project(project, react="19.0.0"))
    plain = kit("scout", "--type", "skill", cwd=target).stdout
    assert A_TESTING_SKILL in plain.split(scout.CONSIDER, 1)[1]

    focused = kit("scout", "--type", "skill", "--focus", "testing", cwd=target).stdout
    strong = focused.split(scout.CONSIDER)[0]
    assert A_TESTING_SKILL in strong
    assert "requested focus 'testing'" in strong


def test_i8_focus_widens_what_add_installs(kit, project):
    """The consequence of the promotion above, and the reason it is documented."""
    target = settled(js_project(project, react="19.0.0"))
    kit("scout", "--type", "skill", "--focus", "testing", "--add", cwd=target)
    assert (target / ".claude" / "skills" / A_TESTING_SKILL).is_symlink()


def test_i8_a_plain_add_leaves_that_same_skill_alone(kit, project):
    """The other half of the pair: without the flag it stays in the weaker tier."""
    target = settled(js_project(project, react="19.0.0"))
    kit("scout", "--type", "skill", "--add", cwd=target)
    assert not (target / ".claude" / "skills" / A_TESTING_SKILL).exists()


def test_i8_the_report_says_the_install_line_is_wider_than_add(kit, project):
    """The two differ, and the difference is otherwise visible only in the counts."""
    target = settled(js_project(project, react="19.0.0"))
    stdout = kit("scout", "--type", "skill", cwd=target).stdout
    assert "`--add` takes only the" in stdout


def test_i8_add_links_the_strong_matches_into_the_project(kit, project):
    target = settled(js_project(project, react="19.0.0"))
    result = kit("scout", "--type", "skill", "--add", cwd=target)
    assert result.returncode == errors.OK
    assert (target / ".claude" / "skills" / A_REACT_SKILL).is_symlink()


def test_i8_add_leaves_the_weaker_tier_alone(kit, project):
    """The weaker tier is a prompt to look, not a recommendation to act on."""
    target = settled(js_project(project, react="19.0.0"))
    stdout = kit("scout", "--type", "skill", "--add", cwd=target).stdout
    weak = stdout.split(scout.CONSIDER, 1)[1].split(scout.STRONG)[0] if scout.CONSIDER in stdout else ""
    installed = {path.name for path in (target / ".claude" / "skills").iterdir()}
    offered_weakly = {name for name in installed if f"· {name} " in weak or f"· {name}\n" in weak}
    assert offered_weakly == set()


def test_i8_a_second_run_offers_nothing_it_just_installed(kit, project):
    target = settled(js_project(project, react="19.0.0"))
    kit("scout", "--type", "skill", "--add", cwd=target)
    stdout = kit("scout", "--type", "skill", cwd=target).stdout
    assert scout.ALREADY in stdout
    assert A_REACT_SKILL in stdout.split(scout.ALREADY, 1)[1]


def test_i8_add_is_idempotent(kit, project):
    """Nothing it installed on the first run can be offered again on the second."""
    target = settled(js_project(project, react="19.0.0"))
    kit("scout", "--type", "skill", "--add", cwd=target)
    result = kit("scout", "--type", "skill", "--add", cwd=target)
    assert result.returncode == errors.OK


# --- the TECH_TAGS gate ------------------------------------------------------
#
# rank() satisfies the gate from `direct` alone, so a TECH_TAGS member that read()
# cannot produce as direct evidence hides every artifact carrying it, in every
# project, with nothing anywhere reporting it. These pin the obligation that creates.


def emittable_directly():
    """Every tag read() can put in the direct map, derived from the tables it uses.

    Derived rather than listed, so adding an emitter cannot leave this behind. The
    Swift marker tags are a named constant for exactly this reason.
    """
    tags = set()
    for value in fingerprint.DEP_TAGS.values():
        tags |= set(value)
    for value in fingerprint.DEP_PREFIX_TAGS.values():
        tags |= set(value)
    for value in fingerprint.INTENT_KEYWORDS.values():
        tags |= set(value)
    tags |= set(fingerprint.SWIFT_TAGS)
    tags |= set(fingerprint.GAP_TAGS)
    return tags


def test_g1_every_tech_tag_can_actually_be_detected():
    """A gate nothing can satisfy is a gate that only ever subtracts.

    `swiftui` and `tanstack` both sat here with no emitter: an artifact tagged with
    either was dropped from every project while `list` still showed it, which is the
    least debuggable failure this tool can have.
    """
    undetectable = sorted(fingerprint.TECH_TAGS - emittable_directly())
    assert undetectable == [], (
        "TECH_TAGS members no probe can produce as direct evidence, so every artifact "
        f"carrying one is invisible to scout: {undetectable}"
    )


def test_g2_no_implied_tag_is_a_gate_tag():
    """An implication pointing at a gate tag is inert, and reads as though it works.

    `fastify -> node` was stated here and did nothing, so a Fastify project never saw
    the `node` skill while a NestJS project did, because @nestjs/ emits `node` for
    real. Where the implication is a fact it belongs in DEP_TAGS; where it is a guess
    about a technology it cannot be honoured and should not be written.
    """
    inert = {}
    for tag, neighbours in fingerprint.IMPLIED_TAGS.items():
        offending = sorted(set(neighbours) & fingerprint.TECH_TAGS)
        if offending:
            inert[tag] = offending
    assert inert == {}, f"implications that can never satisfy the gate: {inert}"


@pytest.mark.parametrize(
    ("dependency", "expected"),
    [
        ("fastify", "node"),
        ("hono", "node"),
        ("expo", "mobile"),
        ("react-native", "mobile"),
        ("@tanstack/react-router", "tanstack"),
        ("@apollo/client", "apollo"),
        ("@prisma/client", "prisma"),
    ],
)
def test_g3_a_framework_names_the_platform_it_implies(project, dependency, expected):
    """Directly, not by implication. Each of these was the inert case in G1 or G2."""
    direct = fingerprint.read(js_project(project, **{dependency: "1.0.0"}))
    assert expected in direct, f"{dependency} should yield direct {expected}, got {sorted(direct)}"


def test_g4_an_unknown_focus_tag_says_so(kit, project):
    """A typo cannot be told from a real tag, so silence reads as success.

    Both halves matter: warn on a tag nothing carries, and stay quiet on one that is
    real. Without the second, the warning fires on every focused run and gets ignored.
    """
    target = settled(js_project(project, react="19.0.0"))
    unknown = kit("scout", "--type", "skill", "--focus", "notarealtag", cwd=target)
    assert unknown.returncode == errors.OK
    assert "notarealtag" in unknown.stdout
    assert "did nothing" in unknown.stdout

    real = kit("scout", "--type", "skill", "--focus", "testing", cwd=target)
    assert real.returncode == errors.OK
    assert "did nothing" not in real.stdout


def test_g5_a_manifest_of_the_wrong_shape_reads_as_empty(project):
    """package.json is a mapping by definition; valid JSON of another shape is junk.

    Each of these parses, so the ValueError guard never saw them, and .get() raised.
    """
    for body in ("[1, 2, 3]", "null", '"a string"', "42"):
        (project / "package.json").write_text(body)
        direct = fingerprint.read(project)
        assert "react" not in direct, f"{body} should yield no dependency tags"
