# AWS profile helpers

Short commands over the AWS CLI's own profiles, so switching accounts needs no flags to remember.

| Command | Does |
|---|---|
| `awsp` | Pick a profile in television (preview shows its account and role) and export it as `AWS_PROFILE` |
| `awsp <name>` | Switch straight to a named profile |
| `awsp off` | Clear `AWS_PROFILE` |
| `awsc` | Show the active profile, its account and the assumed role ARN |
| `awsl` | Sign in again to the SSO session behind the active profile |

`awsp` only opens the browser when the cached SSO token is missing or expired, and every profile on the same `sso-session` shares that token.
`AWS_PROFILE` is a global export, so it lasts for the current shell and its children and never leaks into other terminals.

The picker is the `aws-profiles` cable in [television/cable](../../../television/cable/aws-profiles.toml).
The profiles themselves come from `~/.aws/config`, which the work role renders; see its README's AWS section.
