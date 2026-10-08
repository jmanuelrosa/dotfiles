# Untrusted input: interpreters, parsers, fetchers, files

When to read: the brief or diff builds queries, shell commands, or templates from input, deserializes or parses XML from outside the process, fetches or redirects to URLs taken from input, or accepts uploads or file paths from callers.

## Failure modes to rule out

Each item is a check.
An unresolved item blocks `done`; if the brief forces it, report `needs-decision`.

- **Input concatenated into interpreter syntax.** A value spliced into SQL, a NoSQL filter, LDAP, or XPath becomes code the interpreter runs, and validation alone does not stop it; identifiers (table, column, sort direction) cannot be bound, so they get spliced instead.
  Check: every external value reaches the interpreter only as a bound parameter; identifiers come from a code-defined map with a rejecting default; NoSQL filter values are type-checked as scalars, so a client-supplied object cannot smuggle in operators.
- **Command line handed to a shell.** One command string passed to a shell turns metacharacters in any interpolated value into extra commands, and an argument starting with `-` becomes an option.
  Check: processes start through an argv-array API with no shell and a hardcoded executable; input-derived arguments are allowlisted and separated from options (`--`) where the program supports it.
- **Data compiled as code.** Request data or model output passed to a string-to-template API, `eval`, or dynamic code loading is remote code execution, whatever sanitizing came first.
  Check: templates are source files and data enters only as render variables; no eval-like or dynamic-import sink receives request data or model output, and the template name is never chosen by input.
- **Native deserialization of external bytes.** A language's native object deserializer, or a JSON or YAML mapper that lets the payload name the type to instantiate, runs gadget chains before any check in your code sees the object.
  Check: externally influenced data is decoded only into declared data types through a data-only format; polymorphic type information from the payload is disabled; nothing checks the type after the fact instead.
- **XML parser left at defaults.** Accepting DTDs lets a document read local files, reach internal hosts through external entities, or expand entities until memory runs out.
  Check: DOCTYPE is rejected, or external entities, external DTD loading, and XInclude are off with expansion limits on, for schema and stylesheet processors too; a hardening setting that fails to apply aborts the parse instead of being swallowed.
- **Server fetches where the caller points it.** A URL from input (an image link, an import source, a webhook callback) lets a caller reach cloud metadata, admin ports, and internal services through your network position.
  Check: destinations come from an allowlist; where arbitrary URLs are the feature, the scheme is https only, every resolved address is rejected if private, loopback, link-local, or metadata, the connection goes to the validated IP without re-resolving, redirects are off, and retries reuse the validated path.
- **Redirect target taken from the request.** A `next` or `returnTo` parameter echoed into a redirect turns your domain into a phishing launcher and can leak OAuth codes or tokens to another host.
  Check: redirect targets are relative paths or are looked up in a server-side map, or the parsed scheme, host, and port match an allowlist exactly.
- **Upload trusted by its own metadata.** A client filename used as the stored path enables traversal and overwrites, and a client `Content-Type` or unanchored extension check lets an executable through as an image.
  Check: stored names are server-generated; any filesystem path built from input is resolved and confirmed inside its base directory; the extension is allowlisted after decoding, lowercased, and end-anchored; the client content type is never the only type control.
- **Upload stored where it is executed or served.** A file landing under the web root or in a public bucket is either run by the server or served to every visitor with no access check.
  Check: uploads live outside any executable or publicly served location, and come back only through a handler that authorizes the caller and sets a safe content type and disposition.
- **Unbounded upload or archive.** A missing size cap, or one that measures only the compressed bytes, lets one request exhaust disk or memory, and archive entry names can climb out of the extraction directory.
  Check: per-file and per-request size caps enforced before buffering; decompression and extraction cap total size, entry count, and expansion ratio, and reject entry paths that leave the target directory.

## Escalation triggers (`needs-decision`)

- A feature whose purpose is fetching arbitrary user-supplied URLs or rendering user-authored templates.
- Accepting a new serialized-object, XML, or archive format from outside the trust boundary.
- Adding a parsing, sanitizing, or scanning library to make an input safe (also an ask-first boundary in the agent).

## What good looks like

- Every sink that interprets data (query, shell, template, parser, fetcher, filesystem) is listed for the change, and each one receives input through its safe API, not through escaping.
- Validation is an allowlist on syntax and meaning, layered on top of safe sinks rather than standing in for them.
- Files and URLs from callers are treated as hostile until stored by the server under its own name, behind its own access check.
