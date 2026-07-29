#!/usr/bin/env python3
"""apply.py - reply-and-resolve executor for the /coderabbit skill.

Reads an approved plan and performs the post-reply + resolve-thread loop in one
Bash round-trip, then prints the counters the summary step reports:

    {"repo": "owner/name", "pr": 42, "threads": [
      {"thread": "PRRT_a", "verdict": "fix", "files": ["src/a.ts"]},
      {"thread": "PRRT_b", "verdict": "reply", "reply_to": 123, "body": "@coderabbitai ..."},
      {"thread": "PRRT_c", "verdict": "ask"}
    ], "skipped": {"resolved": 4}}

Reply bodies are public, so they are validated the way commit messages are:
no attribution lines, no long dashes, no emoji, and no echo of CodeRabbit's
"Prompt for AI Agents" block. The skill marker is appended here rather than
drafted, because the next run's idempotency check depends on it.

Nothing here commits or pushes; that is /commit and /pr's job.
"""

import json
import re
import subprocess
import sys

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_INVALID_PLAN = 2
EXIT_PARTIAL = 3

SKILL_MARKER = "<!-- cr-skill -->"
VERDICTS = ("fix", "reply", "ask")

ATTRIBUTION_RE = re.compile(r"(?i)co-authored-by:.*claude|generated with.*\bclaude\b")
# Assembled from codepoints because the house style bans these characters in source.
DASH_RE = re.compile("[" + chr(0x2014) + chr(0x2013) + "]")
EMOJI_RE = re.compile(
    "[" + chr(0x1F300) + "-" + chr(0x1FAFF) + chr(0x2728) + chr(0x2705) + chr(0x274C) + "]"
)
AI_PROMPT_RE = re.compile(r"(?i)prompt for ai agents")

REPLY_BLOCKS = (
    (ATTRIBUTION_RE, "contains a Claude attribution line"),
    (DASH_RE, "contains a long dash; use a hyphen, comma, colon, or parentheses"),
    (EMOJI_RE, "contains an emoji; replies are plain technical prose"),
    (AI_PROMPT_RE, "echoes CodeRabbit's 'Prompt for AI Agents' block"),
)

# No `gh` subcommand resolves a review thread, so this is the one mutation the
# skill needs. The document travels as a JSON request body on stdin, which keeps
# the `ID!` non-null marker intact where a shell would corrupt it to `\!`.
RESOLVE_MUTATION = """
mutation($threadId:ID!){
  resolveReviewThread(input:{threadId:$threadId}){ thread{ id isResolved } }
}
"""


def fail(message, code):
    print(f"apply.py: {message}", file=sys.stderr)
    sys.exit(code)


def run(args, stdin=None):
    return subprocess.run(args, input=stdin, capture_output=True, text=True)


def validate(plan):
    repo = plan.get("repo") or ""
    if "/" not in repo:
        fail("plan needs a repo as owner/name", EXIT_INVALID_PLAN)
    try:
        pr = int(plan.get("pr"))
    except (TypeError, ValueError):
        fail("plan needs a numeric pr", EXIT_INVALID_PLAN)
    threads = plan.get("threads")
    if not threads:
        fail("plan has no threads", EXIT_INVALID_PLAN)

    for i, t in enumerate(threads, 1):
        verdict = t.get("verdict")
        if verdict not in VERDICTS:
            fail(f"thread {i}: verdict must be one of {', '.join(VERDICTS)}", EXIT_INVALID_PLAN)
        if verdict != "ask" and not t.get("thread"):
            fail(f"thread {i}: missing thread node id", EXIT_INVALID_PLAN)
        if verdict != "reply":
            continue
        body = (t.get("body") or "").strip()
        if not body:
            fail(f"thread {i}: reply verdict with an empty body", EXIT_INVALID_PLAN)
        if not t.get("reply_to"):
            fail(f"thread {i}: reply verdict needs reply_to (the thread root comment id)", EXIT_INVALID_PLAN)
        for pattern, complaint in REPLY_BLOCKS:
            if pattern.search(body):
                fail(f"thread {i}: reply {complaint}", EXIT_INVALID_PLAN)
    return repo, pr, threads


def post_reply(repo, pr, reply_to, body):
    if SKILL_MARKER not in body:
        body = body.rstrip() + "\n\n" + SKILL_MARKER
    payload = json.dumps({"body": body, "in_reply_to": int(reply_to)})
    proc = run(
        ["gh", "api", "--method", "POST", f"repos/{repo}/pulls/{pr}/comments", "--input", "-"],
        stdin=payload,
    )
    if proc.returncode != 0:
        return None, proc.stderr.strip() or proc.stdout.strip()
    try:
        return json.loads(proc.stdout).get("html_url") or "", None
    except ValueError:
        return "", None


def resolve_thread(thread_id):
    payload = json.dumps({"query": RESOLVE_MUTATION, "variables": {"threadId": thread_id}})
    proc = run(["gh", "api", "graphql", "--input", "-"], stdin=payload)
    if proc.returncode != 0:
        return proc.stderr.strip() or proc.stdout.strip()
    try:
        data = json.loads(proc.stdout)
    except ValueError as e:
        return f"unparseable graphql output: {e}"
    if data.get("errors"):
        return "; ".join(e.get("message", "?") for e in data["errors"])
    return None


def main():
    if len(sys.argv) != 2:
        fail("usage: apply.py <plan.json>", EXIT_USAGE)
    try:
        with open(sys.argv[1]) as fh:
            plan = json.load(fh)
    except (OSError, ValueError) as e:
        fail(f"cannot read plan: {e}", EXIT_USAGE)

    repo, pr, threads = validate(plan)

    fixed = replied = resolved = asked = 0
    files = []
    failures = []

    for i, t in enumerate(threads, 1):
        verdict = t["verdict"]
        if verdict == "ask":
            asked += 1
            print(f"[{i}] ask: left open for the user")
            continue

        if verdict == "reply":
            url, err = post_reply(repo, pr, t["reply_to"], t["body"])
            if err:
                failures.append(f"thread {t['thread']}: reply failed: {err}")
                print(f"[{i}] reply FAILED, thread left open", file=sys.stderr)
                continue
            replied += 1
            print(f"[{i}] replied: {url}")
        else:
            fixed += 1
            files.extend(t.get("files") or [])
            print(f"[{i}] fixed: {', '.join(t.get('files') or ['(no files listed)'])}")

        err = resolve_thread(t["thread"])
        if err:
            failures.append(f"thread {t['thread']}: resolve failed: {err}")
            print(f"[{i}] resolve FAILED: {err}", file=sys.stderr)
            continue
        resolved += 1

    skipped = sum((plan.get("skipped") or {}).values())
    print()
    print(
        f"summary: {fixed} fixed, {replied} replied, {resolved} resolved, "
        f"{asked} asked, {skipped} skipped"
    )
    if files:
        print(f"files touched: {', '.join(sorted(set(files)))}")
    for f in failures:
        print(f"failure: {f}", file=sys.stderr)

    return EXIT_PARTIAL if failures else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
