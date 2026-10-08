# .NET and ASP.NET

When to read: the brief, diff, or assessed surface touches .NET code or configuration: ASP.NET Core or ASP.NET MVC / Web Forms / Web API controllers, `Startup.cs` / `Program.cs` middleware, `web.config` or `appsettings.json`, ASP.NET Core Identity or Forms authentication, antiforgery tokens, Entity Framework or `SqlCommand` data access, `System.Diagnostics.Process`, .NET serializers, `System.Security.Cryptography`, NuGet packages, WCF bindings, or WinForms / XAML / ClickOnce deployment.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [DotNet Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/DotNet_Security_Cheat_Sheet.html)

## Contents

- Injection and data access
- Deserialization
- Access control
- Authentication and password storage
- Secrets and cryptography
- Session cookies and Forms authentication
- Cross-site request forgery
- Cross-site scripting and request validation
- Server-side request forgery and redirects
- Transport security and response headers
- Configuration and deployment
- Dependencies and build integrity
- Logging and monitoring
- WCF, desktop clients and security testing

## Injection and data access

- **SQL built by string concatenation, including through EF or stored procedures.** Dynamic SQL lets input rewrite the query, and ad hoc queries in Entity Framework or stored procedures are just as susceptible; use an ORM or stored procedures, and where direct SQL is needed use parameterized commands (`SqlParameter` with `context.Database.ExecuteSqlCommand`, `SqlCommand` parameters) for all data access without exception.
  Check: no `SqlCommand`, `ExecuteSqlCommand`, `FromSqlRaw` or stored-procedure call receives a string concatenated or interpolated from user input (CA2100 territory); every value is a parameter. Owner: `backend`. Source: DotNet Security.
- **Application connects to the database with an over-privileged account.** Connect with an account holding only the permissions the use case needs, never the database administrator account.
  Check: the connection string's login is a dedicated least-privilege user whose grants cover only the objects the application touches. Owner: `database`. Source: DotNet Security.
- **SQL Server SQL authentication used where integrated authentication is available.** Prefer integrated authentication over SQL authentication.
  Check: SQL Server connection strings use `Integrated Security` / managed identity rather than an embedded user id and password. Owner: `database`. Source: DotNet Security.
- **Sensitive columns stored without Always Encrypted.** Use Always Encrypted where possible for sensitive data on SQL Server 2016+ and Azure SQL.
  Check: columns holding sensitive data are configured for Always Encrypted, or the reason they cannot be is recorded. Owner: `database`. Source: DotNet Security.
- **User values accepted without an allowlist parse.** List allowable values and assure them with enums, `TryParse` or lookups; a cast to an enum accepts any value of the underlying integer type, so validate with `Enum.IsDefined`.
  Check: request values used in queries or logic are parsed with `TryParse` / lookup tables, and enum-typed input is checked with `Enum.IsDefined`. Owner: `backend`. Source: DotNet Security.
- **`Process.Start` or `ArgumentList` trusted to neutralize untrusted arguments.** Call OS functions through `System.Diagnostics.Process.Start` with `ProcessStartInfo`, but do not assume it stops input from breaking out of one argument into another; `ProcessStartInfo.ArgumentList` performs some escaping yet carries Microsoft's disclaimer that it is not safe with untrusted input, so do not rely on methods without a security guarantee.
  Check: process launches pass a fixed `FileName`, and any user-influenced argument is allowlist-validated before reaching `Arguments` or `ArgumentList`. Owner: `backend`. Source: DotNet Security.
- **Command arguments escaped instead of rejected.** Validate user input with an allowlist (for example `IPAddress.TryParse` for an address), accept only simple alphanumeric characters, and do not assume special characters can be sanitized without removing them (combinations of `\`, `'` and `@` defeat sanitization); consider passing untrusted values Base64-encoded and decoding them in the receiving application.
  Check: arguments reaching a process are parsed into a typed value or matched against an alphanumeric allowlist, or travel Base64-encoded, never through a hand-rolled escape routine. Owner: `backend`. Source: DotNet Security.
- **Active Directory DN components not escaped.** Characters with special meaning in Distinguished Names must be escaped with `\`; a space is escaped only when it is the leading or trailing character of a component such as a Common Name.
  Check: DN values built from input pass through an escaper for the AD character set; see `injection.md` for the full table. Owner: `backend`. Source: DotNet Security.

## Deserialization

- **`BinaryFormatter` used.** `BinaryFormatter` is dangerous and not recommended for data processing; use `XmlSerializer` or `DataContractSerializer` (not `NetDataContractSerializer`), `BinaryReader` / `BinaryWriter` for primitives, or `System.Text.Json`.
  Check: no reference to `BinaryFormatter` or `NetDataContractSerializer` exists; serialization uses one of the named in-box serializers. Owner: `backend`. Source: DotNet Security.
- **Serialized objects accepted from untrusted sources or sent unsigned.** Do not accept serialized objects from untrusted sources and do not send unsigned or unencrypted serialized objects over the network; perform integrity checks or validate digital signatures on serialized objects received, and validate user input such as cookies that could carry altered roles.
  Check: deserialization of network or cookie data is preceded by a signature or MAC verification, and outbound serialized payloads are signed or encrypted. Owner: `backend`. Source: DotNet Security.
- **Domain objects deserialized with full privileges.** Prevent deserialization of domain objects, and run deserialization code with limited access permissions so a hostile object that tries to start a process or reach a resource is denied and raises an alert.
  Check: deserialization targets DTOs rather than domain types, and runs in a context with reduced permissions. Owner: `backend`. Source: DotNet Security.
- See `xml-and-deserialization.md` for the XXE settings of .NET XML parsers and the stack-agnostic deserialization rules.

## Access control

- **Externally facing endpoint without authorization.** Authorize users on all externally facing endpoints, preferably with `[Authorize]` at controller level, otherwise at method level (`[Authorize(Roles = "Admin")]`), or in code with `Roles.IsUserInRole` / `User.Identity.IsInRole`.
  Check: every controller and Web API controller carries `[Authorize]` (or a global policy), and each `[AllowAnonymous]` is deliberate. Owner: `backend`. Source: DotNet Security.
- **Object loaded by id without an ownership check.** Loading a resource by a caller-supplied reference (`_context.Users.FirstOrDefault(e => e.Id == id)`) without confirming the user may access it is an insecure direct object reference.
  Check: handlers taking an id compare the loaded record's owner or tenant against the current identity before returning or editing it; see `authorization.md`. Owner: `backend`. Source: DotNet Security.
- **Web Forms resource requests not explicitly authorized.** Always implement access controls: compare a user-provided username with `User.Identity.Name`, check roles with `User.Identity.IsInRole`, and explicitly authorize resource requests.
  Check: Web Forms pages and handlers check identity and role before serving data, not only via navigation. Owner: `backend`. Source: DotNet Security.

## Authentication and password storage

- **Custom authentication or session management.** Do not roll your own authentication or session management; use what .NET provides, and for new ASP.NET Core applications use ASP.NET Core Identity (PBKDF2 with a random per-user salt by default).
  Check: login, password storage and session issuance go through ASP.NET Core Identity / the framework's cookie authentication rather than custom code. Owner: `backend`. Source: DotNet Security.
- **Password hashed with a general-purpose hash or a direct KDF call.** Store passwords with Identity's `PasswordHasher<TUser>`; do not use SHA-512 or other general-purpose hashes for passwords (SHA-512 is for general hashing needs only), and do not call `KeyDerivation.Pbkdf2` directly, which Microsoft calls a low-level primitive for integrating with existing systems.
  Check: no password flows into `SHA512`, `SHA256` or `KeyDerivation.Pbkdf2`; verification uses `PasswordHasher<TUser>`. Owner: `backend`. Source: DotNet Security.
- **ASP.NET Membership default password storage kept.** The Membership provider's default storage is a single iteration of SHA-1; review it, and prefer ASP.NET Identity (PBKDF2).
  Check: applications on the Membership provider have migrated hashes or a recorded plan; see `authentication.md` for the target algorithm and parameters. Owner: `backend`. Source: DotNet Security.
- **Identity password options enforce composition rules or a short minimum.** Follow NIST: `options.Password.RequiredLength = 15` when passwords can be used without MFA (8 when only used with MFA), with `RequireDigit`, `RequireNonAlphanumeric`, `RequireUppercase` and `RequireLowercase` set to `false` and `RequiredUniqueChars = 1`; the default validator counts UTF-16 code units, so add Unicode code-point length validation, and add breached-password screening, which Identity does not do.
  Check: `IdentityOptions.Password` matches these values, a code-point length validator is registered, and a breached-password check exists; see `authentication.md` for the full policy. Owner: `backend`. Source: DotNet Security.
- **Failed logins not counted toward lockout.** Configure `options.Lockout.DefaultLockoutTimeSpan = TimeSpan.FromMinutes(30)` and `options.Lockout.MaxFailedAccessAttempts = 3`, and call `PasswordSignInAsync(..., lockoutOnFailure: true)` so failures count.
  Check: every `PasswordSignInAsync` passes `lockoutOnFailure: true` and lockout options are set. Owner: `backend`. Source: DotNet Security.
- **Accounts usable before email confirmation.** Set `options.SignIn.RequireConfirmedEmail = true` and `options.User.RequireUniqueEmail = true`.
  Check: both Identity options are set in service configuration. Owner: `backend`. Source: DotNet Security.
- **Logon, registration and password reset not throttled.** Protect these actions against brute force by throttling requests (the sheet's example attribute allows 3 requests per 60 seconds) and consider adding ReCaptcha.
  Check: the three actions carry a rate-limit filter or middleware policy. Owner: `backend`. Source: DotNet Security.
- **Account existence revealed by message or timing.** Logon, registration and password reset must give identical feedback whether or not the account exists, in content and behavior, including response time ("Either the username or password was incorrect"; "If this account exists then a reset token will be sent").
  Check: both branches return the same message and status, and the not-found branch does equivalent work. Owner: `backend`. Source: DotNet Security.

## Secrets and cryptography

- **Secrets in source-controlled config files.** Keep secrets out of `web.config` and `appsettings.json` entirely: use User Secrets in development and a managed store (Azure Key Vault, AWS Secrets Manager, HashiCorp Vault) through Managed Identity / Workload Identity in production; on .NET Framework 4.7.1+ inject them with Configuration Builders (`Microsoft.Configuration.ConfigurationBuilders.Azure`, `...Environment`); encrypt `web.config` sections with `aspnet_regiis -pe` only as a last resort for unmodifiable legacy apps, since it protects the file at rest only.
  Check: no connection string password, API key or token appears in committed config; secrets resolve from a secret store or builder at runtime. Owner: `backend`. Source: DotNet Security.
- **Hand-written cryptographic functions.** Never write your own cryptographic functions; avoid crypto code by using a secrets management solution, and otherwise prefer a trusted, well-known library over the built-in .NET primitives.
  Check: no custom cipher or KDF construction exists; new crypto code has a recorded expert review. Owner: `backend`. Source: DotNet Security.
- **Restorable personal data encrypted with a weak algorithm.** Use a strong algorithm such as AES-256 where personal data must be restored to its original form; with `AesGcm`, use a 32-byte key from `RandomNumberGenerator.Fill`, a 12-byte nonce (`AesGcm.NonceByteSizes.MaxSize`) that is unique for every encryption under the key and stored alongside the ciphertext, and the maximum tag size.
  Check: `AesGcm.Encrypt` receives a freshly filled nonce per call, never a constant or reused buffer, and the key is 256 bits. Owner: `backend`. Source: DotNet Security.
- **Local sensitive data stored without DPAPI.** Use the Windows Data Protection API for secure local storage of sensitive data, and follow the Cryptographic Storage algorithm guidance where DPAPI cannot be used.
  Check: locally persisted secrets on Windows hosts use DPAPI (`ProtectedData`) or a documented equivalent. Owner: `desktop`. Source: DotNet Security.
- **ECDH exchange without public key validation or peer authentication.** The sheet's ECDH sample does not validate public keys and has no verification of authenticity between the two sides; a real design must add both.
  Check: ECDH-based exchanges validate received public keys and authenticate the peer before deriving keys. Owner: `backend`. Source: DotNet Security.
- See `cryptography-and-keys.md` for crypto agility, protecting encryption keys above any other asset, rotation and key storage.

## Session cookies and Forms authentication

- **Auth cookie readable by script.** Send cookies with `HttpOnly`: `options.Cookie.HttpOnly = true` in `ConfigureApplicationCookie`, `CookieHttpOnly = true` in OWIN cookie options, and `httpOnlyCookies` in Web Forms `web.config`.
  Check: the application cookie options and `<httpCookies>` set HttpOnly. Owner: `backend`. Source: DotNet Security.
- **Cookies sent over plain HTTP.** Enforce `<httpCookies requireSSL="true" />` and `<forms requireSSL="true" />` in the production config transforms.
  Check: production transforms set both `requireSSL` attributes (or `CookieSecurePolicy.Always` on Core). Owner: `backend`. Source: DotNet Security.
- **Long or sliding authentication lifetime.** Reduce the window a stolen session is usable: `ExpireTimeSpan = TimeSpan.FromMinutes(60)` with `SlidingExpiration = false` enforces an absolute lifetime, and enabling sliding expiration is a threat-model decision that trades risk for usability; reduce the Forms Authentication timeout from the 20-minute default to the shortest appropriate period, disable `slidingExpiration` if HTTPS is not used, and consider disabling it even with HTTPS.
  Check: cookie options set an explicit `ExpireTimeSpan`, and `SlidingExpiration = true` is justified in the design. Owner: `backend`. Source: DotNet Security.
- **Session or authorization carried in the URL.** Use cookies for Forms authentication persistence (`cookieless` defaults to `UseDeviceProfile`), and do not trust the request URI for persistence of the session or authorization.
  Check: `<forms cookieless="UseCookies">` is set and no auth decision reads identity from the URL. Owner: `backend`. Source: DotNet Security.

## Cross-site request forgery

- **ASP.NET Core state-changing requests not validated globally.** Add `AutoValidateAntiforgeryTokenAttribute` as a global filter (`options.Filters.Add(new AutoValidateAntiforgeryTokenAttribute())`), which validates every method except GET, HEAD, OPTIONS and TRACE; where a global filter is impossible, put `[AutoValidateAntiforgeryToken]` on every controller and Razor page model.
  Check: MVC options register the global filter, or every controller / `PageModel` carries the attribute. Owner: `backend`. Source: DotNet Security.
- **.NET Framework POST action without `[ValidateAntiForgeryToken]`.** Do not accept sensitive data without validating antiforgery tokens; validate at the method or preferably the controller level.
  Check: every POST/PUT action (or its controller) carries `[ValidateAntiForgeryToken]`. Owner: `backend`. Source: DotNet Security.
- **Antiforgery validation switched off or missing on a dangerous GET.** `[IgnoreAntiforgeryToken]` disables validation for an action or page; a GET, HEAD, OPTIONS or TRACE handler that changes state needs `[ValidateAntiforgeryToken]` explicitly.
  Check: each `[IgnoreAntiforgeryToken]` is on a handler with no cookie-authenticated side effect, and state-changing GETs carry `[ValidateAntiforgeryToken]`. Owner: `backend`. Source: DotNet Security.
- **Form or AJAX request sent without the token.** Send the token with every POST/PUT: tag helpers (`@addTagHelper *, Microsoft.AspNetCore.Mvc.TagHelpers`) add it only to `method="post"` forms with an absent or empty `action`, `IHtmlHelper.BeginForm` adds it for non-GET methods, other forms need `@Html.AntiForgeryToken()`, and AJAX requests must include `__RequestVerificationToken` (for example from `IAntiforgery.GetAndStoreTokens`); token generation must always be paired with server-side validation.
  Check: forms outside the automatic cases emit `@Html.AntiForgeryToken()`, and AJAX calls attach the request token. Owner: `backend`, `frontend`. Source: DotNet Security.
- **Antiforgery cookie left after logout.** Remove the tokens completely on logout, including the `__RequestVerificationToken` cookie.
  Check: the logout action expires the antiforgery cookie. Owner: `backend`. Source: DotNet Security.
- **Web Forms page without a user-bound ViewState key or anti-XSRF token.** Set `ViewStateUserKey` (for example `Session.SessionID`) in `OnInit`, or, without ViewState, use the default template's double-submit `__AntiXsrfToken` cookie (HttpOnly, Secure under `RequireSSL`) and validate token and username on postback.
  Check: the master page or each page sets `ViewStateUserKey` or implements the token check that throws on mismatch. Owner: `backend`. Source: DotNet Security.
- See `cross-origin-and-browser.md` for the stack-agnostic CSRF rules.

## Cross-site scripting and request validation

- **`@Html.Raw` or `[AllowHtml]` on unverified content.** Do not use either unless you are absolutely sure the content is safe and properly escaped.
  Check: each `Html.Raw` / `[AllowHtml]` use is fed only by sanitized or constant content. Owner: `backend`. Source: DotNet Security.
- **Classic ASP.NET without context-aware encoding.** Use the AntiXSS encoder for HTML, JavaScript, CSS and LDAP contexts: set `encoderType="Microsoft.Security.Application.AntiXssEncoder, AntiXssLibrary"` on `httpRuntime`, or on .NET Framework 4.5+ use the built-in `AntiXssEncoder`.
  Check: `httpRuntime` names the AntiXSS encoder, or output in non-HTML contexts calls the matching `AntiXssEncoder` method. Owner: `backend`. Source: DotNet Security.
- **`validateRequest` disabled.** Do not disable `validateRequest` in `web.config` or page directives; it gives partial XSS protection, and complete request validation is recommended on top of it.
  Check: no `validateRequest="false"` appears in config or pages. Owner: `backend`. Source: DotNet Security.
- **Untrusted input accepted through a denylist.** Do not trust user data, prefer allowlists over denylists, list allowable values whenever input is accepted, and validate URIs with `Uri.IsWellFormedUriString`.
  Check: input validation uses allowlists or typed parsers, and URI inputs pass `Uri.IsWellFormedUriString`. Owner: `backend`. Source: DotNet Security.
- **No Content Security Policy.** Enable a CSP, for example `default-src 'none'; style-src 'self'; img-src 'self'; font-src 'self'; script-src 'self'` via `web.config` `customHeaders`, or `app.UseCsp(...)` middleware in Core.
  Check: responses carry a `Content-Security-Policy` header from config or middleware; see `xss-and-csp.md` for policy design. Owner: `backend`. Source: DotNet Security.

## Server-side request forgery and redirects

- **Outbound request target taken from user input without an allowlist.** Validate and sanitize user input before using it in a request, allowlist permitted protocols and domains, and use `IPAddress.TryParse()` and `Uri.CheckHostName()` to confirm addresses and host names are valid.
  Check: `HttpClient` calls with a user-influenced URL check scheme and host against an allowlist first; see `ssrf.md`. Owner: `backend`. Source: DotNet Security.
- **Outbound client follows redirects or returns raw responses.** Do not follow HTTP redirects and do not forward raw HTTP responses to the user.
  Check: the `HttpClientHandler` used for user-influenced URLs sets `AllowAutoRedirect = false`, and responses are mapped rather than proxied. Owner: `backend`. Source: DotNet Security.
- **Return URL redirected without a local check.** Redirect a post-login `returnUrl` only when `Url.IsLocalUrl(returnUrl)` is true, otherwise to a fixed landing action.
  Check: every `Redirect(returnUrl)` is guarded by `Url.IsLocalUrl`; see `cross-origin-and-browser.md`. Owner: `backend`. Source: DotNet Security.

## Transport security and response headers

- **SSL or TLS below 1.2 enabled.** Use TLS 1.2+ for the entire site with a strong TLS policy, do not allow SSL, and automate certificate renewal (for example Let's Encrypt).
  Check: server or edge TLS config disables SSL and TLS 1.0/1.1, and certificates renew automatically; see `http-headers-tls-and-caching.md`. Owner: `cloud`. Source: DotNet Security.
- **HTTP requests not redirected to HTTPS.** Always use HTTPS: `app.UseHttpsRedirection()` in Core, a production-only `Application_BeginRequest` redirect when `!Request.IsSecureConnection` in Framework, or an IIS rewrite rule that permanently redirects GET and HEAD when `{HTTPS}` is off.
  Check: the pipeline or IIS config redirects all plain-HTTP requests. Owner: `backend`. Source: DotNet Security.
- **HSTS missing.** Set `Strict-Transport-Security` (`app.UseHsts(hsts => hsts.MaxAge(365).IncludeSubdomains())`, or an IIS outbound rule with `max-age=15768000`) and register for HSTS preload to protect first visits.
  Check: HTTPS responses carry HSTS with `includeSubDomains`, and the domain is preload-registered. Owner: `backend`. Source: DotNet Security.
- **Headers disclose the server stack.** Set `<httpRuntime enableVersionHeader="false"/>` (in `web.config` or `Machine.config`), `<requestFiltering removeServerHeader="true" />`, `<remove name="X-Powered-By"/>`, and remove `Server` in code with `Response.Headers.Remove("Server")`.
  Check: config removes `X-AspNet-Version`, `Server` and `X-Powered-By`. Owner: `backend`. Source: DotNet Security.
- **Hardening headers absent.** Send `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (against clickjacking), `X-Permitted-Cross-Domain-Policies: master-only`, `X-XSS-Protection: 0` and `Referrer-Policy: no-referrer` through `customHeaders` or middleware.
  Check: these headers appear in `web.config` `customHeaders` or the Core middleware; see `http-headers-tls-and-caching.md` for current values. Owner: `backend`. Source: DotNet Security.

## Configuration and deployment

- **Debug or trace enabled in production.** Turn debug and trace off in production via `web.config` transforms (`<compilation xdt:Transform="RemoveAttributes(debug)" />`, `<trace enabled="false" xdt:Transform="Replace"/>`), turn IIS tracing off, and call `UseDeveloperExceptionPage` only when `env.IsDevelopment()`.
  Check: release transforms strip `debug`, disable trace, and the developer exception page is environment-gated. Owner: `backend`. Source: DotNet Security.
- **No custom error pages.** Implement `customErrors` so stack traces never reach users.
  Check: `<customErrors mode="On">` or `RemoteOnly` with a default redirect, or `UseExceptionHandler` in Core. Owner: `backend`. Source: DotNet Security.
- **Default passwords or unused configuration shipped.** Do not use default passwords, lock down config files, and remove every configuration section that is not in use.
  Check: config contains no vendor default credentials or dormant sections. Owner: `backend`. Source: DotNet Security.

## Dependencies and build integrity

- **Framework and packages left unpatched.** Keep the .NET framework patched and NuGet packages current, update third-party libraries that do not ship through NuGet (for example ELMAH) separately, and watch the .NET Core and ASP.NET Core / EF Core security announcement repositories.
  Check: package references are current against advisories and non-NuGet libraries have an update owner. Owner: `dx`. Source: DotNet Security.
- **No dependency vulnerability scan in the build.** Run OWASP Dependency-Check or another SCA tool in the build and CI/CD pipeline and act on any high or critical finding.
  Check: CI runs an SCA step that fails or alerts on high/critical vulnerabilities. Owner: `platform`. Source: DotNet Security.
- **Unsigned assemblies or packages.** Digitally sign assemblies and executable files, and use NuGet package signing.
  Check: the release pipeline signs binaries and NuGet packages and verifies signatures of consumed packages. Owner: `platform`. Source: DotNet Security.
- **Changes merged without review for malicious code.** Review code and configuration changes to avoid introducing malicious code or dependencies.
  Check: branch protection requires review on code, config and dependency changes. Owner: `security`. Source: DotNet Security.

## Logging and monitoring

- **Security failures logged without user context.** Log all login, access-control and server-side input validation failures, plus successful and failed logins, with enough user context to identify suspicious accounts; log the stack trace, error message and user id rather than a generic "Error was thrown", and capture all unhandled errors through `UseExceptionHandler`.
  Check: auth and authorization failure paths call `ILogger` with user id and outcome, and the exception handler logs the stack trace. Owner: `backend`. Source: DotNet Security.
- **Passwords or other sensitive data logged.** Do not log sensitive data such as passwords.
  Check: no log statement includes password fields, tokens or full model objects containing them. Owner: `backend`. Source: DotNet Security.
- **Logger not injected.** Inject `ILogger` through the constructor for classes created by dependency injection (such as MVC controllers), which keeps logging testable.
  Check: controllers receive `ILogger<T>` by constructor rather than static loggers. Owner: `backend`. Source: DotNet Security.
- **No monitoring or alerting on suspicious activity.** Establish monitoring and alerting so suspicious activity is detected and handled in time (for example Application Insights).
  Check: the deployment wires telemetry and alert rules for authentication and authorization failures; see `logging-and-error-handling.md`. Owner: `sre`. Source: DotNet Security.

## WCF, desktop clients and security testing

- **WCF `BasicHttpBinding`.** `BasicHttpBinding` has no default security configuration; use `WSHttpBinding` with at least two security modes (message and transport), as `TransportWithMessageCredential` combines them.
  Check: WCF bindings are `WSHttpBinding` with `TransportWithMessageCredential` or equivalent. Owner: `backend`. Source: DotNet Security.
- **Sensitive values in WCF REST URLs.** Use HTTPS for RESTful requests regardless of method, choose methods by their semantics, and keep sensitive values out of URLs; POST moves data into the body but provides neither confidentiality nor authorization by itself.
  Check: no token, password or personal data appears in route or query parameters. Owner: `backend`. Source: DotNet Security.
- **Desktop app running with more trust than it needs.** Use partial trust for Windows Forms where possible and request a managed list of required permissions declaratively; XAML apps work within Internet Zone constraints; deploy with ClickOnce, using runtime elevation or trusted application deployment for enhanced permissions, on a .NET Framework recent enough for TLS 1.2+.
  Check: the manifest requests a minimal permission set and ClickOnce targets a framework version with TLS 1.2 support. Owner: `desktop`. Source: DotNet Security.
- **Web API and WCF surfaces left out of security testing.** Web API services hidden inside MVC sites are public attack surface and need the same security testing and analysis as MVC; fuzz WCF implementations (for example with ZAP), and after covering the Top 10 consider a professional penetration test.
  Check: the test suite or pipeline covers Web API and WCF endpoints with negative and fuzz tests. Owner: `qa`. Source: DotNet Security.
