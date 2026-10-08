# PHP, Laravel and Symfony

When to read: the brief, diff, or assessed surface touches `php.ini` or PHP runtime images, Laravel (`config/session.php`, `App\Http\Kernel` middleware groups, Eloquent models, Blade templates, `routes/*.php`, `.env` `APP_*` keys), or Symfony (`config/packages/framework.yaml`, `security.yaml`, `nelmio_cors.yaml`, Doctrine DQL, Twig templates, Symfony Forms, `config/secrets/`).
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [PHP Configuration](https://cheatsheetseries.owasp.org/cheatsheets/PHP_Configuration_Cheat_Sheet.html), [Laravel](https://cheatsheetseries.owasp.org/cheatsheets/Laravel_Cheat_Sheet.html), [Symfony](https://cheatsheetseries.owasp.org/cheatsheets/Symfony_Cheat_Sheet.html)

## Contents

- Code execution and injection
- Debug mode, error disclosure and secrets
- Mass assignment, authentication and access control
- Output encoding (XSS)
- CSRF
- Sessions and cookies
- File upload and path traversal
- Redirects
- PHP runtime hardening and deployment
- Rate limiting, headers and CORS
- Dependencies and operations

## Code execution and injection

- **Raw Eloquent or query builder SQL built by concatenation.** `whereRaw`, `DB::table(...)->whereRaw` and other raw expressions concatenated with request input are injectable, because only Eloquent's standard methods bind parameters automatically.
  Check: every `whereRaw`, `selectRaw`, `orderByRaw`, `DB::raw`, `DB::select` call passes request data through a bindings array (`whereRaw('email = ?', [$email])` or named `:email` bindings), never through string concatenation or interpolation. Owner: `backend`. Source: Laravel.
- **Request input chooses a column name.** Databases cannot bind identifiers, so `where($request->input('colname'), ...)` or `orderBy($request->input('sortBy'))` can be injectable on some engines and at least lets the caller query columns the code never intended.
  Check: any column, sort key or identifier taken from the request is first validated against an allowlist (`$request->validate(['sortBy' => 'in:price,updated_at'])`) and read back from `$request->validated()`. Owner: `backend`. Source: Laravel.
- **Validation rule takes a column name from input.** Rules that accept a database column, such as `Rule::unique('users')->ignore($id, $request->input('colname'))`, build a query with that column and are injectable the same way.
  Check: no `Rule::unique`, `Rule::exists` or similar rule receives a column argument derived from request data; hardcode the column. Owner: `backend`. Source: Laravel.
- **Doctrine DQL concatenated with request data.** Doctrine parameterizes only when asked; `createQuery("... WHERE p.id = " . $id)` is injectable.
  Check: DQL and query builder calls use repository methods (`findOneBy(['id' => $id])`) or named parameters with `setParameter()`; no request value is concatenated into a DQL or SQL string. Owner: `backend`. Source: Symfony.
- **Shell command built from request input.** `exec()`, `shell_exec()` and friends with interpolated input allow command injection.
  Check: prefer a PHP or Symfony API that does the job without a shell (`unlink()`, Symfony Filesystem `remove()`, a PHP library instead of `whois`); where a process is unavoidable, use Symfony Process with a fixed executable and an argument array, and validate each argument's format first because argument separation does not stop option injection. Owner: `backend`. Source: Laravel, Symfony.
- **`escapeshellcmd()` used as argument separation.** `escapeshellcmd()` still lets the caller add extra arguments.
  Check: no `escapeshellcmd()` on untrusted data; if a shell call is truly unavoidable, each argument goes through `escapeshellarg()` and is still validated for its meaning to the called program. Owner: `backend`. Source: Laravel.
- See `injection.md` for argument injection and generic OS command defenses.
- **Untrusted input reaches `unserialize`, `eval` or `extract`.** These enable object injection, code injection and variable hijacking.
  Check: no `unserialize()`, `eval()` or `extract()` call receives request data (for example `extract($request->all())`); use JSON decoding and explicit field reads instead. Owner: `backend`. Source: Laravel.
- **Remote URL include enabled.** With `allow_url_fopen` or `allow_url_include` on, a local file inclusion bug escalates to remote file inclusion.
  Check: `php.ini` sets `allow_url_fopen = Off` and `allow_url_include = Off`. Owner: `platform`. Source: PHP Configuration.
- **Dangerous PHP functions left enabled.** Functions the application never calls still widen what an injection can do.
  Check: `php.ini` sets `enable_dl = Off` and a `disable_functions` list covering every unused function from the sheet's set (`system, exec, shell_exec, passthru, phpinfo, show_source, highlight_file, popen, proc_open, fopen_with_path, dbmopen, dbase_open, putenv, move_uploaded_file, chdir, mkdir, rmdir, chmod, rename, filepro, filepro_rowcount, filepro_retrieve, posix_mkfifo`). Owner: `platform`. Source: PHP Configuration.

## Debug mode, error disclosure and secrets

- **Framework debug mode on in production.** Debug pages expose stack traces, configuration and secrets.
  Check: production environment sets `APP_DEBUG=false` (Laravel) or `APP_ENV=prod` (Symfony, which then shows generic error pages and only logs details). Owner: `backend`. Source: Laravel, Symfony.
- **PHP errors displayed to clients.** Displayed errors and argument values leak paths, queries and data.
  Check: production `php.ini` has `display_errors = Off`, `display_startup_errors = Off`, `html_errors = Off` and `zend.exception_ignore_args = On`. Owner: `platform`. Source: PHP Configuration.
- **PHP errors not logged.** Without logging, failures and probing go unseen.
  Check: `php.ini` has `error_reporting = E_ALL`, `log_errors = On`, `error_log` pointing at a valid dedicated path, `ignore_repeated_errors = Off` and `report_memleaks = On`, and the log is reviewed regularly. Owner: `platform`. Source: PHP Configuration.
- **PHP version advertised.** `expose_php` adds an `X-Powered-By` header that fingerprints the runtime.
  Check: `php.ini` sets `expose_php = Off`. Owner: `platform`. Source: PHP Configuration.
- **Laravel application key missing.** The app key protects cookie encryption, signed URLs, password reset tokens and session encryption.
  Check: every environment provisions a generated `APP_KEY` (`php artisan key:generate`) from its secret store, and no real key is committed in `.env` files or examples. Owner: `backend`. Source: Laravel.
- **Symfony secrets in plain config or with a committed decryption key.** Symfony's secrets vault only protects values while the private key stays out of the repository.
  Check: API keys and similar values come from environment variables or the Symfony secrets vault (`secrets:generate-keys`, `secrets:set`); the `config/secrets/<env>/` private decryption key is gitignored; no environment variable silently shadows a secret of the same name, since environment variables always override secrets. Owner: `backend`. Source: Symfony.
- See `secrets-management.md` for secret storage and rotation in general.

## Mass assignment, authentication and access control

- **Whole request mass-assigned to a model.** Passing `$request->all()` to `fill`, `update`, `create` or `forceFill` lets a caller set columns such as `is_admin`.
  Check: model writes use `$request->only([...])` or `$request->validated()`, never `$request->all()`. Owner: `backend`. Source: Laravel.
- **Eloquent mass-assignment protection disabled.** `Model::unguard()` or `protected $guarded = []` switches the built-in protection off.
  Check: no model sets `$guarded` to an empty array and no code calls `unguard()`; models declare `$fillable` or a non-empty `$guarded`. Owner: `backend`. Source: Laravel.
- **`forceFill` or `forceCreate` on unvalidated data.** These bypass mass-assignment protection entirely.
  Check: every `forceFill`/`forceCreate` call receives only an explicitly validated array. Owner: `backend`. Source: Laravel.
- See `authorization.md` for mass assignment and object-level authorization beyond Eloquent.
- **Hand-rolled Laravel authentication.** Laravel recommends its starter kits for login, registration, reset, verification and confirmation flows.
  Check: authentication flows come from Breeze, Fortify or Jetstream (Fortify or Jetstream for two-factor), and API authentication from Passport (OAuth2) or Sanctum (API tokens), configured through guards and providers in `config/auth.php`. Owner: `backend`. Source: Laravel.
- **Symfony route outside firewall or access control.** Firewalls and `access_control` rules in `config/packages/security.yaml` decide which paths require authentication and which roles.
  Check: protected path prefixes (for example `^/admin`) have an `access_control` entry with the required role; `PUBLIC_ACCESS` appears only on intentionally public paths such as login; any firewall with `security: false` matches only profiler, toolbar and static asset patterns; each firewall names its provider and authenticator. Owner: `backend`. Source: Symfony.
- **CSRF or path validation treated as authorization.** A valid CSRF token or a contained file path says nothing about whether the caller may act on that object.
  Check: actions that delete or read a specific post or file check the caller's permission for that object separately from CSRF and path checks. Owner: `backend`. Source: Symfony.

## Output encoding (XSS)

- **Untrusted data rendered with Blade `{!! !!}`.** The unescaped syntax must never carry untrusted data.
  Check: no `{!! ... !!}` renders request data or user-controlled fields; use `{{ }}`. Owner: `frontend`. Source: Laravel.
- **Blade `{{ }}` assumed safe in every context.** `{{ }}` applies `htmlspecialchars`, which suits HTML text and quoted ordinary attributes but does not validate URL schemes or encode JavaScript or CSS.
  Check: data embedded in JavaScript uses `Js::from`; values in `href`/`src`, inline scripts or styles follow context-specific encoding and URL scheme validation. Owner: `frontend`. Source: Laravel.
- **Twig `|raw` or disabled autoescape on untrusted data.** Twig escapes `{{ }}` by default; `|raw` and autoescape-off blocks remove that.
  Check: `|raw` and `{% autoescape false %}` appear only on values the application fully controls. Owner: `frontend`. Source: Symfony.
- See `xss-and-csp.md` for context-specific encoding rules and URL validation.

## CSRF

- **Laravel CSRF middleware missing from the web group.** Without `VerifyCsrfToken`, cookie-authenticated forms are forgeable.
  Check: the `web` middleware group includes `VerifyCsrfToken`; POST forms include `@csrf`; AJAX clients send the `X-CSRF-TOKEN` header. Owner: `backend`. Source: Laravel.
- **Stateful routes in the CSRF `$except` list.** Excluded routes have no CSRF protection.
  Check: `$except` in the CSRF middleware lists only stateless routes such as token-authenticated APIs or webhooks. Owner: `backend`. Source: Laravel.
- **Symfony form with CSRF disabled.** Symfony Forms add and validate a `_token` field automatically unless `csrf_protection` is set to false.
  Check: no form type sets `'csrf_protection' => false` for a cookie-authenticated, state-changing form. Owner: `backend`. Source: Symfony.
- **Manual Symfony CSRF check missing or late.** Outside Symfony Forms, nothing validates the token unless the action does.
  Check: `framework.csrf_protection: true` is set; the route accepts only `POST`; the action calls `isCsrfTokenValid()` with the same token ID used by `csrf_token()` in the template, rejects a missing or non-string token, and does so before any state change. Owner: `backend`. Source: Symfony.
- See `cross-origin-and-browser.md` for CSRF design beyond the framework helpers.

## Sessions and cookies

- **PHP session id accepted from URLs or uninitialized ids.** Without strict mode and cookie-only ids, session fixation and id leakage through URLs are possible.
  Check: `php.ini` sets `session.use_strict_mode = 1`, `session.use_cookies = 1`, `session.use_only_cookies = 1`, `session.use_trans_sid = 0`, `session.sid_length = 256` and `session.sid_bits_per_character = 6`. Owner: `platform`. Source: PHP Configuration.
- **PHP session cookie missing security attributes.** Session cookies without `Secure`, `HttpOnly` and `SameSite` are exposed to sniffing, script theft and cross-site sending.
  Check: `php.ini` sets `session.cookie_secure = 1`, `session.cookie_httponly = 1`, `session.cookie_samesite = Strict`, `session.cookie_domain` to the fully qualified host, and `session.cookie_path` to the application path where applicable. Owner: `platform`. Source: PHP Configuration.
- **PHP session lifetime and storage left at defaults.** Long-lived sessions and shared session storage widen hijack windows.
  Check: `php.ini` sets a dedicated `session.save_path`, a non-default `session.name`, `session.gc_maxlifetime = 600`, `session.cookie_lifetime = 14400` (4 hours), `session.cache_expire = 30`, and `session.referer_check` to the application path. Owner: `platform`. Source: PHP Configuration.
- **`session.auto_start` enabled.** Auto-started sessions bypass the application's session handling, and with Symfony they conflict with the framework's own session management.
  Check: `php.ini` sets `session.auto_start = Off`. Owner: `platform`. Source: PHP Configuration, Symfony.
- **Laravel cookie encryption middleware removed.** Without `EncryptCookies`, clients can read and tamper with cookie contents, including the `cookie` session store.
  Check: the `web` middleware group keeps `EncryptCookies` unless a documented use case requires otherwise. Owner: `backend`. Source: Laravel.
- **Laravel session cookie attributes weakened.** `config/session.php` controls the session cookie's exposure.
  Check: `config/session.php` has `'http_only' => true`, `'same_site' => 'lax'` or `'strict'`, `'secure' => true` for HTTPS-only apps (`null` only for mixed HTTP/HTTPS), and `'domain' => null` unless subdomain sharing is required (a `__Host-` prefixed cookie with `Secure`, `Path=/` and no Domain protects against sibling-subdomain cookie collisions). Owner: `backend`. Source: Laravel.
- **Laravel session idle timeout too long.** OWASP recommends a 2 to 5 minute idle timeout for high-value applications and 15 to 30 minutes for low-risk ones.
  Check: `'lifetime'` in `config/session.php` falls in the range matching the application's risk. Owner: `backend`. Source: Laravel.
- **Symfony session cookie left on `auto` or without HttpOnly.** `cookie_secure: auto` sets the cookie insecure on HTTP requests.
  Check: `framework.session` in `config/packages/framework.yaml` sets `cookie_secure: true` for HTTPS apps, `cookie_httponly: true`, and `cookie_samesite: lax` (or `strict` where navigation allows); CSRF protection stays on for state-changing requests because SameSite does not isolate sibling subdomains. Owner: `backend`. Source: Symfony.
- **Symfony `cookie_lifetime` mistaken for a session timeout.** `cookie_lifetime` is in seconds and cookie expiry does not end the session on the server.
  Check: values are expressed in seconds, and server-side idle and absolute expiration are implemented separately. Owner: `backend`. Source: Symfony.
- See `sessions-and-cookies.md` for idle and absolute timeout design and cookie prefixes.

## File upload and path traversal

- **Upload accepted on type and size validation alone.** Laravel's `mimes` rule infers type from content and does not validate the extension or make the file safe to execute; Symfony's `File` constraint likewise only bounds size and MIME type.
  Check: uploads are validated server-side (`file|max:...|mimes:...` in Laravel, `#[File(maxSize: ..., mimeTypes: [...])]` or a `File` form constraint in Symfony) and, in addition, stored under a generated unique filename, outside the webroot or public directory (or a web server rule denies access), never executable by the server, with aggregate storage and upload frequency bounded. Owner: `backend`. Source: Laravel, Symfony.
- **User input chooses the stored filename or directory.** `storeAs(auth()->id(), $request->input('filename'))` lets `../` write into another user's directory or overwrite files.
  Check: stored names are generated, or user-supplied names pass through `basename()` before reaching `storeAs`, `move` or path building. Owner: `backend`. Source: Laravel.
- **Download path built from a request filename.** `response()->download(storage_path('content/') . $filename)` can serve `../../.env`.
  Check: the filename is reduced with `basename()`, or both base and target are resolved with `realpath()`, a `false` result is rejected, and containment is tested with `str_starts_with($realPath, $realBase . DIRECTORY_SEPARATOR)` so a sibling directory such as `/storage-private` does not match. Owner: `backend`. Source: Laravel, Symfony.
- **ZIP or XML uploads processed.** These expose XXE, entity expansion and zip bomb attacks.
  Check: the feature avoids processing ZIP or XML uploads where possible; where it must, see `xml-and-deserialization.md` and `file-upload.md`. Owner: `backend`. Source: Laravel.
- **PHP upload limits unset.** Default upload settings permit large or numerous uploads.
  Check: `php.ini` sets `file_uploads = Off` when the app takes no uploads; otherwise a dedicated `upload_tmp_dir`, `upload_max_filesize = 2M` and `max_file_uploads = 2` (or values the feature justifies). Owner: `platform`. Source: PHP Configuration.
- See `file-upload.md` for the remaining upload controls.

## Redirects

- **Redirect target taken from request input.** `redirect($request->input('url'))` (Laravel) or `$this->redirect($url)` from a query parameter (Symfony) enables phishing through the trusted domain.
  Check: redirect targets are validated against an allowlist or restricted to relative application paths before use. Owner: `backend`. Source: Laravel, Symfony.
- See `cross-origin-and-browser.md` for redirect validation patterns.

## PHP runtime hardening and deployment

- **Unsupported PHP branch.** A branch past its upstream security-support date receives no fixes; distribution extended support does not make the upstream branch supported.
  Check: the runtime image or platform pins a branch listed on php.net Supported Versions, with an upgrade planned before its security-support end date. Owner: `platform`. Source: PHP Configuration.
- **PHP filesystem reach not confined.** Without path confinement, a file inclusion or traversal bug reaches the whole filesystem.
  Check: `php.ini` sets `doc_root`, `open_basedir`, `include_path`, `extension_dir` and `mime_magic.magicfile` to specific application paths, `variables_order = "GPCS"` and `allow_webdav_methods = Off`. Owner: `platform`. Source: PHP Configuration.
- **PHP resource limits unset.** Unbounded memory, body size and execution time aid denial of service.
  Check: `php.ini` sets `memory_limit = 50M`, `post_max_size = 20M` and `max_execution_time = 60`, or values the application justifies. Owner: `platform`. Source: PHP Configuration.
- **No PHP hardening extension considered.** The sheet names Snuffleupagus as the production-usable hardening module for PHP 7 onward.
  Check: the runtime image documents whether Snuffleupagus or an equivalent is used. Owner: `platform`. Source: PHP Configuration.
- **Application files writable or executable beyond need.** Loose permissions let a compromised process modify code.
  Check: deployment sets directories to at most `775`, non-executable files to at most `664`, and only executables such as Artisan or deploy scripts to `775`. Owner: `platform`. Source: Laravel, Symfony.
- **HTTP served without redirect to HTTPS.** Symfony recommends a properly configured certificate and redirecting all HTTP traffic to HTTPS at the web server.
  Check: web server or ingress config redirects HTTP to HTTPS and references a valid certificate. Owner: `platform`. Source: Symfony.

## Rate limiting, headers and CORS

- **Routes without throttling.** Laravel ships rate limiting but only the `api` group is throttled by default.
  Check: sensitive and expensive routes or groups carry `throttle` middleware (for example `throttle:10,1`) or a named limiter defined with `RateLimiter::for()` keyed by user id or IP (`Limit::perMinute(5)->by($request->user()?->id ?: $request->ip())`), and the `web` group is throttled where appropriate. Owner: `backend`. Source: Laravel.
- **Security headers not set.** Laravel names `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security` (HTTPS-only apps) and `Content-Security-Policy`; Symfony adds `X-Permitted-Cross-Domain-Policies`, `Referrer-Policy`, `Clear-Site-Data`, `Cross-Origin-Embedder-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy` and `Cache-Control`.
  Check: these headers are set in Laravel middleware, a Symfony `kernel.response` (`ResponseEvent`) listener, or the web server config. Owner: `backend`. Source: Laravel, Symfony.
- See `http-headers-tls-and-caching.md` for recommended header values.
- **CORS policy configured ad hoc.** Symfony recommends `nelmio/cors-bundle` to control CORS precisely per path.
  Check: CORS rules live in `config/packages/nelmio_cors.yaml`, scoped under `paths` (for example `'^/api'`), with `allow_origin`, `allow_methods` and `allow_headers` reviewed for each scope; see `cross-origin-and-browser.md` for origin policy. Owner: `backend`. Source: Symfony.

## Dependencies and operations

- **Vulnerable Composer dependencies.** Outdated framework components and libraries carry known vulnerabilities.
  Check: dependencies are kept current (`composer update` under review) and a security checker such as `symfony check:security` scans `composer.lock` regularly or in CI. Owner: `dx`. Source: Laravel, Symfony.
- **No backup and recovery plan.** Symfony recommends regular backups of the production database and critical files with a recovery plan.
  Check: infrastructure defines scheduled backups for the production database and critical files, and a documented restore procedure exists. Owner: `cloud`. Source: Symfony.
- **No production error monitoring.** Symfony recommends monitoring and error reporting to catch production issues quickly.
  Check: the deployment wires error reporting and monitoring for the production environment. Owner: `sre`. Source: Symfony.
