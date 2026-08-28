# Research: Git conditional global ignore

| | |
|---|---|
| Date | 2026-08-28 |
| Mode | code deep-dive |
| Question | Why do the Didomi conditional Git ignore rules appear not to work, and what scope do they actually cover? |
| Repos examined | dotfiles, Didomi admin-api |
| Requested by / source | direct ask |

## TL;DR

The configuration works for untracked paths in repositories beneath `~/Developer/work/didomi`, but Git ignore rules never hide paths already tracked in the index.
The tested `admin-api` repository tracks a `.claude/skills/writing-sequelize-migrations/SKILL.md` path, which explains that observed case.
The condition does not cover every repository beneath `~/Developer/work`; it covers only the `didomi` subtree.
The helper function also does not create the live configuration described in the request: it writes to a different directory and emits only the user identity.

## Context

The global configuration conditionally includes a Didomi-specific config, which in turn sets `core.excludesFile` to a file containing `tailwind.config.ts`, `.claude`, and `.research`.
The expectation was that these names would be ignored in all relevant descendant repositories.

## Current state

The global configuration applies the conditional include only when a repository's Git directory is beneath `~/developer/work/didomi/` (`roles/apps/files/.gitconfig:165-167`).
The included live file sets `core.excludesFile` to `~/Developer/work/.gitignore.didomi` (`/Users/jmanuelrosa/Developer/work/.gitconfig.didomi:5-7`).
That ignore file has three slashless patterns (`/Users/jmanuelrosa/Developer/work/.gitignore.didomi:1-4`).
The helper instead writes `~/developer/<company>/.gitconfig.<company>` and emits only a `[user]` section (`roles/shell/files/fish/functions/create_gitconfig.fish:13-21`).

## Findings

### Does the conditional include cover every repository beneath `~/Developer/work`?

- **Answer:** No. It covers repositories beneath `~/Developer/work/didomi` because `gitdir/i` is case-insensitive and the trailing slash implies recursive matching. Repositories in sibling directories beneath `work` do not match.
- **Evidence:** `roles/apps/files/.gitconfig:165-167`; https://git-scm.com/docs/git-config#_conditional_includes
- **Confidence:** high
- **Assumptions:** none

### Do the three ignore patterns match at arbitrary depth?

- **Answer:** Yes. A pattern without a slash matches the named file or directory at any level. A controlled check against the live included file matched `.claude/new-untracked-file`, `nested/tailwind.config.ts`, and `nested/.research/x`.
- **Evidence:** `/Users/jmanuelrosa/Developer/work/.gitignore.didomi:1-4`; https://git-scm.com/docs/gitignore#_pattern_format
- **Confidence:** high
- **Assumptions:** none

### Why can `.claude` still appear in Git?

- **Answer:** At least one `.claude` path in the tested `admin-api` repository is already tracked. Ignore rules affect only untracked files. The controlled check did not report the tracked path normally, but reported it with `git check-ignore --no-index`, proving both that the rule matches and that index state prevents normal ignore treatment.
- **Evidence:** `admin-api/.claude/skills/writing-sequelize-migrations/SKILL.md:1` (tracked in the index and currently deleted in the worktree); https://git-scm.com/docs/gitignore#_description
- **Confidence:** high
- **Assumptions:** this is the same concrete failure that prompted the question

### Does `create_gitconfig.fish` create this Didomi setup?

- **Answer:** No. For `didomi`, it writes `~/developer/didomi/.gitconfig.didomi`, while the global config includes `~/developer/work/.gitconfig.didomi`. It writes only name and email, not `core.excludesFile` or `sshCommand`.
- **Evidence:** `roles/shell/files/fish/functions/create_gitconfig.fish:13-21`; `roles/apps/files/.gitconfig:165-167`
- **Confidence:** high
- **Assumptions:** none

### Does the Didomi excludes file augment the global excludes file?

- **Answer:** No. The later `core.excludesFile` value in the conditional include replaces the global `~/.gitignore` value for matching repositories; Git does not merge the two configured files.
- **Evidence:** `roles/apps/files/.gitconfig:84-86`; `/Users/jmanuelrosa/Developer/work/.gitconfig.didomi:5-7`; https://git-scm.com/docs/git-config#Documentation/git-config.txt-coreexcludesFile
- **Confidence:** high
- **Assumptions:** no later repository-local override exists in a particular repository

## Contradictions

One adversarial check initially found that broad `.claude` paths were not ignored and saw only an XDG ignore rule.
That check had not loaded the conditional Didomi config.
A controlled invocation with the same `includeIf`, the live included file, and the real `admin-api` repository matched all three requested patterns, so the initial counterexample was a configuration-loading artifact.

## Risks and open questions

- If the intended scope is every repository beneath `~/Developer/work`, the current `didomi` condition is too narrow.
- Removing a tracked path from the index changes repository state and should be done deliberately with `git rm --cached`, usually in a commit shared with collaborators.
- The function's output path and content differ from the live setup, so recreating the file with the helper would not reproduce the current configuration.
- Didomi repositories lose the general patterns from `~/.gitignore` unless those patterns are also present in `.gitignore.didomi` or configured elsewhere.

## Verification notes

- Conditional include activation: challenged with casing, symlink, worktree, and override checks; held.
- Slashless recursive matching: challenged against official documentation and an isolated repository; held.
- Tracked-file explanation: initially downgraded because a refuter omitted the conditional config; corrected to high confidence after a controlled normal versus `--no-index` comparison.
- Helper mismatch: held for path and generated content; the broader claim that all ignore provisioning is manual was rejected because the general `~/.gitignore` is tracked and symlinked by Ansible (`roles/apps/tasks/development.yml:5-13`).

## Sources

- Direct ask (2026-08-28)
- `roles/apps/files/.gitconfig`
- `roles/apps/tasks/development.yml`
- `roles/shell/files/fish/functions/create_gitconfig.fish`
- `/Users/jmanuelrosa/Developer/work/.gitconfig.didomi`
- `/Users/jmanuelrosa/Developer/work/.gitignore.didomi`
- `/Users/jmanuelrosa/Developer/work/didomi/admin-api` Git index and ignore checks
- https://git-scm.com/docs/git-config#_conditional_includes
- https://git-scm.com/docs/git-config#Documentation/git-config.txt-coreexcludesFile
- https://git-scm.com/docs/gitignore

## Next steps

Decide whether the intended scope is only `~/Developer/work/didomi` or all of `~/Developer/work`.
For the current Didomi scope, verify the exact path with `git check-ignore -v --no-index <path>` and remove it from the index only if the team wants Git to stop tracking it.
Align `create_gitconfig.fish` with the actual directory layout and desired generated fields in a separate implementation change if the helper is meant to reproduce this setup.
