# Injection and input validation

When to read: the brief, diff, or assessed surface touches building SQL, ORM, NoSQL, LDAP, or XPath queries, stored procedures or database grants, spawning processes or shelling out, `eval`-style runtime code execution, server-side template rendering or user-authored templates, values written into SMTP/IMAP/FTP command streams, or request parsing and validation rules.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html), [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html), [Query Parameterization](https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html), [NoSQL Security](https://cheatsheetseries.owasp.org/cheatsheets/NoSQL_Security_Cheat_Sheet.html), [LDAP Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LDAP_Injection_Prevention_Cheat_Sheet.html), [OS Command Injection Defense](https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html), [XPath Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/XPath_Injection_Prevention_Cheat_Sheet.html), [Server-Side Template Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Template_Injection_Prevention_Cheat_Sheet.html), [Input Validation](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)

## Contents

- Untrusted data reaching an interpreter
- SQL and ORM queries
- OS commands and process execution
- Server-side templates
- NoSQL queries
- LDAP queries and binds
- XPath queries
- Least privilege for interpreter accounts
- NoSQL deployment hardening
- Input validation
- Review and testing

## Untrusted data reaching an interpreter

- **Untrusted data concatenated into interpreter syntax.** Use a safe API that avoids the interpreter entirely or provides a parameterized interface, so data can never change the structure of the SQL, LDAP, XPath, OS command, template, or protocol command it reaches; injection exists wherever untrusted data is sent to an interpreter as part of a command or query.
  Check: trace every call that hands a string to an interpreter (query execution, directory search, XPath evaluation, process spawning, template compilation, runtime code evaluation, commands written to SMTP/IMAP/FTP sessions) and confirm external values arrive only as bound parameters, never by concatenation, formatting, or interpolation. Owner: `backend`. Source: Injection Prevention, SQL Injection Prevention.
- **Parameterized call site hiding dynamic code underneath.** Some parameterized APIs, such as stored procedures, still introduce injection internally, so a bound call site does not prove the whole path is safe.
  Check: for each parameterized API in the diff, read what it does with the value (dynamic SQL inside the procedure, a helper that concatenates before executing) and treat any internal string building as an unparameterized sink. Owner: `backend`. Source: Injection Prevention, SQL Injection Prevention.
- **Escaping used where a parameterized API exists.** Contextual escaping with the interpreter's own escape syntax is the last resort for when no parameterized API exists; it is fragile, database specific, and cannot be guaranteed to stop every injection, and ad hoc quote replacement is never a substitute for binding. New or low-risk-tolerance code must be built on parameterized queries, safe stored procedures, or an ORM that builds queries.
  Check: flag escaping helpers or hand-rolled quote replacement feeding a query when a binding API exists for that interpreter; escaping is acceptable only as a documented legacy retrofit. Owner: `backend`. Source: Injection Prevention, SQL Injection Prevention, XPath Injection Prevention.
- **Request data passed to runtime code evaluation.** Every scripting language has an `eval`-style call that executes code built at runtime; code assembled from unvalidated, unescaped input lets an attacker subvert application logic and gain local access, and building a database filter by evaluating a string is the same flaw.
  Check: search for `eval`, `exec`, dynamic function constructors, and equivalents and confirm none receive request-derived or stored user data; replace them with data structures or fixed code paths. Owner: `backend`. Source: Injection Prevention, NoSQL Security.
- **Validation treated as the injection defense.** Allowlist validation with canonicalization is recommended, but it is not a complete defense because many fields legitimately need special characters, and validated data is not necessarily safe to string-build into a query or expression.
  Check: code that validates a value and then concatenates it into a query, command, filter, or expression still needs binding; validation stays as a complement, not the control. Owner: `backend`. Source: Injection Prevention, SQL Injection Prevention, XPath Injection Prevention, Input Validation.
- **Validated or bound identifier treated as permission.** A valid account id, a fixed query, a narrow path, or a bound identifier does not establish that the caller may access the record it selects; authorization is a separate check on every request.
  Check: each lookup by a request-supplied identifier is followed by an ownership or permission check for that resource before data is returned. Owner: `backend`. Source: Input Validation, XPath Injection Prevention.

## SQL and ORM queries

- **SQL built by string concatenation with user input.** Use prepared statements with variable binding so all SQL is defined first and each parameter is passed later; the database then always distinguishes code from data and an attacker cannot change the query's intent.
  Check: search query execution calls for concatenation, string formatting, or template literals containing non-constant values and replace them with placeholders bound through the driver. Owner: `backend`. Source: SQL Injection Prevention, Query Parameterization, Injection Prevention.
- **ORM or query-language strings with interpolated input.** SQL abstraction layers such as HQL have the same injection problem (HQL injection); use their named parameters, named queries, or criteria/builder APIs instead of building query text.
  Check: raw, native, or HQL/JPQL-style query strings in the diff use named or positional parameters, never string concatenation of request values. Owner: `backend`. Source: SQL Injection Prevention, Query Parameterization.
- **Parameterization performed on the client.** Many client-side frameworks offer "parameterization" that just concatenates values before sending a raw query to the server; parameterization must happen server-side.
  Check: confirm placeholders are bound by the server-side database driver, not by a library that produces the final SQL string before it reaches the server. Owner: `backend`. Source: Query Parameterization.
- **Dynamic SQL inside stored procedures.** Stored procedures are as safe as prepared statements only when they contain no unsafe dynamic SQL; dynamic SQL in a procedure should be avoided, and when unavoidable it must bind inputs (for example `EXECUTE IMMEDIATE ... USING` in PL/SQL, `sp_executesql` with declared parameters in T-SQL) or apply input validation or proper escaping.
  Check: grep procedure bodies in migrations and schema files for `sp_execute`, `sp_executesql`, `execute`, `exec`, and `EXECUTE IMMEDIATE`, and confirm parameters are bound rather than concatenated into the statement. Owner: `database`. Source: SQL Injection Prevention, Query Parameterization, Injection Prevention.
- **Table, column, or sort direction taken from user input.** Identifiers and sort indicators cannot be bound, so they must come from code: map each user value to a code-defined name through an allowlist that rejects unknown values, or convert input to a boolean, number, date, or enum and use that to select the fragment to append. User-chosen table names are a design smell that warrants a rewrite, and generic table-name validators can cause data loss when names reach queries where they are not expected.
  Check: any identifier or `ASC`/`DESC` appended to SQL originates from a switch/map over fixed literals with a rejecting default, never from the raw parameter. Owner: `backend`. Source: SQL Injection Prevention, Injection Prevention.
- **Stored procedures forcing the application account to owner rights.** Where role management only offers reader, writer, and owner roles, apps end up running as `db_owner` to get execute rights, so a breach yields full database control.
  Check: grants give the application account `EXECUTE` on the specific procedures it calls, not an owner or admin role. Owner: `database`. Source: SQL Injection Prevention.

## OS commands and process execution

- **Shelling out where a library call exists.** Avoid calling OS commands directly; built-in library functions (for example a `mkdir()` API instead of running `mkdir` through the system shell) cannot be manipulated into doing other tasks.
  Check: for each new process spawn, confirm no language or library API performs the same task; replace the command when one does. Owner: `backend`. Source: OS Command Injection Defense.
- **Command line passed to a shell as one string.** When a command is unavoidable, use a structured process API that takes the executable and each argument as separate list elements so data cannot become command syntax; never interpolate an unquoted value into a shell command, and keep the executable and working directory trusted.
  Check: process spawns use an argument-vector API with shell interpretation off; no `system()`-style call or `shell=true` option receives a string containing request data. Owner: `backend`. Source: OS Command Injection Defense, Injection Prevention.
- **User input choosing the executable or its options.** The command must be validated against a list of allowed commands; hardcode the executable so the user never chooses what runs, and hardcode required flags in code rather than in user input.
  Check: the executable path and its fixed options are literals or come from an allowlist in code; request data can only fill validated argument slots. Owner: `backend`. Source: OS Command Injection Defense, Injection Prevention.
- **Command arguments without allowlist validation.** Validate every argument against explicitly allowed values or an allowlist regex that defines permitted characters and a maximum length and excludes metacharacters (`` & | ; $ > < ` \ ! ' " ( ) ``) and whitespace, for example `^[a-z0-9]{3,10}$`; argument separation does not replace argument validation.
  Check: each untrusted argument passes an anchored allowlist pattern or value set before the spawn. Owner: `backend`. Source: OS Command Injection Defense, Injection Prevention.
- **Option injection through argument values.** Every command injection is also argument injection: escaping that stops command chaining still lets a value such as a leading-dash string be read as an extra option. Use `--` to end option parsing where the command supports it; for curl, `--` does not stop additional transfers, so pass exactly one validated URL as one argument, add `--globoff`, and apply SSRF protections because argument separation does not validate the destination.
  Check: untrusted arguments follow `--` or are validated so they cannot start with `-`; URL-fetching commands receive a single validated URL with globbing disabled. Owner: `backend`. Source: OS Command Injection Defense.
- **Whole-command shell escaping.** When user input must go to a shell, escape each argument individually (PHP `escapeshellarg()`) rather than escaping the whole command (`escapeshellcmd()`), which still lets the user add parameters that override hardcoded options.
  Check: no whole-command escaping function wraps a command containing request data; per-argument quoting is applied to each value. Owner: `backend`. Source: OS Command Injection Defense.

## Server-side templates

- **Untrusted data compiled as template source.** Templates are code: keep them with the application source, review them like code, and never build them from untrusted data, whether by concatenation (even inside an expression) or through a string-to-template API such as Jinja2 `from_string()`, Flask `render_template_string()`, Twig `createTemplate()`, or the FreeMarker `Template` constructor. Render a fixed template and pass user values only as named variables.
  Check: search for string-to-template APIs and code that assembles template source, and confirm untrusted data reaches only render variables. Owner: `backend`. Source: SSTI Prevention.
- **Template feature that evaluates a value as code.** A fixed template becomes injectable when it passes a value to a feature that parses strings as template code, such as FreeMarker `?interpret` and `?eval` or Twig `template_from_string()`.
  Check: no template passes a variable to an evaluate-as-template built-in or function. Owner: `backend`. Source: SSTI Prevention.
- **User input choosing the template name, path, or include.** Letting input select a template, path, or include target can make the engine load files it should not; map the user's choice to a fixed server-side list of template names.
  Check: render and include calls take names from a server-side map with a rejecting default, never from a raw parameter. Owner: `backend`. Source: SSTI Prevention.
- **Template syntax filtered out of input.** Denylisting template syntax misses payloads because syntax differs between engines and contexts; do not rely on it.
  Check: no sanitizer that strips braces, delimiters, or directives stands in for keeping input out of template source. Owner: `backend`. Source: SSTI Prevention.
- **Render context carrying secrets or side-effecting objects.** A template can read everything in its context and, depending on the engine, call methods on passed objects; pass only the values the template needs, never secrets, configuration, service clients, or objects with side-effecting methods. This limits reach but does not stop code execution in an unsandboxed engine.
  Check: render calls pass plain values or narrow view models, not whole config objects, request objects, ORM sessions, or clients. Owner: `backend`. Source: SSTI Prevention.
- **More powerful template engine than the feature needs.** Prefer an engine that limits expressions, function calls, and commands, such as a logic-less engine like Mustache; custom helpers and lambdas you register still run as application code.
  Check: a newly introduced engine is justified over a logic-less option, and registered helpers are reviewed as application code. Owner: `backend`. Source: SSTI Prevention.
- **Auto-escaping disabled or bypassed.** Keep output auto-escaping on and never mark untrusted values as safe; it prevents XSS in HTML output but does not prevent SSTI, since it applies to printed values, not to code the engine already parsed.
  Check: engine config keeps auto-escape enabled and no raw/safe marker is applied to user-controlled values. Owner: `backend`. Source: SSTI Prevention.
- **Template rendering surfaces missing from the inventory.** Inventory every place the application renders templates, including email and notification bodies, PDF and report generation, prompts for large language models, and features that let users create or edit templates; treat templates shipped in third-party files as templates you did not write.
  Check: each render site in the diff, including non-HTML ones, is checked against the rules above, and third-party template files are rendered under the user-supplied-template controls. Owner: `backend`. Source: SSTI Prevention.
- **User-authored templates editable by any role.** Letting users write templates runs user-written code, so editing must be limited to authorized roles and template changes logged for audit.
  Check: template create/edit endpoints enforce a privileged role and emit an audit event. Owner: `backend`. Source: SSTI Prevention.
- **User-authored templates rendered without the engine sandbox.** Render with the engine's sandbox or restricted configuration and keep the engine up to date, checking effective settings because frameworks change defaults: Jinja2 `SandboxedEnvironment` (or `ImmutableSandboxedEnvironment` to block mutation of lists, sets, and dicts), with `is_safe_attribute()` overridden and dangerous methods marked `unsafe()`; Twig sandbox in its own environment with a strict `SecurityPolicy` allowlisting tags, filters, functions, tests, methods, and properties (the `Sandbox` class needs Twig 3.29 or later) and never `template_from_string()`; FreeMarker `?new` resolver set to `ALLOWS_NOTHING_RESOLVER` (not `SAFER_RESOLVER`), `?api` left disabled, member access restricted with `SimpleObjectWrapper` or a `WhitelistMemberAccessPolicy`, DOM node wrapping disabled, and a loader that only loads approved files.
  Check: the environment that renders user templates is constructed with these settings and is separate from the trusted-template environment. Owner: `backend`. Source: SSTI Prevention.
- **Unsafe helpers registered in a sandboxed engine.** The sandbox does not limit what your own code does once called, so register only filters, functions, and globals that are safe with any arguments a template author chooses.
  Check: each helper exposed to user templates is safe for arbitrary input and has no file, network, or privileged side effect. Owner: `backend`. Source: SSTI Prevention.
- **Sandboxed rendering without resource and process containment.** A template sandbox does not limit CPU or memory or make output safe; treat the output as untrusted and render user templates in an isolated process or container with time and memory limits, no secrets, and restricted network access.
  Check: user-template rendering runs in a worker with timeouts, memory caps, no secret mounts, and egress restrictions, and its output is encoded before use. Owner: `backend`. Source: SSTI Prevention.

## NoSQL queries

- **Client-supplied object accepted as a query field value.** Building a driver query object does not stop operator injection when the untrusted value is itself an object (MongoDB reads `{ $ne: "" }` as a not-equal query); validate the expected scalar type before constructing the filter and never pass client objects through as field values.
  Check: every request value placed in a filter is type-checked as a string, number, or other expected scalar first. Owner: `backend`. Source: NoSQL Security.
- **Raw JSON query fragments or query strings accepted from the client.** Do not accept raw JSON queries from clients or evaluate untrusted strings; use driver query objects rather than building query strings, and do not concatenate user input into query language strings or into shell commands for database tools.
  Check: no endpoint forwards a client-provided query document or expression to the database, and no filter is built by string assembly. Owner: `backend`. Source: NoSQL Security.
- **Client-controlled query operators.** Disallow operators such as `$where`, `$regex`, and `$expr` from clients unless strictly required and validated; `$where` executes JavaScript inside MongoDB and can consume excessive resources, so use standard operators, and for text search use safe driver APIs such as `$text` with controlled input.
  Check: request-derived keys cannot introduce `$`-prefixed operators into filters; any permitted operator is set by code with a validated value. Owner: `backend`. Source: NoSQL Security.
- **`$` denylist as the only NoSQL input control.** Rejecting any serialized body containing `"$` is a denylist, not an operator allowlist: it rejects legitimate values and does not validate allowed fields or types. Validate and allowlist user-supplied fields (keys) and their types with field-specific validation before building queries.
  Check: a schema or explicit field allowlist with types guards each query-building handler. Owner: `backend`. Source: NoSQL Security, Input Validation.
- **Raw query execution instead of safe builders.** Prefer high-level ODM/ORM APIs that build queries safely, avoid `.eval()`-like features and raw query execution from untrusted data, and sanitize and validate any raw expression before it reaches the database.
  Check: raw command or expression APIs in the diff receive no request data, or receive it only after validation. Owner: `backend`. Source: NoSQL Security.

## LDAP queries and binds

- **Empty password accepted on LDAP bind.** A nonempty name with an empty password performs an unauthenticated bind that establishes anonymous authorization, so a successful result does not prove identity; reject empty passwords before binding and require authenticated access to protected directory data.
  Check: the login path rejects an empty or missing password before calling bind, and directory ACLs deny anonymous reads of protected entries. Owner: `backend`. Source: LDAP Injection Prevention.
- **Untrusted data in LDAP filters or DNs without context-specific encoding.** Untrusted data added to any LDAP query must be escaped, and DNs (RFC 4514) and search filters (RFC 4515) need different encoders: filter values escape `* ( ) \ NUL`; DN values escape `\ # + < > , ; " =`, leading or trailing spaces, and a leading `#`. Use a library encoder for the right context (for example ESAPI `encodeForLDAP` versus `encodeForDN`, .NET `Encoder.LdapFilterEncode` versus `Encoder.LdapDistinguishedNameEncode`, turning off the initial/final escaping flags only when inserting a fragment mid-DN), never custom escaping code. An authenticated bind does not make an unescaped filter safe.
  Check: every LDAP filter or DN built with external data passes it through the encoder matching that context. Owner: `backend`. Source: LDAP Injection Prevention, Injection Prevention.
- **Concatenated LDAP filter where a parameterized form exists.** Prefer a parameterized filter API (placeholder such as `{0}` with an argument array) or a framework that encodes automatically when building LDAP queries.
  Check: LDAP search calls pass user values as filter arguments rather than concatenating them into the filter string. Owner: `backend`. Source: LDAP Injection Prevention.
- **LDAP input validated without normalization.** Use allowlist validation as an additional defense; normalize user input before validation or comparison, store authentic data in sanitized form, and transform special characters to safe values before they enter the allowlist expression. Accepting JNDI or LDAP special characters without comprehensive normalization and allowlisting is discouraged.
  Check: normalization runs before the allowlist check, and the allowlist pattern is anchored and matches the field's real requirements. Owner: `backend`. Source: LDAP Injection Prevention.

## XPath queries

- **XPath expression built from external input.** Write the expression in application code and supply external values through the API's variable binding; do not concatenate or interpolate input even if the expression is compiled afterward, since compilation alone does not separate data from syntax and accepting an expression string does not mean the API binds variables. If the API cannot bind, prefer one that can, or retrieve an authorized set with a fixed expression and compare values in application code.
  Check: trace each XPath evaluate or compile call back to application-controlled text and confirm external values reach it only as bound variables. Owner: `backend`. Source: XPath Injection Prevention, Injection Prevention.
- **User choice inserted into an XPath path or predicate.** XPath variables represent values, not expression fragments; map a user's query mode to a complete fixed expression defined by the application, reject unknown choices, and never accept user-supplied predicates, operators, or function calls.
  Check: mode selection uses a fixed map of full expressions with a rejecting default. Owner: `backend`. Source: XPath Injection Prevention.
- **XPath internals in client-facing errors.** Keep XPath expressions, XML contents, and stack traces out of client-facing error messages; generic errors reduce disclosure but do not prevent injection.
  Check: XPath and XML parsing failures map to generic client errors with details only in server logs. Owner: `backend`. Source: XPath Injection Prevention.
- See `xml-and-deserialization.md` for hardening the XML parser behind XPath (binding values does not harden the parser).

## Least privilege for interpreter accounts

- **Application database account with DBA or admin rights.** Minimize every database account's privileges, starting from nothing and adding only what is needed; never assign DBA or admin access to application accounts, grant read-only accounts read on only the tables they need, and rarely if ever grant create or delete.
  Check: migrations or IaC grants for the application role list specific objects and verbs, with no superuser, owner, `ALL`, or DDL grants. Owner: `database`. Source: SQL Injection Prevention, NoSQL Security.
- **One database account shared across applications or functions.** Each web application gets its own database user rather than a shared owner/admin account, so access is granular (a login flow reads credentials without write rights while sign-up needs insert); keep separate users for admin, backup, read-only, and application use.
  Check: each service or application has its own credentials and role, and admin or backup roles are not used by application connections. Owner: `database`. Source: SQL Injection Prevention, NoSQL Security.
- **Table grants where a view or procedure suffices.** If an account needs only part of a table, grant it a view exposing only those columns and not the underlying table, checking the database's view privilege rules (PostgreSQL checks underlying access with the view owner's privileges); if the policy is stored procedures everywhere, grant only execute on the needed procedures and no direct table rights. Queries against views still need parameterization.
  Check: column-restricted access is implemented as a view grant with no grant on the base table, and procedure-only accounts hold no table privileges. Owner: `database`. Source: SQL Injection Prevention.
- **DBMS running as root or SYSTEM.** Minimize the operating system account the DBMS runs under, replacing the powerful default service account with a restricted one.
  Check: the database server's service or container user is a dedicated unprivileged account. Owner: `database`. Source: SQL Injection Prevention.
- **Over-privileged LDAP binding account.** Minimize the privileges of the account the application binds with to limit what a successful LDAP injection can reach.
  Check: the bind account configured for the application can read only the subtrees and attributes it queries and cannot modify entries unless the feature requires it. Owner: `backend`. Source: LDAP Injection Prevention.
- **Process that runs commands holding more privilege than the task.** Applications should run with the lowest privileges required, and where possible use isolated accounts with limited privileges dedicated to a single task.
  Check: the runtime user of a service that spawns commands is non-root and scoped to that task. Owner: `platform`. Source: OS Command Injection Defense.

## NoSQL deployment hardening

- **NoSQL database running without authentication.** Enable authentication and role-based access control, never run databases unauthenticated, use least-privilege service accounts, and use identity federation or short-lived credentials where supported (for example cloud IAM to DynamoDB).
  Check: database config enables auth and RBAC, and application connections use scoped roles or federated short-lived credentials. Owner: `database`. Source: NoSQL Security.
- **Database ports or admin consoles reachable from the internet.** Bind services to internal interfaces rather than `0.0.0.0`, place them in private subnets behind security groups, restrict remote management to admin networks or VPNs, and require MFA for admin access; network controls alone never compensate for badly written queries.
  Check: bind address, subnet, and security group definitions keep database and console ports private, and admin access requires MFA. Owner: `cloud`. Source: NoSQL Security.
- **Driver, admin, or replication traffic without TLS.** Enforce TLS for client driver connections, admin consoles, and node-to-node and internal replication links where supported.
  Check: server config requires TLS and connection strings enable it with certificate verification. Owner: `database`. Source: NoSQL Security.
- **Insecure NoSQL defaults left in place.** Change default ports, remove default admin accounts and passwords, disable sample and demo users, and turn off or restrict server-side code execution such as MongoDB server-side JavaScript when it is not needed.
  Check: database config disables server-side scripting and contains no default credentials or demo users. Owner: `database`. Source: NoSQL Security.
- See `secrets-management.md` for database credential storage, rotation, ephemeral tokens, and keeping credentials out of images and CI logs (the NoSQL sheet repeats that guidance).
- **No audit trail or anomaly alerting on database access.** Enable audit logging of connection attempts, admin actions, and failed authentication, ship it to a tamper-evident SIEM, and alert on query spikes, slow queries, large data exports, and suspicious commands such as admin actions, `$where`, and map-reduce jobs.
  Check: database audit logging is enabled and forwarded, with alert rules for those patterns. Owner: `sre`. Source: NoSQL Security.
- **Unencrypted or broadly accessible database backups.** Encrypt backups at rest and in transfer, restrict access to backup storage, sanitize backups for PII as policy requires, and validate restore procedures regularly.
  Check: backup jobs and storage enforce encryption and narrow access, and a restore test exists. Owner: `database`. Source: NoSQL Security.
- **Unpatched database server or drivers.** Keep the database and its drivers, ODMs, and plugins patched, since vulnerable drivers are a supply-chain risk.
  Check: server versions and driver dependency versions are current and covered by update automation. Owner: `database`. Source: NoSQL Security.

## Input validation

- **Validation only on the client.** Client-side validation is bypassable and exists for immediate feedback; the server must validate the same fields.
  Check: every rule enforced in a form or client schema has a server-side equivalent on the handler. Owner: `backend`. Source: Input Validation.
- **Data from internal sources trusted without validation.** Validate data from internal APIs, partner feeds, queues, and stored records when it crosses a trust boundary; an internal transport does not establish that a value meets the receiver's rules.
  Check: consumers of queues, webhooks from partners, and internal APIs validate payloads with the same rigor as public input. Owner: `backend`. Source: Input Validation.
- **Field rules missing syntax or semantic checks.** Validate syntax (type and format) and semantics (the value makes sense for the operation, related fields are consistent, an end date follows its start date). Per field: fixed choices require exact membership (including drop-down values), numbers and dates need type, format, and minimum and maximum, strings need length limits and required characters or structure, objects need allowed and required fields and null rules, arrays need minimum and maximum item counts with every item, including nested objects, validated. Parsing text to an integer establishes only a type, not an acceptable quantity.
  Check: each input field in the diff has explicit bounds and business rules, not just a type. Owner: `backend`. Source: Input Validation.
- **Denylisting or cleaning input instead of allowlisting.** Define what the application accepts and reject the rest rather than trying to recognize malicious strings; stripping suspicious characters changes meaning and still provides neither parameterization nor output encoding. A free-form field can allow broad Unicode with a length limit.
  Check: no validator strips or blocks characters (such as apostrophes) as an injection defense; acceptance rules are field-specific. Owner: `backend`. Source: Input Validation.
- **Parser resource limits applied after parsing.** Apply request size limits before buffering or parsing and configure parser limits such as maximum nesting depth (JSON allows limits on size, depth, and numbers); a schema check after parsing cannot protect a parser that already exhausted resources. Use a maintained parser for the expected format, handle parse failures, and validate the result before business processing or storage.
  Check: body size and parser depth limits are configured at the server or parser, ahead of schema validation. Owner: `backend`. Source: Input Validation.
- See `xml-and-deserialization.md` for configuring XML parsers and deserializers for untrusted input.
- **Validating a representation that is decoded again later.** Decode according to the protocol before checking field rules, validate the representation that will actually be used, and avoid decoding it again downstream, since inconsistent decoding invalidates earlier checks.
  Check: no URL, HTML, or base64 decode of a value happens after its validation. Owner: `backend`. Source: Input Validation.
- **JSON schema that neither requires nor rejects fields.** Enforce field rules with framework validators or a schema validator, explicitly configuring required properties and additional properties (listing a property alone neither requires it nor rejects unknown fields), with schemas on nested objects and item schemas plus length limits on arrays; keep business checks such as date ordering alongside.
  Check: schemas in the diff set `required` and `additionalProperties` (or the framework equivalent) at every object level and bound array lengths. Owner: `backend`. Source: Input Validation.
- **Processing continues on partially validated data.** Reject invalid requests with a clear error rather than continuing with partially validated data, and bind only intended input fields to application objects.
  Check: validation failure short-circuits the handler before any side effect. Owner: `backend`. Source: Input Validation.
- See `authorization.md` for mass assignment (binding only intended fields).
- **Unicode text without an encoding and normalization policy.** Agree on one character encoding across components and reject malformed input; preserve legitimate punctuation and scripts in names and comments; where a field needs Unicode normalization, apply the same policy before validation, storage, and comparison, noting that compatibility normalization can erase meaningful distinctions. Normalization is not sanitization and does not replace output encoding.
  Check: malformed encodings are rejected at the boundary and any normalization is applied consistently at validate, store, and compare points. Owner: `backend`. Source: Input Validation.
- **Regex validation that matches partially or backtracks catastrophically.** Use regexes for simple structured fields, require a match of the entire value (a full-match API where available), and verify the engine's character classes and newline behavior; bound input length before matching, avoid backtracking-heavy patterns, use a non-backtracking engine or a match timeout where supported, and treat a timeout as validation failure.
  Check: validation regexes are anchored or use full-match, input length is capped before matching, and nested quantifiers are absent or timeboxed. Owner: `backend`. Source: Input Validation.
- See `xss-and-csp.md` for user-authored HTML, which needs a maintained HTML sanitization library rather than input validation or regexes.
- **Upload filename and content type trusted as metadata.** Treat the submitted filename and content type as untrusted, validate filenames after protocol decoding, and do not treat an allowed extension as proof of safe content.
  Check: upload handlers validate the decoded filename and inspect content rather than trusting the declared type; see `file-upload.md` for content checks, size limits, storage, and serving. Owner: `backend`. Source: Input Validation.
- **Email format check treated as proof of ownership.** Use a maintained email validation library compatible with the addresses your mail system supports; format validation does not prove mailbox access.
  Check: email addresses are validated with a library, and ownership is established by verification; see `authentication.md` for verification and change workflows. Owner: `backend`. Source: Input Validation.
- **Rejected input logged verbatim.** Record the validation failure and relevant metadata without secrets or full request bodies, and escape any retained untrusted values for the log format to prevent log injection.
  Check: validation-failure log lines carry field names and reasons, not raw bodies, and untrusted fragments are encoded. Owner: `backend`. Source: Input Validation.
- **Parameterized queries without input validation as a secondary defense.** Input validation is recommended as a secondary defense in all cases, even when using bind variables, to detect unauthorized input before it reaches the query or directory.
  Check: handlers that query SQL, NoSQL, or LDAP also validate their inputs. Owner: `backend`. Source: SQL Injection Prevention, LDAP Injection Prevention.

## Review and testing

- **No data-flow analysis or security testing for injection sinks in CI.** Static analysis data-flow rules detect unsanitized user input reaching SQL queries or command execution, and security testing should be automated in the CI/CD pipeline.
  Check: the pipeline runs a SAST step with taint rules for query, command, and template sinks, and its findings gate merges. Owner: `platform`. Source: Injection Prevention, NoSQL Security.
- **Validation and query tests that only cover malformed syntax.** Test rejected ranges, missing fields, invalid nested items, oversized arrays, and regex near-matches (which also expose backtracking denial of service), not just malformed syntax; for XPath and query mappings, test ordinary valid values, absent records, unknown choices, and access to resources outside the caller's permissions.
  Check: the test suite for the changed handler includes negative cases for each of these, not only happy-path and parse-error tests. Owner: `qa`. Source: Input Validation, XPath Injection Prevention.
