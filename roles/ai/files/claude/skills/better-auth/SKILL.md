---
name: better-auth
description: >
  Better Auth configuration, setup, and best practices. Use when implementing
  authentication with Better Auth: server/client config, database adapters,
  sessions, plugins (2FA, organizations, passkey), email/password flows,
  OAuth, route handlers, hooks, or security settings. Triggers on: auth.ts,
  betterauth, better-auth, createAuthClient, twoFactor plugin, email
  verification, password reset, or MFA setup.
license: MIT
metadata:
  date: 08-March-2026
  version: "1.0.0"
  sources:
    - https://github.com/better-auth/skills/blob/main/better-auth/best-practices/SKILL.md
---

# Better Auth Guide

**Always consult [better-auth.com/docs](https://better-auth.com/docs) for latest API.**

## Quick Setup

1. Install: `npm install better-auth`
2. Set env vars: `BETTER_AUTH_SECRET` (min 32 chars) and `BETTER_AUTH_URL`
3. Create `auth.ts` with database + config
4. Create route handler for your framework
5. Run `npx @better-auth/cli@latest migrate`
6. Verify: `GET /api/auth/ok` returns `{ status: "ok" }`

## Planning Workflow

Before implementing, scan the project to detect framework, database/ORM, existing auth, and package manager. Then gather requirements:

1. **Auth methods** — email/password, social OAuth, magic link, passkey, phone
2. **Social providers** — Google, GitHub, Apple, Microsoft, Discord
3. **Email verification** — required or optional
4. **Features/plugins** — 2FA, organizations, admin, API bearer tokens, password reset
5. **Auth pages needed** — sign in, sign up, forgot/reset password, email verification
6. **UI style** — minimal, centered card, split layout, glassmorphism

Present a checklist plan and confirm before coding. Decision tree:
- **New project** → full setup from scratch
- **Adding auth** → integrate into existing structure
- **Migrating** → audit current auth, incremental migration, remove old library

## Environment Variables

```env
BETTER_AUTH_SECRET=<generate: openssl rand -base64 32>
BETTER_AUTH_URL=http://localhost:3000
DATABASE_URL=<connection string>
```

Only define `baseURL`/`secret` in config if env vars are NOT set. Add OAuth secrets as needed: `GITHUB_CLIENT_ID`, `GOOGLE_CLIENT_ID`, etc.

## Core Config (auth.ts)

Located at `lib/auth.ts` or `src/lib/auth.ts`. CLI searches `./`, `./lib`, `./utils`, `./src`.

| Option | Notes |
|---|---|
| `appName` | Optional display name |
| `baseURL` | Only if `BETTER_AUTH_URL` not set |
| `basePath` | Default `/api/auth`. Set `/` for root |
| `secret` | Only if `BETTER_AUTH_SECRET` not set |
| `database` | Required. See adapters below |
| `secondaryStorage` | Redis/KV for sessions & rate limits |
| `emailAndPassword` | `{ enabled: true }` to activate |
| `socialProviders` | `{ google: { clientId, clientSecret }, ... }` |
| `plugins` | Array of plugins |
| `trustedOrigins` | CSRF whitelist |

**Type safety:** `export type Session = typeof auth.$Infer.Session`
For separate client/server: `createAuthClient<typeof auth>()`.

## Database Adapters

| Database | Setup |
|---|---|
| SQLite | Pass `better-sqlite3` or `bun:sqlite` instance directly |
| PostgreSQL | Pass `pg.Pool` instance directly |
| MySQL | Pass `mysql2` pool directly |
| Prisma | `prismaAdapter(prisma, { provider: "postgresql" })` from `better-auth/adapters/prisma` |
| Drizzle | `drizzleAdapter(db, { provider: "pg" })` from `better-auth/adapters/drizzle` |
| MongoDB | `mongodbAdapter(db)` from `better-auth/adapters/mongodb` |

**Critical:** Use ORM model name, NOT DB table name. Prisma model `User` mapping to table `users` → use `modelName: "user"`.

## CLI Commands

| Command | Purpose |
|---|---|
| `npx @better-auth/cli@latest migrate` | Apply schema (built-in adapter) |
| `npx @better-auth/cli@latest generate --output prisma/schema.prisma` | Generate for Prisma, then `npx prisma migrate dev` |
| `npx @better-auth/cli@latest generate --output src/db/auth-schema.ts` | Generate for Drizzle, then `npx drizzle-kit push` |
| `npx @better-auth/cli mcp --cursor` | Add MCP to AI tools |

**Re-run after adding/changing plugins.**

## Route Handlers

| Framework | File | Handler |
|---|---|---|
| Next.js App Router | `app/api/auth/[...all]/route.ts` | `toNextJsHandler(auth)` → export `{ GET, POST }` |
| Next.js Pages | `pages/api/auth/[...all].ts` | `toNextJsHandler(auth)` → default export |
| Express | Any file | `app.all("/api/auth/*", toNodeHandler(auth))` |
| SvelteKit | `src/hooks.server.ts` | `svelteKitHandler(auth)` |
| SolidStart | Route file | `solidStartHandler(auth)` |
| Hono | Route file | `auth.handler(c.req.raw)` |

**Next.js Server Components:** Add `nextCookies()` plugin to auth config.

## Client Setup

Import by framework:

| Framework | Import |
|---|---|
| React/Next.js | `better-auth/react` |
| Vue | `better-auth/vue` |
| Svelte | `better-auth/svelte` |
| Solid | `better-auth/solid` |
| Vanilla JS | `better-auth/client` |

Key exports: `signIn`, `signUp`, `signOut`, `useSession`, `getSession`.
Client plugins go in `createAuthClient({ plugins: [...] })`.

## Session Management

**Storage priority:**
1. `secondaryStorage` defined → sessions go there (not DB)
2. Set `session.storeSessionInDatabase: true` to also persist to DB
3. No database + `cookieCache` → fully stateless mode

**Cookie cache strategies:** `compact` (default, smallest), `jwt` (readable, signed), `jwe` (encrypted).

**Key options:** `session.expiresIn` (default 7 days), `session.updateAge` (refresh interval), `session.cookieCache.maxAge`, `session.cookieCache.version` (change to invalidate all).

**Custom session fields are NOT cached** — always re-fetched from DB.

## User & Account

- `user.additionalFields` — extend user schema
- `user.changeEmail.enabled` / `user.deleteUser.enabled` — disabled by default
- `account.accountLinking.enabled` — multi-provider linking
- `account.storeAccountCookie` — for stateless OAuth
- Required for registration: `email` and `name`

## Email & Password

Enable with `emailAndPassword: { enabled: true }`.

- **Email verification:** configure `emailVerification.sendVerificationEmail` callback
- **Require verification:** `emailAndPassword.requireEmailVerification: true` blocks sign-in until verified
- **Password reset:** configure `emailAndPassword.sendResetPassword` callback
- **Callback URLs:** always use absolute URLs (including origin) to prevent inference issues

For detailed email verification, password reset security, and hashing config, see `references/email-password.md`.

## Plugins

**Import from dedicated paths for tree-shaking:**
```ts
import { twoFactor } from "better-auth/plugins/two-factor"
```
NOT `from "better-auth/plugins"`.

| Plugin | Server Import | Client Import | Purpose |
|---|---|---|---|
| `twoFactor` | `better-auth/plugins` | `twoFactorClient` | TOTP/OTP 2FA |
| `organization` | `better-auth/plugins` | `organizationClient` | Teams/orgs |
| `admin` | `better-auth/plugins` | `adminClient` | User management |
| `bearer` | `better-auth/plugins` | — | API token auth |
| `passkey` | `@better-auth/passkey` | `passkeyClient` | WebAuthn |
| `sso` | `@better-auth/sso` | — | Enterprise SSO |
| `openAPI` | `better-auth/plugins` | — | API docs |

**Scoped packages:** `@better-auth/passkey`, `@better-auth/sso`, `@better-auth/stripe`, `@better-auth/scim`, `@better-auth/expo`.

**Pattern:** Server plugin + client plugin + run migrations.

For 2FA setup (TOTP, OTP, backup codes, trusted devices), see `references/two-factor.md`.

## Hooks

**Endpoint hooks:** `hooks.before` / `hooks.after` — array of `{ matcher, handler }`. Use `createAuthMiddleware`. Access `ctx.path`, `ctx.context.returned` (after), `ctx.context.session`.

**Database hooks:** `databaseHooks.user.create.before/after`, same for `session`, `account`.

**Hook context:** `session`, `secret`, `authCookies`, `password.hash()`/`verify()`, `adapter`, `internalAdapter`, `generateId()`, `tables`, `baseURL`.

## Auth UI Flows

**Sign in:** `signIn.email({ email, password })` or `signIn.social({ provider, callbackURL })`. Handle `error`, redirect on success.

**Session check (client):** `useSession()` returns `{ data: session, isPending }`.
**Session check (server):** `auth.api.getSession({ headers: await headers() })`.
**Protected routes:** check session, redirect to `/sign-in` if null.

## Security

**Advanced options:**
- `advanced.useSecureCookies` — force HTTPS cookies (enable in prod)
- `advanced.crossSubDomainCookies.enabled` — share across subdomains
- `advanced.ipAddress.ipAddressHeaders` — custom IP headers for proxies
- `advanced.database.generateId` — custom ID generation or `"serial"`/`"uuid"`/`false`
- `advanced.disableCSRFCheck` / `disableOriginCheck` — security risk, avoid

**Rate limiting:** `rateLimit.enabled`, `rateLimit.window`, `rateLimit.max`, `rateLimit.storage` (`"memory"` | `"database"` | `"secondary-storage"`).

### Security Checklist

- [ ] `BETTER_AUTH_SECRET` set (32+ chars)
- [ ] `advanced.useSecureCookies: true` in production
- [ ] `trustedOrigins` configured
- [ ] Rate limits enabled
- [ ] Email verification enabled
- [ ] Password reset implemented
- [ ] 2FA for sensitive apps
- [ ] CSRF protection NOT disabled
- [ ] `account.accountLinking` reviewed

## Troubleshooting

| Issue | Fix |
|---|---|
| "Secret not set" | Add `BETTER_AUTH_SECRET` env var |
| "Invalid Origin" | Add domain to `trustedOrigins` |
| Cookies not setting | Check `baseURL` matches domain; enable secure cookies in prod |
| OAuth callback errors | Verify redirect URIs in provider dashboard |
| Type errors after adding plugin | Re-run CLI generate/migrate |
| Model vs table name confusion | Config uses ORM model name, not DB table name |
| Sessions not in DB | `secondaryStorage` takes priority; set `storeSessionInDatabase: true` |
| Custom session fields missing | Cookie cache doesn't include custom fields; always re-fetched |

## Resources

- [Docs](https://better-auth.com/docs) | [Options Reference](https://better-auth.com/docs/reference/options) | [LLMs.txt](https://better-auth.com/llms.txt)
- [GitHub](https://github.com/better-auth/better-auth) | [Examples](https://github.com/better-auth/examples)
- [Plugins](https://better-auth.com/docs/concepts/plugins) | [CLI](https://better-auth.com/docs/concepts/cli) | [Migration Guides](https://better-auth.com/docs/guides)
