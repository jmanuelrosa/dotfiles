# Directory-scoped Google Cloud configurations: Design Doc

**Status:** Implemented
**Author:** Jose Manuel Rosa
**Date:** 2026-09-30
**Scope:** Fish startup configuration, shell provisioning, shell tests, and shell documentation.

## Summary

Select a Google Cloud CLI configuration automatically when an interactive Fish shell enters a configured directory tree.
The initial mapping is `~/Developer/work/addingwell` to `didomi`.
Selection stays local to each shell, without direnv, project environment files, or changes to Google's globally active configuration.

## Motivation

Different directory trees belong to different Google Cloud contexts.
Manually changing the globally active configuration can unintentionally affect another terminal working on a different project.
The desired workflow is to change directory and have subsequent CLI commands use the matching configuration, while leaving unrelated directories unchanged.

The switcher must not load `.env`, execute `.envrc`, or introduce another dependency.
Mappings belong in the trusted dotfiles rather than in individual project repositories.

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
Configuration directories are also explicitly created (`roles/shell/tasks/main.yml:39-49`).

`CLOUDSDK_ACTIVE_CONFIG_NAME` selects a configuration for the current process environment without changing Google's global default ([Google Cloud startup documentation](https://docs.cloud.google.com/sdk/gcloud/reference/topic/startup)).
The switcher therefore does not need to invoke `gcloud config configurations activate`.

## Design rules

- Run only in interactive Fish shells.
- Keep mappings and the handler together in one trusted, symlinked startup snippet.
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

Create `roles/shell/files/fish/conf.d/gcloud-profiles/gcloud-profiles.fish` with a global, unexported list of alternating directory roots and configuration names:

```fish
set -g GCLOUD_DIRECTORY_PROFILES \
    "$HOME/Developer/work/addingwell" didomi
```

Additional mappings are added as another root/name pair in this list.
`$HOME` is expanded at startup, rather than embedding a particular user's absolute home directory.
The snippet registers a `PWD` variable-change handler and invokes it once immediately, so a terminal opened inside the mapped tree starts with the correct configuration.

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
Add `.config/fish/conf.d` to the directory-creation list and `.config/fish/conf.d/gcloud-profiles.fish` to the existing backup list.
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

## Testing Decisions

Add `test_gcloud_profiles.py` to the existing shell suite, `roles/shell/files/fish/functions/tests/`, which is already registered in `pytest.ini:29`.
Existing tests such as `test_wt.py` locate their Fish subject relatively; the new tests follow that convention but execute the standalone snippet because source-text checks cannot verify event behavior or restoration.

Use the installed Fish binary with `--no-config`, an isolated temporary home, and temporary directory trees.
Test startup selection, actual `cd` events, descendant and sibling boundaries, overlapping mappings in both orders, incoming unset/empty/named values, repeated sourcing, per-shell independence, nested-shell baselines, and non-interactive exclusion.
Exercise `.envrc` non-execution at runtime and use a fake cloud executable to catch any cloud command invocation.
Creating an actual `.env` fixture returned `Operation not permitted`, so `.env` exclusion is checked through source-level assertions that there are no project-file loaders or environment-file references.
Run through `make test`; no vault or cloud credentials are needed.
Use `UV_OFFLINE=1` when dependency resolution must use uv's existing cache.

Verification: all 26 focused tests passed.
The full suite completed with 1,352 passed, seven failed, and one skipped.
The failing tests concern a Minion state-transition timeout, temporary lockfile permission errors, and generated harness sandbox configuration drift; none are in the shell suite.

## Open questions

- None required for the initial mapping; additional directory roots can be supplied later.
- Live Google Cloud verification must run outside this sandbox: the attempted configuration listing could not read `~/.config/gcloud/active_config` (`Operation not permitted`).

## Appendix: affected files

- Create `roles/shell/files/fish/conf.d/gcloud-profiles/gcloud-profiles.fish`.
- Modify `roles/shell/tasks/main.yml` for directory creation and backup coverage.
- Create `roles/shell/files/fish/functions/tests/test_gcloud_profiles.py`.
- Modify `roles/shell/README.md` to explain mappings, restoration, and credential boundaries.
- Read `roles/shell/files/fish/config.fish`, `roles/shell/files/fish/functions/tests/test_wt.py`, `pytest.ini`, and `Makefile` as integration and testing references.
