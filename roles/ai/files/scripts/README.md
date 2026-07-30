# claude-kit

Installs and maintains the Claude Code artifacts stored in this repo: **skills**, **agents**
and **plugins**. Installing means symlinking one into `~/.claude/` or into a project's
`.claude/`, so editing the source in this repo takes effect immediately everywhere it is
linked, with no re-install.

- **Executable:** [`claude-kit`](claude-kit), a shim the `ai` role symlinks into `~/.local/bin/`
- **Logic:** [`claude_kit/`](claude_kit/), a stdlib-only Python package beside the shim
- **Tests:** [`claude_kit/tests/`](claude_kit/tests/), run with `make test`

The split is deliberate. An extensionless executable cannot be imported, so keeping the code in
a package is what lets the tests call functions directly instead of paying a subprocess per
assertion.

The shim and the package have to stay siblings: the shim puts its own resolved directory on
`sys.path`, which is what keeps the import working for an interpreter started with the implicit
`sys.path[0]` suppressed (`PYTHONSAFEPATH`, `-P`, `-I`). The `ai` role's glob only picks up files,
so a package directory can sit here without landing on `PATH`.

---

## The three artifact types

| Type | Stored in the repo at | Installs to | Notes |
|---|---|---|---|
| `skill` | `claude/skills/<name>/` | `.claude/skills/<name>` | Tracked in `skill-registry.json` |
| `agent` | `claude/agents/<name>.md` | `.claude/agents/<name>.md` | Tracked in `agent-registry.json` |
| `plugin` | `claude/plugins/<name>/` | `.claude/skills/<name>` | No registry row; its `plugin.json` is the metadata |

A plugin installs into the **skills** leaf because Claude Code loads it as `<name>@skills-dir`.
That means a skill and a plugin can occupy the same path, which is why nothing in this tool
identifies a link by its filename alone.

## `--type` is required

Every command except `doctor` and `adopt` requires `--type skill|agent|plugin`. Nothing is
inferred from a name, so the three namespaces are allowed to overlap and a collision is a
`doctor` note rather than an error. Those two take `--type` as an optional filter, because their
result spans all three types: `doctor`'s cross-type checks cannot run inside a single type, and
one `claude-kit.json` holds all three.

## Scope: the `global` tag decides, not your shell

An artifact tagged `global` in its registry belongs in `~/.claude` and loads in every project.
Everything else belongs in one project. **Your working directory never changes which scope an
artifact belongs to.** It only decides *which* project is meant.

**A project is any directory.** There is no detection and no git: run the command where you want
the artifact and that is where it lands, in `<cwd>/.claude/`. A subdirectory is its own project,
not a window onto the repo above it, so `add` from `api/src/handlers` writes
`api/src/handlers/.claude/`. The flip side is that a mistyped cwd creates a stray `.claude/` there
rather than being refused; `claude-kit doctor` is what finds those.

`$HOME` is the one directory that cannot be a project, and not as leftover detection. Its
`.claude` **is** `~/.claude`, so a project-scoped install there would be a global one without
saying so, would load in every repo, and would be deleted by the `ai` role the next time it
prunes `~/.claude/skills`. Use `--global` to write there deliberately.

Membership is the tag **plus one level of declared dependencies**, which is why `grilling`,
`jira`, `domain-modeling`, `documentation-and-adrs` and `planning-and-task-breakdown` are global
without carrying the tag themselves. To check rather than guess, use
`claude-kit list --type skill --group`, which prints `(global)` on every such entry. The flat
listing does not, for the reason given under `list` below.

`update` and `outdated` sit outside all of this. They rewrite the skill sources in this repo and
touch no install, so neither scope applies and neither accepts `--global`.

---

## Commands

The two families above are how `claude-kit -h` groups its listing:

| Family | Commands | Acts on |
|---|---|---|
| Scope-aware | `add`, `remove`, `list`, `doctor`, `adopt` | a project's `.claude/`, or `~/.claude` with `--global` |
| Registry-wide | `update`, `outdated` | this repo's skill sources against upstream |

Each command's own `--help` repeats its scope in one sentence, so `claude-kit add --help` says
where an install lands without a trip back here.

The help is painted in the same palette as the commands: **bold** for a section heading, cyan for
a command or flag name, dim for the closing hint, magenta `✗` for a refusal. Python 3.14 colours
argparse itself, in its own theme, and that is switched off rather than layered under this one.
Every hook paints text argparse has already measured, so stripping the escapes gives back the
plain help byte for byte, which is what a test asserts.

### `list`

```
claude-kit list --type {skill,agent,plugin} [--group [TAG]]
```

Read-only, and the only command that never refuses: in `$HOME` it reports global state and says
so.

**The layout, colours and markers match `claude-skill list` byte for byte**, so the two read
identically side by side. A test runs both and diffs their output, so neither can drift.

| Flag | Meaning |
|---|---|
| `--group` | With no value, group the listing by tag, as `claude-skill list --group` does |
| `--group TAG` | Show only entries carrying that tag. A claude-kit addition; tags are opaque, so any value in the registry works |

Bare `--group` is also how you find a tag worth passing to `add --group` or `remove --group`.

Markers: `✓ (linked)` in green is installed, `·` dim is available, and a dim
`↓ name (not downloaded)` is registered but not yet fetched. Suffixes follow in a fixed order:
`[groups]` in cyan, then `(needs: ...)`, then `(installed for <parent>)`.

```
$ claude-kit list --type skill
🧩 Available skills:
  · cc-review [ai, claude, global, prompt engineering] (needs: skill-writer)
  ✓ coderabbit (linked) [productivity, review, workflow]
  ✓ context-engineering (linked) [ai, claude, prompt engineering] (installed for spec-driven-development)
  · grill-me [global, idea-refinement, planning, pm, product] (needs: grilling)
  ✓ spec-driven-development (linked) [planning, pm, product] (needs: context-engineering, incremental-implementation, planning-and-task-breakdown, test-driven-development)

✨ 65 skills, 4 installed
```

Two additions over `claude-skill`, both below or after the shared template:
`(installed for <parent>)`, which comes from provenance that `claude-skill` does not track, and
the trailing count.

Grouped by tag:

```
$ claude-kit list --type skill --group
📚 Available groups:
  ai:
    · agent-audit (global)
    · cc-review (global) (needs: skill-writer)
    · claude-code-analyzer
  engineering:
    ...
```

Dependency-only skills are hidden, because they cannot be added directly.

Colour is emitted only when stdout is a terminal, so piping to a file or into `grep` gives plain
text. `NO_COLOR` disables it and `FORCE_COLOR` forces it on, with `NO_COLOR` winning.
`claude-skill` follows the same rule, through `_ui color`, so the two agree here too.

**Note the flat view shows no scope marker**, matching `claude-skill`. A skill that is global
only because something global depends on it (`jira`, `documentation-and-adrs`,
`planning-and-task-breakdown`) carries no `global` tag, so nothing in the flat list says so, and
`add` refusing it can look surprising. `--group` does show `(global)`, and `doctor` reports scope
directly.

### `add`

```
claude-kit add NAME [NAME ...] --type {skill,agent,plugin} [--global]
claude-kit add --group TAG --type {skill,agent,plugin} [--global]
```

| Flag | Meaning |
|---|---|
| `--global` | Install into `~/.claude`. **Required** for any artifact that belongs there |
| `--group TAG` | Install every artifact tagged `TAG` instead of naming them. Takes no names of its own |

Dependencies install automatically, each into **its own** scope, transitively. The named
artifact is linked last, so an interrupted run never leaves a parent whose dependencies are
missing.

```
$ claude-kit add spec-driven-development --type skill
✓ Linked 'planning-and-task-breakdown' into ~/.claude/skills  (required by spec-driven-development)
✓ Linked 'incremental-implementation' into ./.claude/skills  (required by spec-driven-development)
✓ Linked 'context-engineering' into ./.claude/skills  (required by spec-driven-development)
✓ Linked 'spec-driven-development' into ./.claude/skills
```

One project-scoped skill, one global dependency, three project ones. No `--global` was needed
for the global dependency: consenting to the parent consents to what it needs.

`--group TAG` installs a whole tag. Most tags straddle both scopes, so **`--global` picks which
half to act on**: without it only the project members install, with it only the global ones. The
other half is named in an aside rather than refused, and nothing reaches `~/.claude` without the
flag. Members are recorded as installed **directly**, exactly as if they had been named, so a
later `remove` cascades their dependencies rather than their own links.

```
$ claude-kit add --group planning --type skill
✓ Linked 'idea-refine' into ./.claude/skills
✓ Linked 'planning-and-task-breakdown' into ~/.claude/skills  (required by spec-driven-development)
✓ Linked 'incremental-implementation' into ./.claude/skills  (required by spec-driven-development)
✓ Linked 'test-driven-development' into ./.claude/skills  (required by spec-driven-development)
✓ Linked 'context-engineering' into ./.claude/skills  (required by spec-driven-development)
✓ Linked 'spec-driven-development' into ./.claude/skills
  The global half of 'planning' is untouched: grill-me, grill-with-docs, planning-and-task-breakdown
  Install that half with: claude-kit add --type skill --group planning --global
✨ Linked 2 of 5 skills tagged 'planning'
```

Two members, six links: dependencies still resolve their own scope, which is why
`planning-and-task-breakdown` lands in `~/.claude` while the members beside it in the skipped
half do not. Re-running is a no-op that exits `OK`: a tag is a set to converge on, so an
already-installed member is an aside rather than an `ALREADY` refusal.

### `remove`

```
claude-kit remove NAME [NAME ...] --type {skill,agent,plugin} [--global] [--no-cascade]
claude-kit remove --group TAG --type {skill,agent,plugin} [--global] [--no-cascade]
```

| Flag | Meaning |
|---|---|
| `--global` | Act on `~/.claude` rather than the project |
| `--no-cascade` | Remove only what is named, leaving its dependencies in place |
| `--group TAG` | Act on every artifact tagged `TAG` instead of naming them. Takes no names of its own |

Unlinks, then cascades: dependencies that arrived *for* the named artifact and that nothing else
still needs go too. The cascade never leaves the project it started in.

```
$ claude-kit remove spec-driven-development --type skill
✓ Unlinked 'spec-driven-development' from ./.claude/skills
✓ Unlinked 'context-engineering' too; nothing installed needs it now
✓ Unlinked 'incremental-implementation' too; nothing installed needs it now
  Kept 'test-driven-development': installed directly
```

`--group TAG` acts on the members **linked in the selected scope**, and consults no global tag to
decide: `--global` alone says where "here" is, for the same reason a removal never leaves the
scope it starts in. A member that is not installed is listed in an aside, not refused, so
removing a tag twice exits `OK`. The cascade runs per member and recomputes what is still needed
each time, so a dependency two members share survives the first and goes with the second.

```
$ claude-kit remove --group planning --type skill
✓ Unlinked 'idea-refine' from ./.claude/skills
✓ Unlinked 'spec-driven-development' from ./.claude/skills
✓ Unlinked 'context-engineering' too; nothing installed needs it now
✓ Unlinked 'incremental-implementation' too; nothing installed needs it now
✓ Unlinked 'test-driven-development' too; nothing installed needs it now
  Not linked in this project: grill-me, grill-with-docs, planning-and-task-breakdown
✨ Removed 2 of 5 skills tagged 'planning'
```

### `update` and `outdated` (skills only)

```
claude-kit update   [NAME ...] --type skill
claude-kit outdated [NAME ...] --type skill
```

With no names, every tracked skill. `update` syncs from upstream GitHub tarballs and stamps
`updated_at`; `outdated` is the same traversal with writes switched off, so its report always
predicts what a sync would do.

These update the **sources in this repo**, not your installs. Since installs are symlinks, every
project already pointing at a skill sees the new content immediately.

Only skills have upstreams: `agent-registry.json` has no repos and plugins are authored here.
Naming a locally authored skill says so and exits `0`; a bare run just leaves them out.

Output matches `claude-skill update` / `claude-skill outdated` line for line: a bold header, a cyan
rule per repo, one row per skill (`⟳` behind in red, `✓` up to date in green, `↓` not downloaded in
yellow, `✗` failed in magenta, blue for anything `update` wrote) and a bold `Done:` tally. An
unreachable repo prints one `✗ FAILED to fetch` line and the run continues with the next.

### `doctor`

```
claude-kit doctor [--type {skill,agent,plugin}]
```

Reports drift and never refuses. Findings are **problems** (something is wrong, exits `9`) or
**notes** (legal, worth seeing, exits `0`).

Checks: broken symlinks, registry entries missing from disk, files on disk in no registry,
dependency edges naming nothing, orphaned `dependency_only` skills, plugin manifests missing
keys or using the reserved `dependencies` key, malformed YAML frontmatter, names used by more
than one type, artifacts linked in the wrong scope, and stale, untracked or now-removable
provenance records.

### `adopt`

```
claude-kit adopt [--type {skill,agent,plugin}] [--dry-run]
```

| Flag | Meaning |
|---|---|
| `--dry-run` | Show what would be recorded without writing anything |

Rebuilds a missing `claude-kit.json` from the links already in the project. Use it after cloning
a repo that ships a `.claude/` but no manifest, or in a project set up by the older
`claude-skill` / `claude-agent` fish functions, which never wrote one. Writes the manifest and
**nothing else**: no symlink is created, moved or deleted.

An installed skill that some other installed artifact declares as a dependency is recorded
`dep-of:<parent>`; everything else is recorded `direct`. That reproduces what a clean
`add <parent>` would have written, which is what usually did happen. What cannot be recovered is
whether such a skill was *also* named directly at some point, so if you want one protected from a
future cascade, `add` it again afterwards and it is promoted to `direct`.

Idempotent and additive: an artifact already in the manifest is left exactly as it is, so a
re-run tops up a partial file and can never demote a `direct` record to a dependency.

```
$ claude-kit adopt --dry-run
📋 Would record in ~/work/api/.claude/claude-kit.json:
  plugin 'backend'                    direct
  skill 'context-engineering'         dep-of:spec-driven-development
  skill 'incremental-implementation'  dep-of:spec-driven-development
  skill 'spec-driven-development'     direct

1 plugin(s), 3 skill(s).
Nothing written (--dry-run).
```

Exits `6` in `$HOME`: `~/.claude` carries no provenance, because a global dependency never
cascades and so nothing needs to know why one is there.

---

## Exit codes

Distinct so scripts can branch without matching message text.

| Code | Name | Meaning |
|---|---|---|
| 0 | `OK` | success |
| 1 | `USAGE` | missing or invalid `--type`, bad flags, an unsupported combination |
| 2 | `NOT_FOUND` | no artifact of that type by that name, or registered but absent on disk |
| 3 | `DEPENDENCY_ONLY` | named a skill that exists only to satisfy another |
| 4 | `WRONG_SCOPE` | a global artifact named without `--global` |
| 5 | `ALREADY` | already installed at the resolved target |
| 6 | `NO_PROJECT` | project-scoped, but cwd is `$HOME`, the one directory that is not a project |
| 7 | `NOT_INSTALLED` | `remove` target absent |
| 8 | `FETCH_FAILED` | `update` / `outdated` could not reach or read an upstream |
| 9 | `DRIFT` | `doctor` found at least one problem |

## Environment

| Variable | Effect |
|---|---|
| `HOME` | Where `~/.claude` is. The tool reads the environment rather than the password database, so overriding it fully redirects a run |
| `DOTFILES_DIR` | Which checkout to read artifacts from. Defaults to walking up from the script for a `dotfiles.yml` marker |
| `NO_COLOR` | Any non-empty value switches escape codes off everywhere, and wins over `FORCE_COLOR` |
| `FORCE_COLOR` | Any non-empty value keeps colour on when stdout is not a terminal, which is how the tests capture a coloured run |

The first two are the only inputs that change what a run *does*, which is what makes a test run
hermetic; the colour pair only changes how it looks.

---

## Output style

Every line these commands print comes from `claude_kit/ui.py`, the shared vocabulary: `title`
(bold heading), `step` (cyan `→`), `ok` (green `✓`), `warn` (yellow `⚠`), `err` (magenta `✗`, on
stderr), `item` (dim `·`), `note` (dim aside) and `done` (`✨` summary). `ui.render(kind, text)`
returns the string instead of printing it, which is how `doctor` feeds its report through a
caller-supplied emitter.

`_ui.fish` in the `shell` role is the same vocabulary for fish, and a differential test renders
every kind through both and compares the bytes. **A topic emoji only ever appears on a `title` or
a `done`**: emoji are double-width, so one used as a row marker would break the suffix columns in
`list`. `weekly-recap`, beside this script, imports the same module.

---

## Examples

**Install a project skill. It lands where you are.**

```console
$ cd ~/work/api
$ claude-kit add coderabbit --type skill
✓ Linked 'coderabbit' into ~/work/api/.claude/skills
```

cwd is the project, so `cd` to the directory you want the skill in. From
`~/work/api/src/handlers` the same command writes `src/handlers/.claude/skills` instead. No git
repo is needed anywhere.

**Install something global.**

```console
$ claude-kit add commit --type skill
✗ 'commit' carries the global tag, so it belongs in ~/.claude.
  Run: claude-kit add commit --type skill --global

$ claude-kit add commit --type skill --global
✓ Linked 'commit' into /Users/you/.claude/skills
```

**Install a plugin and its vendored skill.**

```console
$ claude-kit add product-team --type plugin
✓ Linked 'idea-refine' into ./.claude/skills  (required by product-team)
✓ Linked 'product-team' into ./.claude/skills
  Restart Claude Code from the project root to load 'product-team@skills-dir'; the workspace must be trusted.
```

**Batch install; one bad name does not strand the rest.**

```console
$ claude-kit add coderabbit no-such-thing frontend-design --type skill
✓ Linked 'coderabbit' into ./.claude/skills
✗ 'no-such-thing' is not a known skill.
✓ Linked 'frontend-design' into ./.claude/skills
$ echo $status
2
```

**Set up a repo from a tag, then take it back out.**

```console
$ claude-kit list --type skill --group          # which tags exist
📚 Available groups:
  frontend:
    ...
$ claude-kit add --group frontend --type skill
✓ Linked 'apollo-client' into ./.claude/skills
...
✨ Linked 18 of 18 skills tagged 'frontend'
$ claude-kit add --group frontend --type skill  # idempotent
  Already installed: 18 skills
✨ Linked 0 of 18 skills tagged 'frontend'
$ echo $status
0
$ claude-kit remove --group frontend --type skill
...
✨ Removed 18 of 18 skills tagged 'frontend'
```

**Protect a dependency from a future cascade.**

```console
$ claude-kit add spec-driven-development --type skill    # pulls in test-driven-development
$ claude-kit add test-driven-development --type skill
✓ 'test-driven-development' was already installed as a dependency and is now marked as
  wanted in its own right; removing its parent will keep it.
```

**Find what a `--no-cascade` removal left behind.**

```console
$ claude-kit remove spec-driven-development --type skill --no-cascade
$ claude-kit doctor --type skill
📝 Notes:
  skill 'context-engineering': installed for spec-driven-development, which nothing installed
    needs now. Remove with: claude-kit remove context-engineering --type skill  [removable]

✨ 0 problem(s), 3 note(s) across skills
```

**Take over a cloned repo that has links but no manifest.**

```console
$ git clone git@github.com:us/api.git && cd api
$ claude-kit doctor --type skill
📝 Notes:
  skill 'context-engineering': linked but not recorded, so the cascade will keep it rather than
    guess. Run: claude-kit adopt  [untracked-install]

✨ 0 problem(s), 2 note(s) across skills

$ claude-kit adopt
📋 Recorded in ~/api/.claude/claude-kit.json:
  skill 'context-engineering'      dep-of:spec-driven-development
  skill 'spec-driven-development'  direct

✨ 2 skill(s).
```

`remove spec-driven-development --type skill` now cascades `context-engineering`. Before adopting
it would have kept it, because an unrecorded link is one the cascade refuses to guess about.

**Check upstream without writing anything.**

```console
$ claude-kit outdated --type skill
🔎 Checking 1 repo(s) for updates...

── anthropics/skills (main) ──
  ✓ commit: up to date (last synced 2026-07-25)
  ⟳ frontend-design: behind (last synced 2026-07-25)

✨ Done: 1 behind, 1 up-to-date, 0 not downloaded, 0 failed

$ claude-kit update --type skill frontend-design
```

**Use in a script.**

```fish
if claude-kit doctor >/dev/null
    echo "artifacts are healthy"
else
    claude-kit doctor   # exits 9, so show the detail
end
```

---

## FAQ and corner cases

**Why does `add commit --type skill` fail when `commit` clearly exists?**
Because it is global. Writing into `~/.claude` affects every project, so the flag makes that
explicit at the call site. Exit `4`, and the message contains the exact corrected command.

**A dependency landed in `~/.claude` and I never passed `--global`. Is that a bug?**
No. Dependencies resolve their own scope, so a project skill may depend on a global one.
`spec-driven-development` is the live example: project-scoped, with
`planning-and-task-breakdown` global. The `--global` confirmation governs artifacts *you name*,
not what they pull in; otherwise adding one skill would mean consenting to each dependency's
scope separately.

**Why won't `remove` clean up the global dependency it installed?**
Because it cannot know whether another project still needs it. claude-kit standing in
`~/work/api` cannot see `~/work/web`. Deleting a shared global link would silently break
projects it has no way to inspect, so global dependencies are always kept and the output says
so. One stale link in `~/.claude` costs nothing; a wrong deletion costs a broken session
somewhere you are not looking.

**Why did `remove` keep a dependency in the same project, then?**
Three possible reasons, and it always tells you which: something else installed still declares
it, you added it directly at some point, or it has no provenance record so removing it would be
a guess.

**Why is there a `claude-kit.json` in my project's `.claude/`?**
It records *why* each artifact is present, `direct` or `dep-of:<parent>`. The directory alone
cannot answer that. `add tdd` then `add sdd` produces byte-identical links to `add sdd` alone,
yet `remove sdd` must keep `test-driven-development` in the first case and delete it in the
second. The distinguishing fact is history, not state.

**Can I delete `claude-kit.json`?**
Yes, and nothing breaks. The cascade then treats every dependency as untracked and keeps it,
which is the safe direction. `doctor` lists them as untracked, and `add` re-claims a dependency
it recognises next time it runs. `claude-kit adopt` rebuilds it in one pass.

**I cloned a repo with a `.claude/` and no manifest. What do I lose?**
The cascade, until you run `claude-kit adopt`. Every link reads as untracked, so `remove` keeps
each dependency rather than guessing, and the project slowly collects dependencies nothing needs.
`doctor` reports them as `untracked-install` notes and names the fix.

**Why didn't `adopt` see some of my links?**
Because they point somewhere else. `add` writes an absolute target into the checkout, so a symlink
committed by a teammate whose dotfiles live at a different path is dangling here, and `adopt` only
records links that resolve into this checkout's `claude/` directory. `doctor` reports those as
`broken-link` problems. Re-create them with `add`; adoption deliberately repairs records, never
links.

**`adopt` recorded a skill as a dependency, but I added it on purpose.**
That is the one fact adoption cannot recover: History A and History B leave byte-identical
directories. Run `claude-kit add <name> --type skill` and it is promoted back to `direct`, which
makes a future cascade keep it. Use `--dry-run` first if you want to see the guesses before they
are written.

**What happens if I move or delete the project?**
The record goes with it, since it lives inside the project. There is no machine-wide index to
reconcile, which is exactly why it is not kept in `~/.claude`.

**It says there is no project, but I am clearly in a directory. Why?**
You are in `$HOME`, which is the only way to see exit `6`. Any other directory is a project,
including one with no git repo anywhere above it. If you are not in `$HOME` and still see this,
that is a bug worth reporting.

This used to be the common case rather than the only one: the project was the **git top level**,
so a plain directory got refused and the message explained `$HOME` regardless of the real cause.
Both are gone.

**Why does running from `$HOME` refuse?**
`$HOME/.claude` *is* `~/.claude`, so treating `$HOME` as a project would route a non-global
artifact into the global directory, load it in every repo, and then have it deleted by the `ai`
role the next time it prunes `~/.claude/skills`. It would also leave a `claude-kit.json` in
`~/.claude`, which nothing else ever creates. Exit `6`, and the message offers `--global` if that
is genuinely what you meant.

**I ran `add` from a subdirectory. Where did it go?**
Into that subdirectory: `api/src/handlers/.claude/skills/<name>`, not `api/.claude/`. cwd is the
project, so nothing walks up. Output always prints the absolute target, so check it there. If you
wanted the repo root, `cd` to it first.

**Why is `grilling` refused?**
It is `dependency_only`: it exists to satisfy `grill-me` and `grill-with-docs` and installs
automatically with whichever you add. Exit `3`, and the message points at the parent. The
refusal only applies to naming it directly; as a dependency it installs freely.

**A skill and a plugin have the same name. Which do I get?**
Whichever `--type` says. That is what makes overlap legal. Internally a link is classified by
which store it points into, never by filename, because both types occupy `.claude/skills/`.
`doctor` reports overlaps as a note so they stay visible.

**`remove` says my target is "a real directory". Why won't it delete it?**
Because this tool only owns symlinks it made. A real directory at that path is hand-authored
content, and deleting it would destroy work. Exit `1`, nothing touched. Remove it yourself if
you meant to.

**What about broken symlinks?**
`remove` deletes them, since that is exactly what needs cleaning, and `doctor` reports them. A
broken link still counts as installed: it occupies the path.

**Does `doctor` need PyYAML?**
No. It used to, and said so as a note on any machine without it, which meant the frontmatter
check was skipped exactly where it mattered. It now scans the frontmatter dialect these artifacts
write instead of parsing YAML in general, so the check always runs on plain `python3`. It catches
the unquoted `": "` that stops an artifact loading, along with tabs, reserved openers and lines
that are not mapping entries; it does not model unterminated quotes, undefined aliases or errors
nested under another key. The tests run every case and all 114 real blocks past PyYAML to prove
nothing it reports is a false alarm.

**Why does `update --type agent` fail?**
Only skills have upstreams. `agent-registry.json` has no repos and plugins are authored in this
repo, so there is nothing to sync. Exit `1`.

**Two names in a batch failed. Which exit code do I get?**
The first failure's. Every name is still attempted and every outcome reported, because one code
cannot describe several results. Read the output for detail.

**Does `update` change what my projects use?**
Yes, immediately, and that is intentional. Installs are symlinks into this repo, so syncing a
skill's source updates every project pointing at it with no re-install. Run `outdated` first if
you want to see what would change.

**One repo was unreachable during `update`. Did the rest sync?**
Yes. Each repo is fetched independently and a failure is reported per repo. The run exits `8` so
a script can tell, but the reachable repos are already synced. A skill whose fetch failed is
left exactly as it was, never half-written.

**Where is `claude-kit sync`?**
Not written yet. Commit `0624d1c` removed the `ai` role's block that symlinked global artifacts
into `~/.claude` on the promise that `sync` would replace it, so **nothing currently provisions
`~/.claude` automatically**. Until then, install global artifacts with
`claude-kit add <name> --type <type> --global`.

**Why does `list` look exactly like `claude-skill list`?**
Because they are often used in the same terminal, and two similar-but-different layouts for the
same information is a reading tax. A test runs both against one project and diffs the bytes, so
a change to either implementation fails rather than being spotted by eye.

**`claude-kit list --type skill` and `claude-skill list` differ. Why?**
Two additions, both outside the shared template: `(installed for <parent>)` on rows where
claude-kit has provenance, and the trailing count. Everything in the row template itself is
identical. If anything else differs, that is a bug.

**Why is `list` not coloured when I pipe it?**
Colour is on only for a terminal, so redirecting to a file or through `grep` gives clean text.
Set `FORCE_COLOR=1` to keep it, or `NO_COLOR=1` to switch it off everywhere. `claude-skill` takes
its palette from `_ui color`, which decides the same way, so both go plain when piped. It used to
emit codes unconditionally, because a bare `set_color` does.

**`add` refuses a skill as global, but `list` shows no `(global)` next to it. Why?**
The flat list shows `[groups]`, and a skill reached as a dependency of something global carries
no `global` tag of its own. `claude-skill` has the same gap and the template is matched
deliberately. Use `claude-kit list --type skill --group`, which prints `(global)`, or `doctor`,
which reports scope directly.

**Does `--group` take a value or not?**
On `list`, both. Bare `--group` gives the grouped view, matching `claude-skill list --group`, and
`--group <tag>` narrows to one tag, which claude-skill cannot do. On `add` and `remove` the tag is
required, because there the flag has to name a set to act on.

**Why did `add --group` skip the global members instead of installing them?**
Because `--global` is what says "write to `~/.claude`", and a tag is a filter rather than a name.
Refusing each global member with `WRONG_SCOPE` would make a refusal the normal outcome of adding a
group, since most tags straddle both scopes; installing them anyway would put links in `~/.claude`
without being asked. So each run acts on one half and names the other. Run it twice, once with
`--global`, to get the whole tag.

**Why can I not pass names and `--group` together?**
The summary line counts a tag's members, and there is no honest way to write it when the call also
carried three unrelated names. Two commands cost nothing, so the combination exits `USAGE`.

**Why did adding a group print no `ALREADY` refusal for what was already there?**
A tag describes a set to converge on, so an already-installed member is the steady state. It is
counted in an aside and the run still exits `OK`, which is what makes `add --group` safe to re-run.
Naming that same artifact directly still refuses with `ALREADY`, because then it is the whole
request rather than one member of a set.

**`claude-skill remove --group` leaves dependencies behind. Why does claude-kit not?**
Because it can tell the difference. The cascade needs `claude-kit.json` to know which links arrived
*for* something else, which the fish version never wrote, so it could only delete exactly the
members it matched. `--no-cascade` gives the old behaviour if you want it.

**What about `claude-skill` and `claude-agent`?**
The fish functions are unchanged and still work; they are kept as reference. They use the same
scope rule, so the two agree on placement, but only claude-kit's version is under test.
