#!/usr/bin/env python3
"""context.py - one-shot CodeRabbit thread context for the /coderabbit skill.

Resolves the repo and PR, fetches every review thread with its resolved and
outdated state, drops the threads a previous run already handled, strips
CodeRabbit's collapsed boilerplate, and groups what survives by file path.

Default output is a compact text report the triage step reads directly.
--json emits the same model as structured data.
"""

import argparse
import json
import os
import re
import subprocess
import sys

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_NO_REMOTE = 2
EXIT_NOT_GITHUB = 3
EXIT_NO_PR = 4
EXIT_GH_FAILED = 5

BOT_LOGIN = "coderabbitai[bot]"
SKILL_MARKER = "<!-- cr-skill -->"
PAGE_SIZE = 100
MAX_PAGES = 20

BODY_CAP = int(os.environ.get("CODERABBIT_BODY_CAP", "1600"))
DIFF_CAP = int(os.environ.get("CODERABBIT_DIFF_CAP", "24"))
WALKTHROUGH_CAP = int(os.environ.get("CODERABBIT_WALKTHROUGH_CAP", "1200"))

# Resolved and outdated state exists on no `gh` subcommand and no REST endpoint;
# the GraphQL reviewThreads connection is the only source of truth for what to
# process and what to skip. Passing the document as a JSON request body on stdin
# keeps the `!` non-null markers intact, which a shell would corrupt to `\!`.
THREADS_QUERY = """
query($owner:String!,$name:String!,$pr:Int!,$endCursor:String){
  repository(owner:$owner,name:$name){
    pullRequest(number:$pr){
      reviewThreads(first:%d, after:$endCursor){
        pageInfo{ hasNextPage endCursor }
        nodes{
          id isResolved isOutdated path line originalLine
          comments(first:%d){
            nodes{ databaseId author{login} body path line originalLine diffHunk }
          }
        }
      }
    }
  }
}
""" % (PAGE_SIZE, PAGE_SIZE)

DETAILS_TAG_RE = re.compile(r"</?details\b[^>]*>", re.I)
SUMMARY_RE = re.compile(r"<summary\b[^>]*>.*?</summary>", re.I | re.S)
STRAY_TAG_RE = re.compile(r"</?(?:summary|blockquote)\b[^>]*>", re.I)
SUGGESTION_FENCE_RE = re.compile(
    r"^ {0,3}`{3,}[ \t]*suggestion\b[^\n]*\n.*?^ {0,3}`{3,}[ \t]*$\n?",
    re.M | re.S | re.I,
)
AI_PROMPT_RE = re.compile(
    r"^[^\n]*Prompt for AI Agents[^\n]*\n[ \t]*\n?"
    r"(?:^ {0,3}`{3,}[^\n]*\n.*?^ {0,3}`{3,}[ \t]*$\n?)?",
    re.M | re.S,
)
BLANK_RUN_RE = re.compile(r"\n{3,}")

# Ordered: CodeRabbit stacks several markers on one comment and the most severe
# one decides how the triage step prioritises it.
SEVERITIES = (
    ("potential issue", "potential"),
    ("critical", "potential"),
    ("warning", "warning"),
    ("refactor suggestion", "refactor"),
    ("outside diff range", "outside-diff"),
    ("nitpick", "nitpick"),
)


def fail(message, code):
    print(f"context.py: {message}", file=sys.stderr)
    sys.exit(code)


def run(args, stdin=None):
    return subprocess.run(args, input=stdin, capture_output=True, text=True)


def gh_json(args, stdin=None):
    """(parsed stdout, error) from a gh call that answers in JSON."""
    proc = run(["gh", *args], stdin=stdin)
    if proc.returncode != 0:
        return None, proc.stderr.strip() or proc.stdout.strip()
    try:
        return json.loads(proc.stdout or "null"), None
    except ValueError as e:
        return None, f"unparseable gh output: {e}"


def graphql(query, variables):
    payload, err = gh_json(
        ["api", "graphql", "--input", "-"],
        stdin=json.dumps({"query": query, "variables": variables}),
    )
    if err:
        return None, err
    payload = payload or {}
    if payload.get("errors"):
        return None, "; ".join(e.get("message", "?") for e in payload["errors"])
    return payload.get("data"), None


def drop_details(text):
    """Remove balanced <details> regions, including nested ones."""
    parts = []
    depth = 0
    pos = 0
    for m in DETAILS_TAG_RE.finditer(text):
        if depth == 0:
            parts.append(text[pos:m.start()])
        if m.group(0).startswith("</"):
            depth = max(0, depth - 1)
        else:
            depth += 1
        pos = m.end()
    if depth == 0:
        parts.append(text[pos:])
    return "".join(parts)


def strip_noise(body):
    text = SUMMARY_RE.sub("", body or "")
    text = drop_details(text)
    # Dropped rather than summarised: it is CodeRabbit's instruction block aimed
    # at an agent, so keeping it out of context also keeps it out of the reply.
    text = AI_PROMPT_RE.sub("", text)
    text = SUGGESTION_FENCE_RE.sub("", text)
    text = STRAY_TAG_RE.sub("", text)
    text = BLANK_RUN_RE.sub("\n\n", text)
    return text.strip()


def severity_of(body):
    low = (body or "").lower()
    for needle, label in SEVERITIES:
        if needle in low:
            return label
    return "comment"


def cap_text(text, limit):
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n... [capped at {limit} chars]"


def cap_lines(text, limit):
    lines = (text or "").splitlines()
    if limit <= 0 or len(lines) <= limit:
        return "\n".join(lines)
    kept = lines[:limit]
    kept.append(f"... [capped at {limit} lines]")
    return "\n".join(kept)


def resolve_repo():
    remote = run(["git", "remote", "get-url", "origin"])
    if remote.returncode != 0:
        fail("no origin remote", EXIT_NO_REMOTE)
    url = remote.stdout.strip()
    if "github" not in url.lower():
        fail(f"coderabbit only supports GitHub remotes (got: {url})", EXIT_NOT_GITHUB)
    data, err = gh_json(["repo", "view", "--json", "nameWithOwner"])
    if err or not (data or {}).get("nameWithOwner"):
        fail(f"cannot resolve repo: {err or 'no nameWithOwner in response'}", EXIT_GH_FAILED)
    return data["nameWithOwner"]


def resolve_pr(explicit):
    if explicit is not None:
        return explicit
    # Safe under a user alias like `pr = pr create --web`: gh gives a core command
    # precedence over a same-named alias and never expands it, verified on 2.96.0.
    data, err = gh_json(["pr", "view", "--json", "number"])
    if err or not (data or {}).get("number"):
        fail(
            "no PR for the current branch; pass a PR number or run /pr first",
            EXIT_NO_PR,
        )
    return int(data["number"])


def fetch_threads(owner, name, pr):
    nodes = []
    cursor = None
    for _ in range(MAX_PAGES):
        data, err = graphql(
            THREADS_QUERY,
            {"owner": owner, "name": name, "pr": pr, "endCursor": cursor},
        )
        if err:
            fail(f"reviewThreads query failed: {err}", EXIT_GH_FAILED)
        conn = (((data or {}).get("repository") or {}).get("pullRequest") or {}).get(
            "reviewThreads"
        )
        if conn is None:
            fail(f"no pull request #{pr} on this repo", EXIT_NO_PR)
        nodes.extend(conn.get("nodes") or [])
        page = conn.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
    return nodes


def comments_of(thread):
    return [c for c in (thread.get("comments") or {}).get("nodes") or [] if c]


def author_of(comment):
    return (comment.get("author") or {}).get("login")


def skip_reason(thread, comments):
    if not comments:
        return "empty"
    if author_of(comments[0]) != BOT_LOGIN:
        return "not-coderabbit"
    if thread.get("isResolved"):
        return "resolved"
    if thread.get("isOutdated"):
        return "outdated"
    for c in comments[1:]:
        if SKILL_MARKER in (c.get("body") or "") or author_of(c) != BOT_LOGIN:
            return "answered"
    return None


def build(thread, comments):
    root = comments[0]
    raw = "\n\n".join(c.get("body") or "" for c in comments if author_of(c) == BOT_LOGIN)
    return {
        "thread": thread.get("id"),
        "reply_to": root.get("databaseId"),
        "path": thread.get("path") or root.get("path") or "(no path)",
        "line": thread.get("line")
        or thread.get("originalLine")
        or root.get("line")
        or root.get("originalLine"),
        "severity": severity_of(raw),
        "body": cap_text(strip_noise(raw), BODY_CAP),
        "diff_hunk": cap_lines(root.get("diffHunk") or "", DIFF_CAP),
    }


def walkthrough(pr):
    """Title, description and the bot's latest review, empty if any of it is missing.

    A PR whose metadata cannot be read is not fatal: the threads are the work, and
    they came from a query that already succeeded.
    """
    data, err = gh_json(["pr", "view", str(pr), "--json", "title,body,reviews"])
    if err or not data:
        return {"title": "", "body": "", "walkthrough": ""}
    bot_bodies = [
        r.get("body") or ""
        for r in data.get("reviews") or []
        if author_of(r) == BOT_LOGIN and (r.get("body") or "").strip()
    ]
    latest = strip_noise(bot_bodies[-1]) if bot_bodies else ""
    return {
        "title": data.get("title") or "",
        "body": cap_text(strip_noise(data.get("body") or ""), WALKTHROUGH_CAP),
        "walkthrough": cap_text(latest, WALKTHROUGH_CAP),
    }


def group_by_path(threads):
    grouped = {}
    for t in threads:
        grouped.setdefault(t["path"], []).append(t)
    for items in grouped.values():
        items.sort(key=lambda t: (t["line"] is None, t["line"] or 0))
    return {path: grouped[path] for path in sorted(grouped)}


def indented(text):
    return [f"  {ln}" if ln.strip() else "" for ln in text.splitlines()]


def render(model):
    out = []
    pr = model["pr"]

    def section(title, body=None):
        if out:
            out.append("")
        out.append(f"== {title} ==")
        if body:
            out.append(body)

    section("pr")
    out.append(f"repo: {model['repo']}")
    out.append(f"number: {pr['number']}")
    out.append(f"title: {pr['title']}")
    if pr["body"]:
        section("pr description", pr["body"])
    if pr["walkthrough"]:
        section("coderabbit walkthrough (context only, do not triage as tasks)", pr["walkthrough"])

    section("skipped")
    if model["skipped"]:
        for reason in sorted(model["skipped"]):
            out.append(f"{reason}: {model['skipped'][reason]}")
    else:
        out.append("none")

    total = sum(len(v) for v in model["threads"].values())
    section(f"open threads: {total}")
    if not total:
        out.append(f"No open CodeRabbit threads on PR #{pr['number']}.")
        return "\n".join(out) + "\n"

    n = 0
    for path, items in model["threads"].items():
        out.append("")
        out.append(f"--- {path} ---")
        for t in items:
            n += 1
            line = t["line"] if t["line"] is not None else "?"
            out.append("")
            out.append(
                f"[{n}] {path}:{line} severity={t['severity']} "
                f"thread={t['thread']} reply-to={t['reply_to']}"
            )
            out.append("body:")
            out.extend(indented(t["body"]))
            if t["diff_hunk"]:
                out.append("diff:")
                out.extend(indented(t["diff_hunk"]))
    return "\n".join(out) + "\n"


class Parser(argparse.ArgumentParser):
    """argparse exits 2 on a usage error, which is the no-remote code here."""

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"context.py: {message}\n")


def main():
    parser = Parser(prog="context.py", description=__doc__.splitlines()[0])
    parser.add_argument(
        "pr", nargs="?", type=int, help="PR number; defaults to the current branch's PR"
    )
    parser.add_argument("--json", action="store_true", help="emit the model as JSON")
    args = parser.parse_args()

    repo = resolve_repo()
    owner, _, name = repo.partition("/")
    pr = resolve_pr(args.pr)

    skipped = {}
    kept = []
    for thread in fetch_threads(owner, name, pr):
        comments = comments_of(thread)
        reason = skip_reason(thread, comments)
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
        else:
            kept.append(build(thread, comments))

    model = {
        "repo": repo,
        "pr": {"number": pr, **walkthrough(pr)},
        "skipped": skipped,
        "threads": group_by_path(kept),
    }

    if args.json:
        print(json.dumps(model, indent=2))
    else:
        print(render(model), end="")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
