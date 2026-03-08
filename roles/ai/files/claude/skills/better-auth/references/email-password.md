# Email & Password: Verification, Reset, and Hashing

Detailed patterns for email verification, password reset security, and hashing configuration in Better Auth.

## Email Verification Setup

Configure `emailVerification.sendVerificationEmail` to verify user emails:

```ts
import { betterAuth } from "better-auth"
import { sendEmail } from "./email"

export const auth = betterAuth({
  emailVerification: {
    sendVerificationEmail: async ({ user, url, token }, request) => {
      await sendEmail({
        to: user.email,
        subject: "Verify your email address",
        text: `Click the link to verify your email: ${url}`,
      })
    },
  },
})
```

The `url` contains the full verification link. The `token` is available for custom verification URLs.

### Requiring Verification

Block sign-in until verified:

```ts
export const auth = betterAuth({
  emailAndPassword: {
    requireEmailVerification: true,
  },
})
```

Requires `sendVerificationEmail` to be configured. Only applies to email/password sign-ins. Unverified users receive a new verification email on each sign-in attempt.

## Password Reset Flow

### Server Config

```ts
export const auth = betterAuth({
  emailAndPassword: {
    enabled: true,
    sendResetPassword: async ({ user, url, token }, request) => {
      void sendEmail({
        to: user.email,
        subject: "Reset your password",
        text: `Click the link to reset your password: ${url}`,
      })
    },
    onPasswordReset: async ({ user }, request) => {
      console.log(`Password for user ${user.email} has been reset.`)
    },
  },
})
```

### Sending Reset Request

```ts
// Server-side
const data = await auth.api.requestPasswordReset({
  body: { email: "user@example.com", redirectTo: "https://example.com/reset-password" },
})

// Client-side
const { data, error } = await authClient.requestPasswordReset({
  email: "user@example.com",
  redirectTo: "https://example.com/reset-password",
})
```

### Security Measures

**Timing attack prevention:**
- Background email sending via `runInBackgroundOrAwait` — response time doesn't reveal if email exists
- Dummy operations on invalid requests maintain consistent timing
- Always returns: `"If this email exists in our system, check your email for the reset link"`

**Serverless platforms:** configure background task handler:

```ts
export const auth = betterAuth({
  advanced: {
    backgroundTasks: {
      handler: (promise) => { waitUntil(promise) },
    },
  },
})
```

**Token security:**
- Cryptographically random: `generateId(24)` — 24-char alphanumeric
- Expires after 1 hour (default). Configure: `resetPasswordTokenExpiresIn` (seconds)
- Single-use: deleted after successful reset

```ts
emailAndPassword: {
  resetPasswordTokenExpiresIn: 60 * 30, // 30 minutes
}
```

**Session revocation:** invalidate all sessions on password reset:

```ts
emailAndPassword: {
  revokeSessionsOnPasswordReset: true,
}
```

**Redirect URL validation:** `redirectTo` validated against `trustedOrigins`. Malicious URLs get 403.

**Password requirements:**

```ts
emailAndPassword: {
  minPasswordLength: 12,  // default: 8
  maxPasswordLength: 256, // default: 128
}
```

## Password Hashing

Default: `scrypt` (slow, memory-intensive, native Node.js, OWASP recommended when Argon2id unavailable).

### Custom Hashing (Argon2id)

```ts
import { hash, verify, type Options } from "@node-rs/argon2"

const argon2Options: Options = {
  memoryCost: 65536,  // 64 MiB
  timeCost: 3,
  parallelism: 4,
  outputLen: 32,
  algorithm: 2,       // Argon2id
}

export const auth = betterAuth({
  emailAndPassword: {
    enabled: true,
    password: {
      hash: (password) => hash(password, argon2Options),
      verify: ({ password, hash: storedHash }) => verify(storedHash, password, argon2Options),
    },
  },
})
```

**Warning:** Switching hashing algorithms on an existing system breaks sign-in for users with old hashes. Plan a migration strategy.

## Callback URLs

Always use absolute URLs (including origin) for `callbackURL` in sign-up/sign-in:

```ts
const { data, error } = await authClient.signUp.email({
  callbackURL: "https://example.com/callback", // absolute URL with origin
})
```

Prevents Better Auth from needing to infer the origin (breaks with separate frontend/backend domains).
