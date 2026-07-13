# Injection and input handling

When to read: the assessed surface includes handlers that build queries, commands, paths, templates, or outbound requests from external input; parsers and deserializers.

## Failure modes to rule out

Each item is a check.
An item you could not verify goes in the Not assessed section; silence is never read as safety.

- **Sinks inventoried from memory, not code.** An assessment that reasons about "the queries" without finding them misses the one raw call that matters.
  Check: search the assessed code for each sink class (query construction, process spawning, filesystem paths, template rendering, deserialization, outbound requests) and trace each hit back to its inputs; the inventory goes in the surface map.
- **Parameterization assumed everywhere.** ORMs and query builders still expose raw escape hatches, and one string-built query undoes the rest.
  Check: locate the data layer's raw paths (raw SQL calls, string-interpolated filters, operator injection in document queries) and confirm external input reaches them only through parameters.
- **Command execution fed strings.** Building a command string from input and handing it to a shell executes whatever the input smuggles in.
  Check: locate every process-spawn call; input travels as an argument array, and any shell-interpreting mode fed external input is a finding.
- **Path traversal through file APIs.** User-controlled names joined onto base paths walk out of the intended directory, and uploads stored under attacker-chosen names or types land executable content where it gets served.
  Check: trace file reads, writes, and deletes that take external names: the path is canonicalized and containment against the intended root is checked before use; uploads get server-generated names and validated types.
- **SSRF in the "internal" fetcher.** Server-side fetches of user-supplied URLs (webhooks, importers, previewers, renderers) reach cloud metadata endpoints and internal services.
  Check: find every outbound request whose destination derives from external input; confirm allowlist validation and internal-range blocking in the code, not in a comment.
- **Deserialization of untrusted bytes.** Native deserializers on external data execute code by design in several ecosystems.
  Check: locate deserialization of external input and confirm it uses a data-only format and parser; a native object deserializer fed external bytes is a finding regardless of intent.
- **Template injection.** External input concatenated into template source, not passed as context, executes in the template engine.
  Check: confirm external input enters rendering only as data or context variables, never as part of the template string itself.
- **Validation at the edge, sinks fed from the middle.** Input validated at the HTTP layer protects nothing when the sink is fed by a queue, a job, or a database read.
  Check: trace each sink's inputs to their true origin; validation must sit on the path the sink actually receives, second-order sources included.
- **Output encoding assumed from the framework.** Server-rendered HTML, emails, CSV exports, and response headers each need their own encoding; frameworks cover only some.
  Check: for each output channel that composes external input, confirm encoding appropriate to that channel at the write site (HTML escaping, header sanitization, spreadsheet formula neutralization).

## Escalation triggers (report immediately)

- A traced path from an internet-facing entry point to a query, command, or deserializer with no control between: an actively exploitable P0; lead the report with it.
- The brief asking you to demonstrate an injection with a crafted payload against a running system: exploitation is out of scope (also a hard rule); the evidence is the traced path.

## What good looks like

- Every sink class has an inventory, and every entry is parameterized, encoded, or allowlisted at the sink itself.
- Outbound requests built from user input pass through one shared validation choke point.
- Validation lives where the sink is, not only where the request enters.
