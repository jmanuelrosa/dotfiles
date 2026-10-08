# Ruby on Rails

When to read: the brief, diff, or assessed surface touches a Rails app: controllers and `ApplicationController` (`protect_from_forgery`, `redirect_to`, `render`), ActiveRecord query strings, ERB views (`raw`, `html_safe`, `<%==`, `link_to`), `config/routes.rb`, `config/environments/production.rb`, session store config, Devise or `devise_token_auth` setup, `Rack::Cors`, `ActionDispatch::Response.default_headers`, the `Gemfile`, or files under `config/` and `db/` that may hold credentials.
Sources (OWASP Cheat Sheet Series, CC BY-SA 4.0): [Ruby on Rails](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)

## Contents

- Code and command execution
- SQL injection
- Authorization and attack surface
- Output encoding (XSS)
- CSRF
- Redirects
- Sessions, transport and authentication
- Headers and CORS
- Sensitive files, dependencies and tooling

## Code and command execution

- **Ruby code or shell execution APIs fed with input.** `eval`, `system`, backticks, `exec`, `spawn`, `open("| ...")`, `Process.exec`, `Process.spawn`, `IO.popen` and the `IO.read`/`readlines`/`binread`/`binwrite`/`foreach`/`write` family with a leading `|` all run code or commands; using them in a Rails app is usually a bad idea.
  Check: none of these APIs receives request-derived data; where one is unavoidable, input is matched against an allowlist of possible values and validated as thoroughly as possible. Owner: `backend`. Source: Rails.
- See `injection.md` for OS command injection defenses in general.

## SQL injection

- **ActiveRecord condition string built by concatenation.** `Project.where("name like '" + name + "'")` is injectable even though ActiveRecord's hash conditions are safe.
  Check: string conditions use placeholders (`where("name like ?", value)`), `LIKE` operands pass through `ActiveRecord::Base.sanitize_sql_like`, and no SQL fragment is built from user-controlled input. Owner: `backend`. Source: Rails.

## Authorization and attack surface

- **No object-level authorization on RESTful routes.** Rails has no built-in protection against a user acting on another user's record through guessable ids.
  Check: every action that loads or modifies a record authorizes it, preferably through a resource-based access control library such as `pundit` or `cancancan`, otherwise explicitly in the controller. Owner: `backend`. Source: Rails.
- See `authorization.md` for IDOR and access control design.
- **Catch-all route exposes every controller method.** `match ':controller(/:action(/:id(.:format)))'` lets any public controller method be called as an action.
  Check: `config/routes.rb` declares explicit routes only, and no wildcard controller or action route exists. Owner: `backend`. Source: Rails.
- **User input chooses the rendered view.** Dynamic `render` paths let an attacker render arbitrary views, such as an admin page.
  Check: no `render` call takes a template, partial or file name derived from user input. Owner: `backend`. Source: Rails.

## Output encoding (XSS)

- **ERB escaping bypassed on user data.** `raw`, `<%==` and `.html_safe` mark content as safe without escaping; `html_safe` is itself unsafe despite its name.
  Check: no user-controlled value reaches `raw`, `<%==`, `.html_safe` or other helpers that change how strings are prepared for output. Owner: `frontend`. Source: Rails.
- **Users allowed to submit HTML.** Accepted HTML is a standing XSS risk, and `sanitize` has repeatedly been bypassed.
  Check: rich text uses a markup language such as Markdown or Textile with HTML disallowed; where HTML must be accepted, a Content Security Policy blocks script execution and `sanitize` with an explicit tag allowlist is a last layer, not the whole defense. Owner: `frontend`. Source: Rails.
- **User-controlled `link_to` destination.** `link_to` enforces no scheme allowlist, so a `javascript:` URL executes on click.
  Check: stored or submitted URLs rendered as links are validated to `https` or `http` before rendering, attribute escaping is kept, and CSP is not relied on as the only control. Owner: `backend`. Source: Rails.
- See `xss-and-csp.md` for context-specific encoding and CSP.

## CSRF

- **CSRF protection missing from `ApplicationController`.** Without `protect_from_forgery`, cookie-authenticated actions are forgeable.
  Check: the base `ApplicationController` declares `protect_from_forgery`; every `except:` exception is consciously justified. Owner: `backend`. Source: Rails.
- **State change on a GET action.** Rails does not apply CSRF protection to any `GET` request.
  Check: no `GET` route performs a state-changing action. Owner: `backend`. Source: Rails.
- **CSRF dropped on mixed cookie and token auth.** Only token-only authentication removes the need for CSRF protection.
  Check: controllers that skip CSRF authenticate exclusively with tokens (for example `devise_token_auth`); any path that accepts cookie authentication keeps forgery protection. Owner: `backend`. Source: Rails.

## Redirects

- **`redirect_to` with a request-supplied URL.** Open redirects enable phishing, and `redirect_to params[:to]` with a hash parameter can even produce a `javascript:` destination.
  Check: in-app redirects use `redirect_to url_from(params[:url]) || "/"` with a fixed fallback; Rails' open-redirect protection stays enabled; destinations outside the app come from a server-side map of keys to fixed URLs (for example an `ACCEPTABLE_URLS` hash). Owner: `backend`. Source: Rails.
- **Redirect validated by `URI.parse(...).path` or an unanchored regex.** `//evil.example/path` is a protocol-relative external destination, and unanchored patterns are bypassable.
  Check: validation never relies on `.path`; host checks parse with `URI.parse`, also verify `.scheme` and `.port`, and match the host against an allowlist or regexes anchored with `\A` and `\z` (not `^` and `$`). Owner: `backend`. Source: Rails.
- See `cross-origin-and-browser.md` for redirect allowlisting.

## Sessions, transport and authentication

- **Default cookie session store.** The cookie store does not expire sessions on the server, enabling replay, and exposes its contents to the client.
  Check: sensitive information is never stored in the session, and the app uses a database-backed store (`config.session_store :active_record_store`). Owner: `backend`. Source: Rails.
- See `sessions-and-cookies.md` for session expiry and rotation.
- **TLS not forced in production.** Rails enforces HTTPS, HSTS and secure cookies through one setting.
  Check: `config/environments/production.rb` sets `config.force_ssl = true`. Owner: `backend`. Source: Rails.
- **Authentication built from scratch.** Rails 8's authentication generator is a starting point that must be adapted, including its sign-up flow; Devise is the other common option.
  Check: authentication uses the Rails 8 generator (with sign-up implemented and reviewed) or Devise, and authenticated route groups are wrapped in `authenticate :user do ... end` with public routes outside it. Owner: `backend`. Source: Rails.
- **No password strength enforcement with Devise.** Devise accepts weak passwords by default.
  Check: a strength check such as `devise_zxcvbn` (`:zxcvbnable` on the model) is configured with `config.min_password_score` in `config/initializers/devise.rb` (the sheet's example uses 4). Owner: `backend`. Source: Rails.
- **Custom password hashing or encryption.** Writing your own encryption is a bad idea; Devise's bcrypt is appropriate.
  Check: password hashing uses Devise's bcrypt with `config.stretches` set for production (the sheet cites 10, with 1 only in test) and no custom crypto exists. Owner: `backend`. Source: Rails.
- **Token auth migration keeps unneeded fields.** `devise_token_auth`'s generated migration may add unnecessary or duplicate columns.
  Check: the generated migration was edited to the fields the use case needs. Owner: `database`. Source: Rails.
- See `authentication.md` for login, recovery and brute-force controls.

## Headers and CORS

- **Default security headers not set.** Rails applies `ActionDispatch::Response.default_headers` to every response.
  Check: `default_headers` sets `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff` and `X-XSS-Protection: 0`; HSTS comes from `config.force_ssl = true`; CSP is configured (for example through the `secure_headers` gem). Owner: `backend`. Source: Rails.
- See `http-headers-tls-and-caching.md` for header values.
- **CORS allowing broad origins or resources.** Cross-origin access must be granted narrowly.
  Check: `Rack::Cors` in `config/application.rb` lists only the domains allowed to call, scopes `resource` to specific paths, and restricts `:headers` and `:methods`; preflighted requests return `Access-Control-Allow-Origin` on both the `OPTIONS` and the actual response. Owner: `backend`. Source: Rails.

## Sensitive files, dependencies and tooling

- **Credential-bearing files committed.** `config/database.yml` (production credentials), `config/initializers/secret_token.rb` (session cookie secret), `db/seeds.rb` (bootstrap admin) and `db/development.sqlite3` (real data) leak through source control.
  Check: these files are excluded from the repository or hold no real secrets or data. Owner: `dx`. Source: Rails.
- See `secrets-management.md` for secret storage.
- **No dependency update process for gems.** Most gems are unsigned, and lagging Rails versions make critical patches harder.
  Check: gems are audited, and an update process exists (routine monthly or quarterly updates, weekly security triage, emergency path), backed by automated dependency scanning. Owner: `dx`. Source: Rails.
- **No Rails static analysis in CI.** Brakeman finds easily exposed issues, including XSS, and Bearer covers Ruby and JavaScript.
  Check: CI runs Brakeman (or an equivalent such as Bearer) and findings are triaged. Owner: `platform`. Source: Rails.
- See `abuse-dos-and-business-logic.md` for business logic flaws.
