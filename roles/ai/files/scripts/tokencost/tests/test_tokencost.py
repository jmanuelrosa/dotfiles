"""`tokencost` prices Claude Code transcripts, so the cases pin the arithmetic.

Every figure asserted here is hand-computable from the rate table, which is the point:
a pricing bug is invisible in real data (the number simply looks plausible) and this is
the only place it can be caught. Token counts are all round millions so the expected
dollar amount reads off the multipliers directly.

`HOME` is the single environmental seam, exactly as it is for claude-kit: the tool
resolves `~/.claude/projects` and nothing else, so a fabricated tree under `tmp_path`
exercises every path without touching the real transcripts.
"""

import json
import subprocess
import sys

import pytest

from dotkit.testing import AI_SCRIPTS_DIR

TOKENCOST = AI_SCRIPTS_DIR / "tokencost" / "tokencost"

EXIT_OK = 0
EXIT_NOT_FOUND = 2

# One million tokens in each class, so the expected cost is the rate table by eye.
# Opus is $5 in / $25 out, a 1h cache write is 2x input and a read is 0.1x:
#   5.00 + 10.00 + 0.50 + 25.00 = 40.50
MILLION = 1_000_000
ROUND_USAGE = {
    "input_tokens": MILLION,
    "cache_creation_input_tokens": MILLION,
    "cache_read_input_tokens": MILLION,
    "output_tokens": MILLION,
    "cache_creation": {"ephemeral_1h_input_tokens": MILLION, "ephemeral_5m_input_tokens": 0},
}
ROUND_COST = 40.50


def record(usage, skill=None, model="claude-opus-5", stamp="2026-08-07T12:00:00.000Z"):
    entry = {"type": "assistant", "timestamp": stamp, "message": {"model": model, "usage": usage}}
    if skill:
        entry["attributionSkill"] = skill
    return entry


def write_transcript(home, project, session, records, agent=None):
    """Lay down one transcript, as a session's own or as one of its subagents'."""
    base = home / ".claude" / "projects" / project
    if agent:
        target = base / session / "subagents" / f"{agent}.jsonl"
    else:
        target = base / f"{session}.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as handle:
        for entry in records:
            handle.write(json.dumps(entry) + "\n")
    return target


def run(home, *args):
    result = subprocess.run(
        [sys.executable, str(TOKENCOST), *args],
        capture_output=True,
        text=True,
        env={"HOME": str(home), "PATH": "/usr/bin:/bin", "NO_COLOR": "1"},
    )
    return result


@pytest.fixture
def home(tmp_path):
    (tmp_path / ".claude" / "projects").mkdir(parents=True)
    return tmp_path


def test_prices_one_record_off_the_rate_table(home):
    write_transcript(home, "-tmp-demo", "s1", [record(ROUND_USAGE, skill="pr")])
    result = run(home, "demo")
    assert result.returncode == EXIT_OK
    assert f"{ROUND_COST:.2f}" in result.stdout
    assert "pr" in result.stdout


def test_five_minute_writes_cost_less_than_one_hour_writes(home):
    short = dict(ROUND_USAGE, cache_creation={"ephemeral_1h_input_tokens": 0,
                                              "ephemeral_5m_input_tokens": MILLION})
    write_transcript(home, "-tmp-demo", "s1", [record(short, skill="pr")])
    result = run(home, "demo")
    # 5.00 + 6.25 + 0.50 + 25.00, a 5m write being 1.25x input against 1h's 2x.
    assert "36.75" in result.stdout


def test_output_rate_applies_to_the_model_tier(home):
    write_transcript(home, "-tmp-demo", "s1",
                     [record(ROUND_USAGE, skill="pr", model="claude-sonnet-5")])
    result = run(home, "demo")
    # Sonnet is $3 in / $15 out: 3.00 + 6.00 + 0.30 + 15.00.
    assert "24.30" in result.stdout


def test_unknown_model_is_priced_at_the_top_tier(home):
    write_transcript(home, "-tmp-demo", "s1",
                     [record(ROUND_USAGE, skill="pr", model="something-unreleased")])
    result = run(home, "demo")
    assert f"{ROUND_COST:.2f}" in result.stdout, "an unrecognised model must not read as cheap"


def test_nested_iterations_are_not_counted_twice(home):
    doubled = dict(ROUND_USAGE, iterations=[dict(ROUND_USAGE)])
    write_transcript(home, "-tmp-demo", "s1", [record(doubled, skill="pr")])
    result = run(home, "demo")
    assert f"{ROUND_COST:.2f}" in result.stdout
    assert "81.00" not in result.stdout


def test_missing_ttl_breakdown_falls_back_and_says_so(home):
    flat = {k: v for k, v in ROUND_USAGE.items() if k != "cache_creation"}
    write_transcript(home, "-tmp-demo", "s1", [record(flat, skill="pr")])

    assumed_long = run(home, "demo")
    assert f"{ROUND_COST:.2f}" in assumed_long.stdout
    assert "1,000,000 cache-write tokens had no TTL breakdown" in assumed_long.stdout
    assert "priced as 1h" in assumed_long.stdout

    assumed_short = run(home, "demo", "--assume-ttl", "5m")
    assert "36.75" in assumed_short.stdout
    assert "priced as 5m" in assumed_short.stdout


def test_a_full_breakdown_produces_no_assumption_warning(home):
    write_transcript(home, "-tmp-demo", "s1", [record(ROUND_USAGE, skill="pr")])
    result = run(home, "demo")
    assert "no TTL breakdown" not in result.stdout


def test_records_without_usage_or_of_another_type_are_skipped(home):
    write_transcript(home, "-tmp-demo", "s1", [
        record(ROUND_USAGE, skill="pr"),
        {"type": "user", "message": {"content": "hello"}},
        {"type": "assistant", "message": {"model": "claude-opus-5"}},
        {"not": "json-shaped but parseable"},
    ])
    result = run(home, "demo")
    assert f"{ROUND_COST:.2f}" in result.stdout


def test_unparseable_lines_do_not_abort_the_read(home):
    path = write_transcript(home, "-tmp-demo", "s1", [record(ROUND_USAGE, skill="pr")])
    with path.open("a") as handle:
        handle.write("{ this is not json\n")
    result = run(home, "demo")
    assert result.returncode == EXIT_OK
    assert f"{ROUND_COST:.2f}" in result.stdout


def test_unattributed_main_thread_work_gets_its_own_bucket(home):
    write_transcript(home, "-tmp-demo", "s1", [record(ROUND_USAGE)])
    result = run(home, "demo")
    assert "<unattributed>" in result.stdout


def test_subagents_bucket_under_the_transcript_stem_verbatim(home):
    write_transcript(home, "-tmp-demo", "s1", [record(ROUND_USAGE, skill="pr")])
    write_transcript(home, "-tmp-demo", "s1", [record(ROUND_USAGE)],
                     agent="agent-aux-shaper-route-catalog-a0279db9")
    result = run(home, "demo")
    # The stem is never parsed into an agent name: guessing one is how a first attempt
    # at this counted unrelated agents as pipeline cost.
    assert "agent:agent-aux-shaper-route-catalog-a0279db9" in result.stdout


def test_session_filter_keeps_that_session_and_its_subagents(home):
    write_transcript(home, "-tmp-demo", "wanted", [record(ROUND_USAGE, skill="kept")])
    write_transcript(home, "-tmp-demo", "wanted", [record(ROUND_USAGE)], agent="agent-sub")
    write_transcript(home, "-tmp-demo", "other", [record(ROUND_USAGE, skill="excluded")])

    result = run(home, "demo", "--session", "wanted")
    assert "kept" in result.stdout
    assert "agent:agent-sub" in result.stdout
    assert "excluded" not in result.stdout
    assert "81.00" in result.stdout, "the session's own work plus its subagent's"


def test_since_filters_by_date_but_keeps_undated_records(home):
    write_transcript(home, "-tmp-demo", "s1", [
        record(ROUND_USAGE, skill="old", stamp="2026-08-01T00:00:00.000Z"),
        record(ROUND_USAGE, skill="new", stamp="2026-08-09T00:00:00.000Z"),
        record(ROUND_USAGE, skill="undated", stamp=""),
    ])
    result = run(home, "demo", "--since", "2026-08-05")
    assert "new" in result.stdout
    assert "undated" in result.stdout, "--since must not discard what it cannot date"
    assert "old" not in result.stdout


def test_match_subtotals_the_buckets_that_contain_the_pattern(home):
    write_transcript(home, "-tmp-demo", "s1", [
        record(ROUND_USAGE, skill="product-team:5-decompose"),
        record(ROUND_USAGE, skill="product-team:6-gate-check"),
        record(ROUND_USAGE, skill="feature-team"),
    ])
    result = run(home, "demo", "--match", "product-team")
    assert "matched 2 buckets: $81.00" in result.stdout
    assert "product-team" in result.stdout


def test_match_accepts_several_patterns(home):
    write_transcript(home, "-tmp-demo", "s1", [
        record(ROUND_USAGE, skill="product-team:5-decompose"),
        record(ROUND_USAGE, skill="product-lead"),
        record(ROUND_USAGE, skill="unrelated"),
    ])
    result = run(home, "demo", "--match", "product-team", "--match", "product-lead")
    assert "matched 2 buckets: $81.00" in result.stdout


def test_top_caps_the_listing_and_names_what_it_elided(home):
    write_transcript(home, "-tmp-demo", "s1",
                     [record(ROUND_USAGE, skill=f"skill-{n}") for n in range(5)])
    result = run(home, "demo", "--top", "2")
    assert "3 more buckets totalling $121.50" in result.stdout
    assert "--top 0 for all" in result.stdout

    everything = run(home, "demo", "--top", "0")
    assert "more buckets totalling" not in everything.stdout


def test_sessions_view_lists_one_row_per_session(home):
    write_transcript(home, "-tmp-demo", "first", [record(ROUND_USAGE, skill="pr")])
    write_transcript(home, "-tmp-demo", "second", [record(ROUND_USAGE, skill="pr")])
    result = run(home, "demo", "--sessions")
    assert "first" in result.stdout
    assert "second" in result.stdout
    assert "2 sessions, $81.00" in result.stdout


def test_json_output_carries_the_totals_and_the_assumption(home):
    write_transcript(home, "-tmp-demo", "s1", [record(ROUND_USAGE, skill="pr")])
    payload = json.loads(run(home, "demo", "--json").stdout)
    assert payload["total_usd"] == pytest.approx(ROUND_COST)
    assert payload["assumed_ttl"] == "1h"
    assert payload["cache_tokens_priced_by_assumption"] == 0
    assert payload["buckets"][0]["bucket"] == "pr"
    assert payload["buckets"][0]["tokens"]["output_tokens"] == MILLION
    assert payload["sessions"][0]["session"] == "s1"


def test_a_substring_resolves_to_the_one_project_it_names(home):
    write_transcript(home, "-Users-someone-dev-outdoor-maps", "s1", [record(ROUND_USAGE, skill="pr")])
    result = run(home, "outdoor-maps")
    assert result.returncode == EXIT_OK
    assert f"{ROUND_COST:.2f}" in result.stdout


def test_an_ambiguous_substring_is_refused_with_the_candidates(home):
    write_transcript(home, "-tmp-alpha-api", "s1", [record(ROUND_USAGE, skill="pr")])
    write_transcript(home, "-tmp-beta-api", "s1", [record(ROUND_USAGE, skill="pr")])
    result = run(home, "api")
    assert result.returncode == EXIT_NOT_FOUND
    assert "matches 2 projects" in result.stderr
    assert "-tmp-alpha-api" in result.stdout or "-tmp-alpha-api" in result.stderr


def test_an_exact_name_wins_over_a_substring_of_another(home):
    write_transcript(home, "api", "s1", [record(ROUND_USAGE, skill="exact")])
    write_transcript(home, "-tmp-api-gateway", "s1", [record(ROUND_USAGE, skill="other")])
    result = run(home, "api")
    assert result.returncode == EXIT_OK
    assert "exact" in result.stdout
    assert "other" not in result.stdout


def test_an_unmatched_project_names_where_to_look(home):
    write_transcript(home, "-tmp-demo", "s1", [record(ROUND_USAGE, skill="pr")])
    result = run(home, "nonexistent")
    assert result.returncode == EXIT_NOT_FOUND
    assert "no project matches" in result.stderr


def test_no_argument_lists_the_projects(home):
    write_transcript(home, "-tmp-alpha", "s1", [record(ROUND_USAGE, skill="pr")])
    write_transcript(home, "-tmp-beta", "s1", [record(ROUND_USAGE, skill="pr")])
    result = run(home)
    assert result.returncode == EXIT_OK
    assert "-tmp-alpha" in result.stdout
    assert "-tmp-beta" in result.stdout
    assert "2 projects" in result.stdout


def test_a_missing_transcripts_directory_is_a_refusal_not_a_crash(tmp_path):
    result = run(tmp_path, "anything")
    assert result.returncode == EXIT_NOT_FOUND
    assert "no transcripts directory" in result.stderr


def test_a_project_with_no_priced_records_says_so(home):
    write_transcript(home, "-tmp-demo", "s1", [{"type": "user", "message": {"content": "hi"}}])
    result = run(home, "demo")
    assert result.returncode == EXIT_OK
    assert "no priced records matched" in result.stdout


def test_errors_go_to_stderr_so_a_piped_report_stays_clean(home):
    result = run(home, "nonexistent")
    assert "no project matches" in result.stderr
    assert result.stdout.strip() == "" or "no project matches" not in result.stdout
