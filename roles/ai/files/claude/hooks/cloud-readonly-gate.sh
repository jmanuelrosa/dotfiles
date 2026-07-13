#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to match the other hooks referenced from
# settings.json (hooks.PreToolUse) and symlinked into ~/.claude/hooks.
"""cloud-readonly-gate.sh - PreToolUse hook for Claude Code.

Read-only gate for the cloud CLIs (aws, gcloud, gsutil, bq). Those four
run OUTSIDE the sandbox (settings.json sandbox.excludedCommands) so they
can read their own credential stores natively; that also means the
network egress allowlist does NOT constrain them. This hook is therefore
the primary guardrail on what they may do, in three tiers:

  block (exit 2): credential/token extraction and endpoint redirection -
    print-access-token, export-credentials, get-secret-value,
    get-session-token, assume-role, --endpoint-url, --log-http, ... .
    These emit a live credential or send a signed request somewhere the
    allowlist can't vet, so they are hard-blocked even though a
    Bash(<cli>:*) allow rule exists. exit 2 overrides the allow rule the
    same way the git-skill-gate hook overrides Bash(gh:*).

  ask (permissionDecision "ask"): any other non-read-only cloud command
    (mutations, s3 cp/rm, delete, ...), any command that names the
    credential stores (~/.aws, ~/.config/gcloud), and any cloud CLI
    reached through a wrapper, path, env prefix, or command substitution
    the gate cannot validate. The user decides.

  allow (exit 0, no output): recognized read-only invocations
    (describe-/list-/get- for aws; list/describe/read/get-iam-policy for
    gcloud; ls/stat/cat for gsutil; ls/show/head for bq) pass through to
    the Bash(<cli>:*) allow rule and run without a prompt.

Segment splitting on |, ;, &, && and || is naive about quoting, so a
quoted string containing those tokens can produce a spurious ask/block,
never a spurious allow. block beats ask beats allow when a compound
command mixes tiers. Fail-closed for cloud commands; fail-open only when
stdin is not valid hook JSON. This is a guardrail plus a tripwire, not a
kernel boundary: it can be disabled in settings.json, and the deny rules
plus the sandbox around every OTHER command are the layers beside it.
"""

import json
import re
import sys

CLOUD_WORD_RE = re.compile(r"(?<![\w-])(?:aws|gcloud|gsutil|bq)(?![\w-])")

CRED_PATH_RE = re.compile(
    r"\.aws\b"
    r"|\.config/gcloud"
    r"|application_default_credentials"
    r"|(?:credentials|access_tokens)\.db"
)

SEGMENT_SPLIT_RE = re.compile(r"\|\||&&|\||;|&|\n")

SUBSTITUTION_RE = re.compile(r"`|\$\(|<\(")

# Tier 1: credential/token extraction and endpoint redirection -> hard block.
BLOCK_RES = {
    "aws": re.compile(
        r"--endpoint-url"
        r"|--no-verify-ssl"
        r"|--include-values"
        r"|\bexport-credentials\b"
        r"|\b(?:batch-)?get-secret-value\b"
        r"|\bget-parameter[\w-]*"
        r"|\bget-session-token\b"
        r"|\bget-federation-token\b"
        r"|\bassume-role[\w-]*"
        r"|\bget-login-password\b"
        r"|\bget-authorization-token\b"
        r"|\bget-token\b"
        r"|\bget-password-data\b"
        r"|\bget-cluster-credentials[\w-]*"
        r"|\bgenerate-db-auth-token\b"
        r"|\bget-instance-access-details\b"
        r"|\bget-relational-database-master-user-password\b"
        r"|\bcreate-access-key\b"
        r"|\bcreate-login-profile\b"
    ),
    "gcloud": re.compile(
        r"--log-http"
        r"|\bprint-access-token\b"
        r"|\bprint-identity-token\b"
        r"|\bprint-refresh-token\b"
        r"|\bconfig-helper\b"
        r"|\bauth\s+describe\b"
        r"|\bversions\s+access\b"
        r"|\bkeys\s+create\b"
        r"|\bget-credentials\b"
    ),
    "gsutil": re.compile(r"\bsignurl\b"),
    "bq": re.compile(r"--\S*credential"),
}

# Tier 3: recognized read-only invocations -> pass through to the allow rule.
ALLOW_RES = {
    "aws": re.compile(
        r"^aws(?:\s+--(?:profile|region|output)(?:=|\s+)\S+)*\s+"
        r"(?:"
        r"[a-z0-9-]+\s+(?:describe|list|get)-[a-z0-9][\w-]*"
        r"|s3\s+ls"
        r"|logs\s+tail"
        r"|configure\s+list-profiles"
        r"|(?:[a-z0-9-]+\s+){0,2}help"
        r"|--version"
        r")(?:\s|$)"
    ),
    "gcloud": re.compile(
        r"^gcloud(?:\s+(?:alpha|beta))?(?:\s+--[\w-]+(?:=\S+)?)*"
        r"(?:\s+[a-z][\w-]*)*?\s+"
        r"(?:list|describe|read|get-iam-policy|get-value|search-all-[\w-]+"
        r"|version|info|help)"
        r"(?:\s|$)"
    ),
    "gsutil": re.compile(
        r"^gsutil(?:\s+-[a-zA-Z])*\s+(?:ls|stat|du|cat|hash|version|help)(?:\s|$)"
    ),
    "bq": re.compile(
        r"^bq(?:\s+--[\w./=:_-]+)*\s+(?:ls|show|head|version|help)(?:\s|$)"
    ),
}

BLOCK, ASK = "block", "ask"


def rank(verdict):
    return {None: 0, ASK: 1, BLOCK: 2}[verdict]


def check_cloud_segment(cli, segment):
    if BLOCK_RES[cli].search(segment):
        return BLOCK, (
            f"a {cli} subcommand or flag that emits a live credential/token "
            "or redirects the API endpoint"
        )
    if SUBSTITUTION_RE.search(segment):
        return ASK, f"command substitution inside a {cli} call, which this gate cannot validate"
    if not ALLOW_RES[cli].match(segment):
        return ASK, f"a {cli} command that is not a recognized read-only (describe/list/get) call"
    return None, None


def decide(command):
    if CRED_PATH_RE.search(command):
        return ASK, (
            "a reference to the cloud credential stores (~/.aws, ~/.config/gcloud)"
        )
    if not CLOUD_WORD_RE.search(command):
        return None, None
    verdict, reason = None, None
    for raw_segment in SEGMENT_SPLIT_RE.split(command):
        segment = raw_segment.strip()
        if not segment:
            continue
        first_token = segment.split()[0]
        if first_token in ALLOW_RES:
            v, r = check_cloud_segment(first_token, segment)
        elif CLOUD_WORD_RE.search(segment):
            v, r = ASK, (
                "a cloud CLI invoked through a wrapper, path, env prefix, or "
                "substitution instead of directly"
            )
        else:
            v, r = None, None
        if rank(v) > rank(verdict):
            verdict, reason = v, r
    return verdict, reason


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if (data.get("tool_name") or "") != "Bash":
        sys.exit(0)
    command = (data.get("tool_input") or {}).get("command") or ""
    if not command:
        sys.exit(0)

    try:
        verdict, reason = decide(command)
    except Exception:
        verdict, reason = ASK, "could not be parsed by the read-only gate"

    if verdict == BLOCK:
        print(
            f"cloud-readonly-gate: blocked. This command contains {reason}. "
            "Read-only cloud commands (describe/list/get) run without a prompt; "
            "run credential-emitting or endpoint-redirecting commands in a real "
            "terminal instead.",
            file=sys.stderr,
        )
        sys.exit(2)
    if verdict == ASK:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": f"cloud-readonly-gate: command contains {reason}",
                    }
                }
            )
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
