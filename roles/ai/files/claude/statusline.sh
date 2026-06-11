#!/usr/bin/env python3
# vim: ft=python
# Filename keeps .sh extension to match the path referenced in settings.json
# (statusLine.command) and the symlink in ~/.claude. The shebang is what
# determines execution. Python is used to avoid a jq runtime dependency and to
# match the existing git-skill-gate.sh convention in this repo.
"""statusline.sh — Claude Code status line.

Reads the status-line JSON payload on stdin and prints a single line:

    📁 dotfiles (main) │ ⚡ ▓▓▓░░░░░░░ 28% │ 🤖 Opus 4.8 │ ⚡ +120/-30

Colors: the named segments (repo yellow, branch cyan, model magenta, velocity
green/red) use ANSI color indices, so they track whatever terminal theme is
active. The context bar uses a truecolor gradient tuned to the Solarized accent
palette (green → yellow → orange → red), with a gauge emoji that steps at
20 / 70 / 90 percent (🟢 → ⚡ → 🔥 → 🚨).

Every field is optional in the payload (null / missing early in a session or
right after /compact), so each is pulled defensively and dropped from the line
if unavailable. Always exits 0 with a non-empty line — a blank line or non-zero
exit blanks the status line.
"""
import json
import os
import re
import subprocess
import sys
import unicodedata

# ANSI colors (the status line renders ANSI escapes). GREEN/RED are the 16-color
# SGR codes used for velocity; the context bar uses 24-bit truecolor instead.
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"

SEP = f" {DIM}│{RESET} "
BAR_WIDTH = 10

ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def char_width(ch):
    """Rendered cell width of a single character (0, 1, or 2)."""
    o = ord(ch)
    if o == 0x200D or 0xFE00 <= o <= 0xFE0F or unicodedata.combining(ch):
        return 0  # ZWJ, variation selectors, combining marks
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    # Emoji / symbol ranges that render double-width in modern terminals.
    if (
        0x1F000 <= o <= 0x1FAFF
        or 0x2600 <= o <= 0x27BF
        or 0x2B00 <= o <= 0x2BFF
    ):
        return 2
    return 1


def display_width(s):
    """Visible width of a string, ignoring ANSI escapes."""
    return sum(char_width(ch) for ch in ANSI_RE.sub("", s))


def rgb(r, g, b):
    """24-bit truecolor foreground escape."""
    return f"\033[38;2;{r};{g};{b}m"


# Solarized accent stops for the context gauge: green → yellow → orange → red.
# Truecolor so the gradient is smooth; tuned to the palette to sit well against
# the Solarized Dark background rather than the default neon RGB endpoints.
GRADIENT_STOPS = (
    (0x85, 0x99, 0x00),  # green   #859900
    (0xB5, 0x89, 0x00),  # yellow  #b58900
    (0xCB, 0x4B, 0x16),  # orange  #cb4b16
    (0xDC, 0x32, 0x2F),  # red     #dc322f
)


def gradient(t):
    """Interpolate across the Solarized accent stops for t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    span = len(GRADIENT_STOPS) - 1
    pos = t * span
    i = min(int(pos), span - 1)
    frac = pos - i
    a, b = GRADIENT_STOPS[i], GRADIENT_STOPS[i + 1]
    return tuple(int(a[k] + (b[k] - a[k]) * frac) for k in range(3))


def context_emoji(pct):
    """Dynamic gauge emoji; steps at 20 / 70 / 90 percent."""
    if pct >= 90:
        return "🚨"
    if pct >= 70:
        return "🔥"
    if pct >= 20:
        return "⚡"
    return "🟢"


def context_segment(ctx):
    if not isinstance(ctx, dict):
        return None
    pct_raw = ctx.get("used_percentage")
    pct = int(pct_raw) if isinstance(pct_raw, (int, float)) else 0
    pct = max(0, min(100, pct))
    filled = pct * BAR_WIDTH // 100
    cells = []
    for i in range(BAR_WIDTH):
        if i < filled:
            # Each filled cell is colored by its position along the full bar,
            # so the gradient stays fixed and more of it reveals as usage grows.
            r, g, b = gradient(i / (BAR_WIDTH - 1))
            cells.append(f"{rgb(r, g, b)}▓{RESET}")
        else:
            cells.append(f"{DIM}░{RESET}")
    bar = "".join(cells)
    r, g, b = gradient(pct / 100)
    return f"{context_emoji(pct)} {bar} {rgb(r, g, b)}{pct}%{RESET}"


def git_branch(cwd):
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    branch = out.stdout.strip()
    return branch or None


def repo_segment(workspace):
    if not isinstance(workspace, dict):
        return None
    cwd = workspace.get("current_dir")
    repo = workspace.get("repo") or {}
    name = repo.get("name") if isinstance(repo, dict) else None
    if not name and cwd:
        name = os.path.basename(cwd.rstrip("/")) or None
    if not name:
        return None
    label = f"📁 {BOLD}{YELLOW}{name}{RESET}"
    branch = git_branch(cwd)
    if branch:
        label += f" ({BOLD}{CYAN}{branch}{RESET})"
    return label


def velocity_segment(cost):
    if not isinstance(cost, dict):
        return None
    added = cost.get("total_lines_added")
    removed = cost.get("total_lines_removed")
    if not isinstance(added, (int, float)) and not isinstance(removed, (int, float)):
        return None
    added = int(added) if isinstance(added, (int, float)) else 0
    removed = int(removed) if isinstance(removed, (int, float)) else 0
    return f"⚡ {GREEN}+{added}{RESET}/{RED}-{removed}{RESET}"


def model_segment(model):
    if not isinstance(model, dict):
        return None
    name = model.get("display_name")
    return f"🤖 {MAGENTA}{name}{RESET}" if name else None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    left_segments = [
        repo_segment(data.get("workspace")),
        context_segment(data.get("context_window")),
    ]
    # Model leads the right cluster so it survives right-edge truncation in
    # narrow panels (e.g. the VS Code sidebar); the velocity counter, which is
    # less critical, absorbs any clipping at the edge instead.
    right_segments = [
        model_segment(data.get("model")),
        velocity_segment(data.get("cost")),
    ]
    left = SEP.join(s for s in left_segments if s)
    right = SEP.join(s for s in right_segments if s)

    # Right-align the right group against the terminal edge when Claude Code
    # exposes the width (COLUMNS, v2.1.153+) and both groups fit on one line.
    try:
        cols = int(os.environ.get("COLUMNS", "0"))
    except ValueError:
        cols = 0
    if cols > 0 and left and right:
        gap = cols - display_width(left) - display_width(right)
        if gap >= 1:
            print(left + " " * gap + right)
            return

    # Fallback: everything left-aligned on one line. Never emit an empty line.
    print(SEP.join(s for s in (left, right) if s) or "🤖 Claude Code")


if __name__ == "__main__":
    main()
