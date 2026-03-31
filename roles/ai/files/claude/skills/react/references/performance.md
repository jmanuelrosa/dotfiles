# Performance Reference: Waterfalls, Bundle, Server-Side

Detailed patterns for sections 2-4 of the React Development Guide.

## Eliminating Waterfalls

### Defer Await

```typescript
// BAD: blocks both branches
async function handleRequest(userId: string, skip: boolean) {
  const userData = await fetchUserData(userId)
  if (skip) return { skipped: true }
  return processUserData(userData)
}

// GOOD: only blocks when needed
async function handleRequest(userId: string, skip: boolean) {
  if (skip) return { skipped: true }
  const userData = await fetchUserData(userId)
  return processUserData(userData)
}
```

### Dependency-Based Parallelization

```typescript
// With better-all: config and profile run in parallel
import { all } from 'better-all'
const { user, config, profile } = await all({
  async user() { return fetchUser() },
  async config() { return fetchConfig() },
  async profile() { return fetchProfile((await this.$.user).id) }
})

// Without extra deps: promise chaining
const userPromise = fetchUser()
const profilePromise = userPromise.then(user => fetchProfile(user.id))
const [user, config, profile] = await Promise.all([userPromise, fetchConfig(), profilePromise])
```

### API Route Parallelization

```typescript
// GOOD: start immediately, await late
export async function GET(request: Request) {
  const sessionPromise = auth()
  const configPromise = fetchConfig()
  const session = await sessionPromise
  const [config, data] = await Promise.all([configPromise, fetchData(session.user.id)])
  return Response.json({ data, config })
}
```

### Suspense Streaming

```tsx
// Layout renders immediately, data streams in
function Page() {
  return (
    <div>
      <Sidebar />
      <Header />
      <Suspense fallback={<Skeleton />}>
        <DataDisplay />
      </Suspense>
      <Footer />
    </div>
  )
}
async function DataDisplay() {
  const data = await fetchData()
  return <div>{data.content}</div>
}

// Share promise across components
function Page() {
  const dataPromise = fetchData()
  return (
    <Suspense fallback={<Skeleton />}>
      <DataDisplay dataPromise={dataPromise} />
      <DataSummary dataPromise={dataPromise} />
    </Suspense>
  )
}
function DataDisplay({ dataPromise }: { dataPromise: Promise<Data> }) {
  const data = use(dataPromise)
  return <div>{data.content}</div>
}
```

Don't use Suspense for: SEO-critical above-fold content, small fast queries, layout-dependent data.

## Bundle Size

### Barrel Imports

```tsx
// BAD: loads 1,583 modules
import { Check, X, Menu } from 'lucide-react'

// GOOD: loads 3 modules
import Check from 'lucide-react/dist/esm/icons/check'
import X from 'lucide-react/dist/esm/icons/x'
import Menu from 'lucide-react/dist/esm/icons/menu'

// Alternative: Next.js 13.5+
// next.config.js
module.exports = {
  experimental: { optimizePackageImports: ['lucide-react', '@mui/material'] }
}
```

Common offenders: `lucide-react`, `@mui/material`, `@mui/icons-material`, `@tabler/icons-react`, `react-icons`, `lodash`, `date-fns`, `rxjs`.

### Dynamic Imports

```tsx
import dynamic from 'next/dynamic'
const MonacoEditor = dynamic(() => import('./monaco-editor').then(m => m.MonacoEditor), { ssr: false })
```

### Defer Third-Party

```tsx
const Analytics = dynamic(() => import('@vercel/analytics/react').then(m => m.Analytics), { ssr: false })
```

### Conditional Loading

```tsx
useEffect(() => {
  if (enabled && !frames && typeof window !== 'undefined') {
    import('./animation-frames.js').then(mod => setFrames(mod.frames)).catch(() => setEnabled(false))
  }
}, [enabled, frames, setEnabled])
```

### Preload on Intent

```tsx
const preload = () => { if (typeof window !== 'undefined') void import('./monaco-editor') }
<button onMouseEnter={preload} onFocus={preload} onClick={onClick}>Open Editor</button>
```

## Server-Side Performance

### Auth Server Actions

```typescript
'use server'
export async function deleteUser(userId: string) {
  const session = await verifySession()
  if (!session) throw unauthorized('Must be logged in')
  if (session.user.role !== 'admin' && session.user.id !== userId) throw unauthorized('Cannot delete other users')
  await db.user.delete({ where: { id: userId } })
}
```

Always validate input with zod/similar before performing mutations.

### React.cache()

```typescript
import { cache } from 'react'
export const getCurrentUser = cache(async () => {
  const session = await auth()
  if (!session?.user?.id) return null
  return await db.user.findUnique({ where: { id: session.user.id } })
})
```

Uses `Object.is` for args - inline objects always miss. Pass same reference or primitives.
Next.js auto-deduplicates `fetch`; use `React.cache()` for DB queries, auth checks, computations.

### LRU Cache

```typescript
import { LRUCache } from 'lru-cache'
const cache = new LRUCache<string, any>({ max: 1000, ttl: 5 * 60 * 1000 })

export async function getUser(id: string) {
  const cached = cache.get(id)
  if (cached) return cached
  const user = await db.user.findUnique({ where: { id } })
  cache.set(id, user)
  return user
}
```

Especially effective with Vercel Fluid Compute (shared function instances).

### Minimize RSC Serialization

```tsx
// BAD: serializes 50 fields
<Profile user={user} />

// GOOD: serializes 1 field
<Profile name={user.name} />
```

Don't transform arrays in RSC - `.toSorted()`, `.filter()`, `.map()` create new refs that duplicate serialization. Do transforms in client.

### Parallel RSC Fetching

```tsx
// BAD: sequential - Sidebar waits for Header fetch
async function Page() {
  const header = await fetchHeader()
  return <div><div>{header}</div><Sidebar /></div>
}

// GOOD: parallel - siblings fetch simultaneously
function Page() {
  return <div><Header /><Sidebar /></div>
}
async function Header() { const data = await fetchHeader(); return <div>{data}</div> }
async function Sidebar() { const items = await fetchSidebarItems(); return <nav>{items.map(renderItem)}</nav> }
```

### after() for Non-Blocking Ops

```tsx
import { after } from 'next/server'
export async function POST(request: Request) {
  await updateDatabase(request)
  after(async () => { /* logging, analytics, notifications */ })
  return Response.json({ status: 'success' })
}
```
