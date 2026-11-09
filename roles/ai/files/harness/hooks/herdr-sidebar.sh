#!/usr/bin/env python3
# vim: ft=python
# Kept as .sh like every hook beside it; the shebang selects Python.
"""herdr sidebar reporter: what herdr cannot see for itself, handed to it as metadata tokens.

herdr renders its agent and space rows from tokens a pane or a workspace reports, and only
the agent knows its context fill, its ticket or why it is waiting. This is the one reporter
behind those tokens, reached four ways:

    statusline.sh imports it      each Claude turn: branch, context, ticket, PR poll, usage
    herdr-sidebar.sh report       pi's footer, whenever its branch or context reading moves
    herdr-sidebar.sh [hook]       Claude's PermissionRequest, Notification and Stop hooks
    herdr-sidebar.sh pr / usage   the detached PR poll, and herdr's tab bar command

Every path is best effort and silent. A status line and a hook both run on the agent's hot
path, and a sidebar is never worth an error there, so a failure leaves the token as it was.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time


def _vocabulary():
    """statusline.json, one directory up, found through realpath as every reader does."""
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "statusline.json")
    try:
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


VOCAB = _vocabulary()


def _section(parent, key):
    found = parent.get(key)
    return found if isinstance(found, dict) else {}


HERDR = _section(VOCAB, "herdr")
TOKENS = _section(HERDR, "tokens")
PR_GLYPHS = _section(HERDR, "prGlyphs")
PR_LABELS = _section(HERDR, "prLabels")
WAITING = _section(HERDR, "waiting")
LABELS = _section(VOCAB, "labels")

# Branch names follow `<type>/<TICKET>-<slug>`, where the ticket is a Jira key or `gh-<n>`.
TICKET = re.compile(r"^[a-z]+/((?:[A-Z][A-Z0-9]*|gh)-\d+)-")
# Claude's Notification types that mean the agent waits on an answer rather than a permission;
# a permission prompt also arrives as PermissionRequest, which names the tool.
INPUT_NOTIFICATIONS = frozenset({"elicitation_dialog", "elicitation_url_dialog", "agent_needs_input"})
FAILED_CHECKS = frozenset({"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"})
PENDING_CHECKS = frozenset({"PENDING", "EXPECTED", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED"})
PENDING_PIPELINES = frozenset({"created", "pending", "running", "preparing", "scheduled", "waiting_for_resource"})
FAILED_PIPELINES = frozenset({"failed", "canceled"})
GITLAB_REVIEW = {"not_approved": "REVIEW_REQUIRED", "requested_changes": "CHANGES_REQUESTED"}


def _text(mapping, key):
    found = mapping.get(key)
    return found if isinstance(found, str) and found else None


def _number(key):
    found = HERDR.get(key)
    return found if isinstance(found, int) and found > 0 else None


def token(name):
    return _text(TOKENS, name)


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "herdr-sidebar")


def _state_path(kind, ident):
    return os.path.join(cache_dir(), f"{kind}-{re.sub(r'[^A-Za-z0-9_.-]', '_', ident)}.json")


def _load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _save(path, data):
    """Written through a rename, because a detached PR poll and a status line can race."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        scratch = f"{path}.{os.getpid()}"
        with open(scratch, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(scratch, path)
    except OSError:
        pass


def _inside():
    """The running herdr server, or None outside one.

    The socket's inode stands for the server: a restart drops every reported token and
    recreates the socket, so a cache keyed on it re-reports instead of trusting a dead server.
    """
    if os.environ.get("HERDR_ENV") != "1":
        return None
    sock = os.environ.get("HERDR_SOCKET_PATH")
    herdr = os.environ.get("HERDR_BIN_PATH") or shutil.which("herdr")
    source = _text(HERDR, "source")
    if not sock or not herdr or not source:
        return None
    try:
        server = os.stat(sock).st_ino
    except OSError:
        return None
    return {
        "herdr": herdr,
        "server": server,
        "source": source,
        "pane": os.environ.get("HERDR_PANE_ID"),
        "workspace": os.environ.get("HERDR_WORKSPACE_ID"),
    }


def _run(argv, cwd=None, timeout=2):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except (OSError, subprocess.SubprocessError):
        return None
    return done


def _herdr(ctx, args):
    done = _run([ctx["herdr"], *args])
    return done is not None and done.returncode == 0


def _metadata_args(ctx, scope, target):
    return [scope, "report-metadata", target, "--source", ctx["source"]]


def patch_tokens(ctx, scope, target, wanted):
    """Send only the tokens whose value moved since this server last accepted them."""
    if not target or not wanted:
        return
    path = _state_path(scope, target)
    state = _load(path)
    known = state.get("tokens") if state.get("server") == ctx["server"] else None
    known = known if isinstance(known, dict) else {}
    changed = {name: value for name, value in wanted.items() if known.get(name, "") != value}
    if not changed:
        return
    args = _metadata_args(ctx, scope, target)
    for name, value in changed.items():
        args += ["--token", f"{name}={value}"] if value else ["--clear-token", name]
    if _herdr(ctx, args):
        _save(path, {**state, "server": ctx["server"], "tokens": {**known, **changed}})


def _git(cwd, *args):
    done = _run(["git", "-C", cwd, *args], timeout=1)
    return done.stdout.strip() if done is not None and done.returncode == 0 else None


def repo_facts(cwd):
    """(branch, linked) for cwd, or None outside a repository or on an unborn branch.

    `linked` marks a linked worktree. `wt` and herdr both label a worktree's workspace with
    its branch, so there the agent row leaves the branch out rather than print it twice.
    """
    if not cwd or not os.path.isdir(cwd):
        return None
    out = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD", "--git-dir", "--git-common-dir")
    lines = out.splitlines() if out else []
    if len(lines) != 3:
        return None
    branch, git_dir, common_dir = lines
    linked = os.path.realpath(os.path.join(cwd, git_dir)) != os.path.realpath(os.path.join(cwd, common_dir))
    return ("" if branch == "HEAD" else branch), linked


def ticket_text(cwd, branch):
    """`KEY title` for a ticket branch, the title being the description s-task records."""
    found = TICKET.match(branch or "")
    if not found:
        return ""
    title = _git(cwd, "config", f"branch.{branch}.description")
    first = title.splitlines()[0].strip() if title else ""
    return f"{found.group(1)} {first}" if first else found.group(1)


def context_tokens(pct):
    tokens = {}
    step = _number("contextStepPct") or 1
    handoff = VOCAB.get("handoffPct")
    known = isinstance(pct, (int, float))
    if token("context"):
        tokens[token("context")] = f"{int(pct) // step * step}%" if known else ""
    if token("handoff"):
        due = known and isinstance(handoff, int) and pct >= handoff
        tokens[token("handoff")] = (_text(LABELS, "handoff") or "") if due else ""
    return tokens


def branch_text(branch):
    """The branch behind the git-branch glyph Starship uses, so it never reads as a workspace."""
    if not branch:
        return ""
    mark = _text(HERDR, "branchGlyph")
    return f"{mark} {branch}" if mark else branch


def report_agent(cwd, context_pct=None):
    """Everything an agent turn knows: pane tokens, workspace tokens, and a due PR poll."""
    ctx = _inside()
    if not ctx:
        return
    facts = repo_facts(cwd)
    branch = facts[0] if facts else ""

    pane = context_tokens(context_pct)
    if token("branch"):
        pane[token("branch")] = "" if not facts or facts[1] else branch_text(branch)
    patch_tokens(ctx, "pane", ctx["pane"], pane)

    if token("ticket") and ctx["workspace"]:
        ticket = _cached_ticket(ctx, cwd, branch)
        patch_tokens(ctx, "workspace", ctx["workspace"], {token("ticket"): ticket})
    _maybe_poll_pr(ctx, cwd, branch)


def _cached_ticket(ctx, cwd, branch):
    """One `git config` read per branch rather than per turn."""
    path = _state_path("ticket", ctx["pane"] or ctx["workspace"])
    state = _load(path)
    if state.get("branch") == branch and isinstance(state.get("text"), str):
        return state["text"]
    text = ticket_text(cwd, branch)
    _save(path, {"branch": branch, "text": text})
    return text


def _maybe_poll_pr(ctx, cwd, branch):
    """Start a detached PR poll when the last one for this branch is older than the refresh.

    Detached because the status line must never wait on the network. The timestamp is written
    before the spawn so the next turn does not start a second poll while this one runs.
    """
    refresh = _number("prRefreshSeconds")
    if not token("pr") or not refresh or not branch or not ctx["workspace"]:
        return
    path = _state_path("prpoll", ctx["workspace"])
    state = _load(path)
    fresh = state.get("server") == ctx["server"] and state.get("branch") == branch
    if fresh and time.time() - float(state.get("at") or 0) < refresh:
        return
    _save(path, {"server": ctx["server"], "branch": branch, "at": time.time()})
    argv = [sys.executable, os.path.realpath(__file__), "pr", "--cwd", cwd, "--branch", branch, "--workspace", ctx["workspace"]]
    try:
        subprocess.Popen(
            argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
    except OSError:
        pass


def _checks_from_github(rollup):
    if not isinstance(rollup, list) or not rollup:
        return None
    verdict = "pass"
    for check in rollup:
        if not isinstance(check, dict):
            continue
        outcome = check.get("conclusion") or check.get("state") or ""
        status = check.get("status")
        if outcome in FAILED_CHECKS:
            return "fail"
        if (status and status != "COMPLETED") or outcome in PENDING_CHECKS:
            verdict = "pending"
    return verdict


def _checks_from_gitlab(pipeline):
    status = pipeline.get("status") if isinstance(pipeline, dict) else None
    if status == "success":
        return "pass"
    if status in FAILED_PIPELINES:
        return "fail"
    if status in PENDING_PIPELINES:
        return "pending"
    return None


def _summary(number, state, checks, review):
    closed = _text(PR_LABELS, state) if state in ("MERGED", "CLOSED") else None
    if closed:
        return f"{number} {closed}"
    parts = [number, _text(PR_GLYPHS, checks) if checks else None, _text(PR_LABELS, review) if review else None]
    return " ".join(part for part in parts if part)


def summarize_github(data):
    number = data.get("number")
    if not isinstance(number, int):
        return ""
    checks = _checks_from_github(data.get("statusCheckRollup"))
    return _summary(f"#{number}", data.get("state"), checks, data.get("reviewDecision"))


def summarize_gitlab(data):
    iid = data.get("iid")
    if not isinstance(iid, int):
        return ""
    state = {"merged": "MERGED", "closed": "CLOSED"}.get(data.get("state"))
    review = GITLAB_REVIEW.get(data.get("detailed_merge_status"))
    return _summary(f"!{iid}", state, _checks_from_gitlab(data.get("head_pipeline")), review)


def pr_text(cwd, branch):
    """The PR or MR summary, "" when the branch has none, None when the forge did not answer."""
    remote = _git(cwd, "remote", "get-url", "origin") or ""
    if "github" in remote:
        argv = ["gh", "pr", "view", branch, "--json", "number,state,reviewDecision,statusCheckRollup"]
        summarize, missing = summarize_github, "no pull requests found"
    elif remote:
        argv = ["glab", "mr", "view", branch, "--output", "json"]
        summarize, missing = summarize_gitlab, "no open merge request"
    else:
        return None
    done = _run(argv, cwd=cwd, timeout=20)
    if done is None:
        return None
    if done.returncode != 0:
        return "" if missing in (done.stderr or "").lower() else None
    try:
        data = json.loads(done.stdout)
    except ValueError:
        return None
    return summarize(data) if isinstance(data, dict) else None


def poll_pr(cwd, branch, workspace):
    """Report the PR summary with a TTL, so a poller that stops running stops being believed."""
    ctx = _inside()
    ttl = _number("prTtlSeconds")
    if not ctx or not token("pr") or not ttl:
        return
    text = pr_text(cwd, branch)
    if text is None:
        return
    args = _metadata_args(ctx, "workspace", workspace)
    args += ["--token", f"{token('pr')}={text}", "--ttl-ms", str(ttl * 1000)] if text else ["--clear-token", token("pr")]
    _herdr(ctx, args)


def _usage_path():
    return os.path.join(cache_dir(), "usage.json")


def record_usage(rate_limits):
    """Keep the account's usage windows where herdr's tab bar command can read them."""
    if not _inside() or not isinstance(rate_limits, dict):
        return
    windows = {}
    for key in ("five_hour", "seven_day"):
        window = rate_limits.get(key)
        if isinstance(window, dict) and isinstance(window.get("used_percentage"), (int, float)):
            windows[key] = {"pct": round(window["used_percentage"]), "resets_at": window.get("resets_at")}
    if windows and _load(_usage_path()) != windows:
        _save(_usage_path(), windows)


def usage_text(now=None):
    """`usage 5h 9% 7d 1%`, dropping a window whose reset has passed: its reading is stale."""
    now = time.time() if now is None else now
    windows = _load(_usage_path())
    parts = []
    for key, label in (("five_hour", "5h"), ("seven_day", "7d")):
        window = windows.get(key)
        if not isinstance(window, dict):
            continue
        resets = window.get("resets_at")
        if isinstance(resets, (int, float)) and resets <= now:
            continue
        parts.append(f"{label} {window.get('pct')}%")
    return "usage " + " ".join(parts) if parts else ""


def hook(payload):
    """Name what a blocked agent waits on, as the label herdr shows for the blocked state.

    A state label only renders while herdr reads the agent as blocked, so it needs no clearing
    when the agent resumes. Stop clears it anyway, once per turn and only when one is set, so
    a later block with no hook behind it never shows a stale reason.
    """
    ctx = _inside()
    if not ctx or not ctx["pane"] or not isinstance(payload, dict):
        return
    event = payload.get("hook_event_name")
    if event == "PermissionRequest":
        reason = payload.get("tool_name")
    elif event == "Notification" and payload.get("notification_type") in INPUT_NOTIFICATIONS:
        reason = _text(WAITING, "input")
    elif event == "Stop":
        reason = None
    else:
        return
    path = _state_path("label", ctx["pane"])
    labelled = _load(path).get("server") == ctx["server"]
    args = _metadata_args(ctx, "pane", ctx["pane"])
    if isinstance(reason, str) and reason:
        prefix = _text(WAITING, "prefix")
        text = f"{prefix}: {reason}" if prefix else reason
        if _herdr(ctx, [*args, "--state-label", f"blocked={text}"]):
            _save(path, {"server": ctx["server"]})
    elif labelled and _herdr(ctx, [*args, "--clear-state-labels"]):
        try:
            os.remove(path)
        except OSError:
            pass


def main(argv):
    parser = argparse.ArgumentParser(prog="herdr-sidebar")
    sub = parser.add_subparsers(dest="command")
    report = sub.add_parser("report")
    report.add_argument("--cwd", required=True)
    report.add_argument("--context-pct", type=float)
    pr = sub.add_parser("pr")
    pr.add_argument("--cwd", required=True)
    pr.add_argument("--branch", required=True)
    pr.add_argument("--workspace", required=True)
    sub.add_parser("usage")
    sub.add_parser("hook")
    # A hook is registered as the bare script, so no subcommand means a hook payload on stdin.
    args = parser.parse_args(argv or ["hook"])

    if args.command == "report":
        report_agent(args.cwd, args.context_pct)
    elif args.command == "pr":
        poll_pr(args.cwd, args.branch, args.workspace)
    elif args.command == "usage":
        text = usage_text()
        if text:
            print(text)
    elif args.command == "hook":
        try:
            payload = json.load(sys.stdin)
        except ValueError:
            payload = None
        hook(payload)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception:  # a sidebar is never worth a failing hook or footer
        sys.exit(0)
