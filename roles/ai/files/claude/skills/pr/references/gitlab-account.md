# GitLab account resolution

One GitLab server can back more than one authenticated account (a host alias can point a second account at the same server), and glab picks by the remote's host token, so a repo cloned with a bare or shared host can resolve to the wrong account (silent 404). Resolve from live `glab auth status`, never a fixed list:

```sh
RHOST=$(printf '%s' "$REMOTE" | sed -E 's#^[a-z]+://##; s#^[^@]*@##; s#[:/].*##')
NS=$(printf '%s' "$REMOTE" | sed -E 's#^[a-z]+://[^/]+/##; s#^[^@]*@[^:]+:##; s#\.git$##')
# host <TAB> api-endpoint-host <TAB> account, one line per authenticated host
HOSTMAP=$(glab auth status 2>&1 | awk '
  /^[A-Za-z0-9._-]+$/  { h=$1; a="?" }
  /Logged in to/       { for (i=1;i<=NF;i++) if ($i=="as") a=$(i+1) }
  /REST API Endpoint:/ { u=$NF; gsub(/https?:\/\/|\/.*/, "", u); print h"\t"u"\t"a }')
# candidates: authenticated hosts whose key OR API endpoint matches the remote host token
CANDS=$(printf '%s\n' "$HOSTMAP" | awk -F'\t' -v r="$RHOST" '$1==r || $2==r {print $1"\t"$3}')
```

Pick `$GLHOST` from `$CANDS` (each line is `host <TAB> account`):

- **One** → use its host, don't ask.
- **More than one** → `AskUserQuestion` (`header: "GitLab account"`, `multiSelect: false`, one option per candidate labelled `<host> (<account>)`, default to the one whose account matches `git config --get user.email`). Set `$GLHOST` to the choice.
- **None** → not logged into `$RHOST`: drop `-R` and let glab auto-detect; if that fails, surface "not logged into `$RHOST`: run `glab auth login`".

Carry `$GLHOST`/`$NS` forward; the create step addresses the MR with `glab mr create -R "$GLHOST/$NS"`.
