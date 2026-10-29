# Example: intent end-to-end

**Goal:** create a new intent project in space `staging`, attach an existing AWS integration, and create an S3 bucket via the `intent` tool.

Touches `mutate` (project setup) and `intent` (resource provisioning). Multiple destructive-op gates.

## Step 1 - confirm preconditions

```
query searchIntentProjects
  variables: { input: { predicates: [{ field: "name", constraint: { stringEquals: ["staging-app"] } }] } }
  select: "edges { node { id name space { id } } }"
```

If a project of that name already exists, ask whether to use it instead of creating a new one. If creating fresh, also confirm the AWS integration exists:

```
query awsIntegrationByName
  variables: { name: "staging-aws" }
  select: "id name space { id }"
```

## Step 2 - destructive-op gate (project create)

> Create intent project `staging-app` in space `staging` with description "MCP-managed app infra". Reply `YES` or `CONFIRM` to proceed.

On confirmation:

```
mutate intentProjectCreate
  variables: { name: "staging-app", description: "MCP-managed app infra", space: "staging" }
  select: "id name space { id } state"
```

Capture project `id`.

## Step 3 - attach AWS integration

> Attach AWS integration `staging-aws` to project `staging-app` with read+write in region `us-east-1`. Reply `YES` or `CONFIRM`.

```
mutate awsIntegrationIntentProjectAttach
  variables: { intentProject: "<projectId>", integration: "<awsIntegrationId>", read: true, write: true, awsRegion: "us-east-1" }
  select: "intentProject { id } integration { id } read write awsRegion"
```

## Step 4 - activate the project

```
mutate intentProjectActivate
  variables: { id: "<projectId>" }
  select: "id name"
```

After activation, subsequent `intent` calls operate on this project.

## Step 5 - provider preflight

**Mandatory** before any `intent create`.

```
provider search { query: "aws" }
```

Pick the right namespace (likely `hashicorp/aws`) and a recent version.

```
provider resources-describe
  provider: "hashicorp/aws"
  provider_version: "5.70.0"
  type: "aws_s3_bucket"
```

Read the schema. Required fields, optional fields, valid types. Build `config` strictly to it.

## Step 6 - destructive-op gate (resource create)

> Create `aws_s3_bucket` resource `app-uploads` in project `staging-app`:
> ```
> bucket: "staging-app-uploads-2026"
> tags:   { Environment: "staging", ManagedBy: "spacelift-intent" }
> ```
> Reply `YES` or `CONFIRM`.

## Step 7 - dispatch (async if expected to take >30s)

S3 buckets are usually fast - sync is fine:

```
intent create
  provider: "hashicorp/aws"
  provider_version: "5.70.0"
  type: "aws_s3_bucket"
  resource_id: "app-uploads"
  config: { bucket: "staging-app-uploads-2026", tags: { Environment: "staging", ManagedBy: "spacelift-intent" } }
```

For slower resources (RDS, EKS, NAT gateway): pass `async: true`, capture `operation_id`, poll `intent status` with exponential backoff (2s → 60s).

## Step 8 - handle review pause

If `status` returns `PENDING_REVIEW`:

1. Read the operation:
   ```
   query searchIntentResourcesOperations
     variables: { input: { predicates: [{ field: "operationId", constraint: { stringEquals: ["<opId>"] } }] } }
     select: "edges { node { id status reviewReason } }"
   ```
2. Surface the reason. Ask the user whether to approve or reject.
3. On approve:
   ```
   mutate intentResourceOperationReview
     variables: { intentProject: "<projectId>", operationID: "<opId>", decision: "APPROVE", note: "reviewed" }
     select: "id status"
   ```
4. Wait for `status == READY_FOR_EXECUTION`.
5. Destructive-op gate again before resume:
   > Resume operation `<opId>` (creates `aws_s3_bucket app-uploads`). Reply `YES` or `CONFIRM`.
6. `intent resume operation_id: "<opId>"`.

## Step 9 - register dependencies (if any)

If this resource will be referenced by others (e.g. a bucket policy referencing this bucket), register the edge **immediately** after create, not as a batch later:

```
mutate intentResourceDependencyAdd
  variables: { intentProject: "<projectId>", fromResourceID: "app-uploads-policy", toResourceID: "app-uploads", dependencyType: "REFERENCE" }
  select: "id dependencyType"
```

## Step 10 - verify

```
intent read
  provider: "hashicorp/aws"
  provider_version: "5.70.0"
  type: "aws_s3_bucket"
  config: { bucket: "staging-app-uploads-2026" }
```

Or via search:

```
query searchIntentResources
  variables: { input: { predicates: [{ field: "resourceId", constraint: { stringEquals: ["app-uploads"] } }] } }
  select: "edges { node { id resourceType state } }"
```

Report success: bucket name, ARN, region, and the project / operation IDs.

## Pitfalls avoided

- **Skipped provider preflight** - step 5 is non-negotiable. Without it, `intent create` fails on schema mismatch.
- **Forgot to activate the project** - step 4 prevents subsequent `intent` calls from operating on the wrong (or no) project.
- **Resumed on `PENDING_REVIEW`** - step 8 requires `READY_FOR_EXECUTION` first; review approval must happen via `intentResourceOperationReview`, not `resume`.
- **Late dependency registration** - step 9 registers edges per-resource at creation time, avoiding orphan dependency graphs.
- **Tight polling** - exponential backoff capped at 60s; don't re-dispatch.
