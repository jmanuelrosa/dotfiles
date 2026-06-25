# work

Work-only role. Runs only when `profile=work`.

## What it does

- Installs `acli` (Atlassian) and the `fossa` cask via `BREW_PACKAGES` (with the `atlassian/homebrew-acli` tap). Relies on `shell` / `coreutils` (which run before `work` in `profile_roles[work]`) for `fish` and `television`.
- Renders `~/.config/fish/conf.d/work-secrets.fish` from `templates/exports.fish.j2` (work tokens, mode 0600).
- Symlinks every script under `files/scripts/` into `~/.local/bin/`.
- Renders `~/Library/Application Support/glab-cli/config.yml` from `templates/glab/config.yml.j2` (personal + work GitLab hosts) and verifies each host is authenticated. See [GitLab auth (glab)](#gitlab-auth-glab).
- Symlinks the Jira Television cable (`files/television/cable/jira.toml`) and its helper fish function (`files/fish/functions/_tv_jira.fish`) into `~/.config/`. Both depend on `acli` so they live here rather than in `shell`.

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

Skills that query GitLab **outside** a repo (e.g. `weekly-recap`) can't infer the
host from a remote, so they enumerate every authenticated host and pass
`--hostname` per host to cover both accounts.

## Profile gating

Listed in `profile_roles[work]` only; the personal profile skips this role.
