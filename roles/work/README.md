# work

Work-only role. Runs only when `profile=work`.

## What it does

- Installs `acli` (Atlassian) and the `fossa` cask via `BREW_PACKAGES` (with the `atlassian/homebrew-acli` tap). Relies on `shell` / `coreutils` (which run before `work` in `profile_roles[work]`) for `fish` and `television`.
- Renders `~/.config/fish/conf.d/work-secrets.fish` from `templates/exports.fish.j2` (work tokens, mode 0600).
- Symlinks each tool named in `WORK_SCRIPTS` into `~/.local/bin/`. See [Scripts](#scripts).
- Renders `~/Library/Application Support/glab-cli/config.yml` from `templates/glab/config.yml.j2` (personal + work GitLab hosts) and verifies each host is authenticated. See [GitLab auth (glab)](#gitlab-auth-glab).
- Symlinks the Jira Television cable (`files/television/cable/jira.toml`) and its helper fish function (`files/fish/functions/_tv_jira.fish`) into `~/.config/`. Both depend on `acli` so they live here rather than in `shell`.

## Scripts

Each is a directory under `files/scripts/` holding the executable and whatever else it owns, and the
executable carries the directory's name. The role links the ones named in `WORK_SCRIPTS`, so editing them
here takes effect without re-running the playbook.

- `s-task <ref>`: creates a git branch from an issue, off an up-to-date default branch, and pushes it so the issue links back to it. It is dual-provider and infers which from the reference shape: `PROJ-123` goes to Jira via `acli`, while `456`, `#456`, or a GitHub issue URL goes to GitHub via `gh` (installed by the `apps` role). Force either with `--jira` / `--github`. Branch names are `<type>/PROJ-123-<slug>` for Jira and `<type>/gh-456-<slug>` for GitHub, capped at 50 chars to stay under commitlint's `header-max-length`, truncating the slug at a hyphen boundary. The branch type comes from the Jira issue type, or for GitHub from the issue's native type first and its labels second; `--type` overrides it and `--dry` prints the branch name without creating anything. The `commit` and `pr` skills parse both ticket shapes back out of the branch name, so keep the three in sync. See [Issue linking](#issue-linking) for the push behavior and `--no-push`.
- `s-db [production|staging|local]`: connects to cloud-sql-proxy for the given environment. Three subcommands
  work on the databases themselves rather than on the connection: `s-db dump [ENV]` writes a custom-format dump
  into `backups/`, `s-db restore [FILE]` loads one into local (with no `FILE` it lists what is there and you pick),
  and `s-db dumps` prints that listing. `--dry` prints the exact `pg_dump` / `pg_restore` command without running
  it. Anything that is not a subcommand is still the connect call, so `s-db staging` and `s-db -d prod` are
  unchanged. See [Database dumps](#database-dumps).
- `s-release [REPO ...]`: opens the pull request that deploys to production, which at addingwell means merging
  `develop` into `master`. With no argument it lists every repo that still deploys that way and you pick from it;
  naming repos skips both the lookup and the prompt, which is the point when several ship at once. `--list` prints
  the listing and stops, `--dry` prints the command and the body without creating anything. See
  [Release PRs](#release-prs).
- `weekly-recap [--days N | --since DATE]`: summarises recent Jira, GitHub and GitLab activity as markdown,
  grouped by project or repo. Each platform degrades on its own, so an unauthenticated CLI records one note
  and the other two still report. It lives here rather than in the `ai` role because all three of its sources
  are work ones, and the multi-host `glab` iteration below exists only for the two-account split this role
  creates. On a personal machine it is simply not installed.

### Issue linking

`s-task` ends by putting the branch on `origin`, because that is what makes the issue show it. The two providers get there differently, and only one of them is an API call:

- **GitHub** has a real linked-branch object, and `gh issue develop <n> --name <branch> --base <default> --checkout` is the only thing that creates one. It creates the remote ref and registers it on the issue in a single call, so `s-task` uses it instead of creating the branch locally. A linked branch **is** a remote ref, so there is no local-only version of this. GitHub registers the link only at creation time: if the branch already exists, `s-task` says so and leaves linking to the issue's Development panel.
- **Jira has no API for this.** `acli jira workitem link` creates issue-to-issue links (blocks, relates to), not source-code links. The Development panel is filled in by the Jira git integration app, which finds branches by scanning their names for the issue key. `s-task` already puts the key in the branch name, so the only requirement is that the branch exists on `origin`; the panel picks it up on the integration's next sync. Writing it directly would need `/rest/devinfo/0.10/bulk`, which authenticates as a Connect app (JWT), not as a user.

`--no-push` keeps the branch local. On the Jira path the Development panel then fills in later, whenever the branch gets pushed. On the GitHub path there is no linked branch at all, and the script prints the `gh issue develop` command to run after pushing.

**The push only ever covers a branch `s-task` just created**, off the default branch's tip, with no commits on it. Re-run it on a branch that already exists and it switches to the branch and pushes nothing, because that branch may hold work, and pushing work is `/pr`'s job and its confirmation gate. This is the property that lets `git-skill-gate.sh` leave `s-task` alone: the hook sees Bash commands, not the subprocesses they spawn, so `s-task` could push whatever it wanted, and the script is what keeps that narrow. Its docstring records the exception.

Because the script pushes, running it creates a remote ref before `/pr` does. Branch-push CI will fire on an empty branch, and abandoning the work leaves a ref on the remote.

### Database dumps

`s-db` holds one environment table and every subcommand reads it, which is the reason `dump` and `restore` live here rather than in a script of their own:

| env | port | proxy | user | role |
|---|---|---|---|---|
| `production` | 5434 | yes | `postgres` | - |
| `staging` | 5433 | yes | `postgres` | - |
| `local` | 5432 | no | `testuser` | `testuser` |

`local` is the environment added for these subcommands, and it is the one with nothing to connect: `s-db local` says so and exits 0 rather than treating it as an error.
Database is `addingwell` throughout. All of it is hardcoded, for the same reason the Cloud SQL instances and `s-release`'s `ORG` are: one org, and a layout that changes rarely enough that a config file would only be a second place to look.

Four decisions carry the design, and the first two are the ones not to weaken:

- **`restore` only ever targets local, and no flag reaches further.** Not a confirmation prompt, no `--to`: the option does not exist. A dump is read back locally, and one typo on a target flag would be a production incident. This is the same argument that keeps `s-release`'s base and head constants.
- **`--exclude-table='public._dlt*'` is quoted once, in the script.** In fish an unmatched glob is a hard error, so a retyped command that loses the quotes does not pass the literal through: it fails to launch. `--include-dlt` keeps those tables when they are actually wanted.
- **COPY rather than `--inserts`.** The flag is legal with a custom-format archive, but `man pg_dump` calls the resulting restore "very slow" and the flag "mainly useful for making dumps that can be loaded into non-PostgreSQL databases", which these are not. It survives as `--inserts` for the day a dump has to go somewhere else.
- **No `--password`.** Per the same manual it "is never essential, since pg_dump will automatically prompt for a password if the server demands password authentication"; it only saves a round trip. Dropping it is what lets a `~/.pgpass` or `PGPASSWORD` be honoured if one ever appears, and changes nothing while none does.

`dump` brings the proxy up detached when the port is quiet and reuses it when it is already serving, so one command is the whole job; the proxy stays up afterwards and the script prints the `kill` for it.
Dumps land in `$WORK_DIR/backups/` as `addingwell-<env>-<YYYYMMDD-HHMMSS>.dump`, and the time is in there because a second dump on the same day must not silently overwrite the first.
`--out` overrides the path, and the listing orders by mtime rather than by name so an `--out` file still sorts where it belongs.

`pg_restore` exits non-zero for warnings as well as for failures, so a non-zero exit is reported as a warning naming the code rather than as a `✓`: a half-loaded database looks fine right up until it does not.
`--clean` (which implies `--if-exists`, since `--clean` alone errors on every object that is not there yet) is what to reach for when the objects are already present, and it prompts before dropping anything.

**`backups/` holds real staging and production data.** It sits in the work directory rather than in any checkout, and nothing here ever commits it.

### Release PRs

`s-release` is **temporary by design**. Every repo's `deploy-prod.yml` triggers on a push to `master`, so a release is a PR from `develop`, and merging it is the deploy. When `master` goes, so does this script.

Which repos it offers is **derived, never listed**: one GraphQL call keeps the repos whose default branch is `develop` and that still have a `master` branch. Nothing else in the org has both, so a repo retiring `master` drops off the listing by itself and there is no list to remember to prune. The same call reports any open `develop` into `master` PR, which is how a duplicate is refused; scoping it to `head: develop` is also what keeps it from colliding with the release-please PRs that some of these repos open against `master`.

Three deliberate choices worth knowing:

- **The body replaces the template.** Four of these repos ship a `pull_request_template.md`, and clicking through the UI leaves its checklist in place unfilled, which is what most historic release PRs contain. `s-release` sends a body listing the pull requests being released plus a compare link instead, matching what the most recent hand-made ones did. It walks first parents back to the merge base rather than listing every commit, because the repos disagree about merge style and a raw list is seven lines for three pull requests.
- **The label is the announcement.** `Ready for review` is what each repo's `slack-pr-notification.yml` keys on, so a default run tells the team. `--no-label` opens one quietly.
- **It never merges,** and must not learn how. `git-skill-gate.sh` blocks `gh pr create` outside `/pr` and only sees Bash commands, not the subprocesses they spawn, so this script could open anything it liked. What keeps that exception narrow is that base and head are constants with no flag to reach them, it commits and pushes nothing, and the deploy itself stays a human act. Its docstring records the exception, the same way `s-task`'s does.

It needs no clone: both refs are already on the remote, so `--repo` and `--head` are enough and the script never looks at a working tree. That also sidesteps the fact that the local directory names do not match the repo names (`~/Developer/work/addingwell/front` is `aw-front`).

## Vars

- `BREW_PACKAGES` (defaults/main.yml) — taps/formulas/casks for the work tooling.
- Vault-encrypted secrets live in `vars/work.yml`. See `vars/work.yml.example` for the full key list.

## SSH keys

Work SSH keys are deployed by the `ssh` role from `SSH_KEYS_EXTRA`, defined in `host_vars/work.yml`. This role does not touch `~/.ssh/`.

## GitLab auth (glab)

`glab` is configured for **two GitLab accounts that both live on the real `gitlab.com`**:

- `gitlab.com` — personal account (SSH key `~/.ssh/id_ed25519`).
- `gitlab.com-work` — work account. This is a **local alias, not a real domain**: the SSH host block in `roles/ssh/files/config` maps it to the real `gitlab.com` using the work key `~/.ssh/id_didomi`. The alias is what keeps the two accounts apart.

Hosts and users are rendered into `~/Library/Application Support/glab-cli/config.yml` from `templates/glab/config.yml.j2`; the work username comes from `GLAB_WORK_USER` in the vault. **Tokens are never stored in this repo** — they live in the macOS keychain via `--use-keyring`. The playbook only *verifies* auth (the "Fail loudly" task); you create the tokens manually.

### Authenticating a host

For each host that needs it:

1. Create a Personal Access Token at <https://gitlab.com/-/user_settings/personal_access_tokens>, signed in to the **matching account** (personal or work).
2. Run, replacing `<HOST>`:
   ```sh
   glab auth login --hostname <HOST> --git-protocol ssh --use-keyring
   ```
3. Paste the PAT when prompted.

For `gitlab.com-work`, glab asks a few extra questions because the host is an alias. Answer with the **real** values for everything except the SSH hostname:

| Prompt | Answer |
|---|---|
| API hostname | `gitlab.com` |
| SSH hostname | `gitlab.com-work` |
| Container registry / dependency proxy domains | `gitlab.com,gitlab.com:443,registry.gitlab.com` |
| Token | PAT from the **work** account |

Rule of thumb: anything that reaches a real server uses `gitlab.com`; the **only** field that uses the `gitlab.com-work` alias is the SSH hostname, because that one is resolved locally by `~/.ssh/config` to select the work key. Picking `gitlab.com` there would route work git operations through the personal key.

Verify with `glab auth status --hostname gitlab.com-work`, then re-run the playbook.

### Working with work repos

Clone work repositories with the **`gitlab.com-work` remote**, not the real host:

```sh
git clone git@gitlab.com-work:group/project.git
```

This is the precondition that makes everything else automatic. Both SSH (work key
`id_didomi`) and `glab` (work token) resolve the right identity from the remote
host, so the `pr` and `commit` skills create MRs as the work account with no
`--hostname` flag. If you accidentally clone via `git@gitlab.com:…`, git uses the
personal key and `glab` uses the personal token — wrong account. Fix an existing
clone with `git remote set-url origin git@gitlab.com-work:group/project.git`.

Tooling that queries GitLab **outside** a repo (e.g. the `weekly-recap` script)
can't infer the host from a remote, so it enumerates every authenticated host and
passes `--hostname` per host to cover both accounts.

## Profile gating

Listed in `profile_roles[work]` only; the personal profile skips this role.
