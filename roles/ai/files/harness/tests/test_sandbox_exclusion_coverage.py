"""Every command Claude lets out of its sandbox is gated by a hook or exempted on purpose.

`sandbox.excludedCommands` in Claude's adapter.toml runs a command with no OS boundary and
no network allowlist, so for an allowlisted CLI a PreToolUse hook is the only thing left
between an agent and whatever that CLI can publish. An entry added there without a gate is
how gh and glab came to run unsandboxed and unprompted.

So each entry is either in GATED, with a probe the named hook must refuse or ask about, or
in EXEMPT, with the reason nobody gates it. A new entry in neither fails here, which is the
point: the review happens when the exclusion is added, not after it has been used.
"""

import fnmatch
import json
import re
import subprocess
import sys

import pytest
from harnessgen import manifest

ROOT = manifest.find_root()
POLICY = manifest.load(ROOT)
EXCLUDED = POLICY.adapter("claude")["sandbox"]["excludedCommands"]
CLAUDE_RULE_RE = re.compile(r"^Bash\((.*)\)$")

GATED = {
    "git *": ("git-skill-gate", "git push origin main"),
    "gh *": ("cli-egress-gate", "gh gist create notes.txt"),
    "glab *": ("cli-egress-gate", "glab snippet create -t notes notes.txt"),
    "ntn *": ("cli-egress-gate", "ntn files create"),
    "bru *": ("cli-egress-gate", "bru run"),
    "aws *": ("cloud-readonly-gate", "aws s3 rm s3://bucket/key"),
    "gcloud *": ("cloud-readonly-gate", "gcloud auth print-access-token"),
    "gsutil *": ("cloud-readonly-gate", "gsutil rm gs://bucket/key"),
    "bq *": ("cloud-readonly-gate", "bq rm -f dataset.table"),
}

SKILL_SCRIPT_GAP = (
    "The skill's own script, which commits or pushes and opens the PR/MR in a subprocess no hook sees. "
    "git-skill-gate matches it by path, but its claude_if routes only git, gh and glab to it, so "
    "under Claude the path match never runs. Widening claude_if is not safe yet: across past "
    "sessions, 39 of 136 real runs had no owning-skill attribution in the gate's window, most of "
    "them /pr running the commit script, so the widened gate would have refused them."
)

EXEMPT = {
    "python3 ~/.claude/skills/commit/scripts/apply.py *": SKILL_SCRIPT_GAP,
    "python3 ~/.claude/skills/pr/scripts/apply.py *": SKILL_SCRIPT_GAP,
    "pgcli *": "Reaches only the database a connection names and publishes nothing beyond it.",
    "acli *": "Writes land in the user's own Atlassian site, readable by its members, not the public.",
    "sentry *": "Reads and resolves issues in the user's own Sentry org; nothing it writes is public.",
    "wrangler *": "Not allowlisted, so every call prompts; the exclusion only lets an approved call reach its credentials.",
    "cf *": "Not allowlisted beyond `cf auth whoami`, so every other call prompts before it runs.",
    "bunx ctx7 *": (
        "Excluded for egress to the Context7 API, not for credentials. Its query text is all it sends, "
        "so gating it would prompt on every docs question the global instructions route to it."
    ),
    "npx -y ctx7 *": "The npx spelling of `bunx ctx7`, excluded for the same reason.",
}


def test_every_exclusion_is_gated_or_exempted_on_purpose():
    assert not set(GATED) & set(EXEMPT), "an exclusion is both gated and exempt"
    unreviewed = sorted(set(EXCLUDED) - set(GATED) - set(EXEMPT))
    assert not unreviewed, f"add a gate or a reviewed EXEMPT reason for: {unreviewed}"
    stale = sorted((set(GATED) | set(EXEMPT)) - set(EXCLUDED))
    assert not stale, f"no longer excluded, drop from this table: {stale}"


@pytest.mark.parametrize("exclusion", sorted(GATED))
def test_the_gate_is_wired_for_claude_where_the_probe_reaches_it(exclusion):
    """Registered as a Claude bash pre_tool hook, and its claude_if, if any, matches the probe."""
    hook_id, probe = GATED[exclusion]
    hook = next((h for h in POLICY.hooks_for("claude") if h["id"] == hook_id), None)
    assert hook, f"{hook_id} is not wired for claude"
    assert hook["event"] == "pre_tool" and "bash" in hook["tools"]
    rules = [CLAUDE_RULE_RE.match(rule).group(1) for rule in hook.get("claude_if", [])]
    assert not rules or any(fnmatch.fnmatchcase(probe, rule) for rule in rules), (
        f"{hook_id}'s claude_if never routes `{probe}` to it"
    )


@pytest.mark.parametrize("exclusion", sorted(GATED))
def test_the_gate_refuses_or_asks_about_its_probe(exclusion, tmp_path):
    """A gate that allows the probe covers the exclusion in name only."""
    hook_id, probe = GATED[exclusion]
    hook = next(h for h in POLICY.hooks if h["id"] == hook_id)
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("")
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": probe},
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "hooks" / hook["script"])],
        input=json.dumps(event), capture_output=True, text=True, cwd=tmp_path,
    )
    asked = result.returncode == 0 and '"ask"' in result.stdout
    assert result.returncode == 2 or asked, f"{hook_id} let `{probe}` through"
