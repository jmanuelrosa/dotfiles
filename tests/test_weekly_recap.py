"""`weekly-recap` aggregates Jira, GitHub and GitLab activity into markdown.

The three CLIs are replaced by stubs on PATH, so the cases pin the parts that are
this script's own work: dedupe, label precedence, grouping, and degrading one
platform without taking the other two down. PATH is narrowed to the stub
directory plus /usr/bin and /bin, so a real acli, gh or glab cannot leak in.
"""

import json
import os
import subprocess
import sys

import pytest

from dotkit.testing import AI_SCRIPTS_DIR

RECAP = AI_SCRIPTS_DIR / "weekly-recap"

EXIT_OK = 0
EXIT_USAGE = 1

# Exits 97 on an unmatched call, so a case that forgets a rule fails loudly
# instead of quietly reading an empty result as "no activity".
#
# The shebang points at the running interpreter rather than `python3`, because
# PATH below is narrowed to /usr/bin, where python3 is the Command Line Tools
# shim: it re-resolves via xcrun on every call and cannot write its cache under
# the sandbox, costing ~1.4s per invocation.
STUB = f"#!{sys.executable}\n" + '''import json, os, sys

rules = json.load(open(os.environ["RECAP_STUBS"])).get(os.path.basename(sys.argv[0]), [])
argv = " ".join(sys.argv[1:])
with open(os.environ["RECAP_ARGV"], "a") as log:
    log.write(os.path.basename(sys.argv[0]) + " " + argv + "\\n")
for rule in rules:
    if all(token in argv for token in rule["match"]):
        sys.stdout.write(rule.get("stdout", ""))
        sys.stderr.write(rule.get("stderr", ""))
        sys.exit(rule.get("code", 0))
sys.stderr.write("no stub rule for: " + argv + "\\n")
sys.exit(97)
'''

# The GitLab collector only calls an MR "merged" when its merge date falls inside
# the window, so the fixture timestamp and the window have to be pinned together.
# Left to the default 7 days, every case would start failing a week from now.
WINDOW_START = "2026-07-01"
WHEN = "2026-07-20T10:00:00Z"
# Distinct enough that neither is a substring of the other, so a rule keyed on one
# host cannot also match the other's call.
HOST_A = "example.com"
HOST_B = "example.org"


@pytest.fixture
def recap(tmp_path):
    """Run weekly-recap against stub CLIs. recap(plan, *argv) -> CompletedProcess."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in ("acli", "gh", "glab"):
        stub = bindir / name
        stub.write_text(STUB)
        stub.chmod(0o755)
    plan_file = tmp_path / "stubs.json"
    argv_log = tmp_path / "argv.log"

    def run(plan, *argv):
        if not any(arg.startswith(("--since", "--days")) for arg in argv):
            argv = ("--since", WINDOW_START, *argv)
        plan_file.write_text(json.dumps(plan))
        argv_log.write_text("")
        env = {
            **os.environ,
            "PATH": f"{bindir}:/usr/bin:/bin",
            "RECAP_STUBS": str(plan_file),
            "RECAP_ARGV": str(argv_log),
        }
        result = subprocess.run(
            [sys.executable, str(RECAP), *argv],
            env=env,
            capture_output=True,
            text=True,
        )
        result.calls = argv_log.read_text().splitlines()
        return result

    return run


def jira_item(key, summary="Fix the thing", status="In Review", updated=WHEN):
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status},
            "project": {"key": key.split("-")[0]},
            "updated": updated,
        },
    }


def jira_item_as_acli_returns_it(key, summary="Fix the thing", status="In Review"):
    """The shape the real CLI produces.

    acli's --fields whitelist has no project and no date field, so neither is ever
    present no matter what the query asks for. jira_item above keeps the richer
    shape because the collector still reads it when a version supplies it.
    """
    return {"key": key, "fields": {"summary": summary, "status": {"name": status}}}


def acli_rules(items=(), authenticated=True):
    if not authenticated:
        return [{"match": ["auth", "status"], "code": 1, "stderr": "unauthorized\n"}]
    return [
        {"match": ["auth", "status"], "code": 0},
        {"match": ["workitem", "search"], "stdout": json.dumps(list(items))},
    ]


def pull_request(number, repo="acme/api", state="open", author="me", title="fix: a thing"):
    return {
        "repository": {"nameWithOwner": repo},
        "number": number,
        "title": title,
        "state": state,
        "url": f"https://github.com/{repo}/pull/{number}",
        "updatedAt": WHEN,
        "author": {"login": author},
    }


def gh_rules(created=(), merged=(), reviewed=(), login="me", failing=None):
    rules = [{"match": ["api", "user"], "stdout": json.dumps({"login": login})}]
    for token, payload in (
        ("--created=", created),
        ("--merged-at=", merged),
        ("--reviewed-by=", reviewed),
    ):
        if token == failing:
            rules.append({"match": ["search", "prs", token], "code": 1, "stderr": "boom\n"})
            continue
        rules.append({"match": ["search", "prs", token], "stdout": json.dumps(list(payload))})
    return rules


def merge_request(iid, project="team/app", state="merged", author="me", title="feat: a thing"):
    return {
        "iid": iid,
        "title": title,
        "state": state,
        "merged_at": WHEN,
        "updated_at": WHEN,
        "web_url": f"https://gitlab.example/{project}/-/merge_requests/{iid}",
        "references": {"full": f"{project}!{iid}"},
        "author": {"username": author},
    }


def glab_rules(accounts=None, requests=None):
    """accounts maps host to username; requests maps (host, bucket) to a payload."""
    accounts = {HOST_A: "me"} if accounts is None else accounts
    status = "\n".join(
        f"{host}\n  Logged in to {host} as {user} (keyring)" for host, user in accounts.items()
    )
    rules = [{"match": ["auth", "status"], "stderr": f"{status}\n"}]
    for (host, bucket), payload in (requests or {}).items():
        token = "created_by_me" if bucket == "opened" else "reviewer_username"
        rules.append(
            {"match": ["--hostname", host, token], "stdout": json.dumps(list(payload))}
        )
    # Any host and bucket the case did not name has simply nothing in the window.
    rules.append({"match": ["api"], "stdout": "[]"})
    return rules


def plan(acli=None, gh=None, glab=None):
    return {
        "acli": acli_rules() if acli is None else acli,
        "gh": gh_rules() if gh is None else gh,
        "glab": glab_rules() if glab is None else glab,
    }


def entries(stdout, ref):
    return [line for line in stdout.splitlines() if line.startswith(f"- {ref} ")]


def headers(stdout):
    return [line for line in stdout.splitlines() if line.startswith("## ")]


def test_no_activity_anywhere_says_so_once(recap):
    """Given every platform returns nothing, When the recap runs, Then it says so."""
    result = recap(plan())
    assert result.returncode == EXIT_OK
    assert "No activity recorded between" in result.stdout
    assert headers(result.stdout) == []


def test_a_pull_request_in_every_bucket_collapses_to_one_merged_line(recap):
    """Given one PR returned by all three GitHub queries, When the recap runs,
    Then it appears once, labelled merged.

    Opening and merging the same PR inside the window puts it in every bucket, and
    merged is the strongest label.
    """
    same = pull_request(7, state="merged")
    result = recap(plan(gh=gh_rules(created=[same], merged=[same], reviewed=[same])))
    assert entries(result.stdout, "#7") == ["- #7 (merged) fix: a thing"]


def test_an_open_pull_request_i_authored_is_labelled_opened(recap):
    """Given an open PR I authored, When the recap runs, Then it is labelled opened."""
    result = recap(plan(gh=gh_rules(created=[pull_request(8)])))
    assert entries(result.stdout, "#8") == ["- #8 (opened) fix: a thing"]


def test_a_review_on_someone_elses_pull_request_names_the_author(recap):
    """Given a PR by someone else that I reviewed, When the recap runs,
    Then it is labelled reviewed and names the author."""
    result = recap(plan(gh=gh_rules(reviewed=[pull_request(9, author="alice")])))
    assert entries(result.stdout, "#9") == ["- #9 (reviewed, author: alice) fix: a thing"]


def test_a_pull_request_i_authored_and_reviewed_is_not_a_review(recap):
    """Given the reviewed query returns my own PR, When the recap runs,
    Then it is not counted as a review.

    Reviewing your own PR is not a review contribution, so the label falls back to
    the PR's state.
    """
    result = recap(plan(gh=gh_rules(reviewed=[pull_request(10, author="me")])))
    assert entries(result.stdout, "#10") == ["- #10 (opened) fix: a thing"]


def test_a_merge_request_visible_on_two_hosts_collapses_to_one_line(recap):
    """Given the same MR returned by two authenticated hosts, When the recap runs,
    Then it appears once.

    A personal and a work account can both see one MR, and it is still one MR.
    """
    same = merge_request(89)
    result = recap(
        plan(
            glab=glab_rules(
                accounts={HOST_A: "me", HOST_B: "me"},
                requests={(HOST_A, "opened"): [same], (HOST_B, "opened"): [same]},
            )
        )
    )
    assert entries(result.stdout, "!89") == ["- !89 (merged) feat: a thing"]


def test_a_merge_request_group_drops_the_reference_suffix(recap):
    """Given an MR, When the recap runs, Then its group is the project path alone."""
    result = recap(plan(glab=glab_rules(requests={(HOST_A, "opened"): [merge_request(90)]})))
    assert "## team/app (GitLab)" in headers(result.stdout)


def test_a_jira_item_carries_its_status_and_project(recap):
    """Given a Jira work item, When the recap runs, Then its status is the label and
    its project key is the group."""
    result = recap(plan(acli=acli_rules([jira_item("SER-1234")])))
    assert "## SER (Jira)" in headers(result.stdout)
    assert entries(result.stdout, "SER-1234") == ["- SER-1234 (In Review) Fix the thing"]


def test_a_jira_item_groups_by_key_prefix_when_the_payload_omits_the_project(recap):
    """Given the payload shape the real CLI returns, When the recap runs,
    Then the group is the issue key prefix.

    This is the only shape that ever arrives from acli, so it is the case that
    decides whether the Jira section is right.
    """
    result = recap(plan(acli=acli_rules([jira_item_as_acli_returns_it("SER-1234")])))
    assert "## SER (Jira)" in headers(result.stdout)
    assert entries(result.stdout, "SER-1234") == ["- SER-1234 (In Review) Fix the thing"]


def test_jira_items_keep_the_order_the_query_returned(recap):
    """Given items with no timestamp to sort on, When the recap runs, Then they
    appear in the order acli returned them.

    The JQL orders by updated descending and every item then ties on an empty
    timestamp, so it is the sort's stability that preserves newest-first.
    """
    keys = ["SER-3", "SER-1", "SER-2"]
    result = recap(plan(acli=acli_rules([jira_item_as_acli_returns_it(k) for k in keys])))
    listed = [line.split()[1] for line in result.stdout.splitlines() if line.startswith("- SER-")]
    assert listed == keys


def test_the_jira_query_never_asks_for_a_field_acli_rejects(recap):
    """Given any run, When the Jira query is issued, Then it names no field outside
    acli's whitelist.

    Naming one is not a degraded field, it is a rejected command: the query fails
    whole, Jira falls back to a note, and the section vanishes with the rest of
    the recap still looking healthy.
    """
    result = recap(plan(acli=acli_rules([jira_item_as_acli_returns_it("SER-1")])))
    search = next(call for call in result.calls if "workitem search" in call)
    requested = set()
    if "--fields" in search:
        requested = set(search.split("--fields", 1)[1].split()[0].split(","))
    rejected = {"project", "updated", "created", "resolution", "parent", "duedate"}
    assert not requested & rejected


def test_groups_sort_alphabetically(recap):
    """Given two repos, When the recap runs, Then their headers are in name order."""
    result = recap(
        plan(
            gh=gh_rules(
                created=[pull_request(1, repo="zeta/app"), pull_request(2, repo="alpha/api")]
            )
        )
    )
    assert headers(result.stdout) == ["## alpha/api (GitHub)", "## zeta/app (GitHub)"]


def test_an_unauthenticated_jira_notes_it_and_leaves_the_rest_intact(recap):
    """Given Jira is not authenticated, When the recap runs, Then it notes that and
    still reports GitHub.

    No single platform may take the recap down.
    """
    result = recap(
        plan(acli=acli_rules(authenticated=False), gh=gh_rules(created=[pull_request(3)]))
    )
    assert result.returncode == EXIT_OK
    assert "Jira: not authenticated" in result.stdout
    assert "## acme/api (GitHub)" in headers(result.stdout)


def test_a_failing_github_query_notes_it_and_keeps_the_others(recap):
    """Given one GitHub query fails, When the recap runs, Then the other two still report."""
    result = recap(
        plan(gh=gh_rules(created=[pull_request(4)], failing="--merged-at="))
    )
    assert result.returncode == EXIT_OK
    assert "GitHub: the merged query failed" in result.stdout
    assert entries(result.stdout, "#4") == ["- #4 (opened) fix: a thing"]


def test_an_unauthenticated_gitlab_is_a_note_not_a_failure(recap):
    """Given no authenticated GitLab host, When the recap runs, Then it notes that and exits 0."""
    result = recap(plan(glab=glab_rules(accounts={})))
    assert result.returncode == EXIT_OK
    assert "GitLab: not authenticated" in result.stdout


def test_a_dash_in_a_title_becomes_a_hyphen(recap):
    """Given a title containing an em dash, When the recap runs, Then it prints a hyphen.

    Titles come from other people's systems, and the recap is pasted into a doc
    that bans these.
    """
    dashed = f"fix: cookie banner {chr(0x2014)} z-index"
    result = recap(plan(gh=gh_rules(created=[pull_request(5, title=dashed)])))
    assert entries(result.stdout, "#5") == ["- #5 (opened) fix: cookie banner - z-index"]
    assert chr(0x2014) not in result.stdout
    assert chr(0x2013) not in result.stdout


def test_the_window_appears_in_the_title(recap):
    """Given an explicit start date, When the recap runs, Then the title names the window."""
    result = recap(plan(), "--since", "2026-01-05")
    assert result.stdout.startswith("# Weekly recap, 2026-01-05 to ")


def test_a_zero_day_window_is_a_usage_error(recap):
    """Given --days 0, When the recap runs, Then it refuses."""
    assert recap(plan(), "--days", "0").returncode == EXIT_USAGE


def test_a_malformed_since_is_a_usage_error(recap):
    """Given a --since that is not a date, When the recap runs, Then it refuses."""
    assert recap(plan(), "--since", "last-tuesday").returncode == EXIT_USAGE
