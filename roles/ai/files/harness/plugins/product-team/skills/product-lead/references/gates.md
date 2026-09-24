# Gate protocol

The per-medium mechanics for Gate 0 and Gate 1, split out of [conventions.md](conventions.md) so only the stages that open a gate pay to load it: `0-refine-idea`, `3-red-team`, `setup-strategy` (its strategy sign-off follows the same protocol), and `product-lead` when it reconciles or explains one. What a gate is, and that its decision and reason land in STATUS.md, is in conventions.md; this file is how the answer is collected.

Gated stages never run `git commit`, `git push` or `gh pr create` under either medium.

## gate_medium: session (the default)

The stage ends by asking the human directly with `AskUserQuestion`: proceed, kill, or not yet. Then:

1. Record the answer in the STATUS.md gate row: status, decided by, date, and one line on what convinced them or which concern they accepted.
2. Suggest `/commit` (subject `docs({slug}): gate {n} {stage name}`). Local history is the artifact trail.
3. Stop. Do not continue into the next stage in the same turn.

No branch, no PR, no `gh` calls.

## gate_medium: pr

Each gate gets its own branch, cut fresh from the up-to-date default branch when the gate begins. A gate PR must never carry the previous gate's already-merged commits: repos that squash-merge collapse each merged gate into a new commit that is not an ancestor of a reused branch, so a shared branch diverges and every later gate PR conflicts.

| Gate | Branch |
|---|---|
| 0 | `docs/{slug}-gate-0-brief` |
| 1 | `docs/{slug}-gate-1-prd` |

Switch to the branch if it exists (this gate's PR is open, or you are revising), otherwise cut it fresh from the default branch:

    git fetch origin
    git switch -c docs/{slug}-gate-{n}-{label} origin/{default-branch}

Resolve the default branch from the remote (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`). Where `git fetch` cannot reach the remote, compare local `HEAD` against `gh api repos/{repo}/commits/{default} -q .sha` and cut from the local default branch once they match; a machine with working SSH should keep using the fetch.

The stage then ends by updating the gate row to `pending` with the PR url, printing a handoff block (files written, the commit subject above, the same string as the PR title, a suggested body naming the decision being gated including kill, and a 3 to 5 item reviewer checklist), and stopping. The human runs `/commit`, then `/pr --title "<subject>"`. Merge is the gate passing, and the next stage records it: find the PR with `gh pr list --head docs/{slug}-gate-{n}-{label} --state all --json url,title,state,mergedAt`, then write status, decider, date and reason into the gate row. Closed unmerged is a kill signal: ask before recording it.

## Revision flow

Re-running a stage after Gate 1 is answered means "address the review". Under `session`, read the recorded reason and concerns from the gate row. Under `pr` with the PR still open, read the comments with `gh pr view <url> --comments` (and `gh api repos/{owner}/{repo}/pulls/{n}/comments` for inline ones), address every comment in the artifact, list what changed per comment, and end with the gate protocol again. Never dismiss or resolve review threads yourself.
