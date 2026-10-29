"""The /coderabbit skill's two scripts: thread context gathering and the reply/resolve executor.

`gh` is replaced by a stub on a narrowed PATH, so the cases pin the parts that are
these scripts' own work: the GitHub-only guard, the idempotency filter, noise
stripping, pagination, grouping, and the counters. PATH keeps only the stub
directory plus /usr/bin and /bin, so a real gh cannot leak in while git still
resolves. Structural assertions read context.py's --json model rather than its
text rendering, so the report can be reformatted without breaking the suite.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Beside the subject it exercises, so it is located relatively: move the skill and
# these travel with it. dotkit.testing is for facts about the repo, not this.
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
CONTEXT = SCRIPTS / "context.py"
APPLY = SCRIPTS / "apply.py"

# Mirrors the tables at the top of each script. Tests assert on these rather than
# on message text, so refusals can be reworded without breaking the suite.
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NO_REMOTE = 2
EXIT_NOT_GITHUB = 3
EXIT_NO_PR = 4
EXIT_GH_FAILED = 5

APPLY_INVALID_PLAN = 2
APPLY_PARTIAL = 3

# The spelling GraphQL returns for a Bot actor, which is what these scripts read.
# REST appends "[bot]"; context.py accepts both, and the case below pins that.
BOT = "coderabbitai"
MARKER = "<!-- cr-skill -->"
FENCE = "```"

REPO_SLUG = "acme/api"
PR_NUMBER = 42

# Exits 97 on an unmatched call, so a case that forgets a rule fails loudly
# instead of quietly reading an empty result as "no threads". Rules may also match
# on the request body, which is the only way to tell one GraphQL call from another:
# every one of them is argv-identical `gh api graphql --input -`.
#
# The shebang points at the running interpreter rather than `python3`, because
# PATH below is narrowed to /usr/bin, where python3 is the Command Line Tools
# shim: it re-resolves via xcrun on every call and cannot write its cache under
# the sandbox, costing ~1.4s per invocation.
STUB = f"#!{sys.executable}\n" + '''import json, os, sys

rules = json.load(open(os.environ["CR_STUBS"])).get(os.path.basename(sys.argv[0]), [])
argv = " ".join(sys.argv[1:])
payload = "" if sys.stdin.isatty() else sys.stdin.read()
for rule in rules:
    if not all(token in argv for token in rule["match"]):
        continue
    if not all(token in payload for token in rule.get("stdin_match", [])):
        continue
    sys.stdout.write(rule.get("stdout", ""))
    sys.stderr.write(rule.get("stderr", ""))
    sys.exit(rule.get("code", 0))
sys.stderr.write("no stub rule for: " + argv + " body=" + payload + "\\n")
sys.exit(97)
'''


@pytest.fixture
def stub_gh(tmp_path):
    """A stubbed `gh` on a narrowed PATH. Returns (env_builder, plan_file)."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    stub = bindir / "gh"
    stub.write_text(STUB)
    stub.chmod(0o755)
    plan_file = tmp_path / "stubs.json"

    def env(plan):
        plan_file.write_text(json.dumps(plan))
        return {
            **os.environ,
            "PATH": f"{bindir}:/usr/bin:/bin",
            "CR_STUBS": str(plan_file),
        }

    return env


@pytest.fixture
def project(tmp_path):
    """A throwaway git repo whose origin URL the case chooses."""
    counter = {"n": 0}

    def make(url="git@github.com:acme/api.git"):
        counter["n"] += 1
        proj = tmp_path / f"proj{counter['n']}"
        proj.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
        if url:
            subprocess.run(["git", "remote", "add", "origin", url], cwd=proj, check=True)
        return proj

    return make


@pytest.fixture
def context(stub_gh, project):
    """Run context.py --json against stub gh. context(plan, *argv, url=...) -> model dict."""

    def run(plan, *argv, url="git@github.com:acme/api.git", cwd=None, as_json=True):
        proj = cwd or project(url)
        args = [sys.executable, str(CONTEXT), *argv]
        if as_json:
            args.append("--json")
        proc = subprocess.run(
            args, cwd=str(proj), env=stub_gh(plan), capture_output=True, text=True
        )
        return proc

    return run


def comment(login=BOT, body="The session may be null here.", cid=1001,
            path="src/a.ts", line=42, diff=None):
    return {
        "databaseId": cid,
        "author": {"login": login},
        "body": body,
        "path": path,
        "line": line,
        "originalLine": line,
        "diffHunk": diff if diff is not None else "@@ -1,2 +1,3 @@\n+  decode(session)",
    }


def thread(tid="PRRT_a", resolved=False, outdated=False, path="src/a.ts", line=42, comments=None):
    return {
        "id": tid,
        "isResolved": resolved,
        "isOutdated": outdated,
        "path": path,
        "line": line,
        "originalLine": line,
        "comments": {"nodes": comments if comments is not None else [comment(path=path, line=line)]},
    }


def page(nodes, has_next=False, cursor=None):
    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
                            "nodes": nodes,
                        }
                    }
                }
            }
        }
    )


def gh_rules(pages=None, repo=REPO_SLUG, pr=PR_NUMBER, title="add token guard",
             pr_body="", reviews=None, pr_comments=None, no_pr=False):
    """pages maps an endCursor token to a response, so pagination is deterministic."""
    rules = [
        {"match": ["repo", "view", "nameWithOwner"], "stdout": json.dumps({"nameWithOwner": repo})},
    ]
    if no_pr:
        rules.append({"match": ["pr", "view", "number"], "code": 1, "stderr": "no pull requests found\n"})
    else:
        rules.append({"match": ["pr", "view", "number"], "stdout": json.dumps({"number": pr})})
    rules.append(
        {
            "match": ["pr", "view", "title,body,reviews,comments"],
            "stdout": json.dumps(
                {"title": title, "body": pr_body, "reviews": reviews or [],
                 "comments": pr_comments or []}
            ),
        }
    )
    for cursor_token, response in (pages or {}).items():
        rules.append(
            {
                "match": ["api", "graphql"],
                "stdin_match": [cursor_token],
                "stdout": response,
            }
        )
    return rules


def one_page(nodes):
    return gh_rules(pages={'"endCursor": null': page(nodes)})


def model_of(proc):
    assert proc.returncode == EXIT_OK, proc.stderr
    return json.loads(proc.stdout)


def flat(model):
    return [t for items in model["threads"].values() for t in items]


def test_a_non_github_remote_is_refused(context):
    """Given an origin on GitLab, When context runs, Then it refuses as not GitHub.

    CodeRabbit is a GitHub bot, so there is nothing to fetch anywhere else.
    """
    proc = context({}, url="git@gitlab.com:team/app.git")
    assert proc.returncode == EXIT_NOT_GITHUB


def test_a_missing_origin_is_refused(context):
    """Given a repo with no origin, When context runs, Then it refuses."""
    proc = context({}, url=None)
    assert proc.returncode == EXIT_NO_REMOTE


def test_no_pr_for_the_branch_is_refused(context):
    """Given no PR for the current branch and no argument, When context runs, Then it refuses."""
    proc = context({"gh": gh_rules(no_pr=True)})
    assert proc.returncode == EXIT_NO_PR


def test_an_explicit_pr_number_overrides_branch_detection(context):
    """Given a PR number argument, When context runs, Then it uses it and never asks the branch.

    The branch-detection rule is absent from the plan, so the stub would exit 97
    if the argument were ignored.
    """
    rules = [r for r in one_page([thread()]) if "number" not in r["match"]]
    proc = context({"gh": rules}, "77")
    assert model_of(proc)["pr"]["number"] == 77


def test_a_resolved_thread_is_skipped(context):
    """Given a resolved CodeRabbit thread, When context runs, Then it is skipped as resolved.

    Step 8 resolves everything it acts on, so a prior run's work drops out here.
    """
    model = model_of(context({"gh": one_page([thread(resolved=True)])}))
    assert flat(model) == []
    assert model["skipped"] == {"resolved": 1}


def test_an_outdated_thread_is_skipped(context):
    """Given an outdated CodeRabbit thread, When context runs, Then it is skipped as outdated."""
    model = model_of(context({"gh": one_page([thread(outdated=True)])}))
    assert flat(model) == []
    assert model["skipped"] == {"outdated": 1}


def test_a_thread_from_another_author_is_skipped(context):
    """Given a thread opened by a human, When context runs, Then it is skipped as not CodeRabbit.

    A thread counts as CodeRabbit's only when its first comment is the bot's.
    """
    model = model_of(context({"gh": one_page([thread(comments=[comment(login="alice")])])}))
    assert flat(model) == []
    assert model["skipped"] == {"not-coderabbit": 1}


@pytest.mark.parametrize("login", ["coderabbitai", "coderabbitai[bot]"])
def test_either_spelling_of_the_bot_login_is_recognised(context, login):
    """Given a bot login with or without the "[bot]" suffix, When context runs, Then the thread
    is still treated as CodeRabbit's.

    GraphQL reports a Bot actor's login bare, REST appends "[bot]", and these scripts read
    GraphQL. Pinning the REST spelling alone made every thread read as not-coderabbit, and this
    suite passed anyway because its fixtures used that same spelling in a GraphQL-shaped response.
    """
    model = model_of(context({"gh": one_page([thread(comments=[comment(login=login)])])}))
    assert len(flat(model)) == 1
    assert "not-coderabbit" not in model["skipped"]


def test_a_thread_a_human_already_answered_is_skipped(context):
    """Given a CodeRabbit thread with a human reply, When context runs, Then it is skipped."""
    nodes = [thread(comments=[comment(), comment(login="alice", body="disagree", cid=1002)])]
    model = model_of(context({"gh": one_page(nodes)}))
    assert flat(model) == []
    assert model["skipped"] == {"answered": 1}


def test_a_thread_carrying_the_skill_marker_is_skipped(context):
    """Given a thread already answered by this skill, When context runs, Then it is skipped.

    The marker is the backup signal for a run whose resolve call failed midway.
    """
    nodes = [thread(comments=[comment(), comment(login=BOT, body=f"prior reply\n\n{MARKER}", cid=1002)])]
    model = model_of(context({"gh": one_page(nodes)}))
    assert flat(model) == []
    assert model["skipped"] == {"answered": 1}


def test_a_live_thread_survives_with_its_location_and_diff(context):
    """Given one open CodeRabbit thread, When context runs, Then its path, line, ids and
    diff hunk all survive intact.

    The triage step needs the node id to resolve the thread and the root comment id
    to reply into it, so both have to round-trip verbatim.
    """
    model = model_of(context({"gh": one_page([thread(tid="PRRT_live")])}))
    [t] = flat(model)
    assert t["thread"] == "PRRT_live"
    assert t["reply_to"] == 1001
    assert t["path"] == "src/a.ts"
    assert t["line"] == 42
    assert "decode(session)" in t["diff_hunk"]
    assert "may be null" in t["body"]
    assert model["skipped"] == {}


def test_pagination_returns_the_union_of_both_pages(context):
    """Given threads split across two pages, When context runs, Then both appear.

    The first page's endCursor is the only thing distinguishing the second request,
    so a broken cursor hand-off would exit 97 on the stub instead of silently
    returning half the threads.
    """
    plan = gh_rules(
        pages={
            '"endCursor": null': page([thread(tid="PRRT_p1", path="src/a.ts")], has_next=True, cursor="CUR1"),
            '"endCursor": "CUR1"': page([thread(tid="PRRT_p2", path="src/b.ts")]),
        }
    )
    model = model_of(context({"gh": plan}))
    assert sorted(t["thread"] for t in flat(model)) == ["PRRT_p1", "PRRT_p2"]


def test_collapsed_and_agent_prompt_blocks_are_stripped(context):
    """Given a body carrying details blocks, an AI-prompt block and a suggestion fence,
    When context runs, Then only the human-readable prose survives.

    The prompt block is CodeRabbit's instruction aimed at an agent, so keeping it out
    of context also keeps it out of any reply.
    """
    body = "\n".join([
        "_" + chr(0x26A0) + " Potential issue_",
        "",
        "The session may be null here.",
        "",
        "<details>",
        "<summary>Nitpick comments</summary>",
        "hidden nit",
        "<details><summary>inner</summary>nested junk</details>",
        "</details>",
        "",
        chr(0x1F916) + " Prompt for AI Agents",
        FENCE,
        "You are an expert reviewer, apply this.",
        FENCE,
        "",
        FENCE + "suggestion",
        "if (!session) return;",
        FENCE,
        "",
        "Tail prose.",
    ])
    model = model_of(context({"gh": one_page([thread(comments=[comment(body=body)])])}))
    [t] = flat(model)
    assert "hidden nit" not in t["body"]
    assert "nested junk" not in t["body"]
    assert "expert reviewer" not in t["body"]
    assert "Prompt for AI Agents" not in t["body"]
    assert "return;" not in t["body"]
    assert "The session may be null here." in t["body"]
    assert "Tail prose." in t["body"]
    assert t["severity"] == "potential"


def test_a_nitpick_is_labelled_as_one(context):
    """Given a nitpick-flagged comment, When context runs, Then its severity says so.

    The verdict table's severity column drives how hard the triage step pushes back.
    """
    nit = "_" + chr(0x1F9F9) + " Nitpick (assertive)_\n\nRename this variable."
    model = model_of(context({"gh": one_page([thread(comments=[comment(body=nit)])])}))
    assert flat(model)[0]["severity"] == "nitpick"


def test_threads_group_by_path_in_sorted_order(context):
    """Given threads on three files, When context runs, Then they group by path in name
    order with each file's threads in line order."""
    nodes = [
        thread(tid="PRRT_z", path="src/z.ts", line=10),
        thread(tid="PRRT_a2", path="src/a.ts", line=99),
        thread(tid="PRRT_a1", path="src/a.ts", line=7),
        thread(tid="PRRT_m", path="src/m.ts", line=1),
    ]
    model = model_of(context({"gh": one_page(nodes)}))
    assert list(model["threads"]) == ["src/a.ts", "src/m.ts", "src/z.ts"]
    assert [t["thread"] for t in model["threads"]["src/a.ts"]] == ["PRRT_a1", "PRRT_a2"]


def test_zero_open_threads_is_the_steady_state_not_an_error(context):
    """Given every thread already resolved, When context runs, Then it exits 0 and says so.

    Re-running after a clean pass is normal, not a failure.
    """
    proc = context({"gh": one_page([thread(resolved=True)])}, as_json=False)
    assert proc.returncode == EXIT_OK
    assert f"No open CodeRabbit threads on PR #{PR_NUMBER}." in proc.stdout


def test_the_walkthrough_comes_from_the_bots_latest_review(context):
    """Given several reviews, When context runs, Then the walkthrough is the bot's most
    recent one, with its collapsed blocks stripped."""
    reviews = [
        {"author": {"login": "alice"}, "body": "human review"},
        {"author": {"login": BOT}, "body": "old walkthrough"},
        {"author": {"login": BOT}, "body": "new walkthrough\n<details>junk</details>"},
    ]
    plan = gh_rules(pages={'"endCursor": null': page([thread()])}, reviews=reviews)
    model = model_of(context({"gh": plan}))
    assert model["pr"]["walkthrough"] == "new walkthrough"


def finding(fid="a1b2", level="Major", title="Make delete refuse an in-use endpoint.",
            location="src/domain/mutation.ts:776-778"):
    """One finding block, shaped like CodeRabbit's review body markup."""
    return f"""<details>
<summary><strong><picture><img src="x.svg"></picture> {level}</strong> \u00b7 {title} \u00b7 <code>mutation.ts:776-778</code></summary><blockquote>
<dl>
<dd>

`{location}`
**{level}**

The delete path never checks for forwarding domains.

<details>
<summary>Proposed fix</summary>

{FENCE}diff
+ guard()
{FENCE}
</details>

<details>
<summary>Prompt for AI Agents</summary>

{FENCE}
Verify each finding against current code.
{FENCE}
</details>

<!-- cr-comment:v1:{fid} -->

</dd>
</dl>
</blockquote></details>"""


def review_body(*findings, section="Outside diff range"):
    quoted = "\n".join(f"> {ln}" for ln in "\n\n".join(findings).splitlines())
    return (
        "**Actionable comments posted: 1**\n\n"
        "> [!CAUTION]\n"
        f"> **{section} comments ({len(findings)})**\n>\n{quoted}\n\n---\n"
    )


def outside_rules(reviews, pr_comments=None, nodes=None):
    return gh_rules(
        pages={'"endCursor": null': page(nodes if nodes is not None else [])},
        reviews=[{"author": {"login": BOT}, "body": body} for body in reviews],
        pr_comments=pr_comments,
    )


def test_an_outside_diff_finding_surfaces_from_the_review_body(context):
    """Given a review whose only finding is outside the diff, When context runs, Then it
    surfaces with its full path, lines, level and title, minus the fix and prompt blocks.

    GitHub gives these no thread, so the threads query alone never sees them.
    """
    model = model_of(context({"gh": outside_rules([review_body(finding())])}))
    [found] = model["outside"]
    assert found["id"] == "a1b2"
    assert (found["path"], found["lines"]) == ("src/domain/mutation.ts", "776-778")
    assert (found["level"], found["title"]) == ("major", "Make delete refuse an in-use endpoint.")
    assert "never checks for forwarding domains" in found["body"]
    for leaked in ("Prompt for AI Agents", "guard()", "cr-comment", "<dd>"):
        assert leaked not in found["body"]


def test_an_answered_outside_finding_is_skipped(context):
    """Given a PR comment carrying the finding's skill marker, When context runs, Then the
    finding is skipped and counted, so a re-run never answers it twice."""
    answered = [{"author": {"login": "jmr"}, "body": "x\n<!-- cr-skill:outside:a1b2 -->"}]
    model = model_of(context({"gh": outside_rules([review_body(finding())], answered)}))
    assert model["outside"] == []
    assert model["skipped"]["outside-answered"] == 1


def test_an_outside_finding_repeated_across_reviews_appears_once(context):
    """Given the same finding id in two reviews, When context runs, Then it is listed once."""
    body = review_body(finding())
    model = model_of(context({"gh": outside_rules([body, body])}))
    assert len(model["outside"]) == 1


def test_a_finding_under_another_section_is_not_outside_diff(context):
    """Given a finding under a nitpick heading, When context runs, Then it is not lifted."""
    body = review_body(finding(), section="Nitpick")
    assert model_of(context({"gh": outside_rules([body])}))["outside"] == []


def test_outside_findings_alone_are_still_work(context):
    """Given no open threads but one outside finding, When context runs as text, Then it
    lists the finding and does not report nothing to triage."""
    proc = context({"gh": outside_rules([review_body(finding())])}, as_json=False)
    assert proc.returncode == EXIT_OK, proc.stderr
    assert "[O1] src/domain/mutation.ts:776-778 severity=outside-diff level=major id=a1b2" in proc.stdout
    assert "Nothing to triage" not in proc.stdout


def test_nothing_to_triage_needs_both_sources_empty(context):
    """Given no threads and no outside findings, When context runs, Then it says so."""
    proc = context({"gh": outside_rules([])}, as_json=False)
    assert f"Nothing to triage on PR #{PR_NUMBER}." in proc.stdout


def test_a_failing_threads_query_is_reported(context):
    """Given the GraphQL query fails, When context runs, Then it exits on the gh failure code."""
    plan = gh_rules()
    plan.append({"match": ["api", "graphql"], "code": 1, "stderr": "gone\n"})
    proc = context({"gh": plan})
    assert proc.returncode == EXIT_GH_FAILED


@pytest.fixture
def apply_plan(stub_gh, tmp_path):
    """Run apply.py against stub gh. apply_plan(gh_plan, plan_dict) -> CompletedProcess."""
    plan_path = tmp_path / "plan.json"

    def run(gh_plan, plan):
        plan_path.write_text(json.dumps(plan))
        return subprocess.run(
            [sys.executable, str(APPLY), str(plan_path)],
            env=stub_gh(gh_plan),
            capture_output=True,
            text=True,
        )

    return run


def apply_rules(reply_ok=True, resolve_ok=True, pr_comment_ok=True):
    return [
        {
            "match": [f"issues/{PR_NUMBER}/comments"],
            "stdout": json.dumps({"html_url": "https://github.com/acme/api/pull/42#ic1"}),
            "code": 0 if pr_comment_ok else 1,
            "stderr": "" if pr_comment_ok else "comment rejected\n",
        },
        {
            "match": [f"pulls/{PR_NUMBER}/comments"],
            "stdout": json.dumps({"html_url": "https://github.com/acme/api/pull/42#r1"}),
            "code": 0 if reply_ok else 1,
            "stderr": "" if reply_ok else "reply rejected\n",
        },
        {
            "match": ["api", "graphql"],
            "stdin_match": ["resolveReviewThread"],
            "stdout": json.dumps({"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}}),
            "code": 0 if resolve_ok else 1,
            "stderr": "" if resolve_ok else "resolve rejected\n",
        },
    ]


def base_plan(threads, skipped=None, outside=None):
    return {"repo": REPO_SLUG, "pr": PR_NUMBER, "threads": threads,
            "outside": outside or [], "skipped": skipped or {}}


REPLY = {"thread": "PRRT_b", "verdict": "reply", "reply_to": 1001, "body": "@coderabbitai intentional."}
FIX = {"thread": "PRRT_a", "verdict": "fix", "files": ["src/a.ts"]}
OUTSIDE_FIX = {"id": "a1b2", "verdict": "fix", "title": "Guard delete.", "location": "src/d.ts:7-9"}
OUTSIDE_REPLY = {"id": "c3d4", "verdict": "reply", "title": "Cache it.", "body": "Runs once per boot."}


def test_outside_findings_are_answered_in_one_marked_pr_comment(apply_plan):
    """Given a fixed and a declined outside finding, When apply runs, Then one PR comment
    carries both answers and a marker per finding, and the summary counts them.

    The markers are the only record a re-run can read, since there is no thread to resolve.
    """
    rules = apply_rules()
    rules[0]["stdin_match"] = [
        "@coderabbitai", "Fixed, lands with the next push.", "Runs once per boot.",
        "cr-skill:outside:a1b2", "cr-skill:outside:c3d4",
    ]
    proc = apply_plan({"gh": rules}, base_plan([], outside=[OUTSIDE_FIX, OUTSIDE_REPLY]))
    assert proc.returncode == EXIT_OK, proc.stderr
    assert "summary: 1 fixed, 1 replied, 0 resolved, 0 asked" in proc.stdout


def test_a_failed_outside_comment_counts_nothing(apply_plan):
    """Given the PR comment call fails, When apply runs, Then no finding is counted as handled."""
    proc = apply_plan({"gh": apply_rules(pr_comment_ok=False)}, base_plan([], outside=[OUTSIDE_FIX]))
    assert proc.returncode == APPLY_PARTIAL
    assert "summary: 0 fixed, 0 replied" in proc.stdout


def test_a_declined_outside_finding_without_a_reason_is_refused(apply_plan):
    """Given an outside reply verdict with no body, When apply runs, Then it refuses."""
    entry = {**OUTSIDE_REPLY, "body": ""}
    assert apply_plan({"gh": apply_rules()}, base_plan([], outside=[entry])).returncode == APPLY_INVALID_PLAN


def test_a_replies_only_run_requests_a_review(apply_plan):
    """Given replies and no fixes, When apply runs, Then it asks CodeRabbit to review.

    Nothing is waiting on a push, so no push will trigger CodeRabbit on its own.
    """
    rules = apply_rules()
    rules[0]["stdin_match"] = ["@coderabbitai review"]
    proc = apply_plan({"gh": rules}, base_plan([REPLY]))
    assert proc.returncode == EXIT_OK, proc.stderr
    assert "re-review: requested" in proc.stdout


def test_a_run_with_a_fix_leaves_the_review_to_the_push(apply_plan):
    """Given a fix alongside a reply, When apply runs, Then no review is requested."""
    rules = [r for r in apply_rules() if "issues/" not in r["match"][0]]
    proc = apply_plan({"gh": rules}, base_plan([FIX, REPLY]))
    assert proc.returncode == EXIT_OK, proc.stderr
    assert "re-review: not needed, the push of these fixes triggers it" in proc.stdout


def test_the_summary_counts_every_bucket(apply_plan):
    """Given one fix, one reply and one ask plus skips, When apply runs, Then the summary
    line reports each count.

    Step 9's summary is read off this line rather than tallied by hand.
    """
    plan = base_plan(
        [
            {"thread": "PRRT_a", "verdict": "fix", "files": ["src/a.ts"]},
            {"thread": "PRRT_b", "verdict": "reply", "reply_to": 1001, "body": "@coderabbitai intentional."},
            {"thread": "PRRT_c", "verdict": "ask"},
        ],
        skipped={"resolved": 4, "outdated": 1},
    )
    proc = apply_plan({"gh": apply_rules()}, plan)
    assert proc.returncode == EXIT_OK, proc.stderr
    assert "summary: 1 fixed, 1 replied, 2 resolved, 1 asked, 5 skipped" in proc.stdout
    assert "files touched: src/a.ts" in proc.stdout


def test_an_ask_verdict_resolves_nothing(apply_plan):
    """Given only an ask verdict, When apply runs, Then no thread is resolved.

    An unanswered question is not handled, and resolving it would hide it.
    """
    proc = apply_plan({"gh": apply_rules()}, base_plan([{"verdict": "ask", "thread": "PRRT_c"}]))
    assert proc.returncode == EXIT_OK, proc.stderr
    assert "0 resolved" in proc.stdout


def test_a_failed_reply_leaves_its_thread_open(apply_plan):
    """Given the reply call fails, When apply runs, Then nothing is resolved and it exits partial.

    Resolving a thread whose reply never posted would silence it with no explanation.
    """
    plan = base_plan([{"thread": "PRRT_b", "verdict": "reply", "reply_to": 1001, "body": "@coderabbitai no."}])
    proc = apply_plan({"gh": apply_rules(reply_ok=False)}, plan)
    assert proc.returncode == APPLY_PARTIAL
    assert "0 replied, 0 resolved" in proc.stdout


def test_a_failed_resolve_is_partial_not_fatal(apply_plan):
    """Given the resolve call fails, When apply runs, Then the reply still counts and it
    exits partial.

    The marker plus the isResolved check keep the next run idempotent anyway.
    """
    plan = base_plan([{"thread": "PRRT_b", "verdict": "reply", "reply_to": 1001, "body": "@coderabbitai no."}])
    proc = apply_plan({"gh": apply_rules(resolve_ok=False)}, plan)
    assert proc.returncode == APPLY_PARTIAL
    assert "1 replied, 0 resolved" in proc.stdout


def test_a_reply_with_a_long_dash_is_refused_before_posting(apply_plan):
    """Given a reply body containing an em dash, When apply runs, Then it refuses.

    Replies are public and the house style bans these, so the gate is here rather
    than in the drafting prose.
    """
    body = "@coderabbitai this is intentional " + chr(0x2014) + " leaving it."
    plan = base_plan([{"thread": "PRRT_b", "verdict": "reply", "reply_to": 1001, "body": body}])
    proc = apply_plan({"gh": apply_rules()}, plan)
    assert proc.returncode == APPLY_INVALID_PLAN


def test_a_reply_echoing_the_agent_prompt_is_refused(apply_plan):
    """Given a reply that pastes CodeRabbit's prompt block back, When apply runs, Then it refuses."""
    plan = base_plan(
        [{"thread": "PRRT_b", "verdict": "reply", "reply_to": 1001,
          "body": "@coderabbitai Prompt for AI Agents: fix this."}]
    )
    assert apply_plan({"gh": apply_rules()}, plan).returncode == APPLY_INVALID_PLAN


def test_a_reply_without_a_root_comment_id_is_refused(apply_plan):
    """Given a reply verdict with no reply_to, When apply runs, Then it refuses.

    Without the thread root id the reply detaches into a new top-level thread.
    """
    plan = base_plan([{"thread": "PRRT_b", "verdict": "reply", "body": "@coderabbitai no."}])
    assert apply_plan({"gh": apply_rules()}, plan).returncode == APPLY_INVALID_PLAN


def test_an_unknown_verdict_is_refused(apply_plan):
    """Given a verdict outside the three buckets, When apply runs, Then it refuses."""
    plan = base_plan([{"thread": "PRRT_b", "verdict": "maybe"}])
    assert apply_plan({"gh": apply_rules()}, plan).returncode == APPLY_INVALID_PLAN


def test_a_missing_plan_file_is_a_usage_error(stub_gh):
    """Given a plan path that does not exist, When apply runs, Then it is a usage error."""
    proc = subprocess.run(
        [sys.executable, str(APPLY), "/nonexistent/plan.json"],
        env=stub_gh({}),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == EXIT_USAGE
