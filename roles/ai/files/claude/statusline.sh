#!/usr/bin/env python3
# vim: ft=python
# Kept as .sh to match settings.json (statusLine.command) and the ~/.claude
# symlink; the shebang selects Python, which avoids a jq runtime dependency.
"""Claude Code status line: reads the payload JSON on stdin, prints two rows.

    📁 app (main) │ context [▓▓░░░░░░] 100k (19%) │ usage 5h 9% 7d 1% │ 🤖 Opus 4.8
    ⬢ node 22.4.0 │ 📦 pnpm 9.1.0 │ ⚡ +120/-30 │ v2.1.90

Every field is optional (missing early in a session), so each segment is pulled
defensively and dropped when unavailable; the script always exits 0 with a
non-empty line.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
GREEN, RED, YELLOW, MAGENTA, CYAN = (f"\033[3{n}m" for n in (2, 1, 3, 5, 6))
SEP = f" {DIM}│{RESET} "
BAR_WIDTH = 8
DEFAULT_CONTEXT_WINDOW = 200_000

def rgb(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

ACCENT_5H = rgb(0x26, 0x8B, 0xD2)    # blue   → 5-hour window
ACCENT_7D = rgb(0x6C, 0x71, 0xC4)    # violet → 7-day window
ACCENT_NODE = rgb(0x5F, 0xA0, 0x4E)  # node brand green

# Package-manager brand colors so the active one reads at a glance.
PM_COLORS = {
    "npm": rgb(0xCB, 0x38, 0x37),
    "pnpm": rgb(0xF6, 0x92, 0x20),
    "yarn": rgb(0x2C, 0x8E, 0xBB),
    "bun": rgb(0xE6, 0xC8, 0x9C),
}

# Solarized accent stops for the gauges: green → yellow → orange → red, tuned to
# sit well on a Solarized background rather than the default neon RGB endpoints.
GRADIENT_STOPS = ((0x85, 0x99, 0x00), (0xB5, 0x89, 0x00), (0xCB, 0x4B, 0x16), (0xDC, 0x32, 0x2F))


def gradient(t):
    t = max(0.0, min(1.0, t))
    span = len(GRADIENT_STOPS) - 1
    i = min(int(t * span), span - 1)
    frac = t * span - i
    a, b = GRADIENT_STOPS[i], GRADIENT_STOPS[i + 1]
    return rgb(*(int(a[k] + (b[k] - a[k]) * frac) for k in range(3)))


def gradient_bar(pct):
    filled = int(pct) * BAR_WIDTH // 100
    return "".join(
        f"{gradient(i / (BAR_WIDTH - 1))}▓{RESET}" if i < filled else f"{DIM}░{RESET}"
        for i in range(BAR_WIDTH)
    )


def clamp_pct(value):
    return max(0, min(100, int(round(value)))) if isinstance(value, (int, float)) else None


def fmt_tokens(n):
    """16700 → 16.7k, 200000 → 200k, 512 → 512."""
    if n < 1000:
        return str(int(n))
    return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"


def context_segment(ctx):
    if not isinstance(ctx, dict):
        return None
    pct = clamp_pct(ctx.get("used_percentage")) or 0
    size = ctx.get("context_window_size")
    size = int(size) if isinstance(size, (int, float)) and size else DEFAULT_CONTEXT_WINDOW
    used = _context_used_tokens(ctx, size, pct)
    tokens = f" {DIM}{fmt_tokens(used)}{RESET}" if used is not None else ""
    return f"{DIM}context{RESET} [{gradient_bar(pct)}]{tokens} {gradient(pct / 100)}({pct}%){RESET}"


def _context_used_tokens(ctx, size, pct):
    ti, to = ctx.get("total_input_tokens"), ctx.get("total_output_tokens")
    if isinstance(ti, (int, float)) or isinstance(to, (int, float)):
        return int(ti or 0) + int(to or 0)
    cur = ctx.get("current_usage")
    if isinstance(cur, dict):
        total = sum(int(v) for v in cur.values() if isinstance(v, (int, float)))
        if total:
            return total
    return int(size * pct / 100) if pct else None


def usage_segment(rate_limits):
    if not isinstance(rate_limits, dict):
        return None
    parts = []
    for key, label, accent in (("five_hour", "5h", ACCENT_5H), ("seven_day", "7d", ACCENT_7D)):
        window = rate_limits.get(key)
        pct = clamp_pct(window.get("used_percentage")) if isinstance(window, dict) else None
        if pct is not None:
            parts.append(f"{accent}{label}{RESET} {gradient(pct / 100)}{pct}%{RESET}")
    return f"{DIM}usage{RESET} " + " ".join(parts) if parts else None


def git_branch(cwd):
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


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
    return f"{label} ({BOLD}{CYAN}{branch}{RESET})" if branch else label


def velocity_segment(cost):
    if not isinstance(cost, dict):
        return None
    added, removed = cost.get("total_lines_added"), cost.get("total_lines_removed")
    if not isinstance(added, (int, float)) and not isinstance(removed, (int, float)):
        return None
    added = int(added) if isinstance(added, (int, float)) else 0
    removed = int(removed) if isinstance(removed, (int, float)) else 0
    return f"⚡ {GREEN}+{added}{RESET}/{RED}-{removed}{RESET}"


TOOL_CACHE_FILE = os.path.join(tempfile.gettempdir(), "claude-statusline-tools.json")


def tool_version(tool):
    """`<tool> --version`, cached per tool by binary path + mtime.

    The status line re-runs every turn and a spawn costs ~50ms, so a given
    binary at a fixed path (one version) is resolved at most once per install.
    """
    path = shutil.which(tool)
    if not path:
        return None
    mtime = os.path.getmtime(path) if os.path.exists(path) else 0

    cache = {}
    try:
        with open(TOOL_CACHE_FILE, encoding="utf-8") as fh:
            cache = json.load(fh)
        entry = cache.get(tool, {})
        if entry.get("path") == path and entry.get("mtime") == mtime:
            return entry.get("version") or None
    except (OSError, ValueError, AttributeError):
        cache = cache if isinstance(cache, dict) else {}

    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=1)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = out.stdout.strip().splitlines()
    token = lines[0].strip().lstrip("v").split() if lines else []
    version = token[0] if token else None
    if not version:
        return None

    cache[tool] = {"path": path, "mtime": mtime, "version": version}
    try:
        with open(TOOL_CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(cache, fh)
    except OSError:
        pass
    return version


def node_segment():
    version = tool_version("node")
    return f"⬢ {ACCENT_NODE}node {version}{RESET}" if version else None


# Lockfile → package-manager name, specific before npm.
LOCKFILES = (
    ("bun.lockb", "bun"), ("bun.lock", "bun"), ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"), ("package-lock.json", "npm"), ("npm-shrinkwrap.json", "npm"),
)
KNOWN_PMS = frozenset(name for _, name in LOCKFILES)


def detect_package_manager(cwd):
    """(name, version) for the project's package manager, walking cwd upward.

    Monorepo lockfiles live at the root, above per-package package.json files.
    package.json's `packageManager` field carries name+version with no spawn.
    """
    directory = cwd
    while directory and os.path.isdir(directory):
        found = _pm_from_package_json(directory) or _pm_from_lockfile(directory)
        if found:
            return found
        parent = os.path.dirname(directory)
        if parent == directory:
            return None
        directory = parent
    return None


def _pm_from_package_json(directory):
    try:
        with open(os.path.join(directory, "package.json"), encoding="utf-8") as fh:
            field = json.load(fh).get("packageManager")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(field, str) or "@" not in field:
        return None
    name, _, version = field.partition("@")
    if name not in KNOWN_PMS:
        return None
    return name, version.split("+")[0] or tool_version(name)  # drop corepack hash


def _pm_from_lockfile(directory):
    for fname, name in LOCKFILES:
        if os.path.exists(os.path.join(directory, fname)):
            return name, tool_version(name)
    return None


def pm_segment(workspace):
    cwd = workspace.get("current_dir") if isinstance(workspace, dict) else None
    found = detect_package_manager(cwd) if cwd else None
    if not found:
        return None
    name, version = found
    return f"📦 {PM_COLORS.get(name, ACCENT_NODE)}{name}{' ' + version if version else ''}{RESET}"


def rtk_segment():
    """RTK token-proxy toggle, mirroring the PreToolUse hook's gate.

    The hook only routes through rtk when RTK_ENABLE is set and the binary is on
    PATH, so the segment shows nothing when rtk isn't installed and on/off from
    the env var otherwise.
    """
    if not shutil.which("rtk"):
        return None
    if os.environ.get("RTK_ENABLE"):
        return f"✂️ {GREEN}rtk{RESET}"
    return f"{DIM}✂️ rtk off{RESET}"


def model_segment(model):
    name = model.get("display_name") if isinstance(model, dict) else None
    return f"🤖 {MAGENTA}{name}{RESET}" if name else None


def cc_version_segment(version):
    return f"{DIM}cc{RESET} v{version}" if isinstance(version, str) and version else None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    workspace = data.get("workspace")

    rows = (
        (  # live picture: identity, context, usage windows, model
            repo_segment(workspace),
            context_segment(data.get("context_window")),
            usage_segment(data.get("rate_limits")),
            model_segment(data.get("model")),
            rtk_segment(),
        ),
        (  # toolchain: node, package manager, edit velocity, rtk, CC version
            node_segment(),
            pm_segment(workspace),
            velocity_segment(data.get("cost")),
            cc_version_segment(data.get("version")),
        ),
    )
    lines = [SEP.join(s for s in row if s) for row in rows]
    print("\n".join(line for line in lines if line) or "🤖 Claude Code")

if __name__ == "__main__":
    main()
