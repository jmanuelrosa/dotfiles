# Per-configuration Application Default Credentials

`gcp_adc login [CONFIGURATION]` signs ADC in as the account in an existing named Google Cloud CLI configuration.
Without an argument, it uses `CLOUDSDK_ACTIVE_CONFIG_NAME`.
The browser login runs only when explicitly requested, never on a directory change.

Each profile has an isolated SDK directory at `~/.config/gcloud-profiles/adc/<configuration>/`.
Login uses that directory through a process-local `CLOUDSDK_CONFIG`, without overwriting shared ADC, activating a configuration globally, or changing the caller's environment.
The profile directory is mode 0700 and its ADC file is mode 0600.
These files contain refresh credentials and must never be committed.

`gcp_adc path [CONFIGURATION]` prints the matching ADC file path without accessing Google Cloud.
The directory hook and `s-db` use this to select credentials consistently.
Login uses the named configuration's project for the ADC quota project when one is configured.
It does not grant IAM permissions.

After changing a configuration's account or revoking its credentials, repeat `gcp_adc login CONFIGURATION`.
See ../../conf.d/gcloud-profiles/README.md for directory selection and IAM prerequisites.
