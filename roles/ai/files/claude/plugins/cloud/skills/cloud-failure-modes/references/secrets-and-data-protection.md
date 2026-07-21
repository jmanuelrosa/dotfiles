# Secrets and data protection

When to read: the brief or diff touches secrets, KMS keys, encryption settings, buckets, snapshots, or anything holding data.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Secret literal in configuration.** A password or token in code, a variable file, or a variable default lands in version control and in state, and rotating it becomes a code change.
  Check: secret values exist only in a secret manager; configuration carries references, and generated secrets flow resource to resource without a literal.
- **State as an accidental secret store.** Resource attributes and outputs land in state in plaintext; anyone with backend read access reads them.
  Check: outputs derived from secrets are marked sensitive; resources offering write-only or ephemeral secret arguments use them; whatever still lands in state is named in the report.
- **Encryption left to the default.** Many storage services create unencrypted, or on a provider-default key, unless asked; the resource comes up fine and the finding arrives in the audit.
  Check: everything that stores data encrypts at rest, and the key choice (platform-managed vs customer-managed) follows the project's idiom deliberately.
- **Key without rotation or with a loose policy.** A customer-managed key that never rotates ages into a bigger blast radius, and a key policy broad enough for everyone in the account undoes the encryption.
  Check: customer-managed keys enable rotation, and the key policy is scoped like any IAM policy: exact principals, exact operations.
- **One key for everything.** A single key spanning environments or data classes couples their blast radius: compromising the least protected system unlocks the most sensitive data.
  Check: keys follow the project's separation idiom (per environment or per data class); a new data store states which key it uses and why.
- **Public access blocked at only one layer.** A bucket set private through its ACL is still exposable by a policy or an account-level gap; layered public-access blocks exist because single layers fail.
  Check: account-level and resource-level public-access blocks are on; "private" is verified at every layer the provider offers, not just the nearest one.
- **Snapshot and image exposure.** Backups, snapshots, and machine images inherit none of the source's access controls; a public or broadly shared snapshot is the whole database walking out.
  Check: snapshots and images are unshared or shared to named accounts, and encrypted like their source.
- **Deployment inputs recorded in plaintext.** Deployment engines record parameters into history and logs; a sensitive parameter not marked as such is readable long after the run.
  Check: sensitive parameters use the tool's secure marking (sensitive flags, secure decorators) so history, logs, and diffs redact them.

## Escalation triggers (`needs-decision`)

- Making a data store, snapshot, or machine image publicly accessible (also an ask-first boundary in the agent).
- A brief that supplies a secret value to embed: never write it into configuration; escalate with the secret-manager design instead.
- Weakening encryption or a key policy on data that already exists.

## What good looks like

- Configuration is safe to publish: nothing in it grants access to anything.
- Every layer that could expose data (ACL, policy, account block, snapshot sharing) is explicitly closed.
- Keys rotate, and their policies read like the IAM they are.
