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

Every command except `doctor`, `adopt`, `sync` and `scout` requires `--type skill|agent|plugin`.
Nothing is inferred from a name, so the three namespaces are allowed to overlap and a collision is
a `doctor` note rather than an error. Those four take `--type` as an optional filter, because
their result spans all three types: `doctor`'s cross-type checks cannot run inside a single type,
one `claude-kit.json` holds all three, `sync` converges a directory that holds all three, and a
project's stack implies artifacts of all three — so on each of them a required `--type` could only
ever ask for a partial job.

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

`sync` is where that tag stops being advice and becomes the state of the machine: it links
everything the tag reaches and unlinks everything it does not, so `~/.claude` holds exactly the
derived set and nothing else. `--global` is how you write there deliberately; the tag is how you
write there durably.

`update` and `outdated` sit outside all of this. They rewrite the skill sources in this repo and
touch no install, so neither scope applies and neither accepts `--global`.

---

## Commands

The families above are how `claude-kit -h` groups its listing:

| Family | Commands | Acts on |
|---|---|---|
| Scope-aware | `add`, `remove`, `list`, `scout`, `doctor`, `adopt` | a project's `.claude/`, or `~/.claude` with `--global` |
| Global | `sync` | `~/.claude` alone, whatever the cwd |
| Registry-wide | `update`, `outdated` | this repo's skill sources against upstream |

`sync` gets a family of its own rather than joining the scope-aware set, because `~/.claude` is not
one of two places it might act but the only one. `--global` is therefore not an option there, and
listing it alongside `add` would imply a project-scoped run that does not exist.

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

**The layout, colours and markers came from `claude-skill list`**, the fish function this
replaced, so the two read identically while both shipped. Every row shape is pinned as a literal
in `test_list_format.py`, escape codes included.

| Flag | Meaning |
|---|---|
| `--group` | With no value, group the listing by tag |
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

Two things sit outside that inherited template: `(installed for <parent>)`, which comes from
provenance, and the trailing count.

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
text. `NO_COLOR` disables it and `FORCE_COLOR` forces it on, with `NO_COLOR` winning. `_ui` in fish
follows the same rule, so a fish function and this agree on screen.

**Note the flat view shows no scope marker.** A skill that is global
only because something global depends on it (`jira`, `documentation-and-adrs`,
`planning-and-task-breakdown`) carries no `global` tag, so nothing in the flat list says so, and
`add` refusing it can look surprising. `--group` does show `(global)`, and `doctor` reports scope
directly.

### `scout`

```
claude-kit scout [--type {skill,agent,plugin}] [--focus TAG] [--add]
```

Every other command starts from a name you already know. `scout` starts from the directory: it
fingerprints the project, matches that fingerprint against the catalogue's group tags, and prints
a shortlist with the reason for each entry. It is the answer to *what should I install here*,
which `list` (the whole catalogue, alphabetically, saying nothing about relevance) and `add`
(which assumes you already know) both leave unanswered.

| Flag | Meaning |
|---|---|
| `--type` | **Optional**, as on `doctor` and `adopt`. A project's stack implies artifacts of all three kinds, so the default covers all three; pass one to narrow the whole report |
| `--focus TAG` | Treat that tag as asked-for. Its artifacts sort to the front **and rank as strong matches**, so `--add` takes them |
| `--add` | Install the strong tier — which `--focus` widens. Never the weaker tier |

Read-only without `--add`. Refuses `NO_PROJECT` in `$HOME`, which is never a project.

**Two tiers, and the difference is the grade of evidence.**

| Tier | Earned by | Example reason |
|---|---|---|
| Strong match | Something in the project says so | `react@19.0.0 in package.json`, `no test directory and no test files` |
| Worth considering | A neighbour of a direct hit | `implied by react (react@19.0.0 in package.json)` |

Absence counts as direct evidence: no test suite, no `.github/workflows` and no `docs/` each rank
strongly, because a project without them wants the artifact that fills the gap more than one with
them does. Prose counts too, coarsely — a `CLAUDE.md` mentioning TDD or ADRs is read as intent.

When several tags match, the `Why` cites the one that best explains the match: whatever `--focus`
named, else the most specific tag, which is the one naming a technology. Alphabetical order is the
last resort rather than the rule.

**`--focus` is a third source of direct evidence, not just a sort key.** Asking for a tag is the
evidence for it, so its artifacts rank strongly and their `Why` reads `requested focus 'testing'`.
That is deliberate — a focus `--add` ignored would be a filter that filters nothing — but it means
`scout --focus testing --add` installs artifacts that a plain `scout --add` would have left in the
weaker tier. In a React project with a test suite, `test-driven-development` is *worth
considering*; add `--focus testing` and it becomes a strong match and gets installed.

The closing `→` line always installs **everything shown**, both tiers. `--add` installs the strong
tier only. When the two differ the report says so on the line beneath, because the difference is
otherwise visible only in the counts.

```
$ claude-kit scout --type skill
🔎 Scouting ~/dev/api

Strong match
  · react-best-practices [engineering, frontend, react]
    Why:  react@19.0.0 in package.json
    What: Modern React patterns. Use when writing or reviewing React components …
  · test-driven-development [engineering, frontend, backend, testing]
    Why:  no test directory and no test files
    What: Drives development with tests. Use when implementing any logic …

Worth considering
  · code-review-and-quality [refactoring, backend, frontend, review]
    Why:  implied by react (react@19.0.0 in package.json)
    What: Conducts multi-axis code review. Use before merging any change …

Already in this project
  ✓ coderabbit

→ claude-kit add react-best-practices test-driven-development --type skill
✨ 2 strong, 1 worth considering, 1 already here
```

The closing line is runnable, and with a mixed shortlist there is **one line per type**, because
`--type` applies to every name in a call. A mixed report also labels each row with its type; a
narrowed one does not, since the suffix would be on every row and inform nobody.

Four rules carry the ranking, and each exists to keep the report worth reading:

- **Nothing already available is offered.** That is wider than "linked in this project": it covers
  `~/.claude` too, and anything that *belongs* there whether or not `sync` has run. Offering a
  global artifact would be offering to install what every project already loads. Dependency-only
  skills are out for the same reason `list` hides them, and a registered skill not yet downloaded
  is out because `add` would refuse it.
- **A framework the project does not use is dropped entirely**, however well its other tags match.
  Persona tags like `frontend` are shared by every framework's artifacts, so without this one
  implied `frontend` hit drags Astro and Apollo in beside React.
- **Broad tags never earn a place.** `engineering` is on most of the catalogue, so matching on it
  ranks everything, which says exactly as much as ranking nothing. `observability` counts as broad
  for the same reason and not because it is vague: ten of the fifteen seat plugins carry it as
  boilerplate, so one `@sentry/*` dependency would otherwise make the data, design and gtm seats
  strong matches for a React API. `sentry` is the discriminating tag over that territory. Naming a
  broad tag with `--focus` is how to mean it, and then it matches normally.
- **A stack the catalogue does not cover still gets an answer.** A Rust or Go repo matches no tech
  tag, so scout falls back to the stack-agnostic tags (`workflow`, `review`, `testing`, `git`,
  `planning`, `productivity`, `documentation`, `refactoring`). Those are guesses, so they land in
  the weaker tier and are never claimed as strong.

The combined shortlist is capped at 12, strong matches served first — so a well-covered project
sees no guesses at all.

`--add` installs the strong tier through the same path as `add` itself, so a recommendation
accepted here resolves dependencies, records provenance in `claude-kit.json` and prints the plugin
restart hint exactly as a hand-typed `add` does. It never installs the weaker tier: that tier is a
prompt to go and look, not a recommendation to act on. Nothing scout offers is global, so `--add`
only ever writes into `<cwd>/.claude` and `--global` has nothing to say here.

The fingerprint reads `package.json` (dependencies and devDependencies alike) and the Swift
markers, and deliberately not `Cargo.toml`, `go.mod` or `pyproject.toml`: a hit there implies
nothing installable and would only add noise the reader has to discount. `node_modules` and the
other vendor directories are pruned from the test-file walk, or every JS project would look
tested.

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

### `sync`

```
claude-kit sync [--type {skill,agent,plugin}] [--dry-run]
```

| Flag | Meaning |
|---|---|
| `--type` | Narrow to one type. Narrows both halves of the run, so a `--type agent` sync never reads a global skill as stale |
| `--dry-run` | Show what would be linked and unlinked without touching anything |

Makes `~/.claude` match what the registries say belongs there: links every artifact that is
global, unlinks every one that no longer is. This is the command the `ai` role runs, and it
replaces the derivation, symlink and prune block that commit `0624d1c` removed from
`roles/ai/tasks/main.yml`.

**It converges rather than installs**, which makes it the one command that deletes something you
did not name. `~/.claude` is owned by the registries, so a hand-made change there is transient by
design: removing a global link lasts until the next run, and so does `add --global` on an artifact
that is not tagged `global`. To make either stick, change the tag.

Three narrowings are what make deleting safe, and all three are tested:

- **Only symlinks.** A real directory in `~/.claude/skills` is hand-authored content and is never
  a candidate. Neither is a path where a real directory already sits under a name that belongs;
  that is reported and left alone, and the run exits `1`.
- **Only links into this repo's `files/claude/`.** A link pointing anywhere else is somebody
  else's. This is also how a plugin is told apart from a skill, since both live in
  `.claude/skills/`: the store the link resolves into decides, never the filename.
- **Only when something is left.** If the derived set comes back empty while links exist, every
  one of them is stale and the run would empty the directory. That is what a registry with its
  `global` tags lost looks like, and it is indistinguishable from working correctly until Claude
  Code loads no skills at all, so it refuses with `9` and touches nothing.

Scope is not a question here: `sync` acts on `~/.claude` and only on `~/.claude`, from any cwd, so
`--global` neither applies nor exists. Membership is the same tag-plus-dependencies rule described
above, so `grilling` and `jira` are linked without carrying the tag themselves.

A registered artifact missing from the repo is reported rather than linked, and the run exits `2`.
The old Ansible used `force: true`, which never validated its target, so a registry typo became a
symlink resolving nowhere while the play reported success.

```
$ claude-kit sync
🔄 Syncing global artifacts in ~/.claude
✓ Linked 'commit' (skill) into ~/.claude/skills
✓ Linked 'grilling' (skill) into ~/.claude/skills
✓ Unlinked 'prisma-expert' from ~/.claude/skills; it no longer belongs here
✨ 20 global artifacts, 3 changes (2 linked, 0 relinked, 1 pruned)

$ claude-kit sync
🔄 Syncing global artifacts in ~/.claude
✨ 20 global artifacts, 0 changes
```

Silent about what is already correct, because on a steady-state run that is everything and twenty
lines saying nothing happened is what teaches you to skip the report. The `ai` role matches
`, 0 changes` on that closing line to decide whether the task was `changed`, and a test pins the
wording against the task.

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

Output follows the layout inherited from the fish tooling: a bold header, a cyan
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
a repo that ships a `.claude/` but no manifest, or in a project set up before claude-kit existed, by
the fish functions it replaced, which never wrote one. Writes the manifest and
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
| 1 | `USAGE` | missing or invalid `--type`, bad flags, an unsupported combination, or a real directory where a link belongs |
| 2 | `NOT_FOUND` | no artifact of that type by that name, or registered but absent on disk |
| 3 | `DEPENDENCY_ONLY` | named a skill that exists only to satisfy another |
| 4 | `WRONG_SCOPE` | a global artifact named without `--global` |
| 5 | `ALREADY` | already installed at the resolved target |
| 6 | `NO_PROJECT` | project-scoped, but cwd is `$HOME`, the one directory that is not a project |
| 7 | `NOT_INSTALLED` | `remove` target absent |
| 8 | `FETCH_FAILED` | `update` / `outdated` could not reach or read an upstream |
| 9 | `DRIFT` | `doctor` found at least one problem, or `sync` refused to prune every link in `~/.claude` |

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

Every line these commands print comes from `dotkit/ui.py`, the shared vocabulary: `title`
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

**Find out what a project is missing, then take the shortlist.**

```console
$ cd ~/work/api
$ claude-kit scout --type skill
🔎 Scouting ~/work/api

Strong match
  · react-best-practices [engineering, frontend, react]
    Why:  react@19.0.0 in package.json
    What: Modern React patterns. Use when writing or reviewing React components …

Worth considering
  · knip [engineering, backend, frontend, review]
    Why:  implied by react (react@19.0.0 in package.json)
    What: Run knip to find and remove unused files, dependencies, and exports …

→ claude-kit add react-best-practices --type skill
✨ 1 strong, 1 worth considering, 0 already here

$ claude-kit scout --type skill --add
...
✓ Linked 'react-best-practices' into ~/work/api/.claude/skills
```

`--add` takes the strong tier only. `knip` was a guess, so accepting it stays a decision you make
by hand.

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
✓ Linked 'commit' into ~/.claude/skills
```

**Provision every global artifact at once, which is what the `ai` role does.**

```console
$ claude-kit sync --dry-run
🔄 Checking global artifacts in ~/.claude
✓ Would link 'architect' (agent) into ~/.claude/agents
✓ Would link 'commit' (skill) into ~/.claude/skills
✓ Would unlink 'prisma-expert' from ~/.claude/skills; it no longer belongs here
✨ 20 global artifacts, 3 changes (2 linked, 0 relinked, 1 pruned, dry run)

$ claude-kit sync
🔄 Syncing global artifacts in ~/.claude
✓ Linked 'architect' (agent) into ~/.claude/agents
✓ Linked 'commit' (skill) into ~/.claude/skills
✓ Unlinked 'prisma-expert' from ~/.claude/skills; it no longer belongs here
✨ 20 global artifacts, 3 changes (2 linked, 0 relinked, 1 pruned)
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

**`sync` deleted a link I made by hand. Why?**
Because `~/.claude` is owned by the registries, not by whoever ran a command there last, and that
is the property that lets `make run-role ROLE=ai` be re-runnable. A link is kept only while its
artifact is tagged `global` or is reached as a dependency of one, so `add --global` on an untagged
artifact lasts until the next sync and no longer. Tag it in its registry to keep it, or install it
into the project that actually needs it.

The reverse holds too: deleting a global link by hand is undone on the next run. To drop one for
good, remove its `global` tag.

**Can I still `add --global` then?**
Yes, and it is the right move for a one-off: trying something out in every project for an
afternoon, or reaching for an artifact you have not decided to keep. Just know it is a scratch
change. Anything you want on the machine permanently belongs behind the tag, which is the only
durable statement about what `~/.claude` holds.

**Why does `list` look the way it does?**
It kept the layout of `claude-skill list`, the fish function it replaced, so that the two read
identically for as long as both shipped and the switch cost nobody a second look. The fish
functions are gone now, and `test_list_format.py` pins every row shape as a literal instead.

**Why is `list` not coloured when I pipe it?**
Colour is on only for a terminal, so redirecting to a file or through `grep` gives clean text.
Set `FORCE_COLOR=1` to keep it, or `NO_COLOR=1` to switch it off everywhere. `_ui` in fish decides
the same way, so a fish function piped into a file goes plain too.

**`add` refuses a skill as global, but `list` shows no `(global)` next to it. Why?**
The flat list shows `[groups]`, and a skill reached as a dependency of something global carries
no `global` tag of its own. The gap came with the layout and is kept deliberately. Use
`claude-kit list --type skill --group`, which prints `(global)`, or `doctor`, which reports scope
directly.

**Does `--group` take a value or not?**
On `list`, both. Bare `--group` gives the grouped view and `--group <tag>` narrows to one tag. On
`add` and `remove` the tag is required, because there the flag has to name a set to act on.

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

**Why does `remove --group` cascade to dependencies when the fish tooling did not?**
Because it can tell the difference. The cascade needs `claude-kit.json` to know which links arrived
*for* something else, which the fish version never wrote, so it could only delete exactly the
members it matched. `--no-cascade` gives that behaviour if you want it.

**What happened to `claude-skill` and `claude-agent`?**
Deleted. claude-kit covers everything they did, plus plugins, provenance and the cascade, and it is
the half that is under test. The Television pickers now drive it, and `claude-kit adopt` recovers
the manifest for any project those functions set up.
