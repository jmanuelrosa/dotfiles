# Java

When to read: the brief, diff, or assessed surface touches Java or JVM server code: JDBC or JPA queries, XPath evaluation, the MongoDB Java driver, servlet or JSP output, the OWASP Java Encoder or Java HTML Sanitizer, JCA/JCE or Google Tink cryptography, JAAS `LoginModule`s, Bean Validation (`javax.validation`, `jakarta.validation`, Hibernate Validator), or Log4j 2 / Logback configuration.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Java Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Java_Security_Cheat_Sheet.html), [JAAS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JAAS_Cheat_Sheet.html), [Bean Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Bean_Validation_Cheat_Sheet.html), [Injection Prevention in Java Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_in_Java_Cheat_Sheet.html)

## Contents

- Injection
- Output encoding and HTML sanitization
- Cryptography
- JAAS authentication
- Bean Validation
- Logging

## Injection

- **JDBC query built by string concatenation.** Untrusted input concatenated into SQL and run through `Statement` lets the caller rewrite the query; use `Connection.prepareStatement` with `?` placeholders and bind every value through `setString`, `setInt` and the other typed setters.
  Check: no `createStatement()` / `execute*` call receives a string built with `+`, `String.format` or `StringBuilder` from request data; every dynamic value goes through a `PreparedStatement` setter. Owner: `backend`. Source: Java Security.
- **JPQL query built by string concatenation.** JPA QL is injectable the same way SQL is; use `EntityManager.createQuery` with named parameters (`:colorName`) and `Query.setParameter`.
  Check: `createQuery` / `createNativeQuery` arguments are constant strings with named or positional parameters, never concatenated with untrusted values. Owner: `backend`. Source: Java Security.
- **OS command built where a Java API exists.** Building a shell command from untrusted input invites command injection; use the Java API for the job instead (for example `InetAddress.getByName(host).isReachable(timeout)` rather than invoking `ping`).
  Check: `Runtime.exec` and `ProcessBuilder` calls that carry request data have a library equivalent and are replaced by it; see `injection.md` for the rules when a process call is unavoidable. Owner: `backend`. Source: Java Security.
- **XPath expression built by string concatenation.** Concatenated XPath lets input change the query; register an `XPathVariableResolver` with `XPath.setXPathVariableResolver` and reference values as `$variable` in the compiled expression.
  Check: `XPath.compile` / `evaluate` receive constant expressions whose dynamic parts are `$name` variables resolved by a resolver. Owner: `backend`. Source: Java Security.
- **XML parser feeding XPath left with external entities enabled.** The sheet's XPath sample states that external entity resolution must be disabled on the `DocumentBuilderFactory` in production code.
  Check: every `DocumentBuilderFactory` that parses untrusted XML disables external entities; see `xml-and-deserialization.md` for the exact features. Owner: `backend`. Source: Java Security.
- **MongoDB query built from strings or client-supplied operator objects.** Concatenating untrusted values into query strings, or accepting a client-supplied query or operator document, lets the caller inject query syntax; validate the expected type, length and business format, then use the driver's typed builders with a fixed field name (`Filters.eq("borough", value)`).
  Check: `collection.find` receives a `Bson` built from `Filters.*` with constant field names and string or typed values, never a `Document.parse` of request JSON or a client-supplied filter map. Owner: `backend`. Source: Java Security.
- See `injection.md` for allowlist input validation, LDAP filter and DN escaping, and the stack-agnostic injection rules.

## Output encoding and HTML sanitization

- **Untrusted text written to HTML without context-specific encoding.** Input validation enforces business rules and does not replace XSS controls; encode untrusted text with the OWASP Java Encoder method for the output context (`Encode.forHtml` for an HTML body position, the matching `Encode.for*` method for attribute, JavaScript and CSS contexts).
  Check: every servlet, JSP or template write of request or stored user data passes through the `Encode.for*` method matching its sink, not through a regex validator alone. Owner: `backend`. Source: Java Security.
- **User-supplied markup rendered without a sanitization policy.** When the application intentionally accepts HTML, sanitize it with an OWASP Java HTML Sanitizer policy (`new HtmlPolicyBuilder().allowElements(...)`) that permits only the needed elements and attributes; the sanitized fragment is for HTML body positions only, not attributes, script or style, and must not be encoded afterwards or the tags display as text.
  Check: accepted rich text flows through `PolicyFactory.sanitize` with a narrow allowlist before rendering, and the result is only placed in body context. Owner: `backend`. Source: Java Security.
- **`@SafeHtml` used as the HTML control.** Hibernate Validator deprecated `@SafeHtml` (6.1.0.Final and 6.0.18.Final) and the sheet says to refrain from using it.
  Check: no model field relies on `@SafeHtml`; replace it with a Java HTML Sanitizer policy at the point markup is accepted. Owner: `backend`. Source: Bean Validation.
- See `xss-and-csp.md` for the per-context encoding rules and CSP.

## Cryptography

- **Hand-written cryptographic functions.** Never write your own cryptographic functions; avoid writing crypto code at all by using an existing secret management solution or the cloud provider's, and otherwise prefer a trusted, well-known library such as Google Tink over the built-in JCA/JCE classes, where errors are far too easy to make.
  Check: no custom cipher, MAC, KDF or random construction exists; new encryption code uses Tink primitives (`Aead`, `HybridEncrypt`) or a managed secret service rather than raw `Cipher`. Owner: `backend`. Source: Java Security.
- **Raw JCA/JCE design shipped without expert review.** If a separate library is truly impossible, the sheet strongly recommends a cryptography expert review the full design and code, because the most trivial error can severely weaken the encryption.
  Check: any change introducing `Cipher`, `KeyAgreement` or `KDF` usage records a cryptography review. Owner: `security`. Source: Java Security.
- **AES-GCM nonce reused or mis-sized.** GCM loses confidentiality and integrity when a nonce repeats under one key; use `AES/GCM/NoPadding` with a 256-bit key from `KeyGenerator` seeded by `SecureRandom`, a 128-bit tag (`GCMParameterSpec(128, nonce)`), and a fresh 12-byte (96-bit) `SecureRandom` nonce for every encryption, stored alongside the ciphertext.
  Check: the nonce is generated per `encrypt` call (never a constant, counter reset or field reused across calls), is 12 bytes, and the tag length is 128. Owner: `backend`. Source: Java Security.
- **Encryption context not bound as associated data.** The Tink samples pass relevant context about the encrypted data as associated data so it is verified on decryption.
  Check: `Aead.encrypt` / `HybridEncrypt.encrypt` calls pass meaningful context (sender, record id, purpose) as associated data, and decryption supplies the same value. Owner: `backend`. Source: Java Security.
- **Raw ECDH output used directly as an AES key.** Diffie-Hellman values need extraction before use as a key; derive the key with HKDF (Java 25+ `KDF.getInstance("HKDF-SHA256")` with `HKDFParameterSpec.ofExtract().addIKM(secret).thenExpand(info, length)`) under a domain-specific `info` label, and zero the shared secret afterwards.
  Check: the bytes from `KeyAgreement.generateSecret()` go through HKDF, never straight into `SecretKeySpec`, and the secret array is cleared with `Arrays.fill`. Owner: `backend`. Source: Java Security.
- **Peer public key not validated or authenticated.** HKDF does not authenticate the peer; public keys must be validated and authenticated independently before use, with identity and context bound by the surrounding protocol.
  Check: received public keys are validated and tied to an authenticated identity (certificate, signature, pinned key) before `KeyAgreement.doPhase`. Owner: `backend`. Source: Java Security.
- **Long-lived key agreement pairs.** The samples state key pair generation should be re-performed periodically to avoid a long-lived shared secret.
  Check: ECDH / hybrid key pairs have a rotation path rather than being generated once and kept forever. Owner: `backend`. Source: Java Security.
- See `cryptography-and-keys.md` for algorithm selection, crypto agility, key rotation and key storage, and `secrets-management.md` for secret stores.
- See `supply-chain-and-dependencies.md` for keeping crypto and other packages current through the package manager.

## JAAS authentication

- **`LoginContext.login()` failure not treated as failure.** `login()` returns without a value on success and throws `LoginException` on failure; the authenticated `Subject` is read with `getSubject()` only after a successful login.
  Check: callers catch `LoginException` as an authentication failure and never call `getSubject()` or proceed on the failure path. Owner: `backend`. Source: JAAS.
- **`LoginModule` missing a lifecycle method.** A `LoginModule` must implement `initialize()`, `login()`, `commit()`, `abort()` and `logout()`, and `initialize()` saves the supplied `Subject`, `CallbackHandler`, `sharedState` and `options`.
  Check: each custom module implements all five methods and keeps the four `initialize()` arguments in fields. Owner: `backend`. Source: JAAS.
- **Credentials associated with the `Subject` on a failed module.** `commit()` associates principals and credentials with the shared `Subject` only when this module's authentication succeeded, otherwise cleans up its saved state; it returns `true` on success, `false` when the module is ignored, and throws `LoginException` on failure.
  Check: `commit()` gates every `getPrincipals().add` / credential add on the module's own success flag from `login()`. Owner: `backend`. Source: JAAS.
- **Private credentials stored in the public credential set.** A `Subject` separates credentials by protection: passwords and private keys belong in the private credential set, shareable items such as public key certificates in the public set.
  Check: `commit()` adds secrets via `getPrivateCredentials()`, never `getPublicCredentials()`. Owner: `backend`. Source: JAAS.
- **Password handled as a `String`.** `login()` reads the password from `PasswordCallback.getPassword()` as a `char[]` and compares it against the stored repository value (for example LDAP).
  Check: the module keeps the password as `char[]` and does not convert it to `String` before verification. Owner: `backend`. Source: JAAS.
- **State left behind after a failed login.** `abort()` resets module state, including the captured username and password, before it exits.
  Check: `abort()` clears the stored username, password array and success flags. Owner: `backend`. Source: JAAS.
- **Principals and credentials not released on logout.** `logout()` removes the principals and credentials the module added from the `Subject` (when it is not read-only).
  Check: `logout()` removes each principal and credential class the module's `commit()` added, guarded by `subject.isReadOnly()`. Owner: `backend`. Source: JAAS.
- **`CallbackHandler` coupled to one module.** The `CallbackHandler` lives in its own source file, separate from any single `LoginModule`, so it can serve several modules with differing callbacks.
  Check: the handler is a standalone class implementing `handle()` for the callback types it supports. Owner: `backend`. Source: JAAS.

## Bean Validation

- **Model fields without constraints or controllers without `@Valid`.** Validation only runs when constraints (`@Pattern`, `@Digits`, `@Min`, `@Max`, `@Size`, `@Past`, `@Future`, `@CreditCardNumber`, `@Email`, `@URL`, `@Length`, `@Range`) are declared on the model and the model is passed with `@Valid`; in Spring XML configuration enable it with `<mvc:annotation-driven />`.
  Check: every request-bound model has constraints on its untrusted fields and every handler parameter that binds it carries `@Valid`. Owner: `backend`. Source: Bean Validation.
- **Validation errors ignored by the handler.** A handler that receives `BindingResult` and does not act on `hasErrors()` processes invalid input; reject with `400` (`HttpServletResponse.SC_BAD_REQUEST`) and handle logging and error pages deliberately.
  Check: each `@Valid` parameter's `BindingResult` is checked before business logic runs and failures return 400. Owner: `backend`. Source: Bean Validation.
- **Nested beans skipped by validation.** Constraints on nested objects are not evaluated unless the reference is marked `@Valid` for cascaded validation.
  Check: object-typed and collection fields of a validated model carry `@Valid` when their own constraints must apply. Owner: `backend`. Source: Bean Validation.
- **Free-text fields without allowlist or length bounds.** Strings are constrained with an allowlist `@Pattern` (the sheet's example: `[a-zA-Z0-9 ]+`; see the OWASP Validation Regex Repository) and a `@Size(min, max)` bound, numbers with `@Digits` or combined `@Min` / `@Max`.
  Check: request strings have both a `@Pattern` allowlist or equivalent and a `@Size` maximum; numeric fields have range constraints. Owner: `backend`. Source: Bean Validation.
- **`@Past` / `@Future` applied to date strings.** `@Future` does not validate date strings; apply temporal constraints to supported date types such as `java.util.Date` or `java.time.Instant`.
  Check: `@Past` / `@Future` annotate temporal types, not `String`. Owner: `backend`. Source: Bean Validation.
- **Validation API and provider versions mismatched.** Jakarta Validation 3.0 uses `jakarta.validation` while legacy code uses `javax.validation`; use API and Hibernate Validator versions compatible with the application, at the latest provider version.
  Check: the manifest pins a Hibernate Validator release matching the imported validation namespace and the framework version. Owner: `dx`. Source: Bean Validation.
- **Hardcoded validation messages.** Specify a message id in the annotation (`message="article.title.error"`) so Spring MVC resolves it from a `MessageSource`.
  Check: constraint `message` attributes are keys resolved through the message source. Owner: `backend`. Source: Bean Validation.

## Logging

- **Log message built by string concatenation.** Use parameterized logging with a compile-time constant pattern (`logger.warn("Login failed for user {}.", username)`); mixing concatenation with `{}` parameters lets a value containing `{}` pull the exception into the message.
  Check: Log4j 2 and SLF4J calls pass user data only as parameters to a constant pattern, never concatenated into the pattern. Owner: `backend`. Source: Java Security.
- **Unstructured text log format.** Unstructured logs are open to CR/LF injection (CWE-93); use a structured JSON format: Log4j 2 `JsonTemplateLayout` (2.14.0+), recommended for production with a `Socket` appender, or Logback `JsonEncoder` (1.3.8+) with a bounded rolling policy (the sheet's example rolls 10 files of 5 MB via `FixedWindowRollingPolicy` and `SizeBasedTriggeringPolicy`).
  Check: the production logging config uses `JsonTemplateLayout` or `JsonEncoder` rather than a pattern layout. Owner: `backend`. Source: Java Security.
- **User-controlled log values not length-limited.** Limit the size of user input placed in log messages; with Log4j 2 set `maxStringLength="500"` on `JsonTemplateLayout`, noting it truncates strings only and does not cap encoded bytes or total document size.
  Check: `JsonTemplateLayout` sets `maxStringLength` (500 per the sheet) or the code truncates user values before logging. Owner: `backend`. Source: Java Security.
- See `logging-and-error-handling.md` for applying XSS defenses in browser-based log viewers and for what to log.
