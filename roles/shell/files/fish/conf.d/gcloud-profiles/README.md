# Directory-scoped Google Cloud configurations

`gcloud-profiles.fish` selects an existing Google Cloud CLI configuration when an interactive Fish shell starts in or enters a mapped directory tree.
The initial mapping is `~/Developer/work/addingwell` and its children to `didomi`.
Edit the directory-to-configuration object in `~/.config/gcloud-profiles/config.json`:

```json
{
  "~/Developer/work/addingwell": "didomi"
}
```

The shell role installs jq and symlinks this file to the tracked `config.json` beside the Fish snippet.
Run `make run-role ROLE=shell` to install the dependency and configuration link.
Keys are absolute directory paths or start with `~/`, which expands to the current shell's `$HOME`.
Other environment variables are not interpolated.
Values name existing Google Cloud CLI configurations, not account emails.

The longest matching root wins, regardless of list order.
Matching follows logical `$PWD`: similarly named siblings and unrelated symlink paths do not match.
The hook exports `CLOUDSDK_ACTIVE_CONFIG_NAME` in the current shell only, without changing Google's globally active configuration.
Leaving all mapped trees restores the incoming value, including an empty value or an unset variable.
A nested shell restores its own inherited value, not its parent's earlier baseline.

After installation or editing the mappings, open a new shell or reload:

```fish
source ~/.config/fish/conf.d/gcloud-profiles.fish
```

jq parses the JSON only at startup or explicit reload; changing directory only scans the loaded mappings with Fish builtins.
Reloading preserves an outstanding restoration snapshot.
An empty object disables all mappings and restores any captured incoming value on reload.
If parsing fails, jq prints its diagnostic and the shell keeps its previously loaded mappings; a failed initial load leaves the incoming configuration unchanged.
The hook never invokes cloud commands, loads `.env` or `.envrc` files, authenticates accounts, or switches Application Default Credentials used by SDKs and Terraform.
See [the design](../../../../../../docs/design/gcloud-directory-profiles.md) for scope and verification limits.
