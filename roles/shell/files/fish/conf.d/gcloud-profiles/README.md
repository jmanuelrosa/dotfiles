# Directory-scoped Google Cloud configurations

`gcloud-profiles.fish` selects an existing Google Cloud CLI configuration when an interactive Fish shell starts in or enters a mapped directory tree.
The mappings select `didomi` under `~/Developer/work/addingwell` and `pentla` under `~/Developer/work/pentla`, including their children.
Edit the directory-to-configuration object in `~/.config/gcloud-profiles/config.json`:

```json
{
  "~/Developer/work/addingwell": "didomi",
  "~/Developer/work/pentla": "pentla"
}
```

The shell role installs jq and symlinks this file to the tracked `config.json` beside the Fish snippet.
Run `make run-role ROLE=shell` to install the dependency and configuration link.
Keys are absolute directory paths or start with `~/`, which expands to the current shell's `$HOME`.
Other environment variables are not interpolated.
Values name existing Google Cloud CLI configurations, not account emails.

The longest matching root wins, regardless of list order.
Matching follows logical `$PWD`: similarly named siblings and unrelated symlink paths do not match.
The hook exports `CLOUDSDK_ACTIVE_CONFIG_NAME` and selects that configuration's local ADC file through `GOOGLE_APPLICATION_CREDENTIALS`, without changing Google's globally active configuration or shared ADC.
The credential path is `~/.config/gcloud-profiles/adc/<configuration>/application_default_credentials.json`.
Leaving all mapped trees restores both incoming values, including empty values or unset variables.
A missing profile ADC file stays selected rather than falling back to credentials from another account.
An unset CLI configuration variable falls back to Google's globally active configuration, which the apps role pins to an empty `default` configuration.
Without an inherited selection, agent shells, IDEs and scripts land there too, so an unmapped `gcloud` command fails for lack of an account or project rather than writing into a work configuration.
Give a new project its own named configuration and a mapping here; never set an account or project on `default`.
A nested shell restores its own inherited value, not its parent's earlier baseline.

After installation or editing the mappings, open a new shell or reload:

```fish
source ~/.config/fish/conf.d/gcloud-profiles.fish
```

jq parses the JSON only at startup or explicit reload; changing directory only scans the loaded mappings with Fish builtins.
Reloading preserves an outstanding restoration snapshot.
An empty object disables all mappings and restores any captured incoming value on reload.
If parsing fails, jq prints its diagnostic and the shell keeps its previously loaded mappings; a failed initial load leaves the incoming configuration unchanged.
The hook never invokes cloud commands, loads `.env` or `.envrc` files, or authenticates accounts.
SDKs, Terraform and other tools that support ADC inherit the selected credential file when launched from the mapped shell.
Already-running applications keep their existing environment.

## Credential setup

Install the shell role, then explicitly sign in once per configuration:

```fish
gcp_adc login didomi
gcp_adc login pentla
```

The helper uses each named configuration's account and project, but writes ADC into its own isolated SDK directory.
It does not overwrite shared ADC or change the caller's environment.
Repeat login when credentials are revoked or a configuration's account changes.
Credential files are machine-local secrets, not provisioning inputs or repository files.
See ../../functions/gcp_adc/README.md for the helper's commands and file permissions.

For Cloud SQL IAM access, an administrator must enable IAM database authentication, add the IAM database user, and grant database privileges.
The account needs `roles/cloudsql.client` and `roles/cloudsql.instanceUser` on the instance's project, plus `roles/serviceusage.serviceUsageConsumer` on the quota project.
Login does not grant these permissions.
`s-db` sets its proxy quota project from the selected instance rather than trusting a stale ADC quota project.

Google documentation: <https://docs.cloud.google.com/docs/authentication/application-default-credentials> and <https://docs.cloud.google.com/sql/docs/postgres/iam-logins>.
