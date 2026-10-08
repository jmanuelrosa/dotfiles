# Python: Django, Django REST Framework and FastAPI

When to read: the brief, diff, or assessed surface touches Django `settings.py` (`MIDDLEWARE`, `SECRET_KEY`, `DEBUG`, `SECURE_*`, `*_COOKIE_*`, `AUTH_PASSWORD_VALIDATORS`), Django views, templates or ORM raw SQL, the DRF `REST_FRAMEWORK` settings, serializers, viewsets or permission classes, FastAPI routers, `Depends()` dependencies, Pydantic models, JWT decoding, `CORSMiddleware`, exception handlers, `UploadFile`, or Uvicorn launch flags.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Django Security](https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html), [Django REST Framework](https://cheatsheetseries.owasp.org/cheatsheets/Django_REST_Framework_Cheat_Sheet.html), [FastAPI Security](https://cheatsheetseries.owasp.org/cheatsheets/FastAPI_Security_Cheat_Sheet.html)

## Contents

- Authorization and authentication enforcement
- Token verification
- Injection and code execution
- Mass assignment and data exposure
- Secrets and keys
- Debug mode and information leakage
- HTTPS, proxies and security headers
- Cookies and CSRF
- Passwords and login
- Template XSS
- CORS
- Throttling, pagination and resource exhaustion
- Logging
- Dependencies, configuration process and inventory

## Authorization and authentication enforcement

- **DRF default permission left at `AllowAny`.** DRF's default `DEFAULT_PERMISSION_CLASSES` is `rest_framework.permissions.AllowAny`, so every view is public unless changed.
  Check: `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` names restrictive classes; `AllowAny` appears only on intentionally public endpoints; every per-view `permission_classes` attribute or decorator override is deliberate and reviewed. Owner: `backend`. Source: DRF.
- **DRF `get_object()` overridden without object permission check.** An override that skips `check_object_permissions` returns any object by id.
  Check: every overridden `get_object()` calls `self.check_object_permissions(self.request, obj)` before returning. Owner: `backend`. Source: DRF.
- **DRF authentication classes overridden or missing.** Non-public endpoints must authenticate.
  Check: `DEFAULT_AUTHENTICATION_CLASSES` lists the project's intended classes; no view overrides `authentication_classes` (attribute or decorator) without a documented reason; every non-public endpoint requires authentication. Owner: `backend`. Source: DRF.
- **Django view requiring login left undecorated.** Views that need an authenticated user must enforce it.
  Check: such views use `@login_required` (or the class-based equivalent). Owner: `backend`. Source: Django.
- **FastAPI route without an authentication dependency.** FastAPI enforces nothing unless a `Depends()` dependency does.
  Check: protected routes declare an authentication dependency; routers holding protected routes set `APIRouter(dependencies=[Depends(get_current_user)])` so new routes inherit it. Owner: `backend`. Source: FastAPI.
- **FastAPI authentication mistaken for authorization.** A valid user is not necessarily allowed to perform an elevated operation, and router-level authentication does not check permissions.
  Check: privileged endpoints depend on a permission dependency (for example one that raises `HTTPException(status_code=403)` unless `current_user.is_admin`), not just on `get_current_user`. Owner: `backend`. Source: FastAPI.
- **Pydantic validation trusted as access control.** Schemas validate shape only; they do not authorize or prevent injection.
  Check: endpoints with validated bodies still perform authorization and use parameterized data access. Owner: `backend`. Source: FastAPI, DRF.

## Token verification

- **`OAuth2PasswordBearer` treated as token validation.** It only extracts the bearer token from the `Authorization` header; it does not verify it.
  Check: the dependency that consumes the token verifies signature and claims and rejects invalid credentials before returning a user. Owner: `backend`. Source: FastAPI.
- **Hand-written JWT parsing.** Custom parsing or crypto logic misses verification steps.
  Check: tokens are verified with PyJWT `jwt.decode`, not custom code. Owner: `backend`. Source: FastAPI.
- **JWT claims not required or not verified.** Presence checks alone do not validate values.
  Check: `jwt.decode` uses `options={"require": ["exp", "iss", "aud"]}` with expected `issuer` and `audience` supplied, verification left enabled, and `nbf` validated when present (required if the token profile calls for it). Owner: `backend`. Source: FastAPI.
- **Accepted JWT algorithm taken from the token.** Deriving algorithms from the header enables algorithm confusion.
  Check: `jwt.decode` passes an explicit `algorithms=[...]` list (for example `["HS256"]` for tokens issued that way). Owner: `backend`. Source: FastAPI.
- See `tokens-and-federation.md` for revocation and replay protection beyond expiry.
- **Refresh token cookie without protective attributes or CSRF defense.** Cookies are sent automatically, so refresh endpoints become CSRF targets.
  Check: refresh token cookies set `HttpOnly`, `Secure` and `SameSite=Lax` or `Strict`; refresh and other state-changing cookie-authenticated endpoints validate a CSRF token, with SameSite treated as defense in depth. Owner: `backend`. Source: FastAPI.

## Injection and code execution

- **User input in Django raw SQL APIs.** `raw()`, `extra()` and `cursor.execute()` with interpolated input are injectable.
  Check: no request data is formatted into `raw()`, `extra()` or `cursor.execute()` strings; queries use parameters or the ORM. Owner: `backend`. Source: DRF, FastAPI.
- **Unsafe YAML load.** `yaml.load()` on user-controlled YAML can execute code.
  Check: YAML parsing uses `Loader=yaml.SafeLoader` (or `yaml.safe_load`). Owner: `backend`. Source: DRF.
- **User data reaching `eval`, `exec` or pickle.** These execute attacker-supplied code.
  Check: no `eval()`, `exec()` or `execfile()` receives user input; no user-controlled data is loaded with `pickle` or `pandas.read_pickle()`. Owner: `backend`. Source: DRF.
- See `injection.md` for validating, filtering and sanitizing client and integration data.

## Mass assignment and data exposure

- **DRF serializer exposes or accepts every model field.** `Meta.exclude` and `fields = "__all__"` automatically include newly added model fields in reads and writes.
  Check: every `ModelSerializer` lists an explicit `Meta.fields` allowlist with only the fields the client needs; no `exclude` or `"__all__"`. Owner: `backend`. Source: DRF.
- **Server-controlled DRF fields writable.** Fields clients may read but must not change need explicit read-only marking.
  Check: generated or privileged fields appear in `Meta.read_only_fields`, or declared fields set `read_only=True`; authorization for the operation is still checked. Owner: `backend`. Source: DRF.
- **FastAPI input schema includes server-controlled fields.** A single model reused for input lets clients set `is_admin` or `id`; `extra="forbid"` does not block declared fields.
  Check: separate input schemas (`UserCreate`, `UserUpdate`) omit server-controlled fields, and persistence uses validated fields rather than the raw request dict. Owner: `backend`. Source: FastAPI.
- **Pydantic silently ignores unknown fields.** By default undeclared fields are dropped rather than rejected.
  Check: request models that should reject unexpected input set `model_config = ConfigDict(extra="forbid")`. Owner: `backend`. Source: FastAPI.
- **Lax type coercion in security decisions.** Pydantic converts `"123"` to `123` unless told otherwise.
  Check: fields that feed security decisions use strict types such as `StrictInt` and `StrictBool`. Owner: `backend`. Source: FastAPI.
- **FastAPI returns database objects unfiltered.** Without a response model, fields such as `password_hash` reach the client.
  Check: path decorators set `response_model` to a schema that lists only safe fields. Owner: `backend`. Source: FastAPI.

## Secrets and keys

- **Weak or default Django `SECRET_KEY`.** `SECRET_KEY` signs sessions, reset tokens and more.
  Check: the key is at least 50 characters mixing letters, digits and symbols, generated with a strong generator such as `get_random_secret_key()`, not prefixed `django-insecure-`, rotated regularly and immediately if exposed (accepting that rotation invalidates sessions and reset tokens). Owner: `backend`. Source: Django, DRF.
- **Secrets hardcoded or shipped as defaults.** Hardcoded `SECRET_KEY` values or default JWT signing keys leak through source and reach production.
  Check: `SECRET_KEY` and signing keys are read from deployment-managed storage (preferably a mounted secret file or secret manager, environment variables only when nothing safer exists, for example via Pydantic Settings), no default development key can load in production, local `.env` files with secrets are gitignored, and no default passwords are used. Owner: `backend`. Source: Django, DRF, FastAPI.
- See `secrets-management.md` for provisioning and rotation.

## Debug mode and information leakage

- **Django `DEBUG` on in production.** Debug pages expose settings and stack traces.
  Check: production settings set `DEBUG = False` and `DEBUG_PROPAGATE_EXCEPTIONS = False`. Owner: `backend`. Source: Django, DRF.
- **Empty `ALLOWED_HOSTS` in deployment.** `check --deploy` flags this as `security.W020`.
  Check: production settings define a non-empty `ALLOWED_HOSTS`. Owner: `backend`. Source: Django.
- **FastAPI validation errors echo input.** `RequestValidationError` details can include submitted passwords or tokens.
  Check: a custom `RequestValidationError` handler returns only field locations and safe descriptions (or a generic message), never `str(exc)` or the request body, and does not log secrets. Owner: `backend`. Source: FastAPI.
- **FastAPI docs and schema public by default.** `/docs`, `/redoc` and `/openapi.json` disclose the API surface.
  Check: if documentation should be private, access to all three is restricted or disabled with `FastAPI(openapi_url=None)`; every operation is still authorized regardless. Owner: `backend`. Source: FastAPI.
- **Uvicorn advertises itself.** The default `Server` header identifies the server.
  Check: Uvicorn starts with `--no-server-header`. Owner: `platform`. Source: FastAPI.

## HTTPS, proxies and security headers

- **Django `SecurityMiddleware` absent or unconfigured.** Header and HTTPS settings only apply when the middleware is installed.
  Check: `MIDDLEWARE` includes `django.middleware.security.SecurityMiddleware`; `SECURE_CONTENT_TYPE_NOSNIFF = True`; `SECURE_HSTS_SECONDS` is positive (with preload considered for the first-connection gap); `SECURE_SSL_REDIRECT = True`. Owner: `backend`. Source: Django.
- **Django clickjacking middleware missing or misordered.** `X_FRAME_OPTIONS` only applies through `XFrameOptionsMiddleware`.
  Check: `django.middleware.clickjacking.XFrameOptionsMiddleware` is in `MIDDLEWARE` after `SecurityMiddleware`, and `X_FRAME_OPTIONS` is `'DENY'` or `'SAMEORIGIN'`. Owner: `backend`. Source: Django.
- **No Content Security Policy.** Django 6.0 and later ship CSP support.
  Check: on Django 6.0+, `django.middleware.csp.ContentSecurityPolicyMiddleware` is enabled with `SECURE_CSP` (or `SECURE_CSP_REPORT_ONLY` while monitoring); earlier versions use `django-csp` or set the header otherwise. Owner: `backend`. Source: Django.
- See `xss-and-csp.md` for CSP policy design.
- **`SECURE_PROXY_SSL_HEADER` trusted without a stripping proxy.** A client can forge the header and make Django treat HTTP as HTTPS.
  Check: `SECURE_PROXY_SSL_HEADER` is set only when a trusted proxy strips client copies of the header and sets it only for HTTPS requests, and clients cannot bypass that proxy; otherwise it stays `None`. Owner: `backend`. Source: Django.
- **Uvicorn trusts forwarding headers from anyone.** `--forwarded-allow-ips="*"` lets clients spoof client address and scheme.
  Check: Uvicorn's `--forwarded-allow-ips` lists only trusted reverse proxy addresses, those proxies overwrite untrusted forwarding headers, and `--no-proxy-headers` is used when proxy headers are not needed. Owner: `platform`. Source: FastAPI.
- **Deploy checks not addressed.** `manage.py check --deploy` reports HSTS, SSL redirect, weak key, insecure cookies, `DEBUG` and `ALLOWED_HOSTS` problems.
  Check: the pipeline or release process runs `manage.py check --deploy` against production settings and its warnings are resolved or explicitly justified. Owner: `platform`. Source: Django.

## Cookies and CSRF

- **Django session or CSRF cookie sent over HTTP.** Insecure cookies can be sniffed.
  Check: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, and every `HttpResponse.set_cookie()` call passes `secure=True`. Owner: `backend`. Source: Django.
- **Django CSRF middleware or token missing.** Cookie-authenticated forms are forgeable without it.
  Check: `MIDDLEWARE` includes `django.middleware.csrf.CsrfViewMiddleware`; POST forms render `{% csrf_token %}`; AJAX calls read the token and send it with the request. Owner: `backend`. Source: Django.
- See `cross-origin-and-browser.md` for CSRF controls beyond Django's middleware.

## Passwords and login

- **Hand-rolled Django authentication.** Django's auth app provides vetted login, logout and password change views and forms.
  Check: authentication uses `django.contrib.auth` with `django.contrib.contenttypes` and `django.contrib.sessions` in `INSTALLED_APPS`. Owner: `backend`. Source: Django.
- **Password policy validators missing.** Without `AUTH_PASSWORD_VALIDATORS`, any password is accepted.
  Check: `AUTH_PASSWORD_VALIDATORS` includes `UserAttributeSimilarityValidator` (the sheet's example: `user_attributes` username, email, first_name, last_name; `max_similarity` 0.7), `MinimumLengthValidator` (`min_length` 8 in the sheet's example), `CommonPasswordValidator` and `NumericPasswordValidator`. Owner: `backend`. Source: Django.
- See `authentication.md` for current password length guidance.
- **Passwords hashed or compared by hand.** Custom hashing skips Django's configured hashers.
  Check: passwords are hashed with `make_password` and verified with `check_password` (or the auth framework), never custom code. Owner: `backend`. Source: Django.
- **No brute-force protection on login.** Django does not throttle login attempts by default.
  Check: login is protected by `django_ratelimit`, `django-axes` or an equivalent. Owner: `backend`. Source: Django.
- **Default admin path.** `admin/` is the first target of automated attacks.
  Check: `urlpatterns` mounts `admin.site.urls` at a non-default path. Owner: `backend`. Source: Django.

## Template XSS

- **Django autoescaping bypassed on user data.** `|safe` and `mark_safe` disable escaping.
  Check: templates use Django's built-in template system; `|safe` and `mark_safe` touch only trusted content, never user-controlled input. Owner: `frontend`. Source: Django.
- **Data passed to JavaScript by string interpolation.** Interpolating values into scripts breaks out of the HTML escaping context.
  Check: data handed to JavaScript in templates uses the `json_script` filter. Owner: `frontend`. Source: Django.

## CORS

- **Credentialed FastAPI CORS with wildcard origin.** Combining `allow_credentials=True` with `allow_origins=["*"]` exposes private responses to any site.
  Check: `CORSMiddleware` with `allow_credentials=True` lists explicit trusted origins; `allow_methods` and `allow_headers` list only what the client uses; endpoint authorization does not depend on CORS. Owner: `backend`. Source: FastAPI.

## Throttling, pagination and resource exhaustion

- **DRF without throttling.** DRF's `DEFAULT_THROTTLE_CLASSES` is empty by default, and its throttling is non-atomic and not a security defense.
  Check: `DEFAULT_THROTTLE_CLASSES` and `DEFAULT_THROTTLE_RATES` are set and per-view overrides reviewed, and abuse limits are also enforced at the reverse proxy or API gateway with request-size and resource limits. Owner: `backend`. Source: DRF.
- **DRF list endpoints unpaginated.** Pagination is off by default, so large querysets enable denial of service.
  Check: `DEFAULT_PAGINATION_CLASS` is set (or every list view paginates). Owner: `backend`. Source: DRF.
- **FastAPI rate limits per process only.** Limits held in each worker's memory multiply across replicas.
  Check: route limits (for example with `slowapi`) use a shared counter store such as Redis, and a reverse proxy or gateway limit backs them. Owner: `backend`. Source: FastAPI.
- See `abuse-dos-and-business-logic.md` for layered denial-of-service defenses.
- **Blocking calls inside `async def` routes.** Blocking the event loop stalls every request on that worker.
  Check: `async def` routes use async database and network clients; synchronous libraries run in `def` routes or dependencies; CPU-heavy or long jobs go to a separate worker system such as Celery, not `BackgroundTasks`, which runs in-process. Owner: `backend`. Source: FastAPI.
- **Upload size checked after parsing.** FastAPI parses multipart forms before dependencies run, so checking `UploadFile.size` is too late.
  Check: a request-body limit is enforced at the proxy or gateway (for example Nginx `client_max_body_size`) that clients cannot bypass. Owner: `platform`. Source: FastAPI.
- **Upload metadata trusted.** `UploadFile.filename` and `content_type` are client-controlled.
  Check: the filename is never used directly as a storage path and `content_type` is not taken as proof of type; see `file-upload.md`. Owner: `backend`. Source: FastAPI.
- **API reachable with unneeded HTTP verbs.** Unused methods add attack surface.
  Check: views accept only the HTTP methods they implement (for example via `http_method_names` or explicit actions). Owner: `backend`. Source: DRF.

## Logging

- **Security events not logged with user context.** Without them, malicious accounts cannot be identified.
  Check: failed authentication, denied access and input validation errors are logged with user context, in a format a log management system consumes; errors log stack trace, message and user id rather than a generic line. Owner: `backend`. Source: DRF.
- **Secrets or PII in logs.** Logs are sensitive data and need integrity protection.
  Check: log statements exclude passwords, API tokens and PII. Owner: `backend`. Source: DRF.
- See `logging-and-error-handling.md` for SIEM aggregation, alerting and log integrity.

## Dependencies, configuration process and inventory

- **Django, DRF and dependencies not kept current.** Framework vulnerabilities are disclosed and patched regularly.
  Check: an update process exists (routine monthly or quarterly updates, weekly security triage, emergency path), and new libraries are assessed for update frequency, known vulnerabilities and community health. Owner: `dx`. Source: Django, DRF.
- **No repeatable hardening or configuration assessment.** Manual configuration drifts between environments.
  Check: environments are provisioned by a repeatable hardened process, and an automated step assesses configuration in all environments. Owner: `platform`. Source: DRF.
- **No Python SAST in the pipeline.** The sheet recommends static analysis such as Bandit or Semgrep (which has Django rules).
  Check: CI runs a Python SAST tool and its findings gate or are triaged. Owner: `platform`. Source: DRF.
- **No API host inventory.** Unknown hosts and versions stay unpatched and unmonitored.
  Check: an inventory documents each API host's version, environment, intended network audience, authentication, errors, redirects, rate limiting, CORS policy and endpoints. Owner: `architect`. Source: DRF.
- See `abuse-dos-and-business-logic.md` for business logic flaws.
