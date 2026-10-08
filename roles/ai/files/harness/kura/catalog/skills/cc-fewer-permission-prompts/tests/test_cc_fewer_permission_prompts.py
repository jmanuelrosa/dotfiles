"""mine.py ranks read-only calls from both transcript formats against the shared policy."""

import importlib.util
import json
from itertools import count
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mine.py"
IDS = count()

EXEC_PATTERNS = (
    "python3",
    "bash",
    "npx",
    "bunx",
    "uvx",
    "npm run",
    "make",
    "gh api",
    "docker exec",
    "sudo",
    "-exec",
)

POLICY = """
[commands]
allow = ["kubectl get *", "acli jira workitem view *"]
deny = ["sudo *", "rm -rf *"]

[tools]
allow = ["mcp__srv__read_allowed"]
deny = []

[mcp]
deny = ["blocked"]
"""


def load_mine():
    spec = importlib.util.spec_from_file_location("cc_fewer_permission_prompts_mine", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mine():
    return load_mine()


def claude_entry(*blocks):
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def claude_bash(command, call_id=None):
    return {"type": "tool_use", "id": call_id or f"toolu_{next(IDS)}", "name": "Bash",
            "input": {"command": command, "description": "x"}}


def claude_tool(name):
    return {"type": "tool_use", "id": f"toolu_{next(IDS)}", "name": name, "input": {}}


def pi_entry(*blocks):
    return {"type": "message", "id": f"e{next(IDS)}", "parentId": None,
            "message": {"role": "assistant", "content": list(blocks)}}


def pi_bash(command):
    return {"type": "toolCall", "id": f"call_{next(IDS)}", "name": "bash",
            "arguments": {"command": command}}


def pi_tool(name, arguments=None):
    return {"type": "toolCall", "id": f"call_{next(IDS)}", "name": name,
            "arguments": arguments or {}}


def write_jsonl(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))


def repeat(times, make, *args):
    return [make(*args) for _ in range(times)]


@pytest.fixture
def claude_root(tmp_path):
    root = tmp_path / "claude" / "projects"
    blocks = [
        *repeat(2, claude_bash, "brew info jq"),
        claude_bash("cd /repo && brew info ripgrep 2>/dev/null | head -5"),
        *repeat(3, claude_bash, "FOO=1 timeout 30 terraform show -json"),
        *repeat(4, claude_bash, "git status"),
        *repeat(4, claude_bash, "python3 -c 'print(1)'"),
        *repeat(4, claude_bash, "npm run build"),
        *repeat(4, claude_bash, "gh api repos/x/y"),
        *repeat(4, claude_bash, "sudo ls /root"),
        *repeat(4, claude_bash, "find . -name '*.py' -exec cat {} \\;"),
        *repeat(4, claude_bash, "make test"),
        *repeat(4, claude_bash, "npx -y cowsay hi"),
        *repeat(4, claude_bash, "docker exec box ls"),
        *repeat(4, claude_bash, "git push origin feature/x"),
        *repeat(3, claude_bash, "kubectl get pods -n web"),
        *repeat(3, claude_bash, "acli jira workitem view PROJ-1"),
        claude_bash("dig example.com"),
        *repeat(3, claude_tool, "mcp__srv__list_things"),
        *repeat(3, claude_tool, "mcp__srv__create_thing"),
        *repeat(3, claude_tool, "mcp__srv__read_allowed"),
        *repeat(3, claude_tool, "mcp__blocked__get_page"),
    ]
    write_jsonl(root / "-repo" / "session.jsonl", [claude_entry(block) for block in blocks])
    return root


@pytest.fixture
def pi_root(tmp_path):
    root = tmp_path / "pi" / "sessions"
    entries = [
        {"type": "session", "version": 3, "id": "s", "timestamp": "t", "cwd": "/repo"},
        pi_entry(pi_bash("brew info jq")),
        *(pi_entry(pi_bash("cat <<'EOF' > notes.md\nrm -rf /\nEOF\nnpm view react version"))
          for _ in range(3)),
        *(pi_entry(pi_tool("mcp__linear__list_issues")) for _ in range(3)),
        *(pi_entry(pi_tool("mcp", {"server": "slack", "tool": "slack_read_channel"}))
          for _ in range(3)),
        {"type": "message", "message": {"role": "toolResult", "toolName": "bash", "content": []}},
    ]
    write_jsonl(root / "--repo--" / "session.jsonl", entries)
    return root


@pytest.fixture
def policy(tmp_path):
    path = tmp_path / "permissions.toml"
    path.write_text(POLICY)
    return path


def run(mine, capsys, claude_root, pi_root, policy, *extra):
    code = mine.main([
        "--json",
        "--claude-projects", str(claude_root),
        "--pi-sessions", str(pi_root),
        "--policy", str(policy),
        *extra,
    ])
    assert code == 0
    return json.loads(capsys.readouterr().out)


def patterns(result):
    return [candidate["pattern"] for candidate in result["candidates"]]


def test_ranks_read_only_calls_from_both_harnesses(mine, capsys, claude_root, pi_root, policy):
    result = run(mine, capsys, claude_root, pi_root, policy)

    assert result["scanned"] == {"claude": 1, "pi": 1}
    assert patterns(result) == [
        "brew info *",
        "mcp__linear__list_issues",
        "mcp__srv__list_things",
        "npm view react version",
        "terraform show -json",
    ]
    brew = result["candidates"][0]
    assert brew["count"] == 4
    assert brew["sources"] == {"claude": 3, "pi": 1}
    assert brew["section"] == "commands.allow"
    assert result["candidates"][1]["section"] == "tools.allow"


def test_never_proposes_arbitrary_exec_or_mutation(mine, capsys, claude_root, pi_root, policy):
    result = run(mine, capsys, claude_root, pi_root, policy, "--min-count", "1", "--top", "100")

    for pattern in patterns(result):
        assert not any(pattern == p or pattern.startswith(p + " ") for p in EXEC_PATTERNS), pattern
        assert "-exec" not in pattern
    assert not any(p.startswith(("git push", "rm", "find", "cat")) for p in patterns(result))
    assert "mcp__srv__create_thing" not in patterns(result)
    exec_skipped = {entry["pattern"] for entry in result["skipped"]["arbitrary-exec"]["top"]}
    assert {"python3", "npm run", "gh api", "sudo ls", "make test", "npx", "docker exec", "find"} <= exec_skipped


def test_subtracts_what_the_policy_already_allows_or_denies(mine, capsys, claude_root, pi_root, policy):
    result = run(mine, capsys, claude_root, pi_root, policy)

    allowed = {entry["pattern"] for entry in result["skipped"]["policy-allowed"]["top"]}
    assert allowed == {"kubectl get pods -n web", "acli jira workitem view PROJ-1", "mcp__srv__read_allowed"}
    denied = {entry["pattern"] for entry in result["skipped"]["policy-denied"]["top"]}
    assert denied == {"mcp__blocked__get_page"}
    assert not {"kubectl get pods -n web", "mcp__srv__read_allowed"} & set(patterns(result))


def test_drops_what_claude_already_auto_allows(mine, capsys, claude_root, pi_root, policy):
    result = run(mine, capsys, claude_root, pi_root, policy, "--min-count", "1")

    auto = {entry["pattern"] for entry in result["skipped"]["auto-allowed"]["top"]}
    assert {"git status", "cd", "head"} <= auto
    assert "git status" not in patterns(result)


def test_thresholds_are_options(mine, capsys, claude_root, pi_root, policy):
    loose = run(mine, capsys, claude_root, pi_root, policy, "--min-count", "1")
    assert "dig *" not in patterns(loose)
    assert "dig example.com" in patterns(loose)

    strict = run(mine, capsys, claude_root, pi_root, policy, "--top", "1")
    assert patterns(strict) == ["brew info *"]
    below = {entry["pattern"] for entry in strict["skipped"]["below-threshold"]["top"]}
    assert "dig example.com" in below


def test_a_call_repeated_across_transcripts_counts_once(mine, capsys, tmp_path, pi_root, policy):
    root = tmp_path / "dupes"
    shared = [claude_entry(claude_bash("brew info jq", call_id=f"toolu_same_{n}")) for n in range(3)]
    write_jsonl(root / "a" / "session.jsonl", shared)
    write_jsonl(root / "a" / "session" / "subagents" / "resumed.jsonl", shared)

    result = run(mine, capsys, root, tmp_path / "missing", policy)

    assert result["scanned"] == {"claude": 2, "pi": 0}
    assert result["candidates"][0]["pattern"] == "brew info jq"
    assert result["candidates"][0]["count"] == 3


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("A=1 B=2 brew info jq", [("brew", "info")]),
        ("timeout -s KILL 10 kubectl get pods", [("kubectl", "get")]),
        ("env -u HOME TERM=x brew list", [("brew", "list")]),
        ("nice -n 5 brew deps x", [("brew", "deps")]),
        ("brew info a | brew info b && brew list; brew outdated", [
            ("brew", "info"), ("brew", "info"), ("brew", "list"), ("brew", "outdated"),
        ]),
        ("aws s3 ls s3://bucket 2>&1 > out.txt", [("aws", "s3", "ls")]),
        ("echo $(brew --version)", [("echo",), ("brew", "--version")]),
        ("cat <<EOF\nrm -rf /\nEOF\nbrew list", [("cat",), ("brew", "list")]),
        ("for f in a b; do brew info $f; done", [("brew", "info")]),
        ("./script.sh --list", []),
        ("echo 'unterminated", []),
    ],
)
def test_normalises_shell_to_command_and_subcommand(mine, command, expected):
    assert [key for _, key, _ in mine.shell_invocations(command)] == expected


@pytest.mark.parametrize(
    ("command", "reason"),
    [
        ("sudo brew list", "arbitrary-exec"),
        ("python3.12 -m http.server", "arbitrary-exec"),
        ("uv run pytest", "arbitrary-exec"),
        ("npm exec foo", "arbitrary-exec"),
        ("pnpm run list", "arbitrary-exec"),
        ("docker compose exec web ls", "arbitrary-exec"),
        ("kubectl exec -it pod -- sh", "arbitrary-exec"),
        ("op read op://vault/item", "sensitive"),
        ("gh auth token", "sensitive"),
        ("kubectl delete pod web", "not-read-only"),
        ("go get example.com/x", "not-read-only"),
        ("npm version patch", "not-read-only"),
        ("atuin history delete --all", "not-read-only"),
        ("kubectl get secret db -o yaml", "sensitive"),
        ("printenv", "sensitive"),
        ("env", "sensitive"),
        ("pbpaste", "sensitive"),
        ("bat --pager x file", "not-read-only"),
        ("xxd -r dump out", "not-read-only"),
        ("terraform apply", "not-read-only"),
    ],
)
def test_classifies_unsafe_commands(mine, command, reason):
    assert [found for found, _, _ in mine.shell_invocations(command)] == [reason]


@pytest.mark.parametrize(
    ("rule", "pattern", "covered"),
    [
        ("brew *", "brew info *", True),
        ("brew *", "brew", True),
        ("brew info *", "brew info jq", True),
        ("brew info *", "brew infos", False),
        ("brew info", "brew info *", False),
        ("brew info", "brew info", True),
    ],
)
def test_policy_rule_coverage(mine, rule, pattern, covered):
    assert mine.rule_covers(rule, pattern) is covered


def test_human_report_prints_through_the_shared_vocabulary(
    mine, capsys, monkeypatch, claude_root, pi_root, policy
):
    monkeypatch.setenv("NO_COLOR", "1")
    code = mine.main([
        "--claude-projects", str(claude_root),
        "--pi-sessions", str(pi_root),
        "--policy", str(policy),
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert out.splitlines()[0] == "🔎 Permission rules worth adding"
    assert "  ·  1. brew info *" in out
    assert out.rstrip().splitlines()[-1].startswith("✨ 5 candidates")


def test_missing_policy_is_a_refusal(mine, capsys, tmp_path):
    code = mine.main(["--policy", str(tmp_path / "absent.toml")])

    assert code == 1
    assert "pass --policy" in capsys.readouterr().err


def test_ignores_pi_mcp_proxy_calls(mine, capsys, claude_root, pi_root, policy):
    result = run(mine, capsys, claude_root, pi_root, policy, "--min-count", "1")

    assert not any("slack" in pattern for pattern in patterns(result))


@pytest.mark.parametrize(
    ("invocations", "pattern"),
    [
        ([("brew", "info", "jq"), ("brew", "info", "jq", "--json")], "brew info jq *"),
        ([("brew", "info"), ("brew", "info", "jq")], "brew info *"),
        ([("brew", "info", "a"), ("brew", "info", "b")], "brew info *"),
        ([("kubectl", "get", "pods", "-n", "a"), ("kubectl", "get", "pods")], "kubectl get pods *"),
        ([("kubectl", "get", "pods"), ("kubectl", "get", "svc")], None),
    ],
)
def test_narrowest_pattern_keeps_the_longest_shared_prefix(mine, invocations, pattern):
    assert mine.narrowest(invocations[0][:2], invocations) == pattern


@pytest.mark.parametrize(
    "name",
    ["mcp__gmail__mark_as_read", "mcp__x__search_and_replace", "mcp__srv__send_message",
     "mcp__srv__create_thing"],
)
def test_mutating_mcp_tools_are_not_read_only(mine, name):
    assert mine.mcp_reason(name) == "not-read-only"


def test_a_wildcard_reaching_a_denied_rule_is_dropped(mine):
    policy = {"commands_allow": [], "commands_deny": ["git stash drop *"], "tools_allow": set(),
              "tools_deny": set(), "mcp_deny": []}

    assert mine.policy_reason("shell", "git stash *", policy) == "policy-denied"
    assert mine.policy_reason("shell", "git stash list", policy) is None


def test_the_default_policy_is_the_shared_one(mine):
    assert mine.DEFAULT_POLICY.parts[-3:] == ("harness", "policy", "permissions.toml")
    assert mine.DEFAULT_POLICY.is_file()
