# Directory-scoped Google Cloud configurations

`gcloud-profiles.fish` selects an existing Google Cloud CLI configuration when an interactive Fish shell starts in or enters a mapped directory tree.
The initial mapping is `~/Developer/work/addingwell` and its children to `didomi`.
Add directory/configuration pairs to the central list:

```fish
set -g GCLOUD_DIRECTORY_PROFILES \
    "$HOME/Developer/work/addingwell" didomi
```

The longest matching root wins, regardless of list order.
Matching follows logical `$PWD`: similarly named siblings and unrelated symlink paths do not match.
The hook exports `CLOUDSDK_ACTIVE_CONFIG_NAME` in the current shell only, without changing Google's globally active configuration.
Leaving all mapped trees restores the incoming value, including an empty value or an unset variable.
A nested shell restores its own inherited value, not its parent's earlier baseline.

After installation or editing the mappings, open a new shell or reload:

```fish
source ~/.config/fish/conf.d/gcloud-profiles.fish
```

Reloading preserves an outstanding restoration snapshot.
The hook never invokes cloud commands, loads `.env` or `.envrc` files, authenticates accounts, or switches Application Default Credentials used by SDKs and Terraform.
See [the design](../../../../../../docs/design/gcloud-directory-profiles.md) for scope and verification limits.
