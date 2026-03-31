# Rendering Reference: Re-renders, Rendering, JS Performance

Detailed patterns for sections 6-8 of the React Development Guide.

## Re-render Optimization

### Derive State During Render

```tsx
// BAD: redundant state + effect
const [fullName, setFullName] = useState('')
useEffect(() => { setFullName(firstName + ' ' + lastName) }, [firstName, lastName])

// GOOD: derive inline
const fullName = firstName + ' ' + lastName
```

### Defer State Reads

```tsx
// BAD: subscribes to all searchParams changes
const searchParams = useSearchParams()
const handleShare = () => { const ref = searchParams.get('ref'); shareChat(id, { ref }) }

// GOOD: reads on demand
const handleShare = () => { const ref = new URLSearchParams(window.location.search).get('ref'); shareChat(id, { ref }) }
```

### Memo Components with Stable Defaults

```tsx
// BAD: onClick has different value every render
const UserAvatar = memo(({ onClick = () => {} }) => { /* ... */ })

// GOOD: stable default
const NOOP = () => {}
const UserAvatar = memo(({ onClick = NOOP }) => { /* ... */ })
```

### Extract Expensive Work

```tsx
// BAD: computes avatar even when loading
function Profile({ user, loading }) {
  const avatar = useMemo(() => <Avatar id={computeAvatarId(user)} />, [user])
  if (loading) return <Skeleton />
  return <div>{avatar}</div>
}

// GOOD: skips computation when loading
const UserAvatar = memo(({ user }) => {
  const id = useMemo(() => computeAvatarId(user), [user])
  return <Avatar id={id} />
})
function Profile({ user, loading }) {
  if (loading) return <Skeleton />
  return <div><UserAvatar user={user} /></div>
}
```

Note: React Compiler makes manual `memo()`/`useMemo()` unnecessary.

### Functional setState

```tsx
// BAD: stale closure risk, unstable callback
const addItems = useCallback((newItems) => { setItems([...items, ...newItems]) }, [items])

// GOOD: always latest state, stable callback
const addItems = useCallback((newItems) => { setItems(curr => [...curr, ...newItems]) }, [])
```

### Lazy State Init

```tsx
// BAD: buildSearchIndex runs EVERY render
const [index, setIndex] = useState(buildSearchIndex(items))

// GOOD: runs only on initial render
const [index, setIndex] = useState(() => buildSearchIndex(items))
```

### Transitions

```tsx
import { startTransition } from 'react'
// Non-blocking scroll tracking
const handler = () => { startTransition(() => setScrollY(window.scrollY)) }
```

### useRef for Transient Values

```tsx
// Mouse tracking without re-renders
const lastXRef = useRef(0)
const dotRef = useRef<HTMLDivElement>(null)
useEffect(() => {
  const onMove = (e: MouseEvent) => {
    lastXRef.current = e.clientX
    if (dotRef.current) dotRef.current.style.transform = `translateX(${e.clientX}px)`
  }
  window.addEventListener('mousemove', onMove)
  return () => window.removeEventListener('mousemove', onMove)
}, [])
```

## Rendering Performance

### content-visibility

```css
.message-item {
  content-visibility: auto;
  contain-intrinsic-size: 0 80px;
}
```

For 1000 messages: browser skips layout/paint for ~990 off-screen items.

### Hydration No-Flicker

```tsx
// Inline script sets theme before React hydrates - no flash
<div id="theme-wrapper">{children}</div>
<script dangerouslySetInnerHTML={{ __html: `
  (function() {
    try {
      var theme = localStorage.getItem('theme') || 'light';
      document.getElementById('theme-wrapper').className = theme;
    } catch (e) {}
  })();
` }} />
```

### Activity Component

```tsx
import { Activity } from 'react'
<Activity mode={isOpen ? 'visible' : 'hidden'}>
  <ExpensiveMenu />
</Activity>
```

### useTransition Over Manual Loading

```tsx
// BAD: manual isLoading state
const [isLoading, setIsLoading] = useState(false)
const handleSearch = async (v) => { setIsLoading(true); const data = await fetch(v); setResults(data); setIsLoading(false) }

// GOOD: automatic pending state
const [isPending, startTransition] = useTransition()
const handleSearch = (v) => {
  setQuery(v)
  startTransition(async () => { const data = await fetchResults(v); setResults(data) })
}
```

## JavaScript Performance

### Layout Thrashing

```typescript
// BAD: interleaved reads/writes force reflows
el.style.width = '100px'
const w = el.offsetWidth  // forces reflow
el.style.height = '200px'

// GOOD: batch writes, then read
el.style.width = '100px'
el.style.height = '200px'
const { width, height } = el.getBoundingClientRect()

// BEST: use CSS classes
el.classList.add('highlighted-box')
```

### Map for Repeated Lookups

```typescript
// O(1) per lookup instead of O(n)
const userById = new Map(users.map(u => [u.id, u]))
orders.map(o => ({ ...o, user: userById.get(o.userId) }))
```

### Cache Function Results

```typescript
const slugifyCache = new Map<string, string>()
function cachedSlugify(text: string): string {
  if (slugifyCache.has(text)) return slugifyCache.get(text)!
  const result = slugify(text)
  slugifyCache.set(text, result)
  return result
}
```

### Cache Storage Reads

```typescript
const storageCache = new Map<string, string | null>()
function getLS(key: string) {
  if (!storageCache.has(key)) storageCache.set(key, localStorage.getItem(key))
  return storageCache.get(key)
}
// Invalidate on external changes
window.addEventListener('storage', (e) => { if (e.key) storageCache.delete(e.key) })
```

### Combine Iterations

```typescript
// BAD: 3 iterations
const admins = users.filter(u => u.isAdmin)
const testers = users.filter(u => u.isTester)

// GOOD: 1 iteration
const admins: User[] = [], testers: User[] = []
for (const u of users) {
  if (u.isAdmin) admins.push(u)
  if (u.isTester) testers.push(u)
}
```

### toSorted() for Immutability

```typescript
// BAD: mutates props
const sorted = users.sort((a, b) => a.name.localeCompare(b.name))

// GOOD: new array
const sorted = users.toSorted((a, b) => a.name.localeCompare(b.name))
// Also: .toReversed(), .toSpliced(), .with()
```
