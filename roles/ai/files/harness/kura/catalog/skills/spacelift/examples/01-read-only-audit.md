# Example: read-only audit

**Goal:** find all stacks in the `production` space that are currently failing, and report a summary.

This walks through `discover` → `searchStacksSuggestions` → `searchStacks` with predicates and pagination. Read-only - no confirmation gate.

## Step 1 - confirm the operation shape

```
discover { type: "queries", name: "searchStacks" }
```

Inspect the input/output. Returns `searchStacks(input: SearchInput!): SearchStacksOutput!`.

```
discover { type: "type", name: "SearchStacksOutput" }
```

Confirm the connection shape: `edges { node { ... } } pageInfo { hasNextPage endCursor }`.

## Step 2 - cheap count first

Before listing, get a count via suggestions (`filteredCount` is the total matching predicates):

```
query searchStacksSuggestions
  variables: {
    input: {
      predicates: [
        { field: "spaceId", constraint: { stringEquals: ["production"] } },
        { field: "state",   constraint: { stringMatches: ["FAILED"] } }
      ]
    }
  }
  select: "filteredCount"
```

If `filteredCount` is 0, report "no failing stacks" and stop. No entities loaded.

## Step 3 - paginated list

Only fetch the fields you'll surface in the report:

```
query searchStacks
  variables: {
    input: {
      predicates: [
        { field: "spaceId", constraint: { stringEquals: ["production"] } },
        { field: "state",   constraint: { stringMatches: ["FAILED"] } }
      ],
      orderBy: { field: "stateSetAt", direction: "DESC" },
      first: 50
    }
  }
  select: "edges { node { id name state stateSetAt blocker { id type state } } } pageInfo { hasNextPage endCursor }"
```

Loop with `after: <endCursor>` while `hasNextPage` is true. Stop early once you have what's needed.

## Step 4 - format

For each failing stack, surface:

- Stack `id` and `name`
- When it entered the failed state (`stateSetAt` - Unix timestamp; convert to relative time)
- The blocking run (`blocker.id`, `blocker.type`, `blocker.state`) if any

Don't dump every field. Three columns per stack is enough.

## Step 5 - hand off

Report a markdown table. Mention if pagination was truncated ("first 50 shown - call again with `after: <cursor>` for more"). Don't follow up with mutations unless asked - this was a read-only task.

## Why this shape

- **Suggestions before list** - cheaper, often answers "how many" without ever loading entities.
- **Predicates over post-filter** - server-side filter saves round-trips and tokens.
- **Selection minimal** - `name description createdAt updatedAt labels` is ~5x more than needed.
- **Pagination respected** - production accounts have hundreds of stacks; default `first: 50` and stop early.

## Pitfall avoided

A naive approach: `query stacks` (no args) returns **every stack in the account** with default selection. On a real account this can be 1000+ entities, blowing the context window for a question that only needs a count.
