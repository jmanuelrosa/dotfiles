# The acceptance-criteria lifecycle

## Context

Posting a ticket's acceptance criteria to Jira as a comment after finishing the work turned out to be worth keeping: the criteria end up somewhere the whole team reads, next to the ticket rather than in a branch nobody checks out again.

Doing it by hand has two gaps. The criteria arrive after the code, so they describe what was built rather than what was agreed, which makes them tautologically green. And a second push either appends a duplicate comment or silently does nothing, because nothing records which comment was ours.

The outcome: a Jira-tracked branch carries its criteria in a local file from branch creation onward, and `/ac push` publishes them to one comment that later runs update in place.

## What this deliberately is not

An earlier draft of this plan was larger in every dimension, and the whole of the difference was cut on the grounds that acceptance criteria are already managed in three other places here and a fourth needed to justify itself. What was dropped, and why:

- **No new script.** The mechanism is one flag on `adf.py`, which already owns the criteria section, its lozenge and the Gherkin grammar, and already has a test suite.
- **No changes to `/pr`.** Publishing is an explicit act, so `/pr` needs no acli, no new context vars and no new gate. This also drops the requirement that `/pr` force a ticket to exist when the branch carries no key: worth having, not worth buying at the price of a mid-run ticket creation and branch rename.
- **No hook.** Nothing enforces criteria-before-code. `s-task` prints one line at branch creation, which is the moment it is still possible, and that is the whole of the enforcement.
- **No marker and no `comment list` call.** A sidecar file holding the comment id replaces both. It also carries a hash of the published body on a second line, so a re-push with nothing changed makes no acli call at all.
- **`product-team` is untouched.** Its `ac-writer` owns PRD-traced story criteria and stays the only caller of that path.

## Design

**`adf.py --comment`** relaxes `REQUIRED` to acceptance-criteria-only, renders that section alone, and appends a footer saying the comment is maintained from the branch and edits are overwritten. Mutually exclusive with `--investigation`, whose sentence lands in a Context a comment never renders.

**The working copy** is `<toplevel>/.claude/state/ac/<KEY>.md`, untracked, and is a *pure* `adf.py` template: no metadata header, no extra sections. That is what lets it be handed to the script verbatim with nothing in between to garble it, and it means adding a `## Context` turns the same file into a ticket description body. It also rules out `s-task` seeding a skeleton, since an empty section is an `adf.py` error rather than a starting point.

**`<KEY>.comment-id`** holds the comment id on line 1 and the sha256 of the published body on line 2. The first decides create versus update; the second makes a re-push with nothing changed a no-op that calls acli not at all, which matters because an `update` rewriting a byte-identical body still moves the issue's `updated` timestamp. The hash is over the generated ADF, not the markdown, so reformatting the file without touching a scenario is correctly silent.

Identity from the comment body was designed and rejected: `comment list` returns bodies flattened to plain strings with text nested in lists dropped entirely, and a marker a human can see is one a human can delete, after which every push appends another comment forever with no error.

**The scope gate** is two conditions, checked before anything else, and failing either means the skill does nothing at all: the branch is `<type>/<KEY>-<slug>`, and `KEY`'s prefix equals `$JIRA_PROJECT`. Only the work profile exports that variable, so a personal machine is inert; and the prefix check is what stops the key shape from firing on `fix/UTF-8-decoding-bug`, `HTTP-2` or `ISO-8601`, all of which parse as Jira keys.

**Publishing** is `create --key -F` when the sidecar is absent and `update --key --id --body-adf` when it is present. Those flags are not interchangeable: `update` ignores ADF passed to `-F`.

## Findings that shaped it

**acli cannot sit on the critical path of anything already half-done.** Reproduced twice while planning: acli was authenticated, then every call including `auth status` began returning `unauthorized` and stayed that way. It refreshes its OAuth token by writing `~/.config/acli/jira_config.yaml`, which `settings.json` denies, so the rotation fails and the session is dead until the user re-auths in their own terminal. `jira/SKILL.md` claimed the opposite and was corrected.

**acli only escapes the sandbox as a leading token**, so it cannot be spawned from inside a python script at all. Together with `apply.py` not being idempotent, that is what keeps publishing out of `/pr` rather than merely making it inadvisable.

**`.claude/state/` is untracked and not gitignored**, and `/commit` step 3 actively offers untracked files, so the working copy needed something keeping it out of a diff. A per-repo `.gitignore` line was chosen over widening the machine-wide `.claude/tasks/` guards: the rule is tracked so a `wt` worktree inherits it, and it covers every tool rather than only the two paths those guards see. `git check-ignore` confirmed the entry must be `.claude/state/ac/` and not `.claude/state`, which would also ignore the research memos `research/SPEC.md` leaves the user free to track.

## Files changed

| File | Change |
|---|---|
| `skills/jira/scripts/adf.py` | `--comment` mode: `COMMENT_SECTIONS`, `COMMENT_REQUIRED`, `COMMENT_FOOTER`, a `required` parameter on `parse`, a `comment` parameter on `build`, and the two mode flags made mutually exclusive |
| `skills/jira/tests/test_jira_adf.py` | 6 cases: criteria-only builds as a comment but not a description, the criteria render alone, the footer is last and unmarked, the grammar is still strict, no criteria is refused, both mode flags is a usage error |
| `skills/ac/SKILL.md` | New. The scope gate, the working copy, the publish table, and the boundaries |
| `skill-registry.json` | `ac` row, `global`, `dependencies: ["jira"]` |
| `skills/jira/SKILL.md` | Auth check section rewritten for the token-refresh failure |
| `roles/ai/files/claude/CLAUDE.md` | The same correction in one bullet |
| `CLAUDE.md` | New `### Acceptance criteria live on the branch, then in one comment` |
| `roles/work/files/scripts/s-task/s-task` | One `_ui note` on the Jira path pointing at `/ac` |

**No existing guard was widened.** `git-skill-gate.sh` and `commit/scripts/apply.py` keep their `.claude/tasks/` checks exactly as they were: the AC working copy is kept out of commits by the repo's own `.gitignore` instead, which the skill appends on first use.

No `pytest.ini`, `test_suites.py` or Ansible change: no new suite directory, and the skill reaches `~/.claude` through `claude-kit sync`'s derivation from `groups`.

## Verification

`make test` passes at 1128. `claude-kit doctor` reports no drift and `claude-kit sync --dry-run` reports it would link `ac`.

What tests cannot cover, to be done on a scratch ticket from a terminal where acli is authenticated:

1. `/ac`, write two scenarios, `/ac push`. Confirm the green lozenge, one paragraph per scenario, and the footer.
2. `/ac push` again with nothing changed. Confirm it reports `UNCHANGED`, makes no acli call, and leaves the issue's `updated` where it was.
3. Change one `THEN` and `/ac push`. Confirm the same comment id is rewritten, no second comment appears, and the sidecar's hash moves.
4. Edit the comment in the Jira UI, then `/ac push`. Confirm the edit is overwritten and still no duplicate. This is the case the sidecar design exists to make safe, and it is the only one that exercises Jira's editor.
5. Delete the comment in the UI, then `/ac push`. Confirm the failed update is recovered by creating a new comment and rewriting the sidecar.
6. Confirm the first `/ac` run added `.claude/state/ac/` to the repo's `.gitignore`, then that `git add -A` leaves the working copy unstaged and `git add` naming it directly exits 1.
7. On a branch with no key, and on `fix/UTF-8-decoding-bug`, confirm `/ac` does nothing and calls no acli.

## Known limits

One ticket, one file, one comment: a second branch on the same ticket shares the working copy and the last push wins.

GitHub-issue branches get no criteria, which follows from the scope gate being a Jira key.

The published comment cannot be parsed back into the working copy, because acli flattens comment bodies. A fresh clone re-seeds from the ticket description's criteria section, or starts empty.

Separately, `roles/work/files/television/cable/jira.toml:33` binds Enter to `acli jira workitem open`, which is not a subcommand; the working form is `view <KEY> --web`. Nothing tests that cable. Out of scope here, worth its own commit.
