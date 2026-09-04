"""pi's decision layer, derived from Claude's permission rules rather than written twice.

`pi-sandbox` confines what a command may touch. It does not look at what the command
is, so every `Bash(...)` rule Claude carries, every bare tool name and every `mcp__*`
entry reaches pi as nothing at all. That is 98 of Claude's 182 rules this layer carries
and pi-sandbox could not, including the ones that matter when the agent is wrong rather
than malicious: `git push --force *`, `git reset --hard *`, `rm -rf *`, `sudo *`.

`@gotgenes/pi-permission-system` is the layer that carries them. It decides and
records; the sandbox contains. Both are installed, and both read a committed file
derived from `files/claude/settings.json`, so policy is still written in exactly one
place.

`derive_permissions` below is the whole of the translation and this module is its
specification. To regenerate after changing Claude's settings:

    PYTHONPATH=lib/python python3 -c "import json,sys; sys.path.insert(0,'lib/python/tests'); \
from test_pi_permissions import derive_permissions, CLAUDE_SETTINGS, PI_PERMISSIONS; \
PI_PERMISSIONS.write_text(json.dumps(derive_permissions(json.loads(CLAUDE_SETTINGS.read_text())), indent=2)+chr(10))"

Five things about the translation that are silent if forgotten:

- **Last match wins, so order is the policy.** Claude's rules are order-free and deny
  beats allow. Within one of this package's surface maps the last matching pattern
  wins instead, so the generated file emits a fallback, then allows, then denies. Two
  live cases prove that is not theoretical: `Bash(find:*)` is allowed while `find / *`
  and `find ~ *` are denied, and `Bash(pgcli:*)` is allowed while `pgcli` and
  `pgcli *` are denied. Emitted the other way round, both come out permissive.
- **A translated allow can collide with a translated deny.** `Bash(pgcli:*)` and
  `Bash(pgcli *)` both become the pattern `pgcli *`, which is one JSON key and cannot
  hold two actions. Claude resolves it as a deny, so the colliding allow is dropped
  rather than emitted and immediately overwritten.
- **A doubled star is not a globstar here.** A single `*` already crosses path
  separators and `**` is documented as equivalent to it, so `**/.env` becomes `*/.env`
  rather than the `/**/.env` that `test_pi_sandbox.py` writes for the other layer.
  Anything under `~` keeps its tilde, which this package expands.
- **A reason is only legal inside a pattern map.** The schema takes a surface value as
  either an action string or a map of patterns, so `{"action": "deny", ...}` written
  directly against a tool name is read as a map whose patterns are `action` and
  `reason`, and the config is rejected. A wholly denied tool is therefore spelled as a
  one-entry map, `{"*": <denial>}`, which is also how the package resolves it: every
  surface evaluates its tool-level state against the `*` catch-all, with no per-kind
  branch, so the reason survives and the shape validates.
- **Writes stay silent because the sandbox already holds them.** Claude sets
  `autoAllowBashIfSandboxed`, which is the config saying in its own words: where the
  sandbox confines the action, do not also ask. pi-sandbox confines `bash`, `write` and
  `edit` to `allowWrite` and prompts outside it, so those three surfaces are `allow`
  here and the confinement stays the sandbox's job. This layer's contribution is the
  deny lists, which is the half pi never had. Turning `write`/`edit` to `ask` is the
  one-line change if literal prompt-parity is ever wanted over this reading.

One thing the translation deliberately drops: `WebFetch` and `WebSearch` are allowed
in Claude and are not pi tools, so naming them would be a rule about nothing.

What this layer recovers that `pi-sandbox` could not is the split between Claude's two
read layers, described at length in `test_pi_sandbox.py`. `~/.gitconfig` is a sandbox
`allowRead` so git can commit, and a `Read` deny so the agent cannot open it. pi-sandbox
collapses those into one list and the file becomes readable. Here the sandbox keeps the
syscall-level grant while `path_read` denies the path to any tool or bash token that
names it, so `git commit` still works and `cat ~/.gitconfig` does not.
"""

import json
import re

from dotkit.testing import CLAUDE, PI, REPO

CLAUDE_SETTINGS = CLAUDE / "settings.json"
PI_PERMISSIONS = PI / "permission-system/config.json"
PI_SETTINGS = PI / "settings.json"
AI_TASKS = REPO / "roles/ai/tasks/main.yml"

PACKAGE = "npm:@gotgenes/pi-permission-system@27.1.1"

# Reads the harness itself makes of its own installed trees, which are outside any
# project and would otherwise meet `external_directory: ask` on every session. This is
# the knob the package documents for exactly that, and none of it is user data: pi's
# own docs and examples, and the two agent payload directories this repo owns and
# symlinks into place. A project path never belongs here.
INFRASTRUCTURE_READ_PATHS = [
    "/opt/homebrew/*/@earendil-works/pi-coding-agent/*",
    "~/.pi/agent/*",
    "~/.claude/*",
]

# Tool surfaces pi gates that Claude never prompts for, listed so the universal
# fallback does not have to decide them. Claude auto-allows its read-only and
# orchestration tools in the same way.
SILENT_TOOLS = ("read", "grep", "find", "ls", "write", "edit")


def to_path_pattern(pattern):
    """Claude's globstar, in a dialect where one star already recurses.

    `*` matches any run of characters including a separator and `**` is documented as
    equivalent, so the doubled form is not a second, wider token: it is the same token
    spelled twice. Collapsing it keeps `**/.env` matching `/project/.env` while still
    refusing to match `/project/settings.env`, which a naive `*.env` would have caught.
    """
    return pattern.replace("**", "*")


def to_bash_pattern(pattern):
    """Claude's two `Bash(...)` spellings, as one command pattern.

    The allow list writes `Bash(rg:*)`, meaning `rg` with any arguments. The deny list
    is already written the way this package matches, space-separated, so it passes
    through untouched. A pattern ending in ` *` also matches the bare command, which is
    why `Bash(rg:*)` needs no second entry for a bare `rg`.
    """
    colon = re.fullmatch(r"([^:]+):\*", pattern)
    if colon:
        return f"{colon.group(1)} *"
    return pattern


def rules_for(entries, tool):
    """The inner patterns of one tool's rules, in Claude's order."""
    out = []
    for rule in entries:
        match = re.fullmatch(rf"{tool}\((.*)\)", rule)
        if match:
            out.append(match.group(1))
    return out


def bare_names(entries):
    """Rules that name a tool with no argument list, split from the `mcp__` ones."""
    tools, mcp = [], []
    for rule in entries:
        if "(" in rule:
            continue
        (mcp if rule.startswith("mcp__") else tools).append(rule)
    return tools, mcp


def denial(rule):
    """A refusal that says where it came from.

    A block whose reason is empty reads to the agent as an unexplained failure and it
    retries. Naming the Claude rule turns it into something it can report back.
    """
    return {"action": "deny", "reason": f"denied by Claude Code policy: {rule}"}


def surface(fallback, allows, denies, trailing_allows=()):
    """One surface map, in the four bands that recover deny-beats-allow.

    Fallback first so every later pattern can override it, then the allows, then the
    denies that have to beat them. `trailing_allows` is the inversion: a Claude allow
    that exists to carve an exception out of a deny, which under last-match-wins can
    only work after it.
    """
    out = {"*": fallback}
    denied = {pattern for pattern, _ in denies}
    for pattern in allows:
        if pattern not in denied:
            out[pattern] = "allow"
    for pattern, rule in denies:
        out[pattern] = denial(rule)
    for pattern in trailing_allows:
        out[pattern] = "allow"
    return out


def derive_permissions(settings):
    """Claude's `permissions` block, as this package reads it."""
    allow = settings["permissions"]["allow"]
    deny = settings["permissions"]["deny"]
    denied_tools, denied_mcp = bare_names(deny)

    policy = {
        "*": "allow",
        **{tool: "allow" for tool in SILENT_TOOLS},
        "bash": surface(
            "allow",
            [to_bash_pattern(p) for p in rules_for(allow, "Bash")],
            [(p, f"Bash({p})") for p in rules_for(deny, "Bash")],
        ),
        "path_read": surface(
            "allow",
            [],
            [(to_path_pattern(p), f"Read({p})") for p in rules_for(deny, "Read")],
        ),
        "path_write": surface(
            "allow",
            [],
            [(to_path_pattern(p), f"Edit({p})") for p in rules_for(deny, "Edit")],
            [to_path_pattern(p) for p in rules_for(allow, "Edit")],
        ),
        "external_directory": "ask",
        "mcp": surface(
            "allow",
            [],
            [(f"{name.removeprefix('mcp__')}*", name) for name in denied_mcp],
        ),
    }
    for name in denied_tools:
        policy[name] = {"*": denial(name)}

    return {
        "debugLog": False,
        "permissionReviewLog": True,
        "yoloMode": False,
        "shellTools": {},
        "authorizerChain": [],
        "piInfrastructureReadPaths": list(INFRASTRUCTURE_READ_PATHS),
        "permission": policy,
    }


def claude_settings():
    return json.loads(CLAUDE_SETTINGS.read_text())


def pi_permissions():
    return json.loads(PI_PERMISSIONS.read_text())


def policy():
    return pi_permissions()["permission"]


def action_of(entry):
    """The action of a surface value, which is either a bare string or a reasoned deny."""
    return entry["action"] if isinstance(entry, dict) else entry


def resolve(surface_map, value):
    """What this package decides for `value`, by its own last-match-wins rule."""
    verdict = None
    for pattern, entry in surface_map.items():
        regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
        if re.fullmatch(regex, value):
            verdict = action_of(entry)
    return verdict


# --- the derivation -----------------------------------------------------------


def test_the_committed_config_is_what_the_derivation_produces():
    """One statement of the policy. Editing Claude's rules alone fails here."""
    assert pi_permissions() == derive_permissions(claude_settings())


def test_every_bash_rule_claude_denies_pi_denies():
    """The 64 rules that were the whole reason to add this layer."""
    bash = policy()["bash"]
    for pattern in rules_for(claude_settings()["permissions"]["deny"], "Bash"):
        assert action_of(bash[pattern]) == "deny", f"Bash({pattern}) reaches pi ungated"


def test_the_destructive_commands_resolve_to_deny_and_not_merely_appear():
    """Presence is not enforcement: a deny a later allow shadows is a rule about nothing."""
    bash = policy()["bash"]
    for command in (
        "git push --force origin main",
        "git reset --hard HEAD~1",
        "rm -rf build",
        "sudo softwareupdate",
        "diskutil eraseDisk",
        "gh pr merge 12",
        "find / -name id_rsa",
    ):
        assert resolve(bash, command) == "deny", f"{command} is not denied"


def test_the_allowlisted_commands_stay_allowed():
    """The allow half has to survive the band ordering too, or every read command prompts."""
    bash = policy()["bash"]
    for command in ("rg pattern src", "gh pr list", "find . -name x", "bunx ctx7 library fish"):
        assert resolve(bash, command) == "allow", f"{command} is gated"


def test_a_command_claude_both_allows_and_denies_comes_out_denied():
    """`Bash(pgcli:*)` and `Bash(pgcli *)` translate to one key, and Claude's answer is deny."""
    bash = policy()["bash"]
    assert resolve(bash, "pgcli") == "deny"
    assert resolve(bash, "pgcli --dsn x") == "deny"
    assert bash["pgcli *"] != "allow"


def test_the_credential_paths_claude_hides_are_denied_to_every_tool():
    """The read-layer split pi-sandbox could not carry: denied to the agent, not to git."""
    reads = policy()["path_read"]
    for path in ("~/.ssh/id_ed25519", "~/.aws/credentials", "~/.gitconfig", "~/.zsh_history"):
        assert resolve(reads, path) == "deny", f"{path} is readable by pi"


def test_secrets_are_denied_for_write_as_well_as_read():
    """Claude denies editing what it denies reading, and both halves have to cross."""
    for path in ("/project/.env", "/project/certs/server.pem", "/project/secrets/token"):
        assert resolve(policy()["path_read"], path) == "deny", f"{path} is readable"
        assert resolve(policy()["path_write"], path) == "deny", f"{path} is writable"


def test_the_env_sample_carve_outs_survive_the_deny_band():
    """Claude allows these two by name, so under last-match-wins they come after the denies."""
    writes = policy()["path_write"]
    trailing = list(writes)[-2:]
    assert trailing == ["*/.env.sample", "*/.env.example"]
    for path in ("/project/.env.example", "/project/.env.sample"):
        assert resolve(writes, path) == "allow", f"{path} is denied and Claude allows it"


def test_no_doubled_star_reaches_the_config():
    """`**` is the same token as `*` here, so the doubled spelling is noise that reads as reach."""
    for name in ("path_read", "path_write"):
        for pattern in policy()[name]:
            assert "**" not in pattern, f"{name} carries {pattern}"


def test_no_unexpanded_variable_reaches_the_config():
    """Only `~` and `$HOME` expand, so any other `$VAR` is a rule that matches nothing."""
    rendered = PI_PERMISSIONS.read_text()
    assert "$TMPDIR" not in rendered
    assert not re.search(r"\$(?!HOME)[A-Z_]{2,}", rendered)


def test_the_denied_mcp_servers_cover_their_tools_and_not_only_the_server():
    """`mcp__notion` names a server, and denying it has to reach the tools it registers."""
    mcp = policy()["mcp"]
    for value in ("notion", "notion_search", "Supabase", "supabase_query"):
        assert resolve(mcp, value) == "deny", f"{value} is reachable"


def test_the_bare_tool_denies_reach_their_own_surface():
    """Claude names five tools with no argument list, and a tool wholly denied is hidden."""
    policy_map = policy()
    denied, _ = bare_names(claude_settings()["permissions"]["deny"])
    assert denied
    for name in denied:
        assert resolve(policy_map[name], "*") == "deny", f"{name} is reachable in pi"


def test_no_surface_states_its_action_without_a_pattern_to_hang_it_on():
    """The shape the schema rejects, which fails the whole config rather than one rule.

    A surface value is an action string or a map of patterns. An `action`/`reason`
    object written straight against a surface name is neither: it parses as a map whose
    patterns are the literal words `action` and `reason`, `reason`'s string value is not
    an action, and validation fails. A rejected global config enforces none of these
    denies, so this is the one malformation worth a test of its own.
    """
    for name, entry in policy().items():
        assert "action" not in entry, f"{name} states an action with no pattern"


def test_the_web_tools_claude_allows_are_left_out():
    """pi registers neither, so a rule naming them would be policy about nothing."""
    policy_map = policy()
    assert "WebFetch" not in policy_map
    assert "WebSearch" not in policy_map


def test_every_deny_carries_the_rule_it_came_from():
    """An unexplained block reads to the agent as a broken tool, and it retries."""
    for name, entry in policy().items():
        values = entry.values() if isinstance(entry, dict) and "action" not in entry else [entry]
        for value in values:
            if action_of(value) == "deny":
                assert value["reason"].startswith("denied by Claude Code policy: "), name


def test_writes_are_left_to_the_sandbox_rather_than_prompted_twice():
    """`autoAllowBashIfSandboxed` is Claude saying it too: where the sandbox holds, don't ask."""
    assert claude_settings()["sandbox"]["autoAllowBashIfSandboxed"] is True
    for tool in ("write", "edit", "read"):
        assert policy()[tool] == "allow"


def test_the_project_boundary_still_prompts():
    """Claude sets no additionalDirectories, so reaching outside the tree is a question."""
    assert policy()["external_directory"] == "ask"


def test_the_infrastructure_read_paths_are_the_harness_and_not_a_project():
    """This knob bypasses the boundary gate, so a project path here would be a silent grant."""
    for path in pi_permissions()["piInfrastructureReadPaths"]:
        assert path.startswith(("~/.pi", "~/.claude", "/opt/homebrew")), path


def test_yolo_mode_is_off_and_no_authorizer_can_decide_for_us():
    """Both are opt-in seams that would move the decision away from the derived policy."""
    config = pi_permissions()
    assert config["yoloMode"] is False
    assert config["authorizerChain"] == []


def test_no_shell_tool_alias_is_claimed():
    """pi-cursor-sdk registers pi's own `bash`, so the 64 bash rules already reach it."""
    assert pi_permissions()["shellTools"] == {}


# --- the wiring ---------------------------------------------------------------


def test_the_package_is_declared_in_the_packages_pi_loads():
    """The config is inert without the extension that reads it."""
    assert PACKAGE in json.loads(PI_SETTINGS.read_text())["packages"]


def test_the_package_is_pinned():
    """Four breaking releases so far have been fail-closed corrections.

    Every other entry in `packages` rides latest, which is right for a footer or an
    editor. This one decides what the shell may run, so an unattended `pi update` is
    not allowed to change it. `pi update` skips a versioned spec.

    The pin is also what `min-release-age=7` in `~/.npmrc` will install. That setting
    quarantines any version published in the last week, so a pin chosen from the
    registry's `latest` is unresolvable for seven days and `pi install` fails with
    `ETARGET`. Move this forward to a version that has aged past the window, not to
    whatever `latest` reports.
    """
    assert re.fullmatch(r"npm:@gotgenes/pi-permission-system@\d+\.\d+\.\d+", PACKAGE)


def test_the_sandbox_is_still_installed_beside_it():
    """This layer decides and records. It contains nothing, so removing the other is a loss."""
    assert "npm:pi-sandbox" in json.loads(PI_SETTINGS.read_text())["packages"]


def test_the_role_links_the_config_into_place():
    """A config in the repo that no play links is a policy nothing enforces."""
    assert "pi/permission-system/config.json" in AI_TASKS.read_text()


def test_the_config_is_parseable():
    """The package reads this as JSON and its own examples are jsonc, comments and all.

    A commented config falls back to `ask` for every category, which is a policy nobody
    chose, arrived at silently.
    """
    assert isinstance(pi_permissions(), dict)
    assert "//" not in PI_PERMISSIONS.read_text()
