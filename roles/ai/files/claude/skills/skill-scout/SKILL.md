---
name: skill-scout
description: Recommend which skills from the catalog to add to the current project, matched to its tech stack and needs. Use when the user asks which skills to add, wants skills recommended for this repo or codebase, is discovering relevant skills, or is setting up a project. Excludes skills already installed globally and dependency-only skills.
argument-hint: "[optional focus, e.g. frontend|testing]"
disable-model-invocation: true
---

# Skill Scout

Recommend which skills from the registry are worth adding to the **current
project**, then offer to install them. Work through the steps in order. An
argument narrows ranking to that area (e.g. `frontend`, `testing`); with no
argument, rank across all relevant skills.

## Step 1 — Build the candidate catalog

The catalog metadata lives in the dotfiles registry; descriptions live in each
skill's `SKILL.md`. One command emits the whole annotated catalog —
`name <TAB> groups <TAB> description` — so no per-skill reads are needed later:

```bash
test -n "$DOTFILES_DIR" || { echo "DOTFILES_DIR is not set — cannot read the skill registry."; exit 1; }
DOT="$DOTFILES_DIR/roles/ai/files/claude"; REG="$DOT/skill-registry.json"
JQLIB='def dn($r): (.upstream_path // "") as $p | if ($p == "" or $p == "." or $p == "/") then ($r | split("/")[1]) else ($p | sub("/+$";"") | split("/") | last) end; def allskills: [ (.repos | to_entries[] | .key as $r | .value.skills[] | . + {name: dn($r), repo: $r}), (.local_skills[]? | . + {repo: null}) ]; def visibleskills: allskills | map(select((.dependency_only // false) | not));'
echo "=== GLOBAL (exclude entirely) ==="; ls ~/.claude/skills 2>/dev/null
echo "=== PROJECT (mark already-linked) ==="; ls .claude/skills 2>/dev/null
echo "=== CANDIDATES: name <TAB> groups <TAB> description ==="
jq -r "$JQLIB"' visibleskills | .[] | "\(.name)\t\(.groups // [] | join(", "))"' "$REG" |
while IFS=$'\t' read -r name groups; do
  desc=$(grep -m1 '^description:' "$DOT/skills/$name/SKILL.md" 2>/dev/null | sed 's/^description:[[:space:]]*//')
  printf '%s\t%s\t%s\n' "$name" "$groups" "$desc"
done
```

`visibleskills` already drops `dependency_only` skills. From the candidate list:

- **Drop** any name that appears under `~/.claude/skills/` (installed globally —
  available everywhere already, including `skill-scout` itself).
- **Mark** any name that appears under `.claude/skills/` as already-linked. Keep
  it for the report but never offer to add it again.
- A blank description means a block-scalar frontmatter (3 skills, e.g.
  `humanizer`) — only if such a skill reaches the shortlist, read its `SKILL.md`.

Everything that survives is a **candidate**.

## Step 2 — Analyze the project

The catalog only has **tech-specific** skills for two ecosystems — JS/TS and
Swift/iOS — so the fingerprint targets exactly those, plus language-agnostic
signals. Read what exists; do not assume.

| Signal | How | Yields |
|---|---|---|
| JS/TS stack | read `package.json` (its `dependencies` + `devDependencies`) | react, tailwind, astro, nest, fastify, hono, graphql, prisma, playwright, expo, react-native, tanstack, typescript… — all in one read |
| Swift/iOS | `ls Package.swift *.xcodeproj *.xcworkspace Podfile 2>/dev/null` | swift, ios |
| Gaps (any language) | `ls -d tests test __tests__ .github/workflows docs src 2>/dev/null` | needs from absence (no tests → testing; no CI → ci) |
| Intent | read `CLAUDE.md` / `README.md` | conventions file structure won't reveal (e.g. "we follow DDD" → domain-modeling) |

`package.json` deps encode nearly every JS/TS tag, so there is no need to open
individual config files (vite/tailwind/prisma/playwright/…). Do **not** probe
`Cargo.toml`/`go.mod`/`pyproject.toml`/`Gemfile` — the catalog has no skills for
those stacks.

**No `package.json` and no Swift markers?** The project's stack isn't represented
in the catalog (Rust, Go, Python, Ruby, …). Skip tech matching and recommend the
language-agnostic skills (workflow, quality, review, testing, git, ai, planning,
marketing) inferred from the gaps + CLAUDE.md. Never return an empty report.

## Step 3 — Match & tier

Score each surviving candidate holistically against the project signals, using
its name, groups, and description — all already in the Step 1 catalog. Assign two
tiers:

- **Strong match** — direct, concrete evidence (e.g. `react` in deps, zero test
  files, a `.github/workflows/` dir, an explicit convention in CLAUDE.md).
- **Worth considering** — plausible but weaker signal.

Shortlist roughly the top 12. A focus argument, if given, promotes matching
skills and demotes the rest.

## Step 4 — Present the report

Descriptions are already in the Step 1 catalog — no extra reads. Print the
report (for a blank/block-scalar description, read that one `SKILL.md`):

```
STRONG MATCH
 1. react-best-practices      [engineering, frontend, react]
    Why:  react@19 + vite in package.json
    What: <description>
 2. test-driven-development   [quality, testing]
    Why:  src/ has 0 test files
    What: <description>

WORTH CONSIDERING
 3. tailwind-design-system    [frontend, tailwind]
    Why:  tailwind in deps, no config found
    What: <description>

ALREADY IN THIS PROJECT (skipped)
 ✓ commit  [git]
```

Every recommended line carries: number, skill name, groups, a project-specific
**Why**, and the **What** description. Already-linked skills go in their own
section and are never numbered for install.

## Step 5 — Offer to install

Offer the recommended (non-installed) skills via an AskUserQuestion
multi-select. If there are more than four, batch them across up to four questions
(four options each); anything beyond is already visible in the printed report and
can be added manually.

`claude-skill` is a **fish function**, not a binary — calling it from the Bash
tool's shell fails (`command not found`), and a bare `fish -c` loads the full
fish config (ssh-agent, etc.) and floods stderr with sandbox errors. Invoke it
with config disabled and the function file sourced, passing **all** selected
skills in one call (it resolves dependencies and links them together):

```bash
fish --no-config -c "source $DOTFILES_DIR/roles/shell/files/fish/functions/claude-skill.fish; claude-skill add <name1> <name2> ..."
```

`--no-config` skips the noisy shell startup; sourcing the file defines
`claude-skill` and its helpers; `$DOTFILES_DIR` is inherited by the subshell.
`claude-skill add` resolves transitive dependencies, downloads any missing
skill, and symlinks into `.claude/skills/` **relative to the current directory**
— run from the project root. If a chosen skill declares `dependencies`, say
"also pulls: …" before adding so the user knows what else lands.

**Verify, do not assume.** The symlink target `.claude/skills/` is often outside
the command sandbox's writable roots, so `ln` fails with "Operation not
permitted". After adding, confirm the links exist:

```bash
ls -l .claude/skills/
```

If the expected symlinks are missing (writes were denied), do **not** report
success. Tell the user the sandbox blocked it and hand them the exact command to
run themselves in this session with a leading `!` (runs unsandboxed as fish, so
the function is already available — no sourcing needed):

```
! claude-skill add <name1> <name2> ...
```

Finish with a one-line summary of what was actually linked (verified by the
`ls`), not what was attempted.

## Notes

- The `$DOTFILES_DIR` paths are an intentional host coupling (same source as the
  `claude-skill` CLI); see `SPEC.md` for the full contract and limitations.
