"""pi's permission model, derived from Claude's rather than written twice.

Claude Code carries a `sandbox` block and 180 `permissions` rules. pi ships no
permission model at all, which is why `pi-sandbox` is installed: it confines bash at
the OS level through a fork of Anthropic's own sandbox-runtime, and it applies
allow/deny lists to read, write and edit directly.

The two shapes are close but not identical, so `harnessgen.emit_pi.sandbox` is the
whole of the translation and this module is its specification. `files/pi/sandbox.json` is a
committed real file (symlinked into place like every other config here, so editing it
takes effect without a play), and the test recomputes what it should contain. Editing
Claude's rules without regenerating fails here rather than leaving pi quietly running
last month's policy.

`make harness` regenerates it from policy/, and `make harness-check` names the drift.

Four things the translation cannot carry, verified against pi-sandbox 0.6.5 and the
@carderne/sandbox-runtime it forks, recorded here because each is silent if forgotten:

- `excludedCommands`. Claude runs fourteen entries outside its sandbox: twelve CLIs so
  they can read their own credential stores, plus `bunx ctx7` and `npx -y ctx7`, which
  need it for network egress rather than for credentials. pi-sandbox has no per-command
  exclusion, so those commands are confined like any other. Reads of a denied path are
  *prompted* rather than refused, so `aws` and friends still work, with a prompt.
  ctx7 is the one that does not degrade gracefully: a blocked request is not a prompt,
  it is a causeless `fetch failed`, so under pi a docs question falls back to search.
  Blanket-allowing their credential directories would undo the `denyRead` this repo
  deliberately sets.
- `$TMPDIR`. Only a leading `~` is expanded, so a literal `$TMPDIR` entry would match
  nothing. `/var/folders` is what it resolves to on Darwin and stands in for it.
- Bare tool names and command patterns. `Bash(...)` deny rules describe command shape,
  which pi-sandbox does not match on: it confines what a command may touch instead.
  Those 64 rules, the five bare tool names and the four `mcp__*` entries are carried by
  the decision layer beside this one, specified in `test_pi_permissions.py`.
- The split between Claude's two read layers. Claude keeps them apart by subject:
  `sandbox.filesystem` governs bash subprocesses, so git and ssh are handed the few
  files they need, while `permissions.deny` governs the Read tool. pi has one
  `filesystem` block and reads it twice, with different rules each time, so the split
  cannot survive: `allowRead` explicitly *takes precedence over* `denyRead` for bash
  (the runtime's own schema calls it re-allowing within a denied region), and the read
  tool at `extension.ts` never consults `denyRead` at all, prompting for anything
  outside `allowRead`. Two consequences, both pinned by tests below rather than left to
  be discovered. Claude's bash carve-outs are also read-tool grants, which is why
  `~/.gitconfig` and `~/.ssh/known_hosts` are readable in pi and denied in Claude; the
  ssh *keys* beside them are not, since nothing re-allows them. And every other `Read`
  deny degrades from a refusal to a prompt, which is the same trade `excludedCommands`
  already makes and the reason none of this is a substitute for the deny list. The
  system CA bundle is a third carve-out: its `.pem` suffix matches the secret-file deny,
  but HTTPS subprocesses need this public trust store to verify remote certificates.
  Both consequences are undone a layer up: `path_read` in `test_pi_permissions.py`
  refuses those paths to any tool or bash token that names one, while the syscall-level
  grant here keeps working for the subprocess that needs it. The tests below still pin
  what *this* file does, because that is what the layer above is composing with.
"""

import json
import re

from dotkit.testing import CLAUDE_SETTINGS, PI, REPO, harness_links
from harnessgen import emit_pi, manifest
from harnessgen.emit_pi import SANDBOX, to_sandbox_pattern

PI_SANDBOX = manifest.find_root(PI) / SANDBOX


def covers(pattern, path):
    """Whether pi-sandbox's `matchesPattern` reads `pattern` as covering `path`.

    A `*` anywhere makes the whole pattern a regex; otherwise it is an exact match or a
    path prefix. Mirrored here rather than imported because the point is to assert what
    the other side does with what this file writes.
    """
    if "*" in pattern:
        return re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), path) is not None
    return path == pattern or path.startswith(pattern.rstrip("/") + "/")


def claude_settings():
    return json.loads(CLAUDE_SETTINGS.read_text())


def pi_sandbox():
    return json.loads(PI_SANDBOX.read_text())


# --- the derivation -----------------------------------------------------------


def test_the_committed_config_is_what_the_derivation_produces():
    """One statement of the policy, in policy/. A hand edit to the rendered file fails here."""
    assert pi_sandbox() == emit_pi.sandbox(manifest.load())


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


def test_the_system_ca_bundle_is_readable_but_not_writable():
    """HTTPS needs the public trust store without making certificate files editable."""
    fs = pi_sandbox()["filesystem"]
    ca_bundle = "/etc/ssl/cert.pem"
    assert ca_bundle in fs["allowRead"]
    assert any(covers(pattern, ca_bundle) for pattern in fs["denyWrite"])


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
    assert harness_links()["~/.pi/agent/sandbox.json"] == PI / "sandbox.json"


def test_the_config_is_parseable():
    """pi-sandbox reads this with JSON.parse, and the README's example carries comments.

    A commented config would load as nothing at all, in the same silent way the previous
    checkout's trailing comma cost every pi setting.
    """
    assert isinstance(pi_sandbox(), dict)
    assert "//" not in PI_SANDBOX.read_text()


def test_no_pattern_is_listed_twice():
    """A derived file carrying an obvious repeat reads as an oversight nobody dares touch."""
    fs = pi_sandbox()["filesystem"]
    for key in ("allowWrite", "allowRead", "denyRead", "denyWrite"):
        assert len(fs[key]) == len(set(fs[key])), f"{key} repeats a pattern"


def test_the_read_carve_outs_are_exactly_the_files_bash_cannot_work_without():
    """The one place Claude's policy is knowingly loosened, held to three files.

    `allowRead` beats `denyRead` for bash and is the only list the read tool consults, so
    anything named there is readable by the agent as well as by git. That is the whole
    reason to keep the list to what a subprocess genuinely cannot work without: git needs
    an identity to commit, ssh needs known_hosts to verify a host, and HTTPS needs the
    public system CA bundle to verify a server. None is a credential. A fourth entry is a
    permission grant, so it fails until somebody writes down why.
    """
    fs = pi_sandbox()["filesystem"]
    granted = [p for p in fs["allowRead"] if any(covers(d, p) for d in fs["denyRead"])]
    assert sorted(granted) == ["/etc/ssl/cert.pem", "~/.gitconfig", "~/.ssh/known_hosts"]


def test_the_ssh_keys_are_not_re_allowed_by_the_known_hosts_carve_out():
    """The carve-out has to be the file, never the directory, or it hands over every key."""
    fs = pi_sandbox()["filesystem"]
    for key in ("~/.ssh/id_ed25519", "~/.ssh/id_rsa"):
        assert not any(covers(allowed, key) for allowed in fs["allowRead"]), f"{key} is re-allowed"
        assert any(covers(denied, key) for denied in fs["denyRead"]), f"{key} is not denied"
