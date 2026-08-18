"""pi's permission model, derived from Claude's rather than written twice.

Claude Code carries a `sandbox` block and 180 `permissions` rules. pi ships no
permission model at all, which is why `pi-sandbox` is installed: it confines bash at
the OS level through a fork of Anthropic's own sandbox-runtime, and it applies
allow/deny lists to read, write and edit directly.

The two shapes are close but not identical, so `derive` below is the whole of the
translation and this module is its specification. `files/pi/sandbox.json` is a
committed real file (symlinked into place like every other config here, so editing it
takes effect without a play), and the test recomputes what it should contain. Editing
Claude's rules without regenerating fails here rather than leaving pi quietly running
last month's policy.

To regenerate after changing Claude's settings:

    python3 -c "import json,sys; sys.path.insert(0,'lib/python/tests'); \
from test_pi_sandbox import derive, CLAUDE_SETTINGS, PI_SANDBOX; \
PI_SANDBOX.write_text(json.dumps(derive(json.loads(CLAUDE_SETTINGS.read_text())), indent=2)+chr(10))"

Three things the translation cannot carry, verified against pi-sandbox 0.6.x and
recorded here because each is silent if forgotten:

- `excludedCommands`. Claude runs twelve CLIs outside its sandbox so they can read
  their own credential stores. pi-sandbox has no per-command exclusion, so those
  commands are confined like any other. Reads of a denied path are *prompted* rather
  than refused, so `aws` and friends still work, with a prompt. Blanket-allowing their
  credential directories would undo the `denyRead` this repo deliberately sets.
- `$TMPDIR`. Only a leading `~` is expanded, so a literal `$TMPDIR` entry would match
  nothing. `/var/folders` is what it resolves to on Darwin and stands in for it.
- Bare tool names and command patterns. `Bash(...)` deny rules describe command shape,
  which pi-sandbox does not match on: it confines what a command may touch instead.
  Those 64 rules have no counterpart here, and `pi-permissions` is the package that
  would carry them if that ever earns its keep.
"""

import json
import re

from dotkit.testing import CLAUDE, PI, REPO

CLAUDE_SETTINGS = CLAUDE / "settings.json"
PI_SANDBOX = PI / "sandbox.json"
AI_TASKS = REPO / "roles/ai/tasks/main.yml"


def to_sandbox_pattern(pattern):
    """Claude's "anywhere" prefix, made absolute.

    pi-sandbox runs any pattern containing `*` through `resolve()`, which anchors a
    relative one to the current directory. So `**/.env` would stop meaning "any .env"
    and start meaning "an .env under this project", which is a narrowing no reader of
    the Claude rule would expect. A leading slash restores the original reach.
    """
    if pattern.startswith("**/"):
        return "/" + pattern
    return pattern


def paths_denied(deny, tool):
    """The path patterns from one tool's deny rules, in order."""
    out = []
    for rule in deny:
        match = re.fullmatch(rf"{tool}\((.*)\)", rule)
        if match:
            out.append(to_sandbox_pattern(match.group(1)))
    return out


def derive(settings):
    """Claude's sandbox block plus the path half of its permissions, as pi reads them."""
    sandbox = settings["sandbox"]
    filesystem = sandbox["filesystem"]
    deny = settings["permissions"]["deny"]
    allow_write = [p for p in filesystem["allowWrite"] if not p.startswith("$")]
    return {
        "enabled": True,
        "network": {
            "allowedDomains": list(sandbox["network"]["allowedDomains"]),
            "allowLocalBinding": bool(sandbox["network"].get("allowLocalBinding", False)),
        },
        "filesystem": {
            "allowWrite": allow_write + ["/var/folders"],
            "allowRead": list(filesystem["allowRead"]),
            "denyRead": list(filesystem["denyRead"]) + paths_denied(deny, "Read"),
            "denyWrite": paths_denied(deny, "Edit"),
        },
    }


def claude_settings():
    return json.loads(CLAUDE_SETTINGS.read_text())


def pi_sandbox():
    return json.loads(PI_SANDBOX.read_text())


# --- the derivation -----------------------------------------------------------


def test_the_committed_config_is_what_the_derivation_produces():
    """One statement of the policy. Editing Claude's rules alone fails here."""
    assert pi_sandbox() == derive(claude_settings())


def test_every_network_domain_claude_allows_pi_allows():
    """A domain reachable in one harness and not the other is the drift this exists to stop."""
    claude = claude_settings()["sandbox"]["network"]["allowedDomains"]
    assert pi_sandbox()["network"]["allowedDomains"] == list(claude)


def test_the_credential_paths_claude_hides_are_hidden_from_pi():
    """The reason any of this matters: ~/.ssh and ~/.aws are not pi's to read either."""
    denied = pi_sandbox()["filesystem"]["denyRead"]
    for path in claude_settings()["sandbox"]["filesystem"]["denyRead"]:
        assert path in denied, f"{path} is denied to Claude and readable by pi"


def test_the_anywhere_patterns_survive_translation():
    """`**/.env` anchored to cwd is a rule that looks present and matches almost nothing."""
    assert to_sandbox_pattern("**/.env") == "/**/.env"
    assert to_sandbox_pattern("~/.ssh/**") == "~/.ssh/**"
    for pattern in pi_sandbox()["filesystem"]["denyWrite"]:
        assert not pattern.startswith("**/"), f"{pattern} would silently narrow to the project dir"


def test_secrets_are_denied_for_write_as_well_as_read():
    """Claude denies editing what it denies reading, and both halves have to cross."""
    fs = pi_sandbox()["filesystem"]
    for pattern in ("/**/.env", "/**/*.pem", "/**/*.key"):
        assert pattern in fs["denyRead"], f"{pattern} is readable by pi"
        assert pattern in fs["denyWrite"], f"{pattern} is writable by pi"


def test_no_unexpanded_variable_reaches_the_config():
    """Only a leading ~ is expanded, so a `$VAR` entry is a rule that matches nothing."""
    fs = pi_sandbox()["filesystem"]
    for key in ("allowWrite", "allowRead", "denyRead", "denyWrite"):
        for pattern in fs[key]:
            assert "$" not in pattern, f"{key} carries {pattern}, which pi never expands"


def test_the_darwin_temp_root_stands_in_for_tmpdir():
    """Claude writes to $TMPDIR; pi cannot read that, so the real path is named."""
    claude = claude_settings()["sandbox"]["filesystem"]["allowWrite"]
    assert any(p.startswith("$") for p in claude), "no $VAR left to stand in for"
    assert "/var/folders" in pi_sandbox()["filesystem"]["allowWrite"]


# --- the wiring ---------------------------------------------------------------


def test_pi_sandbox_is_declared_in_the_packages_pi_loads():
    """The config is inert without the extension that reads it."""
    packages = json.loads((PI / "settings.json").read_text())["packages"]
    assert "npm:pi-sandbox" in packages


def test_the_role_links_the_sandbox_config_into_place():
    """A config in the repo that no play links is a policy nothing enforces."""
    assert "pi/sandbox.json" in AI_TASKS.read_text()


def test_the_config_is_parseable():
    """pi-sandbox reads this with JSON.parse, and the README's example carries comments.

    A commented config would load as nothing at all, in the same silent way the previous
    checkout's trailing comma cost every pi setting.
    """
    assert isinstance(pi_sandbox(), dict)
    assert "//" not in PI_SANDBOX.read_text()
