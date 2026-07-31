"""The /pr skill's two scripts: `context.py` gathers, `apply.py` pushes and opens.

`derive_title` and the scope rules are pure, so they are called directly. The
end-to-end cases run against a throwaway repo whose `origin` has no server behind
it, with `git push`, `gh` and `glab` stubbed on a narrowed PATH so a real remote
can never be reached. Cases assert on the scripts' own named exit codes and on
structure, never on message wording.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys

from pathlib import Path

import pytest

# Beside the subject it exercises, so it is located relatively: move the skill and
# these travel with it. dotkit.testing is for facts about the repo, not this.
SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name):
    """Import a script by path, leaving no __pycache__ inside the shipped skill."""
    cached = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location(f"pr_{name}", SCRIPTS / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = cached


context = _load("context")
apply_pr = _load("apply")

REAL_GIT = shutil.which("git")

URL = "https://example.test/o/r/pull/1"

# Delegates every subcommand except push to the real git, so the cases exercise
# real ref resolution and real diffs while the one call that would reach a server
# is recorded instead. Calls are logged as JSON so a value carrying newlines, like
# a GitLab description, survives the round trip. The shebang names the running
# interpreter rather than `env python3`: PATH is narrowed to /usr/bin here, and
# Apple's python3 shim costs about 1.8s per start.
GIT_STUB = '''#!{interpreter}
import json, os, sys

argv = sys.argv[1:]
if "push" in argv:
    with open(os.environ["PR_STUB_LOG"], "a") as log:
        log.write(json.dumps(["git"] + argv) + "\\n")
    sys.exit(int(os.environ.get("PR_STUB_PUSH_CODE", "0")))
os.execv(os.environ["PR_REAL_GIT"], [os.environ["PR_REAL_GIT"]] + argv)
'''

CLI_STUB = '''#!{interpreter}
import json, os, sys

with open(os.environ["PR_STUB_LOG"], "a") as log:
    log.write(json.dumps([os.path.basename(sys.argv[0])] + sys.argv[1:]) + "\\n")
code = int(os.environ.get("PR_STUB_CREATE_CODE", "0"))
if code:
    sys.stderr.write("refused\\n")
    sys.exit(code)
sys.stdout.write(os.environ["PR_STUB_URL"] + "\\n")
'''


def run_git(cwd, *args):
    subprocess.run(
        [REAL_GIT, "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def write(project, path, text="content\n"):
    target_path = project / path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(text)


def commit(project, message):
    run_git(project, "add", "-A")
    run_git(project, "commit", "-q", "-m", message)


def current_branch(project):
    proc = subprocess.run(
        [REAL_GIT, "branch", "--show-current"], cwd=project, capture_output=True, text=True
    )
    return proc.stdout.strip()


@pytest.fixture
def pr_repo(tmp_path):
    """A repo with `main`, a GitHub origin, and no server behind it.

    `origin/main` and `origin/HEAD` are written as local refs, which is what a
    clone leaves behind and what base detection reads.
    """
    project = tmp_path / "project"
    project.mkdir()
    run_git(project, "init", "-q", "-b", "main")
    run_git(project, "config", "user.email", "t@example.test")
    run_git(project, "config", "user.name", "Tester")
    write(project, "README.md", "# project\n")
    commit(project, "chore: init")
    run_git(project, "remote", "add", "origin", "git@github.com:owner/project.git")
    run_git(project, "update-ref", "refs/remotes/origin/main", "main")
    run_git(project, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    return project


@pytest.fixture
def stubs(tmp_path):
    """Run a script with `git push`, `gh` and `glab` stubbed on a narrowed PATH.

    Returns a callable: stubs(script, *argv, cwd=..., extra_env=...), with
    .calls() exposing what the stubs recorded.
    """
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "git").write_text(GIT_STUB.format(interpreter=sys.executable))
    for name in ("gh", "glab"):
        (bindir / name).write_text(CLI_STUB.format(interpreter=sys.executable))
    for name in ("git", "gh", "glab"):
        (bindir / name).chmod(0o755)
    log = tmp_path / "calls.log"

    def run(*argv, cwd, extra_env=None):
        env = {
            **os.environ,
            "PATH": f"{bindir}:/usr/bin:/bin",
            "PR_STUB_LOG": str(log),
            "PR_REAL_GIT": REAL_GIT,
            "PR_STUB_URL": URL,
        }
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, *argv], cwd=str(cwd), env=env, capture_output=True, text=True
        )

    def calls():
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line]

    run.calls = calls
    return run


def target(stdout):
    """The `== target ==` KEY=value block as a dict."""
    found = {}
    for line in stdout.splitlines():
        if line.startswith("=="):
            if found:
                break
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            found[key] = value
    return found


def gather(stubs, project, *argv):
    return stubs(str(SCRIPTS / "context.py"), *argv, cwd=project)


def execute(stubs, project, plan, *extra):
    return stubs(str(SCRIPTS / "apply.py"), str(plan), *extra, cwd=project)


# The three worked examples the skill documented before the derivation moved here.


def test_a_feature_branch_with_a_jira_key_becomes_a_feat_title():
    """Given a feature branch carrying a Jira key, When the title is derived, Then
    the type is feat, the scope is the package and the key is a suffix."""
    derived = context.derive_title(
        "feature/PROJ-123-add-auth", ["apps/auth/login.ts", "apps/auth/routes.ts"]
    )
    assert derived["title"] == "feat(auth): add auth (PROJ-123)"
    assert (derived["ticket"], derived["ticket_kind"]) == ("PROJ-123", "jira")
    assert derived["closes"] == ""


def test_a_github_issue_branch_keeps_the_number_out_of_the_title():
    """Given a fix branch carrying a GitHub issue, When the title is derived, Then no
    suffix appears and the body gets a Closes line.

    GitHub appends its own (#<pr-number>) on squash merge, so (#456) in the title
    would read as a PR number.
    """
    derived = context.derive_title(
        "fix/gh-456-banner-not-persisting", ["src/consent/banner.ts", "src/consent/store.ts"]
    )
    assert derived["title"] == "fix(consent): banner not persisting"
    assert derived["closes"] == "Closes #456"
    assert (derived["ticket"], derived["ticket_kind"]) == ("gh-456", "github")


def test_a_root_only_change_gets_no_scope():
    """Given a chore branch touching only a root file, When the title is derived,
    Then it carries no scope and no ticket."""
    derived = context.derive_title("chore/bump-deps", ["package.json"])
    assert derived["title"] == "chore: bump deps"
    assert (derived["scope"], derived["ticket_kind"]) == ("", "none")


def test_every_branch_type_but_feature_passes_through():
    """Given each Conventional Branch type, When the title is derived, Then only
    feature is renamed, because commitlint calls that one feat."""
    types = {
        branch_type: context.derive_title(f"{branch_type}/do-a-thing", ["README.md"])["type"]
        for branch_type in context.BRANCH_TYPES
    }
    assert types.pop("feature") == "feat"
    assert all(branch_type == commit_type for branch_type, commit_type in types.items())


def test_an_off_convention_branch_yields_no_title():
    """Given a branch that is not <type>/<slug>, When the title is derived, Then
    nothing is derived, so the skill has to stop and ask."""
    for branch in ("wip-something", "hotfix/urgent", "main"):
        derived = context.derive_title(branch, ["src/a.ts"])
        assert derived["conventional"] is False
        assert derived["title"] == ""


def test_a_lowercase_ticket_shape_is_not_mistaken_for_a_key():
    """Given a slug opening with a word and digits, When the title is derived, Then
    it stays in the slug instead of becoming a ticket."""
    derived = context.derive_title("fix/ie11-layout-shift", ["src/a.ts"])
    assert derived["ticket_kind"] == "none"
    assert derived["title"] == "fix: ie11 layout shift"


# Scope precedence: monorepo package, then shared directory, then shared area.


def test_a_monorepo_package_wins_over_a_deeper_shared_directory():
    """Given files sharing packages/<name> and a deeper directory, When the scope is
    derived, Then the package name wins."""
    assert context.derive_scope(
        ["packages/ui/src/components/Button.tsx", "packages/ui/src/components/Card.tsx"]
    ) == ("ui", [])


def test_a_shared_directory_becomes_the_scope():
    """Given files under one directory outside a monorepo root, When the scope is
    derived, Then that directory's name is the scope."""
    assert context.derive_scope(
        ["roles/ai/tasks/main.yml", "roles/ai/defaults/main.yml"]
    ) == ("ai", [])


def test_a_container_directory_is_never_the_scope():
    """Given files whose shared directory only names a container, When the scope is
    derived, Then it walks back to the nearest directory that names something."""
    assert context.derive_scope(["web/checkout/src/a.ts", "web/checkout/src/b.ts"])[0] == "checkout"
    assert context.derive_scope(["src/a.ts", "src/b.ts"])[0] == ""


def test_a_shared_filename_area_becomes_the_scope():
    """Given files in different trees sharing one path segment, When the scope is
    derived, Then that segment is the scope."""
    assert context.derive_scope(["src/auth/login.ts", "web/auth/session.ts"]) == ("auth", [])


def test_files_crossing_areas_leave_the_scope_empty():
    """Given files with nothing in common, When the scope is derived, Then it is
    empty, so the PR reads as repo-wide."""
    assert context.derive_scope(["apps/web/a.ts", "services/api/b.ts"]) == ("", [])


def test_several_shared_areas_come_back_as_candidates():
    """Given files sharing more than one segment, When the scope is derived, Then it
    stays empty and the candidates come back for the skill to ask about."""
    scope, candidates = context.derive_scope(["billing/invoice/a.ts", "invoice/billing/b.ts"])
    assert scope == ""
    assert set(candidates) == {"billing", "invoice"}


# Template discovery.


def test_the_host_template_wins_when_both_platforms_ship_one(tmp_path):
    """Given both a GitHub and a GitLab template, When one is looked up, Then each
    host finds its own."""
    write(tmp_path, ".github/pull_request_template.md", "github\n")
    write(tmp_path, ".gitlab/merge_request_templates/Default.md", "gitlab\n")
    assert context.find_template(tmp_path, "gh").read_text() == "github\n"
    assert context.find_template(tmp_path, "glab").read_text() == "gitlab\n"


def test_the_other_platform_template_is_still_found(tmp_path):
    """Given only a GitLab template, When a GitHub repo looks one up, Then it is
    found anyway rather than the PR going out bare."""
    write(tmp_path, ".gitlab/merge_request_templates/Default.md", "gitlab\n")
    assert context.find_template(tmp_path, "gh").read_text() == "gitlab\n"


def test_a_repo_with_no_template_reports_none(tmp_path):
    """Given no template anywhere, When one is looked up, Then nothing comes back."""
    assert context.find_template(tmp_path, "gh") is None


# GitLab account resolution.


def test_two_accounts_on_one_server_are_both_candidates():
    """Given two accounts whose API endpoint is the same server, When the remote
    names that server, Then both are candidates.

    glab picks by the remote's host token, so a repo cloned with the bare host
    would otherwise resolve to whichever account holds that key and 404.
    """
    accounts = [
        ("gitlab.com", "personal", "gitlab.com"),
        ("gitlab.com-work", "work", "gitlab.com"),
    ]
    assert context.glab_candidates(accounts, "gitlab.com") == [
        ("gitlab.com", "personal"),
        ("gitlab.com-work", "work"),
    ]


def test_an_unauthenticated_server_has_no_candidate():
    """Given no account for the remote's server, When candidates are resolved, Then
    there are none, so the create call drops -R."""
    accounts = [("gitlab.com", "personal", "gitlab.com")]
    assert context.glab_candidates(accounts, "gitlab.example.test") == []


@pytest.mark.parametrize(
    "remote,expected",
    [
        ("git@gitlab.com:group/project.git", ("gitlab.com", "group/project")),
        ("https://gitlab.com/group/sub/project.git", ("gitlab.com", "group/sub/project")),
        (
            "ssh://git@gitlab.example.test:2222/group/project",
            ("gitlab.example.test", "group/project"),
        ),
    ],
)
def test_a_remote_yields_its_host_and_namespace(remote, expected):
    """Given each remote URL shape, When it is parsed, Then host and namespace come
    out, because the -R value is built from them."""
    assert context.parse_remote(remote) == expected


# context.py end to end.


def test_the_base_comes_from_origin_head(stubs, pr_repo):
    """Given a repo whose origin/HEAD points at main, When context runs, Then it
    reports that base without asking the host CLI."""
    run_git(pr_repo, "switch", "-q", "-c", "feature/PROJ-7-add-widget")
    write(pr_repo, "apps/widget/index.ts")
    commit(pr_repo, "feat: widget")
    result = gather(stubs, pr_repo)
    assert result.returncode == context.EXIT_OK
    values = target(result.stdout)
    assert values["HOST"] == "gh"
    assert values["BASE"] == "main"
    assert values["BRANCH"] == "feature/PROJ-7-add-widget"
    assert values["TITLE"] == "feat(widget): add widget (PROJ-7)"
    assert values["TITLE_SOURCE"] == "derived"


def test_a_bare_argument_overrides_the_base(stubs, pr_repo):
    """Given an explicit base branch, When context runs, Then it is used instead of
    origin/HEAD."""
    run_git(pr_repo, "switch", "-q", "-c", "develop")
    write(pr_repo, "develop.txt")
    commit(pr_repo, "chore: develop")
    run_git(pr_repo, "switch", "-q", "-c", "fix/thing")
    write(pr_repo, "src/thing.ts")
    commit(pr_repo, "fix: thing")
    assert target(gather(stubs, pr_repo, "develop").stdout)["BASE"] == "develop"


def test_a_title_override_is_used_verbatim(stubs, pr_repo):
    """Given --title, When context runs, Then the title passes straight through with
    no ticket suffix appended, while the body's Closes line is still derived."""
    run_git(pr_repo, "switch", "-q", "-c", "feature/gh-99-add-thing")
    write(pr_repo, "src/thing.ts")
    commit(pr_repo, "feat: thing")
    override = "chore(build): drop the legacy bundler shim"
    values = target(gather(stubs, pr_repo, "--title", override).stdout)
    assert values["TITLE"] == override
    assert values["TITLE_SOURCE"] == "override"
    assert values["CLOSES"] == "Closes #99"


def test_a_root_lockfile_is_excluded_from_the_diff_but_kept_in_the_stat(stubs, pr_repo):
    """Given a branch touching a root lockfile, When context runs, Then the lockfile
    is in the stat and out of the diff.

    git's default pathspec matching reads `**/name` as requiring a leading
    directory, so the exclusions use the single-star form or every root-level
    lockfile lands in the drafting diff.
    """
    run_git(pr_repo, "switch", "-q", "-c", "chore/bump-deps")
    write(pr_repo, "package-lock.json", '{"lockfileVersion": 3}\n')
    write(pr_repo, "src/app.ts", "export const a = 1\n")
    commit(pr_repo, "chore: bump")
    before, _, diff = gather(stubs, pr_repo).stdout.partition("== diff (noisy paths excluded")
    assert "package-lock.json" in before
    assert "package-lock.json" not in diff
    assert "src/app.ts" in diff


def test_a_repo_without_an_origin_is_a_named_failure(stubs, tmp_path):
    """Given a repo with no origin, When context runs, Then it exits on the no-remote
    code rather than guessing a host."""
    project = tmp_path / "bare"
    project.mkdir()
    run_git(project, "init", "-q", "-b", "main")
    assert gather(stubs, project).returncode == context.EXIT_NO_REMOTE


def test_an_unsupported_forge_is_a_named_failure(stubs, pr_repo):
    """Given an origin that is neither GitHub nor GitLab, When context runs, Then it
    exits on the unsupported-host code."""
    run_git(pr_repo, "remote", "set-url", "origin", "git@bitbucket.org:owner/project.git")
    assert gather(stubs, pr_repo).returncode == context.EXIT_UNSUPPORTED_HOST


# apply.py.


@pytest.fixture
def branch_ready(pr_repo):
    run_git(pr_repo, "switch", "-q", "-c", "fix/flicker")
    write(pr_repo, "src/app.ts", "export const a = 2\n")
    commit(pr_repo, "fix: flicker")
    return pr_repo


def plan_file(project, tmp_path, **overrides):
    body = tmp_path / "body.md"
    body.write_text(overrides.pop("body", "## What\n\nA change.\n"))
    plan = {
        "host": "gh",
        "base": "main",
        "branch": current_branch(project),
        "title": "fix(app): stop the flicker",
        "body_file": str(body),
    }
    plan.update(overrides)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return path


def test_a_github_pr_is_pushed_over_https_and_then_created(stubs, branch_ready, tmp_path):
    """Given an approved plan, When apply runs, Then the push resets the credential
    chain onto the gh helper and the PR is created self-assigned.

    The rewrite exists because this machine sends GitHub over SSH globally and no
    sandboxed session can read ~/.ssh.
    """
    result = execute(stubs, branch_ready, plan_file(branch_ready, tmp_path))
    assert result.returncode == apply_pr.EXIT_OK
    assert result.stdout.strip() == f"Created: {URL}"

    push, create = stubs.calls()
    assert push == [
        "git",
        "-c",
        "url.https://github.com/.pushInsteadOf=git@github.com:",
        "-c",
        "credential.helper=",
        "-c",
        "credential.helper=!gh auth git-credential",
        "push",
        "-u",
        "origin",
        "fix/flicker",
    ]
    assert create[:3] == ["gh", "pr", "create"]
    assert create[create.index("--assignee") + 1] == "@me"
    assert create[create.index("--base") + 1] == "main"


def test_a_gitlab_mr_pins_the_account_and_carries_the_body_as_an_argument(
    stubs, branch_ready, tmp_path
):
    """Given a GitLab plan naming an account, When apply runs, Then -R pins it and
    the description travels as one argv value, because glab has no body-file flag."""
    run_git(branch_ready, "remote", "set-url", "origin", "git@gitlab.com:group/project.git")
    body = "## What\n\n```sh\necho 'a b'\n```\n"
    plan = plan_file(
        branch_ready, tmp_path, host="glab", repo="gitlab.com-work/group/project", body=body
    )
    assert execute(stubs, branch_ready, plan).returncode == apply_pr.EXIT_OK

    push, create = stubs.calls()
    assert push == ["git", "push", "-u", "origin", "fix/flicker"]
    assert create[:5] == ["glab", "mr", "create", "-R", "gitlab.com-work/group/project"]
    assert create[create.index("--description") + 1] == body
    assert "--yes" in create


def test_skip_push_opens_the_pr_against_what_is_already_pushed(stubs, branch_ready, tmp_path):
    """Given --skip-push, When apply runs, Then it creates the PR without pushing,
    which is the retry path after a push run outside the sandbox."""
    result = execute(stubs, branch_ready, plan_file(branch_ready, tmp_path), "--skip-push")
    assert result.returncode == apply_pr.EXIT_OK
    assert [call[0] for call in stubs.calls()] == ["gh"]


def test_a_failed_push_never_reaches_the_create_call(stubs, branch_ready, tmp_path):
    """Given a push that fails, When apply runs, Then it stops on the push code and
    opens nothing."""
    result = stubs(
        str(SCRIPTS / "apply.py"),
        str(plan_file(branch_ready, tmp_path)),
        cwd=branch_ready,
        extra_env={"PR_STUB_PUSH_CODE": "1"},
    )
    assert result.returncode == apply_pr.EXIT_PUSH_FAILED
    assert [call[0] for call in stubs.calls()] == ["git"]


def test_a_refused_create_is_a_named_failure(stubs, branch_ready, tmp_path):
    """Given the host CLI refuses, When apply runs, Then it exits on the create code
    and prints no Created line."""
    result = stubs(
        str(SCRIPTS / "apply.py"),
        str(plan_file(branch_ready, tmp_path)),
        cwd=branch_ready,
        extra_env={"PR_STUB_CREATE_CODE": "1"},
    )
    assert result.returncode == apply_pr.EXIT_CREATE_FAILED
    assert "Created:" not in result.stdout


def test_a_typographic_dash_in_the_title_is_blocked(stubs, branch_ready, tmp_path):
    """Given a title with an em dash, When apply runs, Then nothing is pushed.

    The hook reads dashes out of commit messages only, so a PR title would
    otherwise slip past house style on its way to the remote.
    """
    dashed = f"fix(app): stop the flicker {chr(0x2014)} finally"
    result = execute(stubs, branch_ready, plan_file(branch_ready, tmp_path, title=dashed))
    assert result.returncode == apply_pr.EXIT_BLOCKED
    assert stubs.calls() == []


def test_an_attribution_line_in_the_body_is_blocked(stubs, branch_ready, tmp_path):
    """Given a body carrying a Claude attribution line, When apply runs, Then nothing
    is pushed; settings.json owns attribution."""
    body = "## What\n\nA change.\n\nCo-Authored-By: Claude <noreply@anthropic.test>\n"
    result = execute(stubs, branch_ready, plan_file(branch_ready, tmp_path, body=body))
    assert result.returncode == apply_pr.EXIT_BLOCKED
    assert stubs.calls() == []


def test_a_branch_carrying_agent_task_state_is_never_pushed(stubs, branch_ready, tmp_path):
    """Given a commit touching .claude/tasks/, When apply runs, Then the push is
    refused: it is the last point where that state can be kept local."""
    write(branch_ready, ".claude/tasks/open.json", "{}\n")
    commit(branch_ready, "chore: state")
    result = execute(stubs, branch_ready, plan_file(branch_ready, tmp_path))
    assert result.returncode == apply_pr.EXIT_BLOCKED
    assert stubs.calls() == []


def test_a_cleartext_secret_in_the_branch_is_never_pushed(stubs, branch_ready, tmp_path):
    """Given a committed credentials file, When apply runs, Then the push is refused."""
    write(branch_ready, "config/credentials.yaml", "token: abc\n")
    commit(branch_ready, "chore: creds")
    result = execute(stubs, branch_ready, plan_file(branch_ready, tmp_path))
    assert result.returncode == apply_pr.EXIT_BLOCKED


def test_a_sample_env_file_is_not_treated_as_a_secret(stubs, branch_ready, tmp_path):
    """Given a committed .env.example, When apply runs, Then it proceeds.

    The glob that catches .env also catches the sample files a repo deliberately
    tracks, and settings.json allows editing those by name.
    """
    write(branch_ready, ".env.example", "TOKEN=\n")
    commit(branch_ready, "docs: sample env")
    result = execute(stubs, branch_ready, plan_file(branch_ready, tmp_path))
    assert result.returncode == apply_pr.EXIT_OK


@pytest.mark.parametrize(
    "overrides", [{"host": "hub"}, {"title": "  "}, {"base": ""}, {"body": "\n"}]
)
def test_an_incomplete_plan_is_a_usage_error(stubs, branch_ready, tmp_path, overrides):
    """Given a plan missing or misnaming a required field, When apply runs, Then it is
    a usage error and nothing is pushed."""
    result = execute(stubs, branch_ready, plan_file(branch_ready, tmp_path, **overrides))
    assert result.returncode == apply_pr.EXIT_USAGE
    assert stubs.calls() == []
