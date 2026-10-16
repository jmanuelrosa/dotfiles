# Tracing a behavior across repos

For "what happens when the user does X" and any flow that leaves one repo.
`how` supplies the exploration method; this file adds how to cross a boundary without guessing.

## Method

1. **Find the entry.** The user-facing trigger: a UI event handler, a route, a CLI command, a scheduled job, a webhook, a queue consumer. Cite it.
2. **Follow the call path inside the repo** until the flow leaves the process: a network call, a message publish, a write to shared storage, a spawned job.
3. **Name the contract at the boundary.** The artifact both sides share: a GraphQL operation and its schema file, an HTTP method and path, an RPC name, a topic or queue, a table or bucket, an environment variable naming the target. The contract is what lets the trace continue without assuming.
4. **Find the other side by the contract**, not by guessing the service. Search the profile's repos for the operation name, path, topic or table. More than one match is a finding; say so.
5. **Repeat** until the flow returns to the user or ends in storage, then follow the response or the read path back.

## Marking the flow

- Mark every hop as synchronous (the caller waits) or asynchronous (queued, scheduled, eventually consistent), with what the user sees meanwhile.
- Note where data changes shape: validation, mapping between API and storage models, enrichment, filtering.
- Note error paths at each hop when they change what the user sees.

## When the trace cannot continue

The counterpart repo is not cloned, cannot be read from this session, the contract resolves to an external service, or the target comes from configuration only set at deploy time.
A session started inside one repo often may not read its siblings; reading them works when the session starts at the workspace root or has the sibling directories added to it.
Never describe the far side of a boundary from its name, a package name or a guess; what was not read is Unknown.
Say exactly where the trace stops and why, name what would continue it (a repo to clone, a config value to read), and label everything past that point Unknown.

## Showing it

Present hops as a short ordered list with citations.
For three or more hops, draw the sequence the way `teach` asks: a series of mermaid diagrams, each adding one hop, rather than one diagram with everything.
