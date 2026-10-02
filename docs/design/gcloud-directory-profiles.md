# Directory-scoped Google Cloud configurations: Design Doc

**Status:** Implemented
**Author:** Jose Manuel Rosa
**Date:** 2026-09-30
**Updated:** 2026-10-02
**Scope:** Fish startup configuration, shell provisioning, shell tests, and shell documentation.

## Summary

Select a Google Cloud CLI configuration automatically when an interactive Fish shell enters a configured directory tree.
The initial mapping is `~/Developer/work/addingwell` to `didomi`.
Selection stays local to each shell, without direnv, project environment files, or changes to Google's globally active configuration.

## Motivation

Different directory trees belong to different Google Cloud contexts.
Manually changing the globally active configuration can unintentionally affect another terminal working on a different project.
The desired workflow is to change directory and have subsequent CLI commands use the matching configuration, while leaving unrelated directories unchanged.

The switcher must not load `.env` or execute `.envrc`.
Mappings belong in a trusted, dotfiles-owned JSON configuration rather than in individual project repositories or the event-handler source.
The shell role provisions jq to parse that file once at startup or explicit reload, keeping parser processes out of directory changes.

## Non-goals

- Create, authenticate, or validate Google Cloud configurations.
- Switch Application Default Credentials, SDK credentials, or Terraform authentication.
- Switch configurations inside non-interactive scripts or programs that change their own working directory.
- Change shell prompts or print notifications.
- Associate multiple paths to the same tree by resolving symlinks.
- Add mappings for Pentla or personal projects until their roots are supplied.

## Background

The shell already defines an explicitly loaded event handler and initializes fnm's directory-sensitive integration in `roles/shell/files/fish/config.fish:9-35`.
Fish event handlers must be loaded before events can invoke them; defining one only in an autoloaded function file would not register it automatically.
A startup snippet avoids that problem ([Fish event handlers](https://fishshell.com/docs/current/language.html#event-handlers)).

The shell role discovers `.fish` snippets recursively under `files/fish/conf.d/` and symlinks them by filename into the user's flat Fish configuration directory.
The backup list is explicit, so a new snippet needs its own entry (`roles/shell/tasks/main.yml:62-90`).
Configuration directories are also explicitly created in the same task file.
The JSON mapping file needs its own directory, backup entry, and symlink task because the generic discovery only installs `*.fish` files.

`CLOUDSDK_ACTIVE_CONFIG_NAME` selects a configuration for the current process environment without changing Google's global default ([Google Cloud startup documentation](https://docs.cloud.google.com/sdk/gcloud/reference/topic/startup)).
The switcher therefore does not need to invoke `gcloud config configurations activate`.

## Design rules

- Run only in interactive Fish shells.
- Keep mappings in a trusted, symlinked JSON file and load them once when the Fish snippet is sourced.
- Keep the directory-change handler in Fish so it changes the current shell and performs no parser invocation on directory changes.
- Match a root itself and its descendants, never a similarly named sibling.
- Choose the longest matching root when mappings overlap, regardless of their order.
- Match Fish's logical `$PWD`, not a symlink's resolved target.
- Capture the incoming configuration when first entering a mapped tree; restore it when leaving all mapped trees.
- Distinguish an unset incoming variable from an explicitly empty one.
- Keep bookkeeping shell-local and non-universal; re-sourcing must not overwrite an outstanding restoration snapshot.
- Never read project configuration or credential files, invoke cloud commands, or persist a global selection.

This is a shallow shell-glue module.
Google Cloud continues to own configurations, account selection, projects, and credentials.

## Design

### 1. Central mapping and startup handler

Store the mapping in `roles/shell/files/fish/conf.d/gcloud-profiles/config.json`, installed at `~/.config/gcloud-profiles/config.json`:

```json
{
  "~/Developer/work/addingwell": "didomi"
}
```

Each object key is an absolute directory path or a path beginning with `~/`; each value names an existing Google Cloud CLI configuration.
The loader expands a leading `~/` against the current shell's `$HOME` without evaluating arbitrary environment variables or executable content.
The JSON object needs no ordering because the longest matching root wins.

`gcloud-profiles.fish` uses jq's NUL-delimited output and Fish's `string split0` to load an unexported in-memory list without splitting spaces or interpreting glob characters.
The loader replaces that list only after jq succeeds, preserving previously loaded mappings after a malformed edit.
An empty object clears the list, and the initial handler call restores any outstanding baseline.
On an invalid initial load, jq prints a diagnostic and no directory override is applied.

The snippet registers a `PWD` variable-change handler and invokes it once immediately, so a terminal opened inside the mapped tree starts with the correct configuration.
Mapping edits take effect in a new shell or after explicitly sourcing the snippet, not on every directory change.

### 2. Matching and restoration

The handler scans the trusted mapping pairs using Fish builtins and selects the longest exact-root or descendant match.
It exports that configuration through `CLOUDSDK_ACTIVE_CONFIG_NAME`.
On the first matched directory, it saves whether the incoming variable existed and its value.
Transitions between mapped directories retain that original snapshot rather than replacing it with the last mapped configuration.

On leaving every mapped tree, the handler restores the saved value or erases the override if the incoming variable was unset, then clears the snapshot.
If no mapping has been entered, an unmatched directory does not modify the variable.
A manually selected environment value outside mapped directories becomes the baseline for the next entry.

Each shell owns its own snapshot.
A nested shell treats the environment inherited from its parent as its incoming baseline; no restoration state is exported between shells.

### 3. Provisioning

Use the shell role's recursive conf.d discovery and flat symlink installation to install the snippet.
Install jq through the shell role's formulas and create `~/.config/gcloud-profiles` along with its backup directory.
Include `.config/gcloud-profiles/config.json` in the existing backup flow, then explicitly symlink the tracked JSON there.
Keep `.config/fish/conf.d` and the snippet's existing backup coverage.
Do not add an Ansible template or host-variable layer: this repository already uses live symlinks for trusted shell configuration.
Install through `make run-role ROLE=shell`, which requires the usual interactive passwords.

## Runtime behaviour matrix

| Situation | Result |
|---|---|
| Start or enter `~/Developer/work/addingwell` | Use `didomi` |
| Enter a child of that directory | Continue using `didomi` |
| Enter a similarly named sibling, such as `addingwell-other` | No match; restore the incoming environment if needed |
| Enter a more specific mapped child | Use its configuration, retaining the original snapshot |
| Return from that child to the mapped parent | Use the parent's configuration |
| Leave all mapped roots with no incoming override | Unset the variable, letting Google Cloud use its global default |
| Leave all mapped roots with an incoming override, including an empty value | Restore that value |
| Start a nested shell inside a mapped root, then leave it | Restore the configuration inherited by that nested shell |
| Run two separate terminals | Their selections and snapshots remain independent |
| Run a non-interactive Fish script | The snippet does not install the switcher or change its environment |

## Alternatives considered

- **direnv or ondir:** unnecessary dependencies for a single-variable switcher; project environment loading is unwanted.
- **Project-local `.gcloud-profile` files:** require repository-local artifacts and parent-directory discovery when central ownership is preferred.
- **Global activation on each directory change:** changes shared state and allows terminals to interfere with each other.
- **Ansible-rendered mappings:** add provisioning state and delay mapping edits until a playbook run, unlike the existing symlinked shell configuration.
- **Inline or executable Fish mappings:** avoid a parser dependency but keep mapping edits in executable shell syntax rather than a standard data format.
- **TOML with Python:** supports a standard, comment-friendly format but adds a larger runtime than jq; local sample parsing was also slower.
- **Automatic reload on directory changes:** adds file checks and parser state to the event handler when explicit reload is sufficient.

## Testing Decisions

Add `test_gcloud_profiles.py` to the existing shell suite, `roles/shell/files/fish/functions/tests/`, which is already registered in `pytest.ini:29`.
Existing tests such as `test_wt.py` locate their Fish subject relatively; the new tests follow that convention but execute the standalone snippet because source-text checks cannot verify event behavior or restoration.

Use the installed Fish binary with `--no-config`, an isolated temporary home, and temporary directory trees.
Give each isolated shell its own JSON configuration and test startup selection, actual `cd` events, descendant and sibling boundaries, overlapping mappings in both orders, incoming unset/empty/named values, repeated sourcing, per-shell independence, nested-shell baselines, and non-interactive exclusion.
Also test absolute and home-relative roots, empty mappings, edits requiring explicit reload, parse failure with partial output, and preservation of previously loaded mappings and restoration snapshots.
A recording jq wrapper verifies that parsing happens only at source time and never in non-interactive shells or on directory changes.
The provisioning assertions cover jq, config and backup directories, the JSON backup entry, the explicit symlink, and the shipped initial mapping.
Exercise `.envrc` non-execution at runtime and use a fake cloud executable to catch any cloud command invocation.
Creating an actual `.env` fixture returned `Operation not permitted`, so `.env` exclusion is checked through source-level assertions that there are no project-file loaders or environment-file references.
Run through `make test`; no vault or cloud credentials are needed.
Use `UV_OFFLINE=1` when dependency resolution must use uv's existing cache.

Verification for the JSON configuration update: all 45 focused tests passed, and the complete Fish functions suite passed all 55 tests.
The full suite, run with `GIT_CONFIG_GLOBAL=/dev/null UV_OFFLINE=1 make test` to avoid inaccessible global Git configuration, completed with 1,385 passed, five failed, and one skipped.
The failures concern a Minion state-transition timeout, Pi permission-package pinning, and temporary lockfile permission errors; none are in the shell suite.
`make lint` reached the playbook syntax check but could not decrypt the vault, and `make check-role ROLE=shell` could not proceed without the interactive vault and become passwords.

## Open questions

- None required for the initial mapping; additional directory roots can be supplied later.
- Live Google Cloud verification must run outside this sandbox: the attempted configuration listing could not read `~/.config/gcloud/active_config` (`Operation not permitted`).

## Appendix: affected files

- Create `roles/shell/files/fish/conf.d/gcloud-profiles/gcloud-profiles.fish`.
- Create `roles/shell/files/fish/conf.d/gcloud-profiles/config.json`.
- Modify `roles/shell/defaults/main.yml` to provision jq.
- Modify `roles/shell/tasks/main.yml` for directory creation, backup coverage, and the explicit JSON symlink.
- Create `roles/shell/files/fish/functions/tests/test_gcloud_profiles.py`.
- Modify `roles/shell/README.md` to explain mappings, restoration, and credential boundaries.
- Read `roles/shell/files/fish/config.fish`, `roles/shell/files/fish/functions/tests/test_wt.py`, `pytest.ini`, and `Makefile` as integration and testing references.
