# API discovery (discover / query / mutate)

## Workflow

1. **`discover` first.** Don't guess operation names or argument shapes.
   - `{ type: "queries", name: "stack" }` - list queries matching "stack"
   - `{ type: "mutations", name: "intent" }` - list mutations matching "intent"
   - `{ type: "type", name: "Stack" }` - inspect a type
   - Hides deprecated fields by default. Pass `includeDeprecated: true` only when needed.

2. **`query` / `mutate` second.** Pass `operation`, `variables` (JSON object - **never** a JSON-encoded string), and `select` (GraphQL selection set).

## Selection set syntax

Plain fields, space-separated; nested types in braces:

```
id name state space { id name } trackedCommit { hash authorLogin }
```

Request only what you'll use this turn. Selection bloat is the most common waste.

## Pagination

Most list endpoints take `SearchInput` (`first`, `after`, `predicates`, `orderBy`) and return a connection:

```graphql
{ edges { node { id name } } pageInfo { hasNextPage endCursor } }
```

Loop with `after: <endCursor>` until `hasNextPage` is false. **Stop early** if you have what you need.

## Counting cheaply

Don't list every entity to count. Use **`searchXxxSuggestions`** with predicates - it returns `filteredCount: Int!` (total matching the predicates) plus `fields` for facet discovery, without any entities:

```
query searchStacksSuggestions
  variables: { input: { predicates: [{ field: "state", constraint: { stringMatches: ["FAILED"] } }] } }
  select: "filteredCount fields { name filterable possibleValuesEnum { values { value } } }"
```

`searchXxx(input: { first: 0 })` does **not** return a total - the `SearchXxxOutput` shape is `{ edges, pageInfo }` only. Always use `searchXxxSuggestions` for counts.

## SearchInput predicates (the DSL)

Predicates filter; the schema is:

```json
{
  "predicates": [
    { "field": "state", "constraint": { "stringMatches": ["FAILED"] } },
    { "field": "spaceId", "constraint": { "stringEquals": ["staging-01"] } }
  ],
  "orderBy": { "field": "createdAt", "direction": "DESC" },
  "first": 50
}
```

Use the matching `searchXxxSuggestions` query to discover valid `field` names and constraint kinds. Constraint kinds include `stringEquals`, `stringMatches`, `stringNotMatches`, `booleanEquals`, `enumEquals`, `numberEquals`, `numberInRange`, `timeInLast`.

## Variables - the #1 mistake

`variables` is a **JSON object**, not a JSON-encoded string.

```
✓  variables: { id: "stack-01" }
✗  variables: "{\"id\": \"stack-01\"}"
```

The MCP rejects strings with `InputValidationError`. Trust the SDK; pass the object.

## Idempotency

Most mutations are **not** idempotent:

- `stackCreate` collides on slug; check existence with `query stack(id: <slug>)` first.
- `contextCreate`, `policyCreate` - same pattern.
- "Create" mutations that take an explicit `id` field are usually upserts; ones that auto-generate slugs are not.

When in doubt: `query` for the entity by its natural key first.

## Read-only vs write boundary

| Read-only (no confirmation) | Write (confirmation required) |
|---|---|
| `discover`, `query` | `mutate`, `intent create/update/delete`, `intent import` |
| `provider search/describe` | `intent resume` (it executes a deferred op) |
| `intent read/status/refresh` | |

`intent refresh` reads provider state into Spacelift's stored state but doesn't change provider state - it counts as read-only for the gate, but record any drift it finds before acting on it.

## Tips

- For nested fields, ask `discover` for the type rather than guessing: `{ type: "type", name: "Run" }`.
- When a query returns nested connections (e.g. `stack.runs`), each connection has its own pagination args.
- Errors return structured GraphQL errors; check `errors[].extensions.code` before retrying.
