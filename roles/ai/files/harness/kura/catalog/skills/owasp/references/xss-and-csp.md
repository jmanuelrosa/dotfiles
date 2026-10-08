# XSS and Content Security Policy

When to read: the brief, diff, or assessed surface touches server-side templates or HTML rendering, client-side DOM writes (raw-HTML sinks, `setAttribute`, `eval`, timers with strings), framework raw-HTML escape hatches, HTML sanitizers, URLs or CSS built from user data, inline JSON in pages, JavaScript objects keyed by untrusted input, or the `Content-Security-Policy` / Trusted Types configuration.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Cross Site Scripting Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html), [DOM based XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html), [DOM Clobbering Prevention](https://cheatsheetseries.owasp.org/cheatsheets/DOM_Clobbering_Prevention_Cheat_Sheet.html), [XSS Filter Evasion](https://cheatsheetseries.owasp.org/cheatsheets/XSS_Filter_Evasion_Cheat_Sheet.html), [Content Security Policy](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html), [Prototype Pollution Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Prototype_Pollution_Prevention_Cheat_Sheet.html)

## Contents

- Untrusted data reaching code-execution sinks
- Server-side output encoding by context
- URL and CSS contexts
- DOM sinks and safe DOM construction
- HTML sanitization
- DOM clobbering
- Prototype pollution
- Content Security Policy and Trusted Types
- Defenses that do not work on their own

## Untrusted data reaching code-execution sinks

- **Untrusted data passed to a string-evaluating API.** `eval()`, `Function()`, and `setTimeout` / `setInterval` with a string argument compile their input as code, and JavaScript encoding does not stop it (escaped identifiers still execute); using user-controlled input there must simply not be done rather than sanitized. Where it is truly unavoidable, the data must be delimited as a string, passed through a closure or encoded once per evaluation level, and wrapped in a custom function that never forwards it to another evaluating method.
  Check: grep for `eval(`, `new Function(`, `Function(`, and string first arguments to `setTimeout` / `setInterval`; trace whether any operand comes from the URL, request, storage, or messages; fix by passing a function reference and keeping the value as data. Owner: `frontend`. Source: XSS Prevention, DOM XSS, XSS Filter Evasion.
- **Untrusted code in an event-handler attribute.** The HTML parser decodes character references before the handler's JavaScript runs, so HTML attribute encoding does not protect an `on*` attribute, and JavaScript encoding does not either; an encoder cannot make untrusted handler code safe. Register trusted functions with `addEventListener()` and pass user values as data; assign a function, never a string, to `on*` properties.
  Check: search templates and DOM code for interpolation into `on*` attributes or `on*` values built from strings; replace with listener registration on a trusted function. Owner: `frontend`. Source: XSS Prevention, DOM XSS, CSP.
- **`setAttribute` or attribute binding with a code-bearing attribute name.** `setAttribute(name, value)` coerces the value into the attribute's type, so event-handler names execute it as JavaScript and `srcdoc` parses it as HTML. Keep attribute names fixed and limited to non-executing attributes (the sheets' safe list: `align`, `alt`, `class`, `color`, `cols`, `colspan`, `dir`, `height`, `lang`, `rel`, `rows`, `rowspan`, `span`, `summary`, `tabindex`, `title`, `value`, `width` and similar); for any other attribute ensure a JavaScript value cannot execute.
  Check: find `setAttribute` calls whose name argument is dynamic or is `on*`, `srcdoc`, `href`, `src`, `style`; fixed safe names only, or route URL/CSS values through the URL and CSS rules below. Owner: `frontend`. Source: XSS Prevention, DOM XSS.
- **Text sink used on a script element.** `textContent`, `innerText`, and similar text sinks are only safe on ordinary elements; on a `<script>` element they set executable code, and on `<style>` they set CSS.
  Check: look for `createElement('script')` or style elements whose text is assigned from untrusted data; never do this, load a static script file instead. Owner: `frontend`. Source: XSS Prevention, DOM XSS.
- **JSON parsed with `eval`.** `eval()` executes attacker-supplied code in a JSON string; `JSON.parse()` rejects anything that is not valid JSON.
  Check: any `eval` of response bodies or stored strings must become `JSON.parse()` (and `JSON.stringify()` for serialization). Owner: `frontend`. Source: DOM XSS.
- **Untrusted data on the left side of an expression or as a property key.** `window[userData] = ...` or `obj[untrusted] = ...` lets an attacker subvert internal and external attributes of the object, including `location` and `eval`. Use untrusted data only on the right side of an expression and add an explicit indirection (compare against known keys, then assign the named property).
  Check: find computed member writes and reads on `window`, `document`, or config objects whose key comes from input; replace with an allowlisted mapping. Owner: `frontend`. Source: DOM XSS.

## Server-side output encoding by context

- **Variable rendered without context-specific encoding.** Every variable must be validated and then escaped or sanitized ("perfect injection resistance"); start with the framework's automatic escaping and use a maintained output-encoding library where the framework has gaps. Browsers parse HTML, JavaScript, URLs, and CSS differently, so the wrong encoder introduces weaknesses.
  Check: list every raw or unescaped output directive in templates and every HTML string built by concatenation; each needs the encoder for its exact context or a sanitizer. Owner: `backend`. Source: XSS Prevention.
- **Framework raw-HTML escape hatch fed unsanitized input.** Raw-HTML properties, trust-bypass helpers, unsafe-HTML directives, template injection, and outdated framework plugins or components all bypass the framework's auto-escaping. Know where the framework protects and where it has gaps, and sanitize before any escape hatch.
  Check: grep the project's framework for its raw-HTML and trust-bypass APIs; each call site must receive sanitizer output or a compile-time constant; flag stale framework plugins. Owner: `frontend`. Source: XSS Prevention.
- **HTML body context without entity encoding.** Data placed between tags must be HTML entity encoded: `&` to `&amp;`, `<` to `&lt;`, `>` to `&gt;`, `"` to `&quot;`, `'` to `&#x27;`.
  Check: confirm the template engine's default escaping is on for body text and that no helper disables it. Owner: `backend`. Source: XSS Prevention.
- **Unquoted or dynamically named HTML attribute.** Attribute values must always be surrounded by `"` or `'` and passed through the framework or library attribute encoder; in an unquoted value whitespace ends the value. Keep element and attribute names fixed, use ordinary text attributes, and apply the URL, CSS, HTML, or JavaScript controls when the attribute carries those.
  Check: find attributes rendered without quotes or with names from data; quote and encode, or remove the dynamic name. Owner: `backend`. Source: XSS Prevention.
- **JavaScript string context protected by quote escaping alone.** Server templates may insert untrusted data into inline script only inside a quoted string, using a maintained encoder documented for both the JavaScript string and the enclosing HTML `<script>` context; never insert untrusted code, identifiers, or expressions, and never rely on manual quote escaping or a generic `\xHH` rule. Escaping quotes without escaping the escape character, or JavaScript-escaping without protecting the script block, lets data close the string or the `</script>` tag.
  Check: inline `<script>` blocks with server interpolation must use a context-documented JavaScript encoder and keep the value inside template-supplied quotes; template literals and tagged templates need explicit encoder support; flag any encoded value later passed to `eval`. Owner: `backend`. Source: XSS Prevention, DOM XSS, XSS Filter Evasion.
- **JSON embedded inline or served as HTML.** JSON responses must carry `Content-Type: application/json`, not `text/html`. `JSON.stringify()` is not output encoding; prefer a separate JSON response parsed with `JSON.parse()`, and if JSON must sit in an inline script use a serializer documented for that placement that also neutralizes literal `</script` sequences (HTML entity encoding or quote escaping alone is not sufficient).
  Check: confirm JSON endpoints set `application/json`; find inline `<script>` blocks that interpolate serialized objects and verify the serializer escapes `<`, `</script`, and the string context. Owner: `backend`. Source: XSS Prevention, DOM XSS.
- **Variable placed in a dangerous context.** Output encoding does not make data safe directly inside `<script>` code, inside HTML comments, directly in `<style>`, as an attribute name, as a tag name, in callback names, or in CSS URL handling; do not place variables there.
  Check: grep templates for interpolation inside comments, style blocks, tag or attribute name positions, and JSONP-style callback names; redesign so data lands only in encodable value positions. Owner: `backend`. Source: XSS Prevention.
- **Parameter assumed constant rendered unencoded.** A parameter the developer believes is always an integer or fixed value can be polluted (HTTP parameter pollution) and inject script; every parameter rendered into a page must be validated or encoded, and values placed into built links must be URL-encoded so they cannot add parameters.
  Check: find request parameters echoed into scripts or markup without encoding because they are "always numeric"; validate type strictly or encode. Owner: `backend`. Source: XSS Filter Evasion.
- **Encoding done in a request interceptor instead of at render time.** Output encoding belongs as close to where data is rendered as possible; a filter or interceptor cannot know the output context, misses headers, cookies, and extra path data, double-encodes, cannot see DOM XSS, and ignores data from internal services and databases, which must be treated as tainted unless strictly validated at retrieval.
  Check: flag global input-encoding filters presented as the XSS defense; confirm rendering code encodes per context, including data read from internal APIs and databases. Owner: `backend`. Source: XSS Prevention.
- **Encoding defeated by content type or DOM round trip.** HTML encoding may not protect pages served as XHTML, and encoding is reversed when a value is read back through a DOM element's `value`, so a value written into a sink after that read must be encoded again for the new sink.
  Check: look for `*.value` reads that flow into `document.write`, raw-HTML sinks, or `eval`; switch the sink to a text sink. Owner: `frontend`. Source: DOM XSS.

## URL and CSS contexts

- **Untrusted URL in `href` or `src` without a scheme allowlist.** A full URL from data must be canonicalized, validated, restricted to `http` and `https`, and then attribute-encoded; a framework that blocks `javascript:` URLs does not replace application-specific URL validation.
  Check: find links, frames, and redirects whose whole URL comes from data; require parsing plus an `http`/`https` allowlist before rendering. Owner: `frontend`. Source: XSS Prevention.
- **Query parameter value not percent-encoded.** Values placed in a URL must be `%HH` encoded (client side: `encodeURIComponent()` per parameter value), then HTML-attribute encoded when the URL sits in an attribute; encode parameter values only, not the whole URL or path, since encoding a full URL breaks its scheme. Component encoding does not validate a complete URL; use base64url only when the receiver expects it and apply the destination's encoding after decoding; be aware of character set issues when URL encoding in the DOM.
  Check: find string-concatenated query strings; each untrusted value goes through the component encoder and the result through the attribute encoder. Owner: `backend`. Source: XSS Prevention, DOM XSS.
- **Untrusted data choosing a CSS property or declaration.** Variables may only be placed in a CSS property value, with strict structural validation and CSS hex encoding (`\XX` followed by a space, or zero-padded six-character `\XXXXXX`; alphanumerics stay unencoded). From JavaScript, set a fixed property (for example a named style property) to a value from an application-defined allowlist; never let input pick the property or supply a declaration block, validate URLs for URL-accepting properties, and URL-encode data passed to `url()`.
  Check: find style strings, `setProperty`, or `style` attributes built from input; property names must be constants and values allowlisted or CSS-encoded. Owner: `frontend`. Source: XSS Prevention, DOM XSS.

## DOM sinks and safe DOM construction

- **Untrusted data assigned to an HTML-parsing sink.** `innerHTML`, `outerHTML`, `document.write`, and `document.writeln` parse their input as markup; the fix is the right sink, not better encoding: use `textContent`, `insertAdjacentText`, `createTextNode`, `className`, or a form field's `value`, and treat untrusted data only as displayable text. If an HTML sink is unavoidable, HTML-encode then JavaScript-encode the data, or sanitize it.
  Check: grep for HTML-parsing sinks and trace sources such as `location.hash`, `location.search`, `document.referrer`, storage, and messages; replace with text sinks or sanitizer output. Owner: `frontend`. Source: XSS Prevention, DOM XSS.
- **Dynamic UI built from markup strings.** `document.createElement`, `setAttribute` with safe names, and `appendChild` are the safe way to build dynamic interfaces. Do not pre-encode values assigned through `setAttribute` to ordinary text attributes (it double-encodes); the value is set directly without HTML parsing.
  Check: prefer element-construction APIs over HTML string templates in client code; flag HTML-attribute encoders applied before `setAttribute`. Owner: `frontend`. Source: XSS Prevention, DOM XSS.

## HTML sanitization

- **User-authored HTML rendered without a sanitizer.** When users must author HTML, output encoding breaks the feature, so a maintained HTML sanitizer must strip dangerous markup (the sheets name DOMPurify client side; JSoup, AntiSamy, or an HTML sanitizer for server-side validation).
  Check: every rich-text render path passes through a parser-based sanitizer immediately before the sink. Owner: `frontend`. Source: XSS Prevention, DOM XSS.
- **Sanitized HTML modified after sanitizing.** Modifying sanitized content, or passing it to a library that mutates it, voids the sanitization; a sanitizer filters markup and is not a sandbox for executing JavaScript.
  Check: confirm no string replacement, templating, or markdown processing happens between the sanitizer call and the sink. Owner: `frontend`. Source: XSS Prevention, DOM XSS.
- **HTML sanitizer library not kept current.** Sanitizer libraries must be patched regularly because browsers change behavior and bypasses are found regularly.
  Check: the sanitizer dependency is pinned to a maintained, recent release and covered by automated dependency updates. Owner: `dx`. Source: XSS Prevention.
- **Regex or denylist filter used as the XSS defense.** Input filtering is an incomplete defense: regex tag filters are bypassed by encoding variants, malformed tags, whitespace and control characters, and quote tricks, and only a real parser (state machine) understands the markup.
  Check: flag regex-based tag or keyword stripping on HTML input; replace with output encoding plus a parser-based sanitizer. Owner: `backend`. Source: XSS Filter Evasion.

## DOM clobbering

- **Injected markup can carry `id` or `name` that collides with globals.** Before inserting any markup into the DOM, sanitize `id` and `name` attributes: remove them, namespace them with a constant prefix, or drop those that collide with the existing DOM. With DOMPurify, `SANITIZE_DOM` (default) covers built-in APIs and `SANITIZE_NAMED_PROPS: true` is needed for custom variables (prefixes `user-content-`); with the Sanitizer API, remove `id` and `name` and use it only where supported, never falling back to unsanitized insertion.
  Check: inspect sanitizer configuration for named-property handling on every path that inserts user markup. Owner: `frontend`. Source: DOM Clobbering.
- **Security-sensitive value read from a `window` or `document` global.** Named elements shadow `window` and `document` properties, including built-ins and values assigned earlier, so globals used for script URLs, redirect targets, or config can be replaced by injected markup. Do not store globals on `window` or `document`; use local scope, explicit `var`/`let`/`const` declarations (a `let` does not create `window.X`, so reading `window.X` stays clobberable), strict mode, unique names, and encapsulation.
  Check: find patterns like `window.x || default` or `document.x` feeding `script.src`, `location`, `fetch`, or `eval`; move the value to a module-scoped constant. Owner: `frontend`. Source: DOM Clobbering.
- **`window` or `document` property used without a type check.** A clobbered property resolves to an `Element`; check the type (for example `instanceof`) before a sensitive operation, and feature-detect APIs because an unsupported API is an undefined, clobberable property.
  Check: sensitive reads from `window` / `document` properties are type-checked before use. Owner: `frontend`. Source: DOM Clobbering.
- **Freezing relied on to stop clobbering.** `Object.freeze()` is only an extra control for application-owned config objects with trusted values kept in local scope, and it is shallow; freezing `window`, `document`, or DOM elements does not stop named-property clobbering (`Object.freeze(window)` throws). CSP mitigates only clobbering variants that load new scripts, not abuse of already-present code.
  Check: flag freeze calls on `window` / `document` presented as a defense; require sanitization and local variables instead. Owner: `frontend`. Source: DOM Clobbering.

## Prototype pollution

- **Plain object used as a map for untrusted keys.** Objects inherit from `Object.prototype`, so writing attacker-chosen keys can pollute every object, leading to data exposure, privilege escalation, or remote code execution. Use `new Map()` or `new Set()`; where an object is required create it with `Object.create(null)`, and only as a last resort with a `{__proto__: null}` literal.
  Check: find deep-merge, path-set, or `obj[key] = value` code driven by request bodies, query strings, or parsed config; switch to `Map` / null-prototype objects or reject `__proto__`, `constructor`, and `prototype` keys. Owner: `backend`. Source: Prototype Pollution.
- **Built-in prototypes left mutable.** Freezing built-in prototypes with `Object.freeze()` blocks property additions and makes data properties non-writable (shallow, so referenced objects stay mutable; test compatibility first); `Object.seal()` does not stop changes to existing writable values and must not be relied on.
  Check: look for an application bootstrap that freezes built-in prototypes and confirm seal is not used as the protection. Owner: `backend`. Source: Prototype Pollution.
- **Node.js runs with `__proto__` available.** The `--disable-proto=delete` flag removes `__proto__` as defense in depth; `constructor.prototype` paths remain, so it does not replace safe object handling.
  Check: Node start commands, Dockerfiles, or `NODE_OPTIONS` include `--disable-proto=delete`. Owner: `backend`. Source: Prototype Pollution.

## Content Security Policy and Trusted Types

- **CSP treated as the primary XSS defense.** CSP is a second layer and should not be relied upon alone; it must sit on top of output encoding, sanitization, and safe sinks, and it works best customized per application rather than as one blanket enterprise policy, which breaks legacy apps and drives exceptions.
  Check: confirm encoding and sanitization exist independently of the CSP; flag an organization-wide CSP pasted unchanged across applications. Owner: `architect`. Source: XSS Prevention, CSP.
- **Allowlist-based CSP instead of a strict CSP.** Granular or permissive host allowlists are likely to be bypassed; use a strict policy: `script-src 'nonce-{RANDOM}' 'strict-dynamic'; object-src 'none'; base-uri 'none'` or the hash-based equivalent `script-src 'sha256-{HASH}' 'strict-dynamic'; object-src 'none'; base-uri 'none'`. The strict and basic sample policies admit neither inline script nor `eval`; browsers supporting CSP Level 2 ignore `'unsafe-inline'` when a nonce or hash is present, so it is acceptable only as a fallback for older browsers.
  Check: read the policy; `script-src` must use nonces or hashes with `'strict-dynamic'`, `object-src 'none'` and `base-uri 'none'` must be present, `'unsafe-eval'` absent, and `'unsafe-inline'` present only beside a nonce or hash as a legacy fallback. Owner: `backend`. Source: CSP.
- **Nonce reused or added by a rewriting middleware.** Nonces must be unique random values generated for each HTTP response and rendered into script tags by the templating engine; a middleware that adds the nonce to every `<script>` tag also blesses injected scripts. Hashes break on any change to the script, including whitespace.
  Check: nonce generation uses a CSPRNG per response; no response-body rewriting inserts nonces. Owner: `backend`. Source: CSP.
- **Inline scripts and inline event handlers block a strict policy.** Inline `<script>` code should move to external files and inline handlers such as `onclick` should be replaced with `addEventListener` calls.
  Check: grep templates for inline handlers and unnonced inline scripts. Owner: `frontend`. Source: CSP.
- **CSP missing from some responses or delivered only by `<meta>`.** Deliver the policy with the `Content-Security-Policy` response header on all HTTP responses, not only the index page; a `<meta http-equiv>` policy cannot carry `frame-ancestors`, `sandbox`, or reporting. Do not use `X-Content-Security-Policy` or `X-WebKit-CSP`.
  Check: inspect server, framework, or CDN header config for coverage of every route; flag obsolete prefixed headers. Owner: `backend`. Source: CSP.
- **Report-only policy mistaken for enforcement.** `Content-Security-Policy-Report-Only` is non-blocking (fail open) and is a precursor to enforcement; a strict report-only policy may run beside a looser enforced one.
  Check: confirm an enforcing `Content-Security-Policy` header exists, not only the report-only variant. Owner: `backend`. Source: CSP.
- **CSP reporting on deprecated directives only.** Use `report-to` with a `Reporting-Endpoints` header as the primary mechanism; `report-uri` is deprecated and may be declared alongside for older browsers until no longer needed.
  Check: the policy declares `report-to` (and the endpoint header), optionally `report-uri`. Owner: `backend`. Source: CSP.
- **Removed CSP directives relied on.** `prefetch-src` and `plugin-types` are removed from the specification and ignored; use the standard fetch directives and `object-src 'none'` instead. Directives that are specified do not inherit from `default-src`.
  Check: flag `prefetch-src` or `plugin-types` as controls; verify each needed fetch directive is set explicitly or falls back as intended. Owner: `backend`. Source: CSP.
- **No CSP at all where a strict one is not yet feasible.** The basic fallback is `default-src 'self'; frame-ancestors 'self'; form-action 'self';`, tightened to `default-src 'none'; script-src 'self'; connect-src 'self'; img-src 'self'; style-src 'self'; frame-ancestors 'self'; form-action 'self';`. When migrating to HTTPS, `upgrade-insecure-requests` forces all requests over HTTPS.
  Check: the response headers carry at least the basic policy; `form-action` restricts form targets. Owner: `backend`. Source: CSP.
- **Trusted Types not enforced for DOM XSS sinks.** `Content-Security-Policy: require-trusted-types-for 'script'` makes `innerHTML`, `outerHTML`, `document.write`, `script.src` and similar sinks reject plain strings so every assignment goes through a vetted policy; combine with a default policy that delegates to a sanitizer for legacy code paths.
  Check: the CSP includes `require-trusted-types-for 'script'` and the client defines its Trusted Types policies (default policy calls the sanitizer). Owner: `backend`, `frontend`. Source: XSS Prevention.
- See `cross-origin-and-browser.md` for `frame-ancestors` and framing defenses.
- See `client-code-and-third-party.md` for Subresource Integrity on third-party scripts.

## Defenses that do not work on their own

- **WAF relied on to prevent XSS.** WAFs match known attack strings, are bypassed regularly, cannot stop stored XSS once it passes the filter, and miss client-side DOM XSS; they are not recommended for preventing XSS.
  Check: flag designs or tickets that close an XSS finding by adding a WAF rule instead of fixing encoding or the sink. Owner: `architect`. Source: XSS Prevention, XSS Filter Evasion.
- See `sessions-and-cookies.md` for cookie attributes, which limit XSS impact but do not prevent it.
