"""Regression tests for wt.fish worktree helper.

Static analysis tests that verify critical command sequences without requiring
real git worktrees or the user's home config.
"""

import re
from pathlib import Path

WT_FISH = Path(__file__).parent.parent / "wt.fish"


def extract_wt_add_body():
    """Extract the body of _wt_add function from wt.fish."""
    source = WT_FISH.read_text()
    match = re.search(
        r"^function _wt_add\b.*?^end$",
        source,
        re.MULTILINE | re.DOTALL,
    )
    assert match, "_wt_add function not found in wt.fish"
    return match.group(0)


def test_converge_runs_after_claude_copy():
    """The .agents/skills symlink must exist for Pi to discover project-local skills.

    After copying .claude/ from the source worktree, _wt_add must run `claude-kit
    converge --quiet` in the new worktree to create the bridge. Without this, Pi in
    a fresh `wt add` worktree cannot run project-local skills like /skill:spec-driven-development.

    The test verifies the sequence statically: `claude-kit converge` must appear after
    the `.claude/` copy block and before the lockfile install section.
    """
    body = extract_wt_add_body()

    claude_copy_pattern = re.compile(
        r"if test -d \$main_wt/\.claude\b.*?cp -R \$main_wt/\.claude \$target/.*?end",
        re.DOTALL,
    )
    claude_copy_match = claude_copy_pattern.search(body)
    assert claude_copy_match, ".claude/ copy block not found in _wt_add"
    claude_copy_end = claude_copy_match.end()

    lockfile_pattern = re.compile(r"if test -f pnpm-lock\.yaml")
    lockfile_match = lockfile_pattern.search(body)
    assert lockfile_match, "lockfile install section not found in _wt_add"
    lockfile_start = lockfile_match.start()

    between_section = body[claude_copy_end:lockfile_start]

    converge_pattern = re.compile(r"claude-kit converge\b.*--quiet")
    assert converge_pattern.search(between_section), (
        "claude-kit converge --quiet must be called after copying .claude/ and before "
        "lockfile install, to create the .agents/skills symlink that Pi needs for "
        "project-local skill discovery"
    )
