# Product profile

The skill knows source categories and how to detect them.
Which concrete tools serve a given product is a fact about that product, so it is detected at runtime and recorded in that product's store, never in this skill.

## Finding the profile

Start from the current repo's git common dir (`git rev-parse --path-format=absolute --git-common-dir`, then its parent), so a linked worktree resolves to the same product as its main checkout.
Read `<dir>/.teammate/PROFILE.md` with the file-read tool for the repo, its parent and its grandparent (the same candidates onboarding offers), all three in one message, never `$HOME` or above, and use the nearest that exists.
Do not list or glob parent directories: listing outside the working directory is often blocked, and a blocked listing proves nothing.
Only a failed read of each exact path means there is no profile.
Found: load it and continue.
Not found: answer with Stage A sources from `sources.md` (code, in-repo docs, local git, this repo's own forge PRs or MRs, and tracker items its commits name), then suggest `/teammate init`. Stage B sources (chat, long-form docs, meeting notes, error tracking) stay unsearched until a profile approves them, because a signed-in connector may belong to a different company.

## Onboarding (`/teammate init`)

Keep it to one message of findings and one approval.
When a profile already exists, `init` refreshes it: run the same detection, then propose only the differences (a new repo, a source that signed in or broke, a renamed remote) and keep every earlier approval and off-limits entry unless the user changes it.
After the profile is written, offer `/teammate survey` as the next step.

1. **Workspace root.** Show all three candidates as numbered options: the repo itself, its parent, its grandparent. Mark one recommended: the smallest folder that groups the repos that belong to this product, judged from sibling remotes (same owner or group) and names. A mixed folder that holds several products is not a root; the product's own repos are. The user picks a number or types another path.
2. **Repos in scope.** Every git repo under each candidate, with its remote slug (the remote name often differs from the directory name). Find them with `find <dir> -maxdepth 2 -name .git`. Listing outside the session's working directory is often blocked; then search the candidate with the content-search tool in files mode, or `rg --files --max-depth 2`, for top-level marker files (`README.md`, `package.json`, `go.mod`, `pyproject.toml`, `Makefile`, `*.tf`), since search tools skip `.git` itself. Confirm each hit with `git -C <dir> remote get-url origin`. A blocked listing never means there are no siblings. Note worktrees (`git worktree list`) as views of their main repo, not separate repos. Note repos the code points at but that are not cloned.
3. **Detection**, one category at a time, run as separate commands rather than one pipeline:
   - *Forge*: the host of each remote. `github.com` is `gh`. Anything matching a host in `glab auth status`, including an SSH alias, is `glab` on that host. Confirm access with one read (`gh pr list -R <slug> --limit 1`, `glab mr list -R <slug> --per-page 1`).
   - *Tracker*: count key-shaped tokens in recent commit subjects and in the PR or MR template. A `KEY-123` shape is checked by resolving one key with `acli jira workitem view <key> --fields summary`; if that fails, the tracker is unknown, not assumed to be Jira. `Fixes #N` or `Closes #N` means forge issues. A trailing `(#N)` on a squash commit is the PR number, not an issue.
   - *Chat, long-form docs, meeting notes, error tracking*: which tools exist in this session (a Slack or Drive connector, `ntn`, `sentry`), and which account or workspace each is signed in to (the Slack own-profile read, `ntn whoami`, `sentry` account mapping). A tool that needs sign-in is listed as unavailable, never signed in on the user's behalf.
   - *In-repo knowledge*: CLAUDE.md, AGENTS.md, CONTEXT.md, GLOSSARY.md, `docs/adr`, `docs/`, `.claude/docs`, and any repo whose name or README marks it as specs or knowledge.
4. **Approval.** Show the root, repos and detected sources in one table. The forge and the tracker these repos' commits name are Stage A in `sources.md`, so they are proposed on; every Stage B source (chat, long-form docs, meeting notes, error tracking) is proposed off until the user turns it on. The user approves sources and names anything off-limits (a channel, a folder, a space). An explicit yes writes `PROFILE.md` through the store gate in `knowledge.md`.

## Isolation

- Sources not approved in a product's profile are never searched for that product, even when signed in. One account often spans several companies, so being signed in proves nothing about ownership.
- One product's store is never read for another product's question. If a question spans two products, say so and ask which store applies.
- Nothing from one product's sources is quoted in another product's store.

## Drift

A probe that fails in a later session (expired auth, connector gone, repo moved) is a gap for that session, reported once.
The profile changes only through the store gate, so a transient failure never rewrites it.

## PROFILE.md shape

```markdown
# <product> teammate profile

Root: <absolute path>
Created: <date>, updated: <date>

## Repos
| Dir | Remote | Role | Notes |

## Sources
| Category | Tool | Account or workspace | Approved | Off-limits |

## In-repo knowledge
- <path>: <what it covers>
```
