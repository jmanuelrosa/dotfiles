# Two-Factor Authentication (2FA)

Complete guide for Better Auth's `twoFactor` plugin: TOTP, OTP, backup codes, trusted devices, and sign-in flow.

## Setup

1. Add `twoFactor()` plugin to server config with `issuer`
2. Add `twoFactorClient()` plugin to client config
3. Run `npx @better-auth/cli migrate`
4. Verify: `twoFactorSecret` column exists on user table

```ts
// Server
import { twoFactor } from "better-auth/plugins"

export const auth = betterAuth({
  plugins: [
    twoFactor({ issuer: "My App" }),
  ],
})
```

```ts
// Client
import { createAuthClient } from "better-auth/client"
import { twoFactorClient } from "better-auth/client/plugins"

export const authClient = createAuthClient({
  plugins: [
    twoFactorClient({
      onTwoFactorRedirect() { window.location.href = "/2fa" },
    }),
  ],
})
```

## Enabling 2FA for Users

Requires password verification. Returns TOTP URI (for QR code) and backup codes.

```ts
const { data, error } = await authClient.twoFactor.enable({ password })
// data.totpURI — generate QR code from this
// data.backupCodes — display to user, store securely
```

`twoFactorEnabled` is NOT set to `true` until first TOTP verification succeeds. Override with `skipVerificationOnEnable: true` (not recommended).

2FA can only be enabled for credential (email/password) accounts.

## TOTP (Authenticator App)

### QR Code Display

```tsx
import QRCode from "react-qr-code"
const TotpSetup = ({ totpURI }: { totpURI: string }) => <QRCode value={totpURI} />
```

### Verify TOTP

```ts
const { data, error } = await authClient.twoFactor.verifyTotp({
  code,
  trustDevice: true,
})
```

Accepts codes from one period before/after current time.

### TOTP Options

```ts
twoFactor({
  totpOptions: {
    digits: 6,    // 6 or 8 (default: 6)
    period: 30,   // seconds (default: 30)
  },
})
```

## OTP (Email/SMS)

### Configure Delivery

```ts
twoFactor({
  otpOptions: {
    sendOTP: async ({ user, otp }, ctx) => {
      await sendEmail({
        to: user.email,
        subject: "Your verification code",
        text: `Your code is: ${otp}`,
      })
    },
    period: 5,            // minutes (default: 3)
    digits: 6,            // default: 6
    allowedAttempts: 5,   // default: 5
  },
})
```

### Send and Verify

- Send: `authClient.twoFactor.sendOtp()`
- Verify: `authClient.twoFactor.verifyOtp({ code, trustDevice: true })`

### OTP Storage Security

```ts
otpOptions: {
  storeOTP: "encrypted", // "plain" | "encrypted" | "hashed"
}

// Custom encryption:
otpOptions: {
  storeOTP: {
    encrypt: async (token) => myEncrypt(token),
    decrypt: async (token) => myDecrypt(token),
  },
}
```

## Backup Codes

Generated automatically when 2FA is enabled. Each code is single-use.

**Regenerate** (invalidates all previous):
```ts
const { data } = await authClient.twoFactor.generateBackupCodes({ password })
// data.backupCodes
```

**Verify for recovery:**
```ts
await authClient.twoFactor.verifyBackupCode({ code, trustDevice: true })
```

**Configuration:**
```ts
twoFactor({
  backupCodeOptions: {
    amount: 10,                  // default: 10
    length: 10,                  // default: 10
    storeBackupCodes: "encrypted", // "plain" | "encrypted"
  },
})
```

## 2FA Sign-In Flow

1. Call `signIn.email({ email, password })`
2. Check `context.data.twoFactorRedirect` in `onSuccess`
3. If `true`, redirect to `/2fa` verification page
4. Verify via TOTP, OTP, or backup code
5. Session cookie created on successful verification

```ts
const { data, error } = await authClient.signIn.email(
  { email, password },
  {
    onSuccess(context) {
      if (context.data.twoFactorRedirect) {
        window.location.href = "/2fa"
      }
    },
  }
)
```

Server-side: check `"twoFactorRedirect" in response` when using `auth.api.signInEmail`.

## Trusted Devices

Pass `trustDevice: true` when verifying. Default trust: 30 days (`trustDeviceMaxAge`). Refreshes on each sign-in.

## Security

**Session flow:** credentials → session removed → temporary 2FA cookie (10 min default) → verify → session created.

```ts
twoFactor({
  twoFactorCookieMaxAge: 600, // 10 min (default)
})
```

**Rate limiting:** built-in 3 requests per 10 seconds for all 2FA endpoints. OTP has additional attempt limiting (`allowedAttempts`).

**Encryption at rest:** TOTP secrets encrypted with auth secret. Backup codes encrypted by default. OTP configurable. Uses constant-time comparison.

## Disabling 2FA

Requires password. Revokes trusted device records:

```ts
await authClient.twoFactor.disable({ password })
```

## Complete Config Example

```ts
twoFactor({
  issuer: "My App",
  totpOptions: { digits: 6, period: 30 },
  otpOptions: {
    sendOTP: async ({ user, otp }) => {
      await sendEmail({ to: user.email, subject: "Your code", text: `Code: ${otp}` })
    },
    period: 5,
    allowedAttempts: 5,
    storeOTP: "encrypted",
  },
  backupCodeOptions: { amount: 10, length: 10, storeBackupCodes: "encrypted" },
  twoFactorCookieMaxAge: 600,
  trustDeviceMaxAge: 30 * 24 * 60 * 60,
})
```
