# Integrations

Cloud, VCS, contexts, worker pools - all the things stacks/intent attach to.

## Cloud integrations

| Cloud | Account-level | Stack-level | Intent-level |
|---|---|---|---|
| AWS | `awsIntegrationCreate(input)` | `awsIntegrationAttach(id, stack, read, write)` | `awsIntegrationIntentProjectAttach(intentProject, integration, read, write, awsRegion)` |
| Azure | `azureIntegrationCreate(input)` | `azureIntegrationAttach(id, stack, read, write, subscriptionId?)` | (via stack only) |
| GCP (legacy stack-level) | (none - stack only) | `stackIntegrationGcpCreate(id, tokenScopes)` | (via stack only) |

`read`/`write` are independent flags - a stack can have one read attachment and one write attachment per integration. A single integration may serve both. Update with `awsIntegrationAttachmentUpdate(id, read, write)`.

Inspect candidates: `attachableAwsIntegrationsInSpace(id)`, `attachableAzureIntegrationsInSpace(id)`. Listed via `awsIntegrations(includeLegacy?)`, `azureIntegrations`.

### Detach

`awsIntegrationDetach(id)`, `azureIntegrationDetach(id)`, `awsIntegrationIntentProjectDetach(intentProject, integration)`, `stackIntegrationGcpDelete(id)`.

## VCS integrations

| Provider | Mutation set | Notes |
|---|---|---|
| GitHub App (managed) | `githubIntegrationUpdate`, `githubAppCreateFromManifest`, `githubAppGenerateManifest` | Built-in; webhook URL via `account.githubIntegration` |
| GitHub Enterprise | `githubEnterpriseIntegrationCreate/Update/Delete/Test/RegenerateWebhookSecret` | Self-hosted GitHub |
| GitLab | `gitlabIntegrationCreate/Update/Delete/Test/RegenerateWebhookSecret` | |
| Bitbucket Cloud | `bitbucketCloudIntegrationCreateV2(input) / UpdateV2 / Delete / Test / RegenerateWebhookSecret` | Use the V2 API |
| Bitbucket Datacenter | `bitbucketDatacenterIntegrationCreate/Update/Delete/Test/RegenerateWebhookSecret` | |
| Azure DevOps | `azureDevOpsRepoIntegrationCreate/Update/Delete/Test` | Pass `accessibleProjects` to scope |

VCS integrations may be space-scoped (V2 APIs accept `customInput` with space). Inspect via `vcsIntegrations`, `vcsIntegration(provider, id?)`, `attachableVCSIntegrationsForProviderInSpace(id, provider)`. Test live with `vcsIntegrationTest(provider, id)`.

Webhook endpoints (per-account, immutable URLs): `gitlabWebhooksEndpoint`, `bitbucketCloudWebhooksEndpoint`, `bitbucketDatacenterWebhooksEndpoint`, `azureDevOpsWebhooksEndpoint`, `githubEnterpriseWebhooksEndpoint(id?)`.

## Contexts

A **Context** is a bundle of config (env vars + file mounts) attachable to multiple stacks. Useful to share secrets / env across stacks.

| Operation | Mutation |
|---|---|
| Create | `contextCreateV2(input)` (preferred) or `contextCreate` |
| Update | `contextUpdateV2(id, input, replaceConfigElements?)` - `replaceConfigElements: true` overwrites all config elements; default leaves them untouched |
| Delete | `contextDelete(id, force?)` |
| Add config elem | `contextConfigAdd(context, config)` |
| Delete config elem | `contextConfigDelete(context, id)` |
| Attach to stack | `contextAttach(id, stack, priority)` - higher priority wins on conflict |
| Detach | `contextDetach(id)` (id is the attachment ID) |

Inspect: `context(id)`, `contexts`, `attachableContextsInSpace(id)`. Stacks have `attachedContexts`, `attachableContexts`, runtime-merged `runtimeConfig`.

## Worker pools

Workers actually run runs. Two flavors: shared **public** pool and **private** pools.

| Operation | Mutation |
|---|---|
| Create | `workerPoolCreate(name, certificateSigningRequest, description?, labels?, space?, driftDetectionRunLimit?)` |
| Update | `workerPoolUpdate(id, name, ...)` |
| Reset CSR | `workerPoolReset(id, certificateSigningRequest)` |
| Cycle (rotate workers) | `workerPoolCycle(id)` |
| Delete | `workerPoolDelete(id)` |
| Drain a worker | `workerDrainSet(workerPool, id, drain)` |
| Attach to intent project | `intentProjectAttachWorkerPool(intentProject, workerPool)` |
| Detach from intent project | `intentProjectDetachWorkerPool(intentProject)` |

Stacks set their pool via `StackInput.workerPool` field (in `stackUpdate`/`stackCreate`).

Inspect: `workerPool(id)`, `workerPools`, `attachableWorkerPoolsInSpace(id)`, `publicWorkerPool`, `defaultPrivateWorkerPoolRunnerImage`, `defaultPublicWorkerPoolRunnerImage`.

## Pitfalls

- **`awsIntegrationAttach` requires at least one of `read` or `write` true.** Both false errors out.
- **Subscription override on Azure:** `azureIntegrationAttach(subscriptionId)` per attachment overrides the integration default. Forget it and you'll deploy to the wrong subscription.
- **VCS webhook URLs are immutable** per account/integration - regenerate the **secret** if compromised, not the URL.
- **Context priority** is numerical higher-wins. When two contexts both define `FOO`, the higher priority overrides. Document the convention in your team.
- **Worker pool deletion** while runs are queued orphans those runs - drain workers first.
- **Default GCP (legacy)** stack integration uses a Spacelift-generated service account; treat it as opaque.
